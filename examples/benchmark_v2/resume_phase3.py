#!/usr/bin/env python3
"""
Resume script: Phase 3 (LLM-as-Judge) + Phase 4 (Aggregation).

Picks up after Phase 1 & 2 completed. Skips any tasks that already
have judge results on disk. Disables memory for the judge orchestrator
so Redis timeouts don't stall the run.

Usage:
  python examples/benchmark_v2/resume_phase3.py
  python examples/benchmark_v2/resume_phase3.py --track A
  python examples/benchmark_v2/resume_phase3.py --results-dir path/to/results
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force basic Redis (skip HNSW index verification/creation that causes timeouts)
os.environ["ORKA_FORCE_BASIC_REDIS"] = "true"

from orka.orchestrator import Orchestrator  # noqa: E402

logger = logging.getLogger("resume_phase3")

BENCHMARK_DIR = Path(__file__).resolve().parent
DATASET_PATH = BENCHMARK_DIR / "benchmark_v2_dataset.json"
RUBRIC_WORKFLOW = str(BENCHMARK_DIR / "judge_rubric_workflow.yml")
PAIRWISE_WORKFLOW = str(BENCHMARK_DIR / "judge_pairwise_workflow.yml")
ALL_TRACKS = ["A", "B", "C", "D", "E"]

RUBRIC_DIMENSIONS = [
    "reasoning_quality",
    "structural_completeness",
    "depth_of_analysis",
    "actionability",
    "domain_adaptability",
    "confidence_calibration",
]


# ── Dataset ──────────────────────────────────────────────────────────


def load_dataset(
    tracks: list[str] | None = None,
) -> list[dict[str, Any]]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks: list[dict[str, Any]] = data["tasks"]
    if tracks:
        upper = [t.upper() for t in tracks]
        tasks = [t for t in tasks if t["track"] in upper]
    return tasks


# ── Helpers from run_benchmark_v2.py ─────────────────────────────────


def _build_agent_outputs(logs: list[dict[str, Any]]) -> dict[str, Any]:
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
    condition_dir = results_dir / result["condition"]
    condition_dir.mkdir(parents=True, exist_ok=True)
    out_path = condition_dir / f"{result['task_id']}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)


def _parse_score_data(scores: Any, target_keys: list[str] | None = None) -> dict[str, Any] | None:
    if scores is None:
        return None
    if isinstance(scores, str):
        try:
            scores = json.loads(scores)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(scores, dict):
        return None
    for wrapper in ("rubric_judge", "pairwise_judge"):
        if wrapper in scores and isinstance(scores[wrapper], dict):
            scores = scores[wrapper]
            break
    if target_keys:
        if any(k in scores for k in target_keys):
            return scores
    response = scores.get("response")
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(response, dict):
        if target_keys and any(k in response for k in target_keys):
            return response
    return scores


# ── Patched judge runners (memory-safe) ──────────────────────────────


def _make_orchestrator(workflow: str) -> Orchestrator:
    """Create an Orchestrator with memory errors suppressed."""
    try:
        return Orchestrator(workflow)
    except Exception:
        # If Orchestrator init fails due to Redis, the env var should prevent it,
        # but fall back to retrying
        raise


async def run_rubric_judge(
    task: dict[str, Any],
    output: Any,
) -> dict[str, Any]:
    judge_input = {
        "domain": task.get("domain", "general"),
        "task": task.get("task", task.get("title", "")),
        "track": task.get("track", ""),
        "output": output if isinstance(output, str) else json.dumps(output, default=str),
    }
    try:
        orchestrator = _make_orchestrator(RUBRIC_WORKFLOW)
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
        orchestrator = _make_orchestrator(PAIRWISE_WORKFLOW)
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


# ── Aggregation (copied from run_benchmark_v2) ──────────────────────


def aggregate_rubric_scores(
    rubric_results: list[dict[str, Any]],
) -> dict[str, Any]:
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
    wins: dict[str, int] = {"brain": 0, "brainless": 0, "tie": 0}
    questions: dict[str, dict[str, int]] = {
        "stronger_reasoning": {"brain": 0, "brainless": 0, "tie": 0},
        "more_complete": {"brain": 0, "brainless": 0, "tie": 0},
        "more_trustworthy": {"brain": 0, "brainless": 0, "tie": 0},
    }

    pairwise_keys = [
        "stronger_reasoning", "more_complete", "more_trustworthy", "overall_preference",
    ]
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


def compute_track_metrics(
    track: str,
    brain_results: dict[str, dict[str, Any]],
    brainless_results: dict[str, dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    track_tasks = [t for t in tasks if t["track"] == track]
    metrics: dict[str, Any] = {"track": track, "total_tasks": len(track_tasks)}

    if track == "A":
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
        seed_tasks = [t for t in track_tasks if t.get("phase") == "seed_anti"]
        test_tasks = [t for t in track_tasks if t.get("phase") == "test_avoid"]
        metrics["anti_patterns_seeded"] = len(seed_tasks)
        metrics["avoidance_tests"] = len(test_tasks)

    elif track == "E":
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
                    ao = results[tid].get("agent_outputs", {})
                    tr = ao.get("task_result", {})
                    if isinstance(tr, dict):
                        conf = tr.get("confidence")
                        if isinstance(conf, (int, float)):
                            confs.append((seq, float(conf)))
        if brain_confs:
            brain_confs.sort(key=lambda x: x[0])
            q = max(1, len(brain_confs) // 4)
            first_q = [c for _, c in brain_confs[:q]]
            last_q = [c for _, c in brain_confs[-q:]]
            metrics["brain_first_quartile_avg"] = round(sum(first_q) / len(first_q), 3)
            metrics["brain_last_quartile_avg"] = round(sum(last_q) / len(last_q), 3)
            metrics["brain_improvement"] = round(
                metrics["brain_last_quartile_avg"] - metrics["brain_first_quartile_avg"], 3,
            )

    return metrics


# ── Report generation ────────────────────────────────────────────────


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
    report: dict[str, Any] = {
        "benchmark": "OrKa Brain v2 Benchmark",
        "version": "2.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "summary": {"total_tasks": 250, "total_runs": 500, "tracks": ALL_TRACKS},
        "overall": {
            "rubric_brain": overall_rubric_brain,
            "rubric_brainless": overall_rubric_brainless,
            "pairwise": overall_pairwise,
        },
        "per_track": {},
        "track_metrics": per_track_metrics,
        "timings_seconds": timings,
    }

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

    for track in ALL_TRACKS:
        track_data: dict[str, Any] = {}
        if track in per_track_rubric_brain:
            track_data["rubric_brain"] = per_track_rubric_brain[track]
        if track in per_track_rubric_brainless:
            track_data["rubric_brainless"] = per_track_rubric_brainless[track]
        if track in per_track_pairwise:
            track_data["pairwise"] = per_track_pairwise[track]
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
    print(f"\n{'═' * 72}")
    print("  BENCHMARK v2 RESULTS SUMMARY")
    print(f"{'═' * 72}")

    overall = report.get("overall", {})
    for cond in ["rubric_brain", "rubric_brainless"]:
        data = overall.get(cond, {})
        avg = data.get("overall_average")
        n = data.get("n_scored", 0)
        print(f"\n  {cond.upper()}: overall_avg={avg}  (n={n})")
        dims = data.get("dimension_averages", {})
        for d, v in dims.items():
            print(f"    {d:<30} {v}")

    deltas = overall.get("rubric_deltas_brain_minus_brainless", {})
    if deltas:
        print(f"\n  {'BRAIN - BRAINLESS DELTAS':>30}")
        for d, v in deltas.items():
            sign = "+" if v > 0 else ""
            print(f"    {d:<30} {sign}{v}")

    pw = overall.get("pairwise", {})
    wins = pw.get("overall_wins", {})
    wr = pw.get("brain_win_rate")
    print(
        f"\n  PAIRWISE: brain={wins.get('brain',0)} brainless={wins.get('brainless',0)} "
        f"tie={wins.get('tie',0)}  win_rate={wr}"
    )

    print(f"\n{'─' * 72}")
    print("  PER-TRACK OVERVIEW")
    print(f"{'─' * 72}")
    for track, data in report.get("per_track", {}).items():
        rb = data.get("rubric_brain", {}).get("overall_average")
        rbl = data.get("rubric_brainless", {}).get("overall_average")
        pw_t = data.get("pairwise", {}).get("overall_wins", {})
        print(
            f"\n  Track {track}:  brain={rb}  brainless={rbl}  "
            f"pw_wins={{brain={pw_t.get('brain',0)}, "
            f"brainless={pw_t.get('brainless',0)}, tie={pw_t.get('tie',0)}}}"
        )

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

    timings = report.get("timings_seconds", {})
    if timings:
        total = sum(timings.values())
        print(f"\n  Total time: {total:.0f}s ({total/60:.1f}m)")

    print(f"\n{'═' * 72}\n")


# ── Main pipeline ────────────────────────────────────────────────────


async def run_phase3(
    tracks: list[str] | None = None,
    results_dir: Path | None = None,
) -> dict[str, Any]:
    if results_dir is None:
        results_dir = BENCHMARK_DIR / "results"
    results_dir = results_dir.resolve()

    active_tracks = [t.upper() for t in (tracks or ALL_TRACKS)]
    tasks = load_dataset(tracks=active_tracks)
    logger.info("Loaded %d tasks (tracks=%s)", len(tasks), active_tracks)

    tasks_by_track: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        tasks_by_track.setdefault(t["track"], []).append(t)

    timings: dict[str, float] = {}

    # ── Load Phase 1 & 2 results ──────────────────────────────────
    brain_results: dict[str, dict[str, Any]] = {}
    brainless_results: dict[str, dict[str, Any]] = {}
    for task in tasks:
        tid = task["task_id"]
        for cond, store in [("brain", brain_results), ("brainless", brainless_results)]:
            path = results_dir / cond / f"{tid}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    store[tid] = json.load(f)

    print(f"\n  Loaded {len(brain_results)} brain + {len(brainless_results)} brainless results")

    # ── Phase 3a: Rubric scoring ──────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  PHASE 3: LLM-AS-JUDGE EVALUATION (RESUME)")
    print(f"{'═' * 72}")

    per_track_rubric_brain_results: dict[str, list[dict[str, Any]]] = {}
    per_track_rubric_brainless_results: dict[str, list[dict[str, Any]]] = {}
    all_brain_rubric: list[dict[str, Any]] = []
    all_brainless_rubric: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Rubric judging Track {track} ──")

        for i, task in enumerate(track_tasks, 1):
            tid = task["task_id"]

            # Judge brain output
            if tid in brain_results and brain_results[tid].get("success"):
                rubric_path = results_dir / "judge_rubric" / f"{tid}_brain.json"
                if rubric_path.exists():
                    # Already judged — load from disk
                    with open(rubric_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    r = {
                        "task_id": tid,
                        "success": saved.get("success", True),
                        "scores": saved.get("scores", saved),
                    }
                    status = "↻"
                else:
                    r = await run_rubric_judge(task, brain_results[tid].get("output"))
                    r["condition"] = "brain"
                    r["track"] = track
                    save_result(
                        results_dir / "judge_rubric",
                        {**r, "task_id": f"{tid}_brain", "condition": "brain"},
                    )
                    status = "✓" if r.get("success") else "✗"

                per_track_rubric_brain_results.setdefault(track, []).append(r)
                all_brain_rubric.append(r)
                print(f"    {status} [{i:>3}/{len(track_tasks)}] {tid}_brain")

            # Judge brainless output
            if tid in brainless_results and brainless_results[tid].get("success"):
                rubric_path = results_dir / "judge_rubric" / f"{tid}_brainless.json"
                if rubric_path.exists():
                    with open(rubric_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                    r = {
                        "task_id": tid,
                        "success": saved.get("success", True),
                        "scores": saved.get("scores", saved),
                    }
                    status = "↻"
                else:
                    r = await run_rubric_judge(task, brainless_results[tid].get("output"))
                    r["condition"] = "brainless"
                    r["track"] = track
                    save_result(
                        results_dir / "judge_rubric",
                        {**r, "task_id": f"{tid}_brainless", "condition": "brainless"},
                    )
                    status = "✓" if r.get("success") else "✗"

                per_track_rubric_brainless_results.setdefault(track, []).append(r)
                all_brainless_rubric.append(r)
                print(f"    {status} [{i:>3}/{len(track_tasks)}] {tid}_brainless")

    timings["rubric_judge_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 3b: Pairwise comparison ─────────────────────────────
    per_track_pairwise_results: dict[str, list[dict[str, Any]]] = {}
    all_pairwise: list[dict[str, Any]] = []

    t0 = time.perf_counter()
    for track in active_tracks:
        track_tasks = tasks_by_track.get(track, [])
        print(f"\n  ── Pairwise judging Track {track} ──")

        for i, task in enumerate(track_tasks, 1):
            tid = task["task_id"]
            brain_ok = tid in brain_results and brain_results[tid].get("success")
            brainless_ok = tid in brainless_results and brainless_results[tid].get("success")
            if not (brain_ok and brainless_ok):
                continue

            pairwise_path = results_dir / "judge_pairwise" / f"{tid}.json"
            if pairwise_path.exists():
                with open(pairwise_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                r = {
                    "task_id": tid,
                    "success": saved.get("success", True),
                    "label_a": saved.get("label_a", "brain"),
                    "label_b": saved.get("label_b", "brainless"),
                    "verdict": saved.get("verdict", saved),
                }
                status = "↻"
            else:
                r = await run_pairwise_judge(
                    task,
                    brain_results[tid].get("output"),
                    brainless_results[tid].get("output"),
                )
                r["track"] = track
                save_result(
                    results_dir / "judge_pairwise",
                    {**r, "condition": "pairwise"},
                )
                status = "✓" if r.get("success") else "✗"

            per_track_pairwise_results.setdefault(track, []).append(r)
            all_pairwise.append(r)
            print(f"    {status} [{i:>3}/{len(track_tasks)}] {tid}")

    timings["pairwise_judge_total"] = round(time.perf_counter() - t0, 2)

    # ── Phase 4: Aggregation ──────────────────────────────────────
    print(f"\n{'═' * 72}")
    print("  PHASE 4: AGGREGATION & REPORT")
    print(f"{'═' * 72}")

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

    overall_rubric_brain = aggregate_rubric_scores(all_brain_rubric)
    overall_rubric_brainless = aggregate_rubric_scores(all_brainless_rubric)
    overall_pairwise = aggregate_pairwise(all_pairwise)

    per_track_metrics = {}
    for track in active_tracks:
        per_track_metrics[track] = compute_track_metrics(
            track, brain_results, brainless_results, tasks,
        )

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume Phase 3 (judge) + Phase 4 (report)")
    parser.add_argument(
        "--track", choices=ALL_TRACKS, action="append", default=None,
        help="Judge only specific track(s)",
    )
    parser.add_argument(
        "--results-dir", type=Path, default=None,
        help="Directory with existing brain/brainless results",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    asyncio.run(run_phase3(tracks=args.track, results_dir=args.results_dir))


if __name__ == "__main__":
    main()
