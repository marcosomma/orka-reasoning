#!/usr/bin/env python3
"""
OrKa Brain Benchmark v2 — Standalone Aggregation & Report
===========================================================

Aggregate judge scores and generate the benchmark report.
Reads from ``results/judge_rubric_{tag}/`` and ``results/judge_pairwise_{tag}/``.

Usage::

    # Aggregate local judge results
    python aggregate_benchmark.py --judge-tag local

    # Exclude Track C from overall aggregates
    python aggregate_benchmark.py --judge-tag local --exclude-tracks C

    # Compare two judge tags side-by-side
    python aggregate_benchmark.py --compare-tags local,gpt4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BENCHMARK_DIR = Path(__file__).resolve().parent
DATASET_PATH = BENCHMARK_DIR / "benchmark_v2_dataset.json"
ALL_TRACKS = ["A", "B", "C", "D", "E"]

RUBRIC_DIMENSIONS = [
    "reasoning_quality",
    "structural_completeness",
    "depth_of_analysis",
    "actionability",
    "domain_adaptability",
    "confidence_calibration",
]


# ── Dataset loading ─────────────────────────────────────────────────


def load_dataset(
    tracks: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load the benchmark dataset, optionally filtering by track(s)."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tasks: list[dict[str, Any]] = data["tasks"]
    if tracks:
        upper = [t.upper() for t in tracks]
        tasks = [t for t in tasks if t["track"] in upper]
    return tasks


# ── Score parsing ───────────────────────────────────────────────────


def _parse_score_data(scores: Any, target_keys: list[str] | None = None) -> dict[str, Any] | None:
    """Safely extract score data from judge output.

    Agent outputs arrive in inconsistent formats — nested in ``response``,
    wrapped as JSON strings, etc.  This normalizes them.
    """
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
        boilerplate = {"confidence", "internal_reasoning", "_metrics", "formatted_prompt", "response"}
        if set(response.keys()) - boilerplate:
            return response

    return scores


# ── Aggregation ─────────────────────────────────────────────────────


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
        "overall_average": (
            round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else None
        ),
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


# ── Report generation ───────────────────────────────────────────────


def load_judge_results(
    results_dir: Path,
    tag: str,
    tracks: list[str],
    exclude_tracks: list[str],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    """Load judge results from disk, grouped by track.

    Returns (rubric_brain, rubric_brainless, pairwise) dicts of track → results.
    """
    rubric_brain: dict[str, list[dict[str, Any]]] = {}
    rubric_brainless: dict[str, list[dict[str, Any]]] = {}
    pairwise: dict[str, list[dict[str, Any]]] = {}

    effective_tracks = [t for t in tracks if t not in exclude_tracks]

    for track in effective_tracks:
        rubric_brain[track] = []
        rubric_brainless[track] = []
        pairwise[track] = []

    # Rubric brain
    rubric_brain_dir = results_dir / f"judge_rubric_{tag}" / "brain"
    if rubric_brain_dir.exists():
        for p in rubric_brain_dir.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            track = data.get("track", "")
            if track in effective_tracks:
                rubric_brain.setdefault(track, []).append(data)

    # Rubric brainless
    rubric_brainless_dir = results_dir / f"judge_rubric_{tag}" / "brainless"
    if rubric_brainless_dir.exists():
        for p in rubric_brainless_dir.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            track = data.get("track", "")
            if track in effective_tracks:
                rubric_brainless.setdefault(track, []).append(data)

    # Pairwise
    pairwise_dir = results_dir / f"judge_pairwise_{tag}" / "pairwise"
    if pairwise_dir.exists():
        for p in pairwise_dir.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            track = data.get("track", "")
            if track in effective_tracks:
                pairwise.setdefault(track, []).append(data)

    return rubric_brain, rubric_brainless, pairwise


def generate_report(
    tag: str,
    per_track_rubric_brain: dict[str, dict[str, Any]],
    per_track_rubric_brainless: dict[str, dict[str, Any]],
    per_track_pairwise: dict[str, dict[str, Any]],
    overall_rubric_brain: dict[str, Any],
    overall_rubric_brainless: dict[str, Any],
    overall_pairwise: dict[str, Any],
    exclude_tracks: list[str],
) -> dict[str, Any]:
    """Generate the JSON report dict."""
    report: dict[str, Any] = {
        "benchmark": "OrKa Brain v2 Benchmark",
        "version": "2.0.0",
        "judge_tag": tag,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "excluded_tracks": exclude_tracks,
        "overall": {
            "rubric_brain": overall_rubric_brain,
            "rubric_brainless": overall_rubric_brainless,
            "pairwise": overall_pairwise,
        },
        "per_track": {},
    }

    # Overall deltas
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

    # Per-track
    all_tracks = sorted(
        set(list(per_track_rubric_brain) + list(per_track_rubric_brainless) + list(per_track_pairwise))
    )
    for track in all_tracks:
        track_data: dict[str, Any] = {}
        if track in per_track_rubric_brain:
            track_data["rubric_brain"] = per_track_rubric_brain[track]
        if track in per_track_rubric_brainless:
            track_data["rubric_brainless"] = per_track_rubric_brainless[track]
        if track in per_track_pairwise:
            track_data["pairwise"] = per_track_pairwise[track]
        # Per-track deltas
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

    return report


def compare_tags(
    results_dir: Path,
    tags: list[str],
    tracks: list[str],
    exclude_tracks: list[str],
) -> dict[str, Any]:
    """Generate a side-by-side comparison of two or more judge tags."""
    comparison: dict[str, Any] = {
        "benchmark": "OrKa Brain v2 Benchmark — Judge Comparison",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tags_compared": tags,
        "excluded_tracks": exclude_tracks,
        "per_tag": {},
    }

    for tag in tags:
        rb_raw, rbl_raw, pw_raw = load_judge_results(results_dir, tag, tracks, exclude_tracks)
        all_brain: list[dict[str, Any]] = []
        all_brainless: list[dict[str, Any]] = []
        all_pairwise: list[dict[str, Any]] = []
        for v in rb_raw.values():
            all_brain.extend(v)
        for v in rbl_raw.values():
            all_brainless.extend(v)
        for v in pw_raw.values():
            all_pairwise.extend(v)

        overall_brain = aggregate_rubric_scores(all_brain)
        overall_brainless = aggregate_rubric_scores(all_brainless)
        overall_pw = aggregate_pairwise(all_pairwise)

        comparison["per_tag"][tag] = {
            "rubric_brain": overall_brain,
            "rubric_brainless": overall_brainless,
            "pairwise": overall_pw,
        }

    return comparison


def print_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary to console."""
    print(f"\n{'═' * 72}")
    print(f"  BENCHMARK v2 AGGREGATED REPORT  (tag={report.get('judge_tag', '?')})")
    if report.get("excluded_tracks"):
        print(f"  Excluded tracks: {', '.join(report['excluded_tracks'])}")
    print(f"{'═' * 72}")

    overall = report.get("overall", {})

    for cond in ["rubric_brain", "rubric_brainless"]:
        data = overall.get(cond, {})
        avg = data.get("overall_average")
        n = data.get("n_scored", 0)
        label = cond.replace("rubric_", "").upper()
        print(f"\n  {label:>12}: overall={avg}  (n={n})")
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
        f"\n  PAIRWISE: brain={wins.get('brain', 0)} brainless={wins.get('brainless', 0)} "
        f"tie={wins.get('tie', 0)}  win_rate={wr}"
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
            f"pw_wins={{brain={pw_t.get('brain', 0)}, "
            f"brainless={pw_t.get('brainless', 0)}, tie={pw_t.get('tie', 0)}}}"
        )

    print(f"\n{'═' * 72}\n")


