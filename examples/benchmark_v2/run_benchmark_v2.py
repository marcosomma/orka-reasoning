#!/usr/bin/env python3
"""
OrKa Brain Benchmark v2 Runner
================================

End-to-end automation for the Brain v2 benchmark (5 tracks, 250 tasks,
500+ total runs). Runs brain-enabled and brainless conditions,
evaluates with LLM-as-judge, and produces an aggregated report.

Tracks:
  A — Cross-Domain Skill Transfer       (50 tasks × 2 = 100 runs)
  B — Anti-Pattern Avoidance            (50 tasks × 2 = 100 runs)
  C — GraphScout Brain-Assisted Routing (50 tasks × 2 = 100 runs)
  D — Multi-Skill Composition           (50 tasks × 2 = 100 runs)
  E — Longitudinal Learning Curve       (50 tasks × 2 = 100 runs)

  Total: 500 execution runs + judge runs

Prerequisites:
  - Redis running: orka-start
  - LM Studio running on localhost:1234 with model loaded
  - conda activate orka_0.9.12

Usage:
  python examples/benchmark_v2/run_benchmark_v2.py                    # full run
  python examples/benchmark_v2/run_benchmark_v2.py --track A          # single track
  python examples/benchmark_v2/run_benchmark_v2.py --track C --track E  # subset
  python examples/benchmark_v2/run_benchmark_v2.py --skip-brainless   # brain only
  python examples/benchmark_v2/run_benchmark_v2.py --judge-only       # evaluate
  python examples/benchmark_v2/run_benchmark_v2.py --id track_a_05    # single task
"""

from __future__ import annotations

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

RUBRIC_WORKFLOW = str(BENCHMARK_DIR / "judge_rubric_workflow.yml")
PAIRWISE_WORKFLOW = str(BENCHMARK_DIR / "judge_pairwise_workflow.yml")

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


# ── Judge evaluation ────────────────────────────────────────────────


async def run_rubric_judge(
    task: dict[str, Any],
    output: Any,
) -> dict[str, Any]:
    """Run the rubric judge on a single output."""
    judge_input = {
        "domain": task.get("domain", "general"),
        "task": task.get("task", task.get("title", "")),
        "track": task.get("track", ""),
        "output": output if isinstance(output, str) else json.dumps(output, default=str),
    }
    try:
        orchestrator = Orchestrator(RUBRIC_WORKFLOW)
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
        orchestrator = Orchestrator(PAIRWISE_WORKFLOW)
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


# ── Aggregation ─────────────────────────────────────────────────────

RUBRIC_DIMENSIONS = [
    "reasoning_quality",
    "structural_completeness",
    "depth_of_analysis",
    "actionability",
    "domain_adaptability",
    "confidence_calibration",
]


def _parse_score_data(scores: Any, target_keys: list[str] | None = None) -> dict[str, Any] | None:
    """Safely extract score data from judge output.

    Agent outputs come in inconsistent formats:
      1. Scores at top level: {"reasoning_quality": 8, ...}
      2. Scores nested in 'response' dict: {"response": {"reasoning_quality": 8, ...}, "confidence": ...}
      3. Scores as JSON string in 'response': {"response": "{...}", "confidence": ...}
      4. Wrapped in a judge key: {"rubric_judge": {"reasoning_quality": 8, ...}}

    Args:
        scores: The raw score data from the judge agent.
        target_keys: Optional list of keys to look for to identify the actual score dict.
    """
    if scores is None:
        return None

    # Unwrap from string
    if isinstance(scores, str):
        try:
            scores = json.loads(scores)
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(scores, dict):
        return None

    # Unwrap from known wrapper keys
    for wrapper in ("rubric_judge", "pairwise_judge"):
        if wrapper in scores and isinstance(scores[wrapper], dict):
            scores = scores[wrapper]
            break

    # If target_keys supplied, check if any are present at top level
    if target_keys:
        if any(k in scores for k in target_keys):
            return scores

    # Try 'response' field — may contain the actual scores
    response = scores.get("response")
    if isinstance(response, str):
        # JSON string inside response
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(response, dict):
        # Scores nested in response dict
        if target_keys and any(k in response for k in target_keys):
            return response
        # If no target_keys, prefer response if it has more keys than boilerplate
        boilerplate = {"confidence", "internal_reasoning", "_metrics", "formatted_prompt", "response"}
        non_boilerplate = set(response.keys()) - boilerplate
        if non_boilerplate:
            return response

    # Fall back to top-level dict itself
    return scores


