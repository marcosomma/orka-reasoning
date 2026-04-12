#!/usr/bin/env python3
"""
OrKa Brain Benchmark v2 — Execution Runner
=============================================

Run brain-enabled and brainless benchmark conditions (Phases 1 & 2 only).
Judge evaluation and aggregation are handled by the standalone scripts
``judge_benchmark.py`` and ``aggregate_benchmark.py``.

Tracks:
  A — Cross-Domain Skill Transfer       (50 tasks × 2 = 100 runs)
  B — Anti-Pattern Avoidance            (50 tasks × 2 = 100 runs)
  C — GraphScout Brain-Assisted Routing (50 tasks × 2 = 100 runs)
  D — Multi-Skill Composition           (50 tasks × 2 = 100 runs)
  E — Longitudinal Learning Curve       (50 tasks × 2 = 100 runs)

  Total: up to 500 execution runs (750 with baseline)

Prerequisites:
  - Redis running: orka-start
  - LM Studio running on localhost:1234 with model loaded
  - conda activate orka_0.9.12

Usage:
  python run_benchmark_v2.py                                    # full run
  python run_benchmark_v2.py --track A                          # single track
  python run_benchmark_v2.py --track C --track E                # subset
  python run_benchmark_v2.py --skip-brainless                   # brain only
  python run_benchmark_v2.py --skip-brain                       # brainless only
  python run_benchmark_v2.py --include-baseline                 # add single-pass baseline
  python run_benchmark_v2.py --exclude-tracks C                 # skip Track C
  python run_benchmark_v2.py --id track_a_05                    # single task
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orka.orchestrator import Orchestrator  # noqa: E402

logger = logging.getLogger("benchmark_v2")

# ── Paths ────────────────────────────────────────────────────────────
BENCHMARK_DIR = Path(__file__).resolve().parent
DATASET_PATH = BENCHMARK_DIR / "benchmark_v2_dataset.json"

# Track → workflow mapping
BRAIN_WORKFLOWS: dict[str, str] = {
    "A": str(BENCHMARK_DIR / "brain_track_a.yml"),
    "B": str(BENCHMARK_DIR / "brain_track_b.yml"),
    "C": str(BENCHMARK_DIR / "brain_track_c.yml"),
    "D": str(BENCHMARK_DIR / "brain_track_d.yml"),
    "E": str(BENCHMARK_DIR / "brain_track_e.yml"),
}

BRAINLESS_WORKFLOWS: dict[str, str] = {
    "A": str(BENCHMARK_DIR / "brainless_track_a.yml"),
    "B": str(BENCHMARK_DIR / "brainless_track_b.yml"),
    "C": str(BENCHMARK_DIR / "brainless_track_c.yml"),
    "D": str(BENCHMARK_DIR / "brainless_track_d.yml"),
    "E": str(BENCHMARK_DIR / "brainless_track_e.yml"),
}

BASELINE_WORKFLOWS: dict[str, str] = {
    "A": str(BENCHMARK_DIR / "baseline_track_a.yml"),
    "B": str(BENCHMARK_DIR / "baseline_track_b.yml"),
    "D": str(BENCHMARK_DIR / "baseline_track_d.yml"),
    "E": str(BENCHMARK_DIR / "baseline_track_e.yml"),
}

ALL_TRACKS = ["A", "B", "C", "D", "E"]


# ── Dataset loading ─────────────────────────────────────────────────


def load_dataset(
    tracks: list[str] | None = None,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load the benchmark dataset, optionally filtering by track(s) or task_id."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks: list[dict[str, Any]] = data["tasks"]
    if task_id:
        tasks = [t for t in tasks if t["task_id"] == task_id]
    elif tracks:
        upper = [t.upper() for t in tracks]
        tasks = [t for t in tasks if t["track"] in upper]
    return tasks


def build_input_for_task(task: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON input payload for a single task."""
    payload: dict[str, Any] = {
        "domain": task.get("domain", "general"),
    }

    # Track A: task description + execution trace for learn phase
    if task["track"] == "A":
        payload["task"] = task.get("task", task.get("title", ""))
        if task.get("execution_trace"):
            payload["execution_trace"] = task["execution_trace"]
        if task.get("outcome"):
            payload["outcome"] = task["outcome"]

    # Track B: anti-pattern for seed, or task for test
    elif task["track"] == "B":
        if task.get("anti_pattern"):
            payload["anti_pattern"] = task["anti_pattern"]
        payload["task"] = task.get("task", task.get("title", ""))

    # Track C: path skill + anti-pattern for seed, or task for route
    elif task["track"] == "C":
        if task.get("path_skill"):
            payload["path_skill"] = task["path_skill"]
        if task.get("anti_pattern"):
            payload["anti_pattern"] = task["anti_pattern"]
        payload["task"] = task.get("task", task.get("title", ""))

    # Track D: recipe + anti-pattern + path for seed, or task for compose
    elif task["track"] == "D":
        if task.get("recipe"):
            payload["recipe"] = task["recipe"]
        if task.get("anti_pattern"):
            payload["anti_pattern"] = task["anti_pattern"]
        if task.get("path_skill"):
            payload["path_skill"] = task["path_skill"]
        payload["task"] = task.get("task", task.get("title", ""))

    # Track E: sequential architecture reviews
    elif task["track"] == "E":
        payload["task"] = task.get("task", "")
        payload["sequence"] = task.get("sequence", 0)

    return payload


