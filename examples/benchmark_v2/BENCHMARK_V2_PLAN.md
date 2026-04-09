# OrKa Brain v2 Benchmark Plan

## Overview

Comprehensive benchmark comparing **Brain-enabled** vs **Brainless** workflows
across 5 evaluation tracks, totalling **500+ execution runs** plus LLM-as-Judge
evaluation.

| Track | Focus | Tasks | Brain Unique Capability |
|-------|-------|-------|------------------------|
| A | Cross-Domain Skill Transfer | 50 | `learn` + `recall` + `feedback` |
| B | Anti-Pattern Avoidance | 50 | `learn_anti` + recall avoidance |
| C | GraphScout Brain-Assisted Routing | 50 | `learn_path` + brain-assisted routing |
| D | Multi-Skill Composition | 50 | All 3 skill types + recall composition |
| E | Longitudinal Learning Curve | 50 | Accumulated knowledge over 50 sequential runs |

**Total: 250 tasks × 2 conditions = 500 execution runs**
**+ 500 rubric judge runs + 250 pairwise judge runs = 1,250 total orchestrator calls**

---

## Execution Pipeline

```
Phase 1: Brainless Condition (250 runs)
  ├── Flush brain → Track A (50 runs) → Track B → Track C → Track D → Track E
  └── Save per-task results to results/brainless/{task_id}.json

Phase 2: Brain Condition (250 runs)
  ├── For each track: Flush brain → run all 50 tasks in order
  └── Brain accumulates knowledge WITHIN a track, not across tracks

Phase 3: LLM-as-Judge Evaluation
  ├── Rubric scoring: 500 judge runs (250 brain + 250 brainless)
  └── Pairwise comparison: 250 head-to-head comparisons

Phase 4: Aggregation & Report
  └── benchmark_v2_report.json + console summary
```

---

## Track Details

### Track A — Cross-Domain Skill Transfer (50 tasks)

**Hypothesis**: Brain-enabled workflows improve quality by recalling solutions
from related domains.

| Phase | Count | What happens |
|-------|-------|-------------|
| `learn` | 10 | Seed 10 high-quality solutions with execution traces across 5 domains |
| `recall` | 40 | New tasks in same/adjacent domains; brain should recall relevant skills |

**Key metrics**: `transfer_rate` — fraction of recall tasks where brain found a skill.

### Track B — Anti-Pattern Avoidance (50 tasks)

**Hypothesis**: Brain avoids known failure modes that brainless workflows repeat.

| Phase | Count | What happens |
|-------|-------|-------------|
| `seed_anti` | 10 | Teach 10 anti-patterns (what failed, why, severity) |
| `test_avoid` | 40 | Tasks where a naïve approach would trigger anti-patterns |

**Key metrics**: `anti_patterns_seeded`, `avoidance_tests` count.

### Track C — GraphScout Brain-Assisted Routing (50 tasks)

**Hypothesis**: Brain-assisted GraphScout selects better routes than heuristics alone.

| Phase | Count | What happens |
|-------|-------|-------------|
| `seed_path` | 10 | Teach 10 proven routing paths with quality scores |
| `route` | 40 | Tasks requiring intelligent routing to 8 specialist agents |

**Brain workflow**: `graph-scout` with `brain_assisted: true`, `k_beam: 3`
**Brainless workflow**: `graph-scout` with `brain_assisted: false` (heuristics only)

**Key metrics**: `brain_avg_routing_confidence`, `brainless_avg_routing_confidence`.

### Track D — Multi-Skill Composition (50 tasks)

**Hypothesis**: Brain composes multiple skill types for better results than raw LLM.

| Phase | Count | What happens |
|-------|-------|-------------|
| `seed` | 10 | Seed recipe + anti-pattern + path skills simultaneously |
| `compose` | 40 | Tasks requiring integration of multiple recalled skills |

**Key metrics**: `multi_skill_compositions`, `composition_rate`.

### Track E — Longitudinal Learning Curve (50 tasks)

**Hypothesis**: Brain's quality improves over time as knowledge accumulates.

All 50 tasks are sequential software architecture reviews. Brain accumulates
knowledge from every completed task.

