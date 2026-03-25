# OrKa Brain Benchmark Plan

## Evaluation Goal

**Falsifiable claim** (from the paper):

> An agent equipped with procedural skill memory demonstrates measurably
> higher task-success rates on novel but structurally similar tasks compared
> to a stateless baseline, without additional training or fine-tuning.

This benchmark provides the data to support or refute that claim with
quantitative evidence across two complementary evaluation tracks.

---

## 1  Design Overview

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **LLM** | LM Studio local — `openai/gpt-oss-20b` | Reproducible, no API cost, offline |
| **Temperature** | 0.3 (execution), 0.1 (judge) | Low variance for fair comparison |
| **Baseline** | Same workflow minus brain agents | Identical prompts ⇒ isolates Brain effect |
| **Judge** | LLM-as-judge: Rubric + Pairwise | Two orthogonal quality signals |
| **Automation** | End-to-end Python script | One-command full run |
| **Redis** | Flushed between conditions | No cross-contamination |

### Track A — Cross-Domain Transfer (10 tasks)

Three *learn* phases teach the Brain procedural patterns in distinct domains
(text analysis, customer support, creative writing).  Seven *recall* phases
test whether those patterns transfer to unrelated domains (code review,
content moderation, code optimization, financial analysis, API infrastructure,
education, DevOps incident response).

**Key metric**: Does the brain condition recall and apply the learned pattern
in a novel domain, and does that improve output quality?

### Track B — Same-Domain Accumulation (20 tasks)

Twenty veterinary diagnostic cases run sequentially.  Each case exercises the
full brain loop (learn → recall → feedback).  The brain condition should
improve over time as it accumulates domain-specific diagnostic skills.

**Key metric**: Does the brain condition's rubric score trend upward across
cases 1–20 compared to a flat baseline?

---

## 2  Benchmark Artifacts

All files live under `examples/benchmark/` and `scripts/`.

| File | Purpose |
|------|---------|
| `benchmark_dataset.json` | 30-task unified dataset (10 Track A + 20 Track B) |
| `brain_benchmark_workflow.yml` | 6-agent Brain-enabled pipeline |
| `brainless_benchmark_workflow.yml` | 3-agent stateless baseline pipeline |
| `judge_rubric_workflow.yml` | Independent rubric scoring (6 dimensions, 1–10) |
| `judge_pairwise_workflow.yml` | Side-by-side A/B comparison (3 questions) |
| `scripts/run_benchmark.py` | Full automation runner |

---

## 3  Workflow Pipelines

### 3.1  Brain-Enabled Pipeline (6 agents)

```
task_reasoner → brain_learn → brain_recall → task_applier → brain_feedback → task_result
```

1. **task_reasoner** (local_llm) — Analyzes the task and produces a step-by-step plan.
2. **brain_learn** (brain, operation: learn) — Extracts a procedural skill from the reasoning.
3. **brain_recall** (brain, operation: recall) — Searches brain for applicable skills.
4. **task_applier** (local_llm) — Solves the task, guided by any recalled skill.
5. **brain_feedback** (brain, operation: feedback) — Records whether the transfer succeeded.
6. **task_result** (local_llm) — Formats the structured output.

### 3.2  Brainless Baseline Pipeline (3 agents)

```
task_reasoner → task_applier → task_result
```

Identical prompts to the brain pipeline, but:
- No brain_learn, brain_recall, or brain_feedback agents.
- `task_applier` prompt explicitly states "You have NO prior experience with similar tasks and NO recalled skills."
- Output format is identical for fair comparison.

### 3.3  Judge Rubric Pipeline (1 agent)

Scores a **single** output on 6 dimensions (1–10 each):

| Dimension | What it measures |
|-----------|-----------------|
| Reasoning Quality | Logical coherence, evidence-based conclusions |
| Structural Completeness | All necessary steps present, well-organized |
| Depth of Analysis | Beyond surface-level, edge cases, trade-offs |
| Actionability | Concrete, implementable recommendations |
| Domain Adaptability | Domain-appropriate vs generic boilerplate |
| Confidence Calibration | Self-reported confidence matches actual quality |

**Output**: JSON with per-dimension score + justification + overall average.

### 3.4  Judge Pairwise Pipeline (1 agent)

Compares two outputs side-by-side with **randomized A/B labeling** to prevent
position bias.  Three preference questions:

1. **Stronger Reasoning** — Which demonstrates more logically coherent reasoning?
2. **More Structurally Complete** — Which covers all necessary steps better?
3. **More Trustworthy** — Which would you trust more in production?

**Output**: JSON with per-question winner (A/B/TIE) + justification + overall preference.

---

## 4  Execution Protocol

### Prerequisites

```bash
# 1. Redis with search module
orka-start

# 2. LM Studio with model loaded
#    Model: openai/gpt-oss-20b
#    URL:   http://localhost:1234

# 3. Python environment
conda activate orka_0.9.12
```

### Full Run (recommended)

```bash
python scripts/run_benchmark.py --verbose
```

This executes four phases end-to-end:

| Phase | What happens | Duration (est.) |
|-------|-------------|-----------------|
| 1 | Flush Redis brain keys → run brainless on all 30 tasks | ~60 min |
| 2 | Flush Redis brain keys → run brain on all 30 tasks | ~90 min |
| 3 | Rubric judge on all 60 outputs + pairwise on 30 pairs | ~60 min |
| 4 | Aggregate scores → generate `results/benchmark_report.json` | Instant |

### Partial Runs