# ── Execution ────────────────────────────────────────────────────────


def _build_agent_outputs(logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a dict of agent_id → output from execution logs."""
    outputs: dict[str, Any] = {}
    for log in logs:
        if not isinstance(log, dict):
            continue
        agent_id = log.get("agent_id", "")
        if not agent_id or log.get("event_type") == "MetaReport":
            continue
        payload = log.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if "result" in payload:
            outputs[agent_id] = payload["result"]
        elif "response" in payload:
            outputs[agent_id] = {
                "response": payload["response"],
                "confidence": payload.get("confidence", "0.0"),
                "internal_reasoning": payload.get("internal_reasoning", ""),
            }
    return outputs


async def run_single_task(
    workflow: str,
    task_input: dict[str, Any],
    task_id: str,
    condition: str,
) -> dict[str, Any]:
    """Execute a single workflow on one task and return the result."""
    logger.info("[%s] Running %s ...", condition, task_id)
    start = time.perf_counter()
    try:
        orchestrator = Orchestrator(workflow)
        logs = await orchestrator.run(task_input, return_logs=True)
        elapsed = time.perf_counter() - start
        agent_outputs = _build_agent_outputs(logs if isinstance(logs, list) else [])

        # Extract the task_result output as the primary output
        output = agent_outputs.get("task_result", agent_outputs)

        logger.info("[%s] %s completed in %.1fs", condition, task_id, elapsed)
        return {
            "task_id": task_id,
            "condition": condition,
            "elapsed_s": round(elapsed, 2),
            "success": True,
            "output": output,
            "agent_outputs": agent_outputs,
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.error("[%s] %s FAILED after %.1fs: %s", condition, task_id, elapsed, exc)
        return {
            "task_id": task_id,
            "condition": condition,
            "elapsed_s": round(elapsed, 2),
            "success": False,
            "error": str(exc),
            "output": None,
            "agent_outputs": {},
        }


def save_result(results_dir: Path, result: dict[str, Any]) -> None:
    """Save a single task result to disk."""
    condition_dir = results_dir / result["condition"]
    condition_dir.mkdir(parents=True, exist_ok=True)
    out_path = condition_dir / f"{result['task_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)


def flush_redis_brain() -> None:
    """Flush brain-related Redis keys so each condition starts clean."""
    try:
        import redis as redis_lib

        r = redis_lib.Redis(host="localhost", port=6380, decode_responses=True)
        keys = r.keys("orka:brain:*")
        if keys:
            r.delete(*keys)
            logger.info("Flushed %d brain Redis keys", len(keys))
        else:
            logger.info("No brain keys to flush")
    except Exception as exc:
        logger.warning("Could not flush Redis brain keys: %s", exc)


# ── Main pipeline ───────────────────────────────────────────────────


async def run_benchmark(
    tracks: list[str] | None = None,
    exclude_tracks: list[str] | None = None,
    results_dir: Path | None = None,
    skip_brainless: bool = False,
    skip_brain: bool = False,
    include_baseline: bool = False,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Run the benchmark execution pipeline (Phases 1 & 2 only).

    Judge evaluation and aggregation are handled by the standalone scripts
    ``judge_benchmark.py`` and ``aggregate_benchmark.py``.
    """
    if results_dir is None:
        results_dir = BENCHMARK_DIR / "results"
    results_dir = results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    active_tracks = [t.upper() for t in (tracks or ALL_TRACKS)]
    if exclude_tracks:
        excluded = [t.upper() for t in exclude_tracks]
        active_tracks = [t for t in active_tracks if t not in excluded]

    tasks = load_dataset(tracks=active_tracks, task_id=task_id)
    logger.info("Loaded %d tasks (tracks=%s)", len(tasks), active_tracks)

    timings: dict[str, float] = {}

    tasks_by_track: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        tasks_by_track.setdefault(t["track"], []).append(t)

    # ── Phase 1: Brainless condition ──────────────────────────────
    if not skip_brainless:
        print(f"\n{'═' * 72}")
        print("  PHASE 1: BRAINLESS CONDITION")
        print(f"{'═' * 72}")
        t0 = time.perf_counter()

        for track in active_tracks:
            track_tasks = tasks_by_track.get(track, [])
            if not track_tasks:
                continue
            workflow = BRAINLESS_WORKFLOWS.get(track)
            if not workflow:
                logger.warning("No brainless workflow for track %s", track)
                continue

            print(f"\n  ── Track {track}: {len(track_tasks)} tasks ──")
            flush_redis_brain()

            for i, task in enumerate(track_tasks, 1):
                task_input = build_input_for_task(task)
                result = await run_single_task(
                    workflow, task_input, task["task_id"], "brainless"
                )
                save_result(results_dir, result)
                status = "✓" if result["success"] else "✗"
                print(
                    f"    {status} [{i:>3}/{len(track_tasks)}] {task['task_id']} "
                    f"({result['elapsed_s']:.1f}s)"
                )

        timings["brainless_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 2: Brain condition ─────────────────────────────────
    if not skip_brain:
        print(f"\n{'═' * 72}")
        print("  PHASE 2: BRAIN CONDITION")
        print(f"{'═' * 72}")
        t0 = time.perf_counter()

        for track in active_tracks:
            track_tasks = tasks_by_track.get(track, [])
            if not track_tasks:
                continue
            workflow = BRAIN_WORKFLOWS.get(track)
            if not workflow:
                logger.warning("No brain workflow for track %s", track)
                continue

            print(f"\n  ── Track {track}: {len(track_tasks)} tasks ──")
            flush_redis_brain()

            for i, task in enumerate(track_tasks, 1):
                task_input = build_input_for_task(task)
                result = await run_single_task(
                    workflow, task_input, task["task_id"], "brain"
                )
                save_result(results_dir, result)
                status = "✓" if result["success"] else "✗"
                print(
                    f"    {status} [{i:>3}/{len(track_tasks)}] {task['task_id']} "
                    f"({result['elapsed_s']:.1f}s)"
                )

        timings["brain_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 2b: Baseline condition (optional) ──────────────────
    if include_baseline:
        print(f"\n{'═' * 72}")
        print("  PHASE 2b: SINGLE-PASS BASELINE")
        print(f"{'═' * 72}")
        t0 = time.perf_counter()

        for track in active_tracks:
            track_tasks = tasks_by_track.get(track, [])
            if not track_tasks:
                continue
            workflow = BASELINE_WORKFLOWS.get(track)
            if not workflow:
                logger.info("No baseline workflow for track %s, skipping", track)
                continue

            print(f"\n  ── Track {track}: {len(track_tasks)} tasks ──")
            flush_redis_brain()

            for i, task in enumerate(track_tasks, 1):
                task_input = build_input_for_task(task)
                result = await run_single_task(
                    workflow, task_input, task["task_id"], "baseline"
                )
                save_result(results_dir, result)
                status = "✓" if result["success"] else "✗"
                print(
                    f"    {status} [{i:>3}/{len(track_tasks)}] {task['task_id']} "
                    f"({result['elapsed_s']:.1f}s)"
                )

        timings["baseline_total"] = round(time.perf_counter() - t0, 2)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  EXECUTION COMPLETE")
    print(f"{'═' * 72}")
    for phase, elapsed in timings.items():
        print(f"  {phase}: {elapsed:.0f}s ({elapsed / 60:.1f}m)")
    total = sum(timings.values())
    print(f"  Total: {total:.0f}s ({total / 60:.1f}m)")
    print(f"\n  Results in: {results_dir}")
    print(f"\n  Next steps:")
    print(f"    python judge_benchmark.py --output-tag local")
    print(f"    python aggregate_benchmark.py --judge-tag local")
    print(f"{'═' * 72}\n")

    return {"timings": timings, "tracks": active_tracks, "results_dir": str(results_dir)}


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="OrKa Brain Benchmark v2 — Execution Runner")
    parser.add_argument(
        "--track",
        choices=ALL_TRACKS,
        action="append",
        default=None,
        help="Run only specific track(s). Can be repeated: --track A --track C",
    )
    parser.add_argument(
        "--exclude-tracks",
        type=str,
        default=None,
        help="Comma-separated tracks to exclude (e.g. C or A,C)",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        help="Run a single task by task_id (e.g. track_a_05)",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Directory for results (default: benchmark_v2/results/)",
    )
    parser.add_argument(
        "--skip-brainless",
        action="store_true",
        help="Skip brainless condition (re-run brain only)",
    )
    parser.add_argument(
        "--skip-brain",
        action="store_true",
        help="Skip brain condition (brainless only or for baseline runs)",
    )
    parser.add_argument(
        "--include-baseline",
        action="store_true",
        help="Also run single-pass baseline condition",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    exclude_tracks = args.exclude_tracks.split(",") if args.exclude_tracks else None

    asyncio.run(
        run_benchmark(
            tracks=args.track,
            exclude_tracks=exclude_tracks,
            results_dir=args.results_dir,
            skip_brainless=args.skip_brainless,
            skip_brain=args.skip_brain,
            include_baseline=args.include_baseline,
            task_id=args.id,
        )
    )


if __name__ == "__main__":
    main()