def aggregate_rubric_scores(
    rubric_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate rubric scores across tasks for a condition."""
    totals: dict[str, list[float]] = {d: [] for d in RUBRIC_DIMENSIONS}
    overall_scores: list[float] = []

    for r in rubric_results:
        if not r.get("success"):
            continue
        score_data = _parse_score_data(r.get("scores"), target_keys=RUBRIC_DIMENSIONS)
        if not score_data:
            continue
        for dim in RUBRIC_DIMENSIONS:
            val = score_data.get(dim)
            if isinstance(val, (int, float)):
                totals[dim].append(float(val))
        ov = score_data.get("overall_score")
        if isinstance(ov, (int, float)):
            overall_scores.append(float(ov))

    averages = {}
    for dim in RUBRIC_DIMENSIONS:
        vals = totals[dim]
        averages[dim] = round(sum(vals) / len(vals), 2) if vals else None

    return {
        "dimension_averages": averages,
        "overall_average": round(sum(overall_scores) / len(overall_scores), 2)
        if overall_scores
        else None,
        "n_scored": sum(1 for r in rubric_results if r.get("success")),
        "n_failed": sum(1 for r in rubric_results if not r.get("success")),
    }


def aggregate_pairwise(pairwise_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate pairwise comparison results."""
    wins: dict[str, int] = {"brain": 0, "brainless": 0, "tie": 0}
    questions: dict[str, dict[str, int]] = {
        "stronger_reasoning": {"brain": 0, "brainless": 0, "tie": 0},
        "more_complete": {"brain": 0, "brainless": 0, "tie": 0},
        "more_trustworthy": {"brain": 0, "brainless": 0, "tie": 0},
    }

    pairwise_keys = ["stronger_reasoning", "more_complete", "more_trustworthy", "overall_preference"]
    for r in pairwise_results:
        if not r.get("success"):
            continue
        verdict = r.get("verdict", {})
        verdict_data = _parse_score_data(verdict, target_keys=pairwise_keys)
        if not verdict_data:
            continue

        label_a = r.get("label_a", "brain")
        label_b = r.get("label_b", "brainless")

        for q_key in questions:
            pref = str(verdict_data.get(q_key, "")).upper()
            if pref == "A":
                questions[q_key][label_a] += 1
            elif pref == "B":
                questions[q_key][label_b] += 1
            elif pref == "TIE":
                questions[q_key]["tie"] += 1

        overall = str(verdict_data.get("overall_preference", "")).upper()
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
        "n_failed": sum(1 for r in pairwise_results if not r.get("success")),
    }


# ── Track-specific metrics ──────────────────────────────────────────