# ── Main pipeline ───────────────────────────────────────────────────


def run_aggregation(
    results_dir: Path,
    judge_tag: str,
    exclude_tracks: list[str] | None = None,
    compare_tags_list: list[str] | None = None,
    output_path: Path | None = None,
) -> None:
    """Aggregate judge results and produce a report."""
    exclude = [t.upper() for t in (exclude_tracks or [])]

    if compare_tags_list and len(compare_tags_list) >= 2:
        comparison = compare_tags(results_dir, compare_tags_list, ALL_TRACKS, exclude)
        out_path = output_path or results_dir / "benchmark_v2_comparison.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)
        print(f"Comparison report saved to {out_path}")
        return

    rb_raw, rbl_raw, pw_raw = load_judge_results(results_dir, judge_tag, ALL_TRACKS, exclude)

    # Per-track aggregation
    per_track_rb_agg: dict[str, dict[str, Any]] = {}
    per_track_rbl_agg: dict[str, dict[str, Any]] = {}
    per_track_pw_agg: dict[str, dict[str, Any]] = {}

    effective_tracks = [t for t in ALL_TRACKS if t not in exclude]
    for track in effective_tracks:
        per_track_rb_agg[track] = aggregate_rubric_scores(rb_raw.get(track, []))
        per_track_rbl_agg[track] = aggregate_rubric_scores(rbl_raw.get(track, []))
        per_track_pw_agg[track] = aggregate_pairwise(pw_raw.get(track, []))

    # Overall
    all_brain: list[dict[str, Any]] = []
    all_brainless: list[dict[str, Any]] = []
    all_pairwise: list[dict[str, Any]] = []
    for v in rb_raw.values():
        all_brain.extend(v)
    for v in rbl_raw.values():
        all_brainless.extend(v)
    for v in pw_raw.values():
        all_pairwise.extend(v)

    overall_brain = aggregate_rubric_scores(all_brain)
    overall_brainless = aggregate_rubric_scores(all_brainless)
    overall_pw = aggregate_pairwise(all_pairwise)

    report = generate_report(
        judge_tag,
        per_track_rb_agg,
        per_track_rbl_agg,
        per_track_pw_agg,
        overall_brain,
        overall_brainless,
        overall_pw,
        exclude,
    )

    out_path = output_path or results_dir / f"benchmark_v2_report_{judge_tag}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {out_path}")
    print_summary(report)


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate judge scores and generate benchmark report."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=BENCHMARK_DIR / "results",
        help="Results directory (default: benchmark_v2/results/)",
    )
    parser.add_argument(
        "--judge-tag",
        type=str,
        default="local",
        help='Which judge results to aggregate (default: "local")',
    )
    parser.add_argument(
        "--exclude-tracks",
        type=str,
        default=None,
        help="Comma-separated tracks to exclude (e.g. C or A,C)",
    )
    parser.add_argument(
        "--compare-tags",
        type=str,
        default=None,
        help="Compare two judge tags side-by-side (e.g. local,gpt4)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report output file (default: results/benchmark_v2_report_{tag}.json)",
    )
    args = parser.parse_args()

    exclude_tracks = args.exclude_tracks.split(",") if args.exclude_tracks else None
    compare_list = args.compare_tags.split(",") if args.compare_tags else None

    run_aggregation(
        results_dir=args.results_dir.resolve(),
        judge_tag=args.judge_tag,
        exclude_tracks=exclude_tracks,
        compare_tags_list=compare_list,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