```bash
# Only Track A (cross-domain transfer)
python scripts/run_benchmark.py --track A

# Only Track B (same-domain accumulation)
python scripts/run_benchmark.py --track B

# Re-run brain only (keep existing brainless results)
python scripts/run_benchmark.py --skip-brainless

# Run judges on existing results (skip execution)
python scripts/run_benchmark.py --judge-only

# Custom output directory
python scripts/run_benchmark.py --results-dir my_results/
```

---

## 5  Results Structure

```
results/
├── brainless/
│   ├── track_a_01.json
│   ├── track_a_02.json
│   ├── ...
│   └── track_b_20.json
├── brain/
│   ├── track_a_01.json
│   ├── ...
│   └── track_b_20.json
├── judge_rubric/
│   ├── brain/
│   │   ├── track_a_01.json
│   │   └── ...
│   └── brainless/
│       ├── track_a_01.json
│       └── ...
├── judge_pairwise/
│   ├── pairwise/
│   │   ├── track_a_01.json
│   │   └── ...
└── benchmark_report.json    ← final aggregated report
```

### Individual Task Result Format

```json
{
  "task_id": "track_a_04",
  "condition": "brain",
  "elapsed_s": 42.3,
  "success": true,
  "output": {
    "task_result": {
      "response": "...",
      "domain": "code_review",
      "task": "...",
      "solution_steps": ["Step 1...", "Step 2..."],
      "quality_self_assessment": 0.85,
      "brain_assisted": true,
      "recalled_skill": "Decompose-Analyze-Synthesize from text_analysis",
      "confidence": 0.88,
      "internal_reasoning": "..."
    }
  }
}
```

### Aggregated Report Format

```json
{
  "benchmark": "OrKa Brain vs Brainless",
  "timestamp": "2025-07-XX",
  "rubric_scores": {
    "brain": {
      "dimension_averages": {
        "reasoning_quality": 7.8,
        "structural_completeness": 8.1,
        "depth_of_analysis": 7.5,
        "actionability": 7.9,
        "domain_adaptability": 8.3,
        "confidence_calibration": 7.2
      },
      "overall_average": 7.8
    },
    "brainless": { "...same structure..." }
  },
  "rubric_deltas_brain_minus_brainless": {
    "reasoning_quality": 1.2,
    "structural_completeness": 0.8,
    "..."
  },
  "pairwise_comparison": {
    "overall_wins": {"brain": 22, "brainless": 5, "tie": 3},
    "brain_win_rate": 0.733,
    "per_question": {
      "stronger_reasoning": {"brain": 20, "brainless": 7, "tie": 3},
      "more_complete": {"brain": 21, "brainless": 6, "tie": 3},
      "more_trustworthy": {"brain": 23, "brainless": 4, "tie": 3}
    }
  }
}
```

---

## 6  Analysis & Paper Sections

### 6.1  Primary Hypothesis Test

**H₁**: Brain overall rubric average > Brainless overall rubric average.

Report the rubric delta table.  A consistent positive delta across all 6
dimensions supports H₁.

### 6.2  Track A — Cross-Domain Transfer Analysis

For each of the 7 recall tasks:
- Did the brain condition recall the expected skill pattern?
- How does the rubric score compare to the brainless baseline on that task?
- Plot: grouped bar chart of brain vs brainless rubric scores per recall task.

### 6.3  Track B — Accumulation Curve

Plot rubric scores for cases 1–20 in sequence for both conditions.
- **Brain**: Expect upward trend as skills accumulate.
- **Brainless**: Expect flat (no learning).
- Compute linear regression slope for both; brain slope should be positive.

### 6.4  Pairwise Preference Rate

- Brain win rate across all 30 tasks.
- Per-question breakdown (reasoning, completeness, trustworthiness).
- Position-bias check: verify A/B randomization is roughly 50/50.

### 6.5  Paper Section Mapping

| Paper Section | Data Source |
|---------------|------------|
| Abstract | Overall rubric delta + pairwise win rate |
| §3 Methodology | This benchmark plan document |
| §4.1 Cross-domain transfer | Track A rubric + pairwise |
| §4.2 Within-domain accumulation | Track B accumulation curve |
| §4.3 Ablation | Brain vs Brainless rubric delta table |
| §5 Discussion | Failure cases, dimension analysis |

---

## 7  Reproducibility Notes

1. **Determinism**: Temperature 0.3 for execution, 0.1 for judge. Results
   will vary across runs due to LLM non-determinism. Run 3× and report
   mean ± std for robustness.

2. **Redis state**: The runner flushes `orka:brain:*` keys before each
   condition. Verify with `redis-cli -p 6380 KEYS "orka:brain:*"` that
   state is clean before each phase.

3. **Model version**: Record exact model version/hash from LM Studio.
   Different quantizations may affect results.

4. **Track B ordering**: Cases are numbered 01–20 and run in order. The
   sequential ordering is essential for the accumulation hypothesis.

5. **Judge independence**: The rubric judge sees one output at a time
   (blind to condition). The pairwise judge sees two outputs with
   randomized A/B labels (blind to which is brain/brainless).

---

## 8  Checklist

- [ ] Redis running (`orka-start`)
- [ ] LM Studio running with `openai/gpt-oss-20b`
- [ ] Verify brain workflows: `orka --json-input run examples/benchmark/brain_benchmark_workflow.yml '{"domain":"test","task":"hello"}'`
- [ ] Verify brainless workflows: `orka --json-input run examples/benchmark/brainless_benchmark_workflow.yml '{"domain":"test","task":"hello"}'`
- [ ] Run full benchmark: `python scripts/run_benchmark.py --verbose`
- [ ] Inspect `results/benchmark_report.json`
- [ ] Generate plots for paper
- [ ] Run 3× for statistical robustness (if budget allows)