def compute_track_metrics(
    track: str,
    brain_results: dict[str, dict[str, Any]],
    brainless_results: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute track-specific metrics beyond rubric/pairwise."""
    track_tasks = [t for t in tasks if t["track"] == track]
    metrics: dict[str, Any] = {
        "track": track,
        "total_tasks": len(track_tasks),
    }

    if track == "A":
        # Measure skill transfer rates: how often brain_recall found a skill
        brain_transfers = 0
        for t in track_tasks:
            tid = t["task_id"]
            if tid in brain_results and brain_results[tid].get("success"):
                ao = brain_results[tid].get("agent_outputs", {})
                recall = ao.get("brain_recall", {})
                if isinstance(recall, dict) and recall.get("skill_name"):
                    brain_transfers += 1
        metrics["brain_skill_recalls"] = brain_transfers
        metrics["transfer_rate"] = (
            round(brain_transfers / len(track_tasks), 3) if track_tasks else 0
        )

    elif track == "B":
        # Measure anti-patterns seeded and avoided
        seed_tasks = [t for t in track_tasks if t.get("phase") == "seed_anti"]
        test_tasks = [t for t in track_tasks if t.get("phase") == "test_avoid"]
        metrics["anti_patterns_seeded"] = len(seed_tasks)
        metrics["avoidance_tests"] = len(test_tasks)

    elif track == "C":
        # Measure routing accuracy and confidence
        route_tasks = [t for t in track_tasks if t.get("phase") == "route"]
        brain_confs: list[float] = []
        brainless_confs: list[float] = []
        for t in route_tasks:
            tid = t["task_id"]
            for results, confs in [
                (brain_results, brain_confs),
                (brainless_results, brainless_confs),
            ]:
                if tid in results and results[tid].get("success"):
                    ao = results[tid].get("agent_outputs", {})
                    router = ao.get("smart_router", {})
                    if isinstance(router, dict):
                        conf = router.get("confidence")
                        if isinstance(conf, (int, float)):
                            confs.append(float(conf))
        metrics["brain_avg_routing_confidence"] = (
            round(sum(brain_confs) / len(brain_confs), 3) if brain_confs else None
        )
        metrics["brainless_avg_routing_confidence"] = (
            round(sum(brainless_confs) / len(brainless_confs), 3) if brainless_confs else None
        )

    elif track == "D":
        # Measure multi-skill composition success
        compose_tasks = [t for t in track_tasks if t.get("phase") == "compose"]
        brain_composed = 0
        for t in compose_tasks:
            tid = t["task_id"]
            if tid in brain_results and brain_results[tid].get("success"):
                ao = brain_results[tid].get("agent_outputs", {})
                applier = ao.get("task_applier", {})
                if isinstance(applier, dict):
                    skills = applier.get("skills_composed", [])
                    if isinstance(skills, list) and len(skills) > 1:
                        brain_composed += 1
        metrics["multi_skill_compositions"] = brain_composed
        metrics["composition_rate"] = (
            round(brain_composed / len(compose_tasks), 3) if compose_tasks else 0
        )

    elif track == "E":
        # Measure learning curve: quality trend across sequence
        brain_confs: list[tuple[int, float]] = []
        brainless_confs: list[tuple[int, float]] = []
        for t in track_tasks:
            tid = t["task_id"]
            seq = t.get("sequence", 0)
            for results, confs in [
                (brain_results, brain_confs),
                (brainless_results, brainless_confs),
            ]:
                if tid in results and results[tid].get("success"):
                    out = results[tid].get("output", {})
                    if isinstance(out, dict):
                        conf = out.get("confidence") or out.get("quality_self_assessment")
                        if isinstance(conf, (int, float)):
                            confs.append((seq, float(conf)))

        # Split into first/last quartile to detect improvement
        if brain_confs:
            brain_confs.sort(key=lambda x: x[0])
            q = max(1, len(brain_confs) // 4)
            first_q = [c for _, c in brain_confs[:q]]
            last_q = [c for _, c in brain_confs[-q:]]
            metrics["brain_first_quartile_avg"] = round(sum(first_q) / len(first_q), 3)
            metrics["brain_last_quartile_avg"] = round(sum(last_q) / len(last_q), 3)
            metrics["brain_improvement"] = round(
                metrics["brain_last_quartile_avg"] - metrics["brain_first_quartile_avg"], 3
            )
        if brainless_confs:
            brainless_confs.sort(key=lambda x: x[0])
            q = max(1, len(brainless_confs) // 4)
            first_q = [c for _, c in brainless_confs[:q]]
            last_q = [c for _, c in brainless_confs[-q:]]
            metrics["brainless_first_quartile_avg"] = round(sum(first_q) / len(first_q), 3)
            metrics["brainless_last_quartile_avg"] = round(sum(last_q) / len(last_q), 3)
            metrics["brainless_improvement"] = round(
                metrics["brainless_last_quartile_avg"]
                - metrics["brainless_first_quartile_avg"],
                3,
            )

    return metrics


# ── Report generation ───────────────────────────────────────────────


def generate_report(
    results_dir: Path,
    per_track_rubric_brain: dict[str, dict[str, Any]],
    per_track_rubric_brainless: dict[str, dict[str, Any]],
    per_track_pairwise: dict[str, dict[str, Any]],
    per_track_metrics: dict[str, dict[str, Any]],
    timings: dict[str, float],
    overall_rubric_brain: dict[str, Any],
    overall_rubric_brainless: dict[str, Any],
    overall_pairwise: dict[str, Any],
) -> dict[str, Any]:
    """Generate the comprehensive benchmark report."""
    report: dict[str, Any] = {
        "benchmark": "OrKa Brain v2 Benchmark",
        "version": "2.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {
            "total_tasks": 250,
            "total_runs": 500,
            "tracks": ALL_TRACKS,
        },
        "overall": {
            "rubric_brain": overall_rubric_brain,
            "rubric_brainless": overall_rubric_brainless,
            "pairwise": overall_pairwise,
        },
        "per_track": {},
        "track_metrics": per_track_metrics,
        "timings_seconds": timings,
    }

    # Compute overall deltas
    if overall_rubric_brain.get("dimension_averages") and overall_rubric_brainless.get(
        "dimension_averages"
    ):
        deltas = {}
        for dim in RUBRIC_DIMENSIONS:
            b = overall_rubric_brain["dimension_averages"].get(dim)
            bl = overall_rubric_brainless["dimension_averages"].get(dim)
            if b is not None and bl is not None:
                deltas[dim] = round(b - bl, 2)
        report["overall"]["rubric_deltas_brain_minus_brainless"] = deltas

    # Per-track results
    for track in ALL_TRACKS:
        track_data: dict[str, Any] = {}
        if track in per_track_rubric_brain:
            track_data["rubric_brain"] = per_track_rubric_brain[track]
        if track in per_track_rubric_brainless:
            track_data["rubric_brainless"] = per_track_rubric_brainless[track]
        if track in per_track_pairwise:
            track_data["pairwise"] = per_track_pairwise[track]
        # Compute per-track deltas
        rb = per_track_rubric_brain.get(track, {}).get("dimension_averages", {})
        rbl = per_track_rubric_brainless.get(track, {}).get("dimension_averages", {})
        if rb and rbl:
            track_deltas = {}
            for dim in RUBRIC_DIMENSIONS:
                b_val = rb.get(dim)
                bl_val = rbl.get(dim)
                if b_val is not None and bl_val is not None:
                    track_deltas[dim] = round(b_val - bl_val, 2)
            track_data["rubric_deltas"] = track_deltas
        report["per_track"][track] = track_data

    report_path = results_dir / "benchmark_v2_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", report_path)
    return report


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary to console."""
    print(f"\n{'═' * 72}")
    print("  BENCHMARK v2 RESULTS SUMMARY")
    print(f"{'═' * 72}")

    overall = report.get("overall", {})

    # Overall rubric
    for cond in ["rubric_brain", "rubric_brainless"]:
        data = overall.get(cond, {})
        avg = data.get("overall_average")
        n = data.get("n_scored", 0)
        label = cond.replace("rubric_", "").upper()
        print(f"\n  {label:>12}: overall={avg}  (n={n})")
        dims = data.get("dimension_averages", {})
        for d, v in dims.items():
            print(f"    {d:<30} {v}")

    # Deltas
    deltas = overall.get("rubric_deltas_brain_minus_brainless", {})
    if deltas:
        print(f"\n  {'BRAIN - BRAINLESS DELTAS':>30}")
        for d, v in deltas.items():
            sign = "+" if v > 0 else ""
            print(f"    {d:<30} {sign}{v}")

    # Pairwise
    pw = overall.get("pairwise", {})
    wins = pw.get("overall_wins", {})
    wr = pw.get("brain_win_rate")
    print(f"\n  PAIRWISE: brain={wins.get('brain',0)} brainless={wins.get('brainless',0)} "
          f"tie={wins.get('tie',0)}  win_rate={wr}")

    # Per-track summary
    print(f"\n{'─' * 72}")
    print("  PER-TRACK OVERVIEW")
    print(f"{'─' * 72}")
    for track, data in report.get("per_track", {}).items():
        rb = data.get("rubric_brain", {}).get("overall_average")
        rbl = data.get("rubric_brainless", {}).get("overall_average")
        pw_t = data.get("pairwise", {}).get("overall_wins", {})
        print(f"\n  Track {track}:  brain={rb}  brainless={rbl}  "
              f"pw_wins={{brain={pw_t.get('brain',0)}, "
              f"brainless={pw_t.get('brainless',0)}, tie={pw_t.get('tie',0)}}}")

    # Track-specific metrics
    tm = report.get("track_metrics", {})
    if tm:
        print(f"\n{'─' * 72}")
        print("  TRACK-SPECIFIC METRICS")
        print(f"{'─' * 72}")
        for track, m in tm.items():
            print(f"\n  Track {track}:")
            for k, v in m.items():
                if k not in ("track", "total_tasks"):
                    print(f"    {k}: {v}")

    # Timings
    timings = report.get("timings_seconds", {})
    if timings:
        total = sum(timings.values())
        print(f"\n  Total time: {total:.0f}s ({total/60:.1f}m)")

    print(f"\n{'═' * 72}\n")


# ── Main pipeline ───────────────────────────────────────────────────


async def run_benchmark(
    tracks: list[str] | None = None,
    results_dir: Path | None = None,
    skip_brainless: bool = False,
    judge_only: bool = False,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Run the full benchmark pipeline."""
    if results_dir is None:
        results_dir = BENCHMARK_DIR / "results"
    results_dir = results_dir.resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    active_tracks = [t.upper() for t in (tracks or ALL_TRACKS)]
    tasks = load_dataset(tracks=active_tracks, task_id=task_id)
    logger.info("Loaded %d tasks (tracks=%s)", len(tasks), active_tracks)

    timings: dict[str, float] = {}

    # Group tasks by track for ordered execution
    tasks_by_track: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        tasks_by_track.setdefault(t["track"], []).append(t)

    # ── Phase 1: Brainless condition ──────────────────────────────
    if not judge_only and not skip_brainless:
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
                print(f"    {status} [{i:>3}/{len(track_tasks)}] {task['task_id']} "
                      f"({result['elapsed_s']:.1f}s)")

        timings["brainless_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 2: Brain condition ─────────────────────────────────
    if not judge_only:
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
            # Flush brain between tracks so each track starts with clean slate
            # (accumulation happens WITHIN a track, not across tracks)
            flush_redis_brain()

            for i, task in enumerate(track_tasks, 1):
                task_input = build_input_for_task(task)
                result = await run_single_task(
                    workflow, task_input, task["task_id"], "brain"
                )
                save_result(results_dir, result)
                status = "✓" if result["success"] else "✗"
                print(f"    {status} [{i:>3}/{len(track_tasks)}] {task['task_id']} "
                      f"({result['elapsed_s']:.1f}s)")

        timings["brain_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 3: LLM-as-Judge ────────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  PHASE 3: LLM-AS-JUDGE EVALUATION")
    print(f"{'═' * 72}")

    # Load all saved results
    brain_results: dict[str, dict[str, Any]] = {}
    brainless_results: dict[str, dict[str, Any]] = {}
    for task in tasks:
        tid = task["task_id"]
        for cond, store in [("brain", brain_results), ("brainless", brainless_results)]:
            path = results_dir / cond / f"{tid}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    store[tid] = json.load(f)

    # 3a: Rubric scoring
    per_track_rubric_brain_results: dict[str, list[dict[str, Any]]] = {}
    per_track_rubric_brainless_results: dict[str, list[dict[str, Any]]] = {}
    all_brain_rubric: list[dict[str, Any]] = []
    all_brainless_rubric: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Rubric judging Track {track} ──")

        for task in track_tasks:
            tid = task["task_id"]

            # Judge brain output
            if tid in brain_results and brain_results[tid].get("success"):
                r = await run_rubric_judge(task, brain_results[tid].get("output"))
                r["condition"] = "brain"
                r["track"] = track
                per_track_rubric_brain_results.setdefault(track, []).append(r)
                all_brain_rubric.append(r)
                save_result(
                    results_dir / "judge_rubric",
                    {**r, "task_id": f"{tid}_brain", "condition": "brain"},
                )

            # Judge brainless output
            if tid in brainless_results and brainless_results[tid].get("success"):
                r = await run_rubric_judge(task, brainless_results[tid].get("output"))
                r["condition"] = "brainless"
                r["track"] = track
                per_track_rubric_brainless_results.setdefault(track, []).append(r)
                all_brainless_rubric.append(r)
                save_result(
                    results_dir / "judge_rubric",
                    {**r, "task_id": f"{tid}_brainless", "condition": "brainless"},
                )

    timings["rubric_judge_total"] = round(time.perf_counter() - t0, 2)

    # 3b: Pairwise comparison
    per_track_pairwise_results: dict[str, list[dict[str, Any]]] = {}
    all_pairwise: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Pairwise judging Track {track} ──")

        for task in track_tasks:
            tid = task["task_id"]
            brain_ok = tid in brain_results and brain_results[tid].get("success")
            brainless_ok = tid in brainless_results and brainless_results[tid].get("success")
            if brain_ok and brainless_ok:
                r = await run_pairwise_judge(
                    task,
                    brain_results[tid].get("output"),
                    brainless_results[tid].get("output"),
                )
                r["track"] = track
                per_track_pairwise_results.setdefault(track, []).append(r)
                all_pairwise.append(r)
                save_result(
                    results_dir / "judge_pairwise",
                    {**r, "condition": "pairwise"},
                )

    timings["pairwise_judge_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 4: Aggregation ─────────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  PHASE 4: AGGREGATION & REPORT")
    print(f"{'═' * 72}")

    # Per-track aggregation
    per_track_rubric_brain_agg: dict[str, dict[str, Any]] = {}
    per_track_rubric_brainless_agg: dict[str, dict[str, Any]] = {}
    per_track_pairwise_agg: dict[str, dict[str, Any]] = {}

    for track in active_tracks:
        per_track_rubric_brain_agg[track] = aggregate_rubric_scores(
            per_track_rubric_brain_results.get(track, [])
        )
        per_track_rubric_brainless_agg[track] = aggregate_rubric_scores(
            per_track_rubric_brainless_results.get(track, [])
        )
        per_track_pairwise_agg[track] = aggregate_pairwise(
            per_track_pairwise_results.get(track, [])
        )

    # Overall aggregation
    overall_rubric_brain = aggregate_rubric_scores(all_brain_rubric)
    overall_rubric_brainless = aggregate_rubric_scores(all_brainless_rubric)
    overall_pairwise = aggregate_pairwise(all_pairwise)

    # Track-specific metrics
    per_track_metrics = {}
    for track in active_tracks:
        per_track_metrics[track] = compute_track_metrics(
            track, brain_results, brainless_results, tasks
        )

    # Generate report
    report = generate_report(
        results_dir,
        per_track_rubric_brain_agg,
        per_track_rubric_brainless_agg,
        per_track_pairwise_agg,
        per_track_metrics,
        timings,
        overall_rubric_brain,
        overall_rubric_brainless,
        overall_pairwise,
    )

    print_summary(report)
    return report


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="OrKa Brain Benchmark v2 Runner")
    parser.add_argument(
        "--track",
        choices=ALL_TRACKS,
        action="append",
        default=None,
        help="Run only specific track(s). Can be repeated: --track A --track C",
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
        "--judge-only",
        action="store_true",
        help="Skip execution, run judges on existing results",
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
        run_benchmark(
            tracks=args.track,
            results_dir=args.results_dir,
            skip_brainless=args.skip_brainless,
            judge_only=args.judge_only,
            task_id=args.id,
        )
    )


if __name__ == "__main__":
    main()