**Key metrics**: `brain_first_quartile_avg`, `brain_last_quartile_avg`,
`brain_improvement` (delta).

---

## Evaluation System

### Rubric Judge (6 dimensions, 1-10 scale)

Each output is scored independently on:

| Dimension | What it measures |
|-----------|-----------------|
| `reasoning_quality` | Logical coherence, inferential depth |
| `structural_completeness` | Covers scope, no major gaps |
| `depth_of_analysis` | Going beyond surface-level |
| `actionability` | Concrete, implementable advice |
| `domain_adaptability` | Appropriate for the domain context |
| `confidence_calibration` | Confidence matches evidence |

### Pairwise Judge (A/B comparison)

Randomized label assignment (prevents position bias). For each pair:
- `stronger_reasoning`: Which output reasons better? (A/B/TIE)
- `more_complete`: Which is more complete? (A/B/TIE)
- `more_trustworthy`: Which would you trust more? (A/B/TIE)
- `overall_preference`: Overall which is better? (A/B/TIE)

---

## File Structure

```
examples/benchmark_v2/
├── BENCHMARK_V2_PLAN.md          # This document
├── benchmark_v2_dataset.json     # 250 tasks across 5 tracks
├── brain_track_a.yml             # Brain workflow: Cross-domain transfer
├── brain_track_b.yml             # Brain workflow: Anti-pattern avoidance
├── brain_track_c.yml             # Brain workflow: GraphScout routing
├── brain_track_d.yml             # Brain workflow: Multi-skill composition
├── brain_track_e.yml             # Brain workflow: Longitudinal learning
├── brainless_track_a.yml         # Brainless workflow: Track A
├── brainless_track_b.yml         # Brainless workflow: Track B
├── brainless_track_c.yml         # Brainless workflow: Track C  
├── brainless_track_d.yml         # Brainless workflow: Track D
├── brainless_track_e.yml         # Brainless workflow: Track E
├── judge_rubric_workflow.yml     # 6-dimension rubric scoring
├── judge_pairwise_workflow.yml   # A/B pairwise comparison
├── run_benchmark_v2.py           # Automation runner script
└── results/                      # Generated during run
    ├── brain/                    # Per-task brain results
    ├── brainless/                # Per-task brainless results
    ├── judge_rubric/             # Per-task rubric scores
    ├── judge_pairwise/           # Per-task pairwise verdicts
    └── benchmark_v2_report.json  # Final aggregated report
```

---

## Running the Benchmark

### Prerequisites

```bash
# Start Redis
orka-start

# Ensure LM Studio is running on localhost:1234 with model loaded
# Verify: curl http://localhost:1234/v1/models
```

### Full Run (~2-4 hours depending on model speed)

```bash
python examples/benchmark_v2/run_benchmark_v2.py -v
```

### Partial Runs

```bash
# Single track
python examples/benchmark_v2/run_benchmark_v2.py --track A

# Multiple tracks  
python examples/benchmark_v2/run_benchmark_v2.py --track A --track C

# Single task (debugging)
python examples/benchmark_v2/run_benchmark_v2.py --id track_a_05

# Brain only (skip brainless)
python examples/benchmark_v2/run_benchmark_v2.py --skip-brainless

# Re-run judge on existing results
python examples/benchmark_v2/run_benchmark_v2.py --judge-only
```

### Custom results directory

```bash
python examples/benchmark_v2/run_benchmark_v2.py --results-dir ./my_results/
```

---

## Design Decisions

1. **Sequential within tracks**: Tasks within a track run in order so the brain
   can accumulate knowledge (especially important for Track E).

2. **Brain flushed between tracks**: Each track starts with a clean brain to
   isolate the effect of each track's specific skill types.

3. **Brainless runs first**: Prevents any brain contamination of baseline.

4. **Randomized pairwise labels**: Prevents judge position bias by randomly
   assigning brain/brainless to A/B slots.

5. **Orchestrator with return_logs**: Uses `Orchestrator.run(input, return_logs=True)`
   for rich per-agent output data instead of just the final response string.

6. **Resumable**: Results are saved per-task. The judge-only mode can re-evaluate
   without re-running the full benchmark.
