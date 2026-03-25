#!/usr/bin/env python3
"""
OrKa Brain Benchmark Runner
============================

End-to-end automation for the Brain vs Brainless benchmark.
Runs both conditions on the unified dataset, evaluates with LLM-as-judge,
and produces an aggregated results report.

Prerequisites:
  - Redis running: orka-start
  - LM Studio running on localhost:1234 with openai/gpt-oss-20b loaded
  - conda activate orka_0.9.12

Usage:
  python scripts/run_benchmark.py                         # full run
  python scripts/run_benchmark.py --track A               # only Track A
  python scripts/run_benchmark.py --track B               # only Track B
  python scripts/run_benchmark.py --skip-brainless        # re-run brain only
  python scripts/run_benchmark.py --judge-only            # skip execution, run judges
  python scripts/run_benchmark.py --results-dir results/  # custom output dir
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path so we can import orka
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orka.cli.core import run_cli_entrypoint  # noqa: E402

logger = logging.getLogger("benchmark")

# ── Paths ────────────────────────────────────────────────────────────────
DATASET_PATH = PROJECT_ROOT / "examples" / "benchmark" / "benchmark_dataset.json"
BRAIN_WORKFLOW = str(PROJECT_ROOT / "examples" / "benchmark" / "brain_benchmark_workflow.yml")
BRAINLESS_WORKFLOW = str(
    PROJECT_ROOT / "examples" / "benchmark" / "brainless_benchmark_workflow.yml"
)
RUBRIC_WORKFLOW = str(PROJECT_ROOT / "examples" / "benchmark" / "judge_rubric_workflow.yml")
PAIRWISE_WORKFLOW = str(PROJECT_ROOT / "examples" / "benchmark" / "judge_pairwise_workflow.yml")


def load_dataset(track_filter: str | None = None) -> list[dict[str, Any]]:
    """Load the benchmark dataset, optionally filtering by track."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks = data["tasks"]
    if track_filter:
        tasks = [t for t in tasks if t["track"] == track_filter.upper()]
    return tasks


