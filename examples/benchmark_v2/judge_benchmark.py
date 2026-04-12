#!/usr/bin/env python3
"""
OrKa Brain Benchmark v2 — Standalone Judge Runner
===================================================

Score existing benchmark results using a pluggable judge workflow.
Reads execution results from ``results/{brain,brainless}/`` and writes
judge scores to ``results/judge_rubric_{tag}/`` and
``results/judge_pairwise_{tag}/``.

Usage::

    # Default local judge (DeepSeek R1)
    python judge_benchmark.py --output-tag local

    # GPT-4 as judge
    python judge_benchmark.py --judge-workflow judge_rubric_gpt4.yml \\
                              --pairwise-workflow judge_pairwise_gpt4.yml \\
                              --output-tag gpt4

    # Resume after crash
    python judge_benchmark.py --output-tag local --skip-existing
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orka.orchestrator import Orchestrator  # noqa: E402

logger = logging.getLogger("judge_benchmark")

BENCHMARK_DIR = Path(__file__).resolve().parent
DATASET_PATH = BENCHMARK_DIR / "benchmark_v2_dataset.json"
ALL_TRACKS = ["A", "B", "C", "D", "E"]


# ── Shared utilities ────────────────────────────────────────────────


def load_dataset(
    tracks: list[str] | None = None,
    task_id: str | None = None,
) -> list[dict[str, Any]]:
    """Load the benchmark dataset, optionally filtering by track(s)."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks: list[dict[str, Any]] = data["tasks"]
    if task_id:
        tasks = [t for t in tasks if t["task_id"] == task_id]
    elif tracks:
        upper = [t.upper() for t in tracks]
        tasks = [t for t in tasks if t["track"] in upper]
    return tasks


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


def save_result(results_dir: Path, result: dict[str, Any]) -> None:
    """Save a single judge result to disk."""
    condition_dir = results_dir / result.get("condition", "")
    condition_dir.mkdir(parents=True, exist_ok=True)
    out_path = condition_dir / f"{result['task_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)


# ── Judge execution ─────────────────────────────────────────────────


async def run_rubric_judge(
    task: dict[str, Any],
    output: Any,
    workflow_path: str,
) -> dict[str, Any]:
    """Run the rubric judge on a single output."""
    judge_input = {
        "domain": task.get("domain", "general"),
        "task": task.get("task", task.get("title", "")),
        "track": task.get("track", ""),
        "output": output if isinstance(output, str) else json.dumps(output, default=str),
    }
    try:
        orchestrator = Orchestrator(workflow_path)
        logs = await orchestrator.run(judge_input, return_logs=True)
        agent_outputs = _build_agent_outputs(logs if isinstance(logs, list) else [])
        scores = agent_outputs.get("rubric_judge", agent_outputs)
        return {"task_id": task["task_id"], "success": True, "scores": scores}
    except Exception as exc:
        logger.error("Rubric judge failed for %s: %s", task["task_id"], exc)
        return {"task_id": task["task_id"], "success": False, "error": str(exc)}


async def run_pairwise_judge(
    task: dict[str, Any],
    brain_output: Any,
    brainless_output: Any,
    workflow_path: str,
) -> dict[str, Any]:
    """Run the pairwise judge with randomized A/B assignment."""
    if random.random() < 0.5:
        output_a, output_b = brain_output, brainless_output
        label_a, label_b = "brain", "brainless"
    else:
        output_a, output_b = brainless_output, brain_output
        label_a, label_b = "brainless", "brain"

    judge_input = {
        "domain": task.get("domain", "general"),
        "task": task.get("task", task.get("title", "")),
        "track": task.get("track", ""),
        "output_a": output_a if isinstance(output_a, str) else json.dumps(output_a, default=str),
        "output_b": output_b if isinstance(output_b, str) else json.dumps(output_b, default=str),
    }
    try:
        orchestrator = Orchestrator(workflow_path)
        logs = await orchestrator.run(judge_input, return_logs=True)
        agent_outputs = _build_agent_outputs(logs if isinstance(logs, list) else [])
        verdict = agent_outputs.get("pairwise_judge", agent_outputs)
        return {
            "task_id": task["task_id"],
            "success": True,
            "label_a": label_a,
            "label_b": label_b,
            "verdict": verdict,
        }
    except Exception as exc:
        logger.error("Pairwise judge failed for %s: %s", task["task_id"], exc)
        return {"task_id": task["task_id"], "success": False, "error": str(exc)}


# ── Main pipeline ───────────────────────────────────────────────────