def build_input_for_task(task: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON input payload for a single task.

    Track A tasks: inline task description.
    Track B tasks: load from the referenced input file and wrap.
    """
    if task["track"] == "B" and task.get("input_file"):
        input_file = PROJECT_ROOT / task["input_file"]
        if input_file.exists():
            with open(input_file, "r", encoding="utf-8") as f:
                case_data = json.load(f)
            return {
                "domain": task["domain"],
                "task": json.dumps(case_data, indent=2),
            }
        else:
            logger.warning("Input file %s not found; falling back to task description", input_file)

    # Track A or fallback
    return {
        "domain": task["domain"],
        "task": task["task"],
    }


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
        result = await run_cli_entrypoint(workflow, task_input)
        elapsed = time.perf_counter() - start
        logger.info("[%s] %s completed in %.1fs", condition, task_id, elapsed)
        return {
            "task_id": task_id,
            "condition": condition,
            "elapsed_s": round(elapsed, 2),
            "success": True,
            "output": result,
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
        }


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


def save_result(results_dir: Path, result: dict[str, Any]) -> None:
    """Save a single task result to disk."""
    condition_dir = results_dir / result["condition"]
    condition_dir.mkdir(parents=True, exist_ok=True)
    out_path = condition_dir / f"{result['task_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)


# ── Judge evaluation ───────────────────────────────────────────────────


async def run_rubric_judge(
    task: dict[str, Any],
    output: Any,
) -> dict[str, Any]:
    """Run the rubric judge on a single output."""
    judge_input = {
        "domain": task["domain"],
        "task": task["task"],
        "output": output if isinstance(output, str) else json.dumps(output, default=str),
    }
    try:
        result = await run_cli_entrypoint(RUBRIC_WORKFLOW, judge_input)
        return {"task_id": task["task_id"], "success": True, "scores": result}
    except Exception as exc:
        logger.error("Rubric judge failed for %s: %s", task["task_id"], exc)
        return {"task_id": task["task_id"], "success": False, "error": str(exc)}


async def run_pairwise_judge(
    task: dict[str, Any],
    brain_output: Any,
    brainless_output: Any,
) -> dict[str, Any]:
    """Run the pairwise judge with randomized A/B assignment."""
    # Randomize label assignment to avoid position bias
    if random.random() < 0.5:
        output_a, output_b = brain_output, brainless_output
        label_a, label_b = "brain", "brainless"
    else:
        output_a, output_b = brainless_output, brain_output
        label_a, label_b = "brainless", "brain"

    judge_input = {
        "domain": task["domain"],
        "task": task["task"],
        "output_a": output_a if isinstance(output_a, str) else json.dumps(output_a, default=str),
        "output_b": output_b if isinstance(output_b, str) else json.dumps(output_b, default=str),
    }
    try:
        result = await run_cli_entrypoint(PAIRWISE_WORKFLOW, judge_input)
        return {
            "task_id": task["task_id"],
            "success": True,
            "label_a": label_a,
            "label_b": label_b,
            "verdict": result,
        }
    except Exception as exc:
        logger.error("Pairwise judge failed for %s: %s", task["task_id"], exc)
        return {"task_id": task["task_id"], "success": False, "error": str(exc)}


# ── Aggregation ────────────────────────────────────────────────────────


def aggregate_rubric_scores(
    rubric_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate rubric scores across all tasks for a condition."""
    dimensions = [
        "reasoning_quality",
        "structural_completeness",
        "depth_of_analysis",
        "actionability",
        "domain_adaptability",
        "confidence_calibration",
    ]
    totals: dict[str, list[float]] = {d: [] for d in dimensions}
    overall_scores: list[float] = []

    for r in rubric_results:
        if not r.get("success"):
            continue
        scores = r.get("scores", {})
        # scores might be a dict or a nested structure with agent id key
        if isinstance(scores, dict):
            # Try to find the rubric_judge output (might be nested under agent id)
            score_data = scores.get("rubric_judge", scores)
            if isinstance(score_data, str):
                try:
                    score_data = json.loads(score_data)
                except (json.JSONDecodeError, TypeError):
                    continue
            for dim in dimensions:
                val = score_data.get(dim)
                if isinstance(val, (int, float)):
                    totals[dim].append(float(val))
            ov = score_data.get("overall_score")
            if isinstance(ov, (int, float)):
                overall_scores.append(float(ov))

    averages = {}
    for dim in dimensions:
        vals = totals[dim]
        averages[dim] = round(sum(vals) / len(vals), 2) if vals else None

    return {
        "dimension_averages": averages,
        "overall_average": round(sum(overall_scores) / len(overall_scores), 2)
        if overall_scores
        else None,
        "n_scored": len([r for r in rubric_results if r.get("success")]),
        "n_failed": len([r for r in rubric_results if not r.get("success")]),
    }


def aggregate_pairwise(pairwise_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate pairwise comparison results."""
    wins = {"brain": 0, "brainless": 0, "tie": 0}
    questions = {
        "stronger_reasoning": {"brain": 0, "brainless": 0, "tie": 0},
        "more_complete": {"brain": 0, "brainless": 0, "tie": 0},
        "more_trustworthy": {"brain": 0, "brainless": 0, "tie": 0},
    }

    for r in pairwise_results:
        if not r.get("success"):
            continue
        verdict = r.get("verdict", {})
        if isinstance(verdict, dict):
            verdict_data = verdict.get("pairwise_judge", verdict)
            if isinstance(verdict_data, str):
                try:
                    verdict_data = json.loads(verdict_data)
                except (json.JSONDecodeError, TypeError):
                    continue
        else:
            continue

        label_a = r.get("label_a", "brain")
        label_b = r.get("label_b", "brainless")

        # Map A/B preferences back to brain/brainless
        for q_key in questions:
            pref = verdict_data.get(q_key, "").upper()
            if pref == "A":
                questions[q_key][label_a] += 1
            elif pref == "B":
                questions[q_key][label_b] += 1
            elif pref == "TIE":
                questions[q_key]["tie"] += 1

        overall = verdict_data.get("overall_preference", "").upper()
        if overall == "A":
            wins[label_a] += 1
        elif overall == "B":
            wins[label_b] += 1
        elif overall == "TIE":
            wins["tie"] += 1

    n_valid = sum(wins.values())
    return {
        "overall_wins": wins,
        "brain_win_rate": round(wins["brain"] / n_valid, 3) if n_valid else None,
        "per_question": questions,
        "n_compared": n_valid,
        "n_failed": len([r for r in pairwise_results if not r.get("success")]),
    }


def generate_report(
    results_dir: Path,
    brain_rubric: dict[str, Any],
    brainless_rubric: dict[str, Any],
    pairwise_agg: dict[str, Any],
    timings: dict[str, float],
) -> dict[str, Any]:
    """Generate the final benchmark report."""
    report = {
        "benchmark": "OrKa Brain vs Brainless",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rubric_scores": {
            "brain": brain_rubric,
            "brainless": brainless_rubric,
        },
        "pairwise_comparison": pairwise_agg,
        "timings_seconds": timings,
    }

    # Compute deltas
    if brain_rubric.get("dimension_averages") and brainless_rubric.get("dimension_averages"):
        deltas = {}
        for dim in brain_rubric["dimension_averages"]:
            b = brain_rubric["dimension_averages"].get(dim)
            bl = brainless_rubric["dimension_averages"].get(dim)
            if b is not None and bl is not None:
                deltas[dim] = round(b - bl, 2)
        report["rubric_deltas_brain_minus_brainless"] = deltas

    report_path = results_dir / "benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", report_path)
    return report


# ── Main ───────────────────────────────────────────────────────────────


async def run_benchmark(
    track: str | None = None,
    results_dir: Path = Path("results"),
    skip_brainless: bool = False,
    judge_only: bool = False,
) -> dict[str, Any]:
    """Run the full benchmark pipeline."""
    results_dir = results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_dataset(track)
    logger.info("Loaded %d tasks (track=%s)", len(tasks), track or "all")

    timings: dict[str, float] = {}

    # ── Phase 1: Brainless condition ──
    if not judge_only and not skip_brainless:
        logger.info("=" * 60)
        logger.info("PHASE 1: BRAINLESS CONDITION")
        logger.info("=" * 60)
        flush_redis_brain()
        t0 = time.perf_counter()
        for task in tasks:
            task_input = build_input_for_task(task)
            result = await run_single_task(
                BRAINLESS_WORKFLOW, task_input, task["task_id"], "brainless"
            )
            save_result(results_dir, result)
        timings["brainless_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 2: Brain condition ──
    if not judge_only:
        logger.info("=" * 60)
        logger.info("PHASE 2: BRAIN CONDITION")
        logger.info("=" * 60)
        flush_redis_brain()
        t0 = time.perf_counter()
        for task in tasks:
            task_input = build_input_for_task(task)
            result = await run_single_task(
                BRAIN_WORKFLOW, task_input, task["task_id"], "brain"
            )
            save_result(results_dir, result)
        timings["brain_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 3: LLM-as-Judge ──
    logger.info("=" * 60)
    logger.info("PHASE 3: LLM-AS-JUDGE EVALUATION")
    logger.info("=" * 60)

    # Load saved results from disk for judging
    brain_results: dict[str, dict[str, Any]] = {}
    brainless_results: dict[str, dict[str, Any]] = {}

    for task in tasks:
        brain_path = results_dir / "brain" / f"{task['task_id']}.json"
        brainless_path = results_dir / "brainless" / f"{task['task_id']}.json"
        if brain_path.exists():
            with open(brain_path, "r", encoding="utf-8") as f:
                brain_results[task["task_id"]] = json.load(f)
        if brainless_path.exists():
            with open(brainless_path, "r", encoding="utf-8") as f:
                brainless_results[task["task_id"]] = json.load(f)

    # 3a: Rubric scoring
    brain_rubric_results: list[dict[str, Any]] = []
    brainless_rubric_results: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    for task in tasks:
        tid = task["task_id"]
        # Judge brain output
        if tid in brain_results and brain_results[tid].get("success"):
            r = await run_rubric_judge(task, brain_results[tid]["output"])
            r["condition"] = "brain"
            brain_rubric_results.append(r)
            save_result(results_dir / "judge_rubric", {**r, "condition": "brain"})

        # Judge brainless output
        if tid in brainless_results and brainless_results[tid].get("success"):
            r = await run_rubric_judge(task, brainless_results[tid]["output"])
            r["condition"] = "brainless"
            brainless_rubric_results.append(r)
            save_result(results_dir / "judge_rubric", {**r, "condition": "brainless"})

    timings["rubric_judge_total"] = round(time.perf_counter() - t0, 2)

    # 3b: Pairwise comparison
    pairwise_results: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for task in tasks:
        tid = task["task_id"]
        brain_ok = tid in brain_results and brain_results[tid].get("success")
        brainless_ok = tid in brainless_results and brainless_results[tid].get("success")
        if brain_ok and brainless_ok:
            r = await run_pairwise_judge(
                task,
                brain_results[tid]["output"],
                brainless_results[tid]["output"],
            )
            pairwise_results.append(r)
            save_result(results_dir / "judge_pairwise", {**r, "condition": "pairwise"})

    timings["pairwise_judge_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 4: Aggregation and Reporting ──
    logger.info("=" * 60)
    logger.info("PHASE 4: AGGREGATION & REPORT")
    logger.info("=" * 60)

    brain_rubric_agg = aggregate_rubric_scores(brain_rubric_results)
    brainless_rubric_agg = aggregate_rubric_scores(brainless_rubric_results)
    pairwise_agg = aggregate_pairwise(pairwise_results)

    report = generate_report(
        results_dir, brain_rubric_agg, brainless_rubric_agg, pairwise_agg, timings
    )

    # Print summary to console
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print("=" * 60)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="OrKa Brain Benchmark Runner")
    parser.add_argument(
        "--track", choices=["A", "B"], default=None, help="Run only a specific track"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("results"),
        help="Directory for benchmark results (default: results/)",
    )
    parser.add_argument(
        "--skip-brainless",
        action="store_true",
        help="Skip brainless condition (re-run brain only)",
    )
    parser.add_argument(
        "--judge-only",
        action="store_true",
        help="Skip execution, run judges on existing results",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(
        run_benchmark(
            track=args.track,
            results_dir=args.results_dir,
            skip_brainless=args.skip_brainless,
            judge_only=args.judge_only,
        )
    )


if __name__ == "__main__":
    main()