async def judge_benchmark(
    results_dir: Path,
    rubric_workflow: str,
    pairwise_workflow: str,
    output_tag: str,
    tracks: list[str] | None = None,
    skip_existing: bool = False,
    task_id: str | None = None,
) -> None:
    """Score existing benchmark results with the specified judge workflows."""
    active_tracks = [t.upper() for t in (tracks or ALL_TRACKS)]
    tasks = load_dataset(tracks=active_tracks, task_id=task_id)
    logger.info("Loaded %d tasks (tracks=%s)", len(tasks), active_tracks)

    rubric_brain_dir = results_dir / f"judge_rubric_{output_tag}" / "brain"
    rubric_brainless_dir = results_dir / f"judge_rubric_{output_tag}" / "brainless"
    pairwise_dir = results_dir / f"judge_pairwise_{output_tag}"

    rubric_brain_dir.mkdir(parents=True, exist_ok=True)
    rubric_brainless_dir.mkdir(parents=True, exist_ok=True)
    pairwise_dir.mkdir(parents=True, exist_ok=True)

    # Load execution results
    brain_results: dict[str, dict[str, Any]] = {}
    brainless_results: dict[str, dict[str, Any]] = {}
    for task in tasks:
        tid = task["task_id"]
        for cond, store in [("brain", brain_results), ("brainless", brainless_results)]:
            path = results_dir / cond / f"{tid}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    store[tid] = json.load(f)

    # ── Rubric judging ───────────────────────────────────────────
    print(f"\n{'═' * 72}")
    print(f"  RUBRIC JUDGING (tag={output_tag})")
    print(f"{'═' * 72}")

    t0 = time.perf_counter()
    rubric_count = 0

    tasks_by_track: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        tasks_by_track.setdefault(t["track"], []).append(t)

    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Rubric judging Track {track} ({len(track_tasks)} tasks) ──")

        for task in track_tasks:
            tid = task["task_id"]

            # Judge brain output
            if tid in brain_results and brain_results[tid].get("success"):
                out_path = rubric_brain_dir / f"{tid}.json"
                if skip_existing and out_path.exists():
                    continue
                r = await run_rubric_judge(
                    task, brain_results[tid].get("output"), rubric_workflow
                )
                r["condition"] = "brain"
                r["track"] = track
                save_result(
                    results_dir / f"judge_rubric_{output_tag}",
                    {**r, "task_id": tid, "condition": "brain"},
                )
                rubric_count += 1

            # Judge brainless output
            if tid in brainless_results and brainless_results[tid].get("success"):
                out_path = rubric_brainless_dir / f"{tid}.json"
                if skip_existing and out_path.exists():
                    continue
                r = await run_rubric_judge(
                    task, brainless_results[tid].get("output"), rubric_workflow
                )
                r["condition"] = "brainless"
                r["track"] = track
                save_result(
                    results_dir / f"judge_rubric_{output_tag}",
                    {**r, "task_id": tid, "condition": "brainless"},
                )
                rubric_count += 1

    rubric_time = time.perf_counter() - t0
    print(f"\n  Rubric judging: {rubric_count} evaluations in {rubric_time:.0f}s")

    # ── Pairwise judging ─────────────────────────────────────────
    print(f"\n{'═' * 72}")
    print(f"  PAIRWISE JUDGING (tag={output_tag})")
    print(f"{'═' * 72}")

    t0 = time.perf_counter()
    pairwise_count = 0

    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Pairwise judging Track {track} ({len(track_tasks)} tasks) ──")

        for task in track_tasks:
            tid = task["task_id"]
            brain_ok = tid in brain_results and brain_results[tid].get("success")
            brainless_ok = tid in brainless_results and brainless_results[tid].get("success")
            if brain_ok and brainless_ok:
                out_path = pairwise_dir / "pairwise" / f"{tid}.json"
                if skip_existing and out_path.exists():
                    continue
                r = await run_pairwise_judge(
                    task,
                    brain_results[tid].get("output"),
                    brainless_results[tid].get("output"),
                    pairwise_workflow,
                )
                r["track"] = track
                r["condition"] = "pairwise"
                save_result(
                    results_dir / f"judge_pairwise_{output_tag}",
                    {**r, "task_id": tid, "condition": "pairwise"},
                )
                pairwise_count += 1

    pairwise_time = time.perf_counter() - t0
    print(f"\n  Pairwise judging: {pairwise_count} comparisons in {pairwise_time:.0f}s")

    print(f"\n{'═' * 72}")
    print(f"  JUDGING COMPLETE — tag={output_tag}")
    print(f"  Results in: {results_dir / f'judge_rubric_{output_tag}'}")
    print(f"              {results_dir / f'judge_pairwise_{output_tag}'}")
    print(f"{'═' * 72}\n")


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score benchmark results with a pluggable judge workflow."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=BENCHMARK_DIR / "results",
        help="Results directory (default: benchmark_v2/results/)",
    )
    parser.add_argument(
        "--judge-workflow",
        type=str,
        default=str(BENCHMARK_DIR / "judge_rubric_workflow.yml"),
        help="YAML workflow for rubric judging",
    )
    parser.add_argument(
        "--pairwise-workflow",
        type=str,
        default=str(BENCHMARK_DIR / "judge_pairwise_workflow.yml"),
        help="YAML workflow for pairwise judging",
    )
    parser.add_argument(
        "--output-tag",
        type=str,
        default="local",
        help='Subdirectory tag for results (e.g. "local", "gpt4")',
    )
    parser.add_argument(
        "--track",
        choices=ALL_TRACKS,
        action="append",
        default=None,
        help="Score a single track (default: all). Repeatable.",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        help="Score a single task by task_id",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip already-scored task IDs (enables resume after crash)",
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

    asyncio.run(
        judge_benchmark(
            results_dir=args.results_dir.resolve(),
            rubric_workflow=args.judge_workflow,
            pairwise_workflow=args.pairwise_workflow,
            output_tag=args.output_tag,
            tracks=args.track,
            skip_existing=args.skip_existing,
            task_id=args.id,
        )
    )


if __name__ == "__main__":
    main()
