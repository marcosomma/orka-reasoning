# Procedural Skill Memory at Scale: A Follow-Up Evaluation of OrKa Brain on a 250-Task, Five-Track Benchmark

**Marco Somma**
Independent Researcher, Barcelona, Spain
Creator of OrKa (Orchestrator Kit Agents)

*Follow-up to "Procedural Skill Memory for LLM Agent Systems: Architecture, Benchmark, and Honest Limits of a First Implementation."*

---

## Abstract

A prior study introduced OrKa Brain, a procedural skill memory loop for LLM agent systems, and evaluated it on a 30-task benchmark. That study reported a modest pairwise preference for the Brain condition (63.3 percent), near-parity on absolute rubric scores, and a ceiling effect: the underlying model already possessed the procedural knowledge the Brain recalled. This follow-up scales the evaluation roughly eight-fold, to 250 tasks across five distinct track types (cross-domain transfer, anti-pattern avoidance, brain-assisted routing, multi-skill composition, and longitudinal accumulation), under the same single local model and the same LLM-as-judge protocol. The headline finding is sobering and is the opposite of a victory lap. At scale the raw pairwise advantage shrinks to 53.8 percent, and the pairwise judge exhibits a severe position bias: it selects the first-presented option 74.4 percent of the time regardless of content. After controlling for position, the Brain advantage disappears or reverses on four of five tracks. It survives in exactly one place: the longitudinal same-domain track, where the Brain condition is preferred 74 percent of the time even when assigned to the disfavored position. The absolute rubric scores again show near-parity (plus 0.12 overall on a 10-point scale), confirming the ceiling effect at scale. The semantic-retrieval and LLM-abstraction upgrades identified as future work in the first paper were not enabled in this run, so this study measures scale and task diversity, not improved mechanisms. I report the negative and confounded results in full, because they change the honest reading of the first paper.

---

## 1. Introduction and Motivation

The first OrKa Brain paper made a deliberately limited claim: the procedural skill memory loop is buildable and runs end-to-end, it produces a consistent but small and ambiguous pairwise preference, and its absolute quality advantage is suppressed by a ceiling effect. That paper closed with an open question. It identified architectural slots for improvement (LLM-powered abstraction, embedding-based retrieval, vector indexing) and asked whether filling them, or simply testing at larger scale and on more task types, would reveal a meaningful advantage.

This follow-up answers part of that question on the scale-and-diversity axis. It does not yet answer the mechanism axis, because the semantic and abstraction upgrades were not active in this run (Section 2.3). The contribution here is empirical and corrective:

1. An eight-fold larger benchmark (250 tasks) spanning five track types, three of which (anti-pattern avoidance, brain-assisted routing, multi-skill composition) did not exist in the first study.

2. A position-controlled re-analysis of the pairwise protocol, prompted by a position bias so large that the raw pairwise numbers cannot be trusted at face value.

3. An honest revision of the first paper's reading: the ceiling effect is confirmed and strengthened, the cross-domain transfer story weakens further, and the single durable signal is longitudinal same-domain accumulation, although even that signal does not appear as a learning curve in the rubric.

The tone of the first paper was to report negatives as prominently as positives. This follow-up keeps that contract, and the negatives here are larger.

---

## 2. What Changed and What Did Not

### 2.1 Scale and Track Diversity (changed)

The first benchmark had 30 tasks in 2 tracks. This benchmark (OrKa Brain v2 Benchmark Dataset, version 2.0.0) has 250 tasks in 5 tracks of 50 tasks each, for 500 execution runs plus the judge passes. Three track types are new. Section 3 describes them.

### 2.2 Protocol and Model (unchanged)

The execution model is the same single local model used in the first study, openai/gpt-oss-20b served by LM Studio at localhost:1234, offline, with RedisStack on port 6380. The evaluation protocol is the same dual LLM-as-judge design: per-output rubric scoring on six dimensions and side-by-side pairwise comparison with randomized A and B assignment. The judge is the same local model family as the executor, so the self-evaluation caveat from the first paper still applies.

### 2.3 Retrieval Mechanism (unchanged, and this matters)

The first paper's strongest stated limitation was that default retrieval falls back to keyword-set Jaccard arithmetic when no embedding model is configured, and that skill extraction copies execution-trace steps verbatim rather than abstracting them. The v2 brain workflows (the `brain_track_*.yml` files) do not configure a sentence-transformer embedder. By the retrieval design described in the first paper, recall in this run therefore operated in the keyword regime, identical to v1. The verbatim extraction path was likewise unchanged.

The consequence is important for interpretation. This study scales the evaluation; it does not test the semantic-retrieval or LLM-abstraction upgrades. Any reading that "the improved Brain still does not help" would be wrong, because the improved mechanisms were not in the loop. What this study tests is whether the v1-class Brain, given far more tasks and more varied task structures, reveals an advantage that the smaller benchmark missed.

---

## 3. Benchmark v2 Design

Five tracks, 50 tasks each. Each track has a seed or learn phase (typically 10 tasks) that populates the Brain, and a test phase (typically 40 tasks) that exercises recall. The brainless condition runs the same tasks with no memory.

**Table 1: Benchmark v2 Tracks**

| Track | Name | Design | Phase split |
|-------|------|--------|-------------|
| A | Cross-Domain Skill Transfer | Learn procedural patterns in seed domains, then test transfer to 40 novel domains. | 10 learn, 40 recall |
| B | Anti-Pattern Avoidance | Seed 10 anti-patterns, then present 40 tasks that could trigger them. Measures whether the Brain prevents known bad patterns. | 10 seed, 40 test |
| C | GraphScout Brain-Assisted Routing | Seed path skills, then use GraphScout with brain-assisted routing. Measures routing quality with vs without recalled paths. | 10 seed, 40 route |
| D | Multi-Skill Composition | Tasks requiring recall and composition of multiple skill types (recipe plus anti-pattern plus path). | 10 seed, 40 compose |
| E | Longitudinal Learning Curve | 50 sequential same-domain (software engineering and architecture) tasks. Measures whether quality improves over the sequence via accumulation. | 50 sequential |

The brain pipeline and brainless pipeline mirror the first paper: the brain condition adds `brain_learn`, `brain_recall`, and `brain_feedback` steps around the same reasoning and application agents, while the brainless condition runs reasoning and application only. The confounds from that design (extra processing passes, extra context injection) carry over and are discussed in Section 7.

---

## 4. Evaluation Protocol

**Rubric scoring.** An independent judge scores each output on a 1-10 scale across six dimensions (Reasoning Quality, Structural Completeness, Depth of Analysis, Actionability, Domain Adaptability, Confidence Calibration) and an overall score. The judge sees one output at a time and is blind to condition.

**Pairwise comparison.** A judge sees both outputs side by side with randomized A and B labeling and answers three preference questions (Stronger Reasoning, More Complete, More Trustworthy). I derive a per-task overall winner by majority vote across the three questions.

**Coverage.** Of 250 tasks per condition, the rubric judge produced a parseable overall score for 237 brain outputs and 246 brainless outputs; the remainder were unparseable judge responses, not execution failures. The pairwise judge produced 249 decisive comparison records. All denominators below use the parseable counts, following the corrected methodology from the first paper.

Redis brain keys are flushed between conditions to prevent cross-contamination, and the brainless condition runs first.

---

## 5. Results

### 5.1 Rubric Scores: The Ceiling Effect, Confirmed at Scale

**Table 2: Mean Rubric Scores by Condition (overall, all tracks)**

| Dimension | Brain | Brainless | Delta |
|-----------|------:|----------:|------:|
| Reasoning Quality | 8.44 | 8.43 | +0.01 |
| Structural Completeness | 8.66 | 8.47 | +0.19 |
| Depth of Analysis | 7.59 | 7.41 | +0.18 |
| Actionability | 8.55 | 8.35 | +0.20 |
| Domain Adaptability | 8.68 | 8.50 | +0.18 |
| Confidence Calibration | 8.74 | 8.67 | +0.07 |
| **Overall** | **8.39** | **8.27** | **+0.12** |

The overall delta is plus 0.12 on a 10-point scale, statistically indistinguishable from the plus 0.10 reported in the first study. The dimension deltas are all small and all non-negative this time (the first study had a small negative on Structural Completeness). The pattern is the same as before: both conditions produce competent output in the 8 to 9 range, and the gap between them is within noise. At N around 240 per condition the variance is lower than in the first study, but the effect size is not larger. This is the ceiling effect from the first paper, reproduced at eight times the scale.

### 5.2 Pairwise Comparison: The Headline Number Shrinks

**Table 3: Raw Pairwise Wins (all tracks, majority vote)**

| Winner | Count | Share |
|--------|------:|------:|
| Brain | 134 | 53.8% |
| Brainless | 104 | 41.8% |
| Tie | 11 | 4.4% |

**Table 4: Raw Pairwise Wins by Question**

| Question | Brain | Brainless | Tie |
|----------|------:|----------:|----:|
| Stronger Reasoning | 133 | 101 | 15 |
| More Complete | 135 | 100 | 14 |
| More Trustworthy | 135 | 104 | 10 |

The raw pairwise preference for Brain is 53.8 percent, down from 63.3 percent in the first study. The per-question pattern is consistent (Brain preferred on all three), but the margin is smaller and, as the next section shows, the raw number is not trustworthy.

### 5.3 The Position-Bias Problem

The first study noted a position bias: position A was preferred in 60.7 percent of decisive verdicts. In this study the same artifact is far larger. Counting raw A versus B selections across all three questions and all comparisons, the judge chose position A in 527 of 708 cases, a 74.4 percent rate. A judge that picks the first option three times out of four, independent of content, cannot produce a reliable pairwise signal on its own. The randomized A and B assignment means this bias largely cancels in expectation across the whole dataset, but it injects enormous noise, and it can bias any individual track where assignment happened to be uneven. This forces a position-controlled analysis.

### 5.4 Position-Controlled Per-Track Analysis

The honest way to read pairwise data under a 74.4 percent position bias is to ask: when the Brain output was placed in the disfavored position (position B), did it still win? That removes the bias in the Brain's favor and gives a conservative estimate of the true preference. Table 5 reports the raw per-track Brain win rate, the Brain win rate when the Brain was in position A (bias-favored), and the Brain win rate when the Brain was in position B (the fair, conservative estimate).

**Table 5: Position-Controlled Brain Win Rate by Track**

| Track | Design | Raw Brain win | Brain in A (favored) | Brain in B (fair) |
|-------|--------|--------------:|---------------------:|------------------:|
| A | Cross-domain transfer | 42% | 15/22 (68%) | 6/28 (21%) |
| B | Anti-pattern avoidance | 44% | 21/26 (81%) | 2/24 (8%) |
| C | Brain-assisted routing | 31% | 13/17 (76%) | 2/23 (9%) |
| D | Multi-skill composition | 68% | 21/22 (95%) | 13/28 (46%) |
| E | Longitudinal accumulation | 84% | 25/27 (93%) | 17/23 (74%) |

The gap between the "favored" and "fair" columns is the position bias made visible. Reading the fair column:

- **Tracks A, B, and C: the Brain loses.** In the position-controlled comparison the Brain is preferred only 8 to 21 percent of the time. Cross-domain transfer and anti-pattern avoidance, the two capabilities these tracks were designed to test, show no Brain advantage and in fact a preference for the stateless baseline.

- **Track D (composition): a coin flip.** The raw 68 percent collapses to 46 percent once position is controlled. The apparent strong win was mostly the Brain landing in position A. There is no defensible composition advantage in this run.

- **Track E (longitudinal): a real signal.** The Brain is preferred 74 percent of the time even when placed in the disfavored position. This is the only track where the advantage survives the bias control, and it is the strongest result in the benchmark.

Aggregating the fair (Brain-in-B) comparisons across tracks A, B, D, and E (excluding the confounded Track C, see Section 5.6), the Brain wins only 38 of 103, or 37 percent. In other words, once position bias is removed, the pooled pairwise preference reverses: the stateless baseline is preferred, except in the longitudinal track.

### 5.5 Track E: Preference Without a Learning Curve

Track E is the one place the Brain shows a durable advantage, so it deserves scrutiny. The track runs 50 sequential same-domain tasks, and the hypothesis is compounding: Brain quality should rise over the sequence as skills accumulate, while brainless quality stays flat. Table 6 reports the mean overall rubric score by block of ten sequential tasks.

**Table 6: Track E Rubric Overall Score by Sequence Block**

| Tasks | Brain | Brainless | Brain minus Brainless |
|-------|------:|----------:|----------------------:|
| 1-10 | 9.18 | 8.87 | +0.31 |
| 11-20 | 9.00 | 8.75 | +0.25 |
| 21-30 | 8.71 | 8.90 | -0.19 |
| 31-40 | 8.98 | 8.53 | +0.45 |
| 41-50 | 8.73 | 8.55 | +0.18 |

The Brain condition is above the baseline in four of the five blocks, which is consistent with the pairwise preference. But there is no learning curve. Both conditions drift slightly downward over the sequence (Brain from 9.18 to 8.73, brainless from 8.87 to 8.55). The Brain does not improve as skills accumulate; it sits at a roughly constant small offset above the baseline from the very first block.

This is an important qualification. The Track E pairwise signal is real and survives position control, but the rubric data does not support the specific mechanism the track was designed to demonstrate (compounding over time). The most defensible reading is that recalled same-domain context makes individual outputs marginally and consistently more preferable, not that the system learns across the sequence. The compounding hypothesis from the first paper remains untested by positive evidence.

### 5.6 Track C: Brain-Assisted Routing, Confounded

Track C measures GraphScout routing quality with brain-assisted recall. Two facts make its results uninterpretable in this run. First, absolute scores are low for both conditions (Brain overall 5.94, brainless 5.57), well below the 8 to 9 range of the other tracks, which suggests the rubric was applied to routing decisions rather than full task outputs and is not directly comparable. Second, and more important, the Track C execution outputs were generated before a set of GraphScout correctness fixes landed in the engine (candidate-path deduplication, activation of the commit-margin logic that was previously dead under the require-terminal path, and removal of routing out of terminal nodes). The routing condition is therefore confounded by a since-corrected implementation, and Track C should be re-run before any claim is made about brain-assisted routing. I exclude it from the pooled fair estimate in Section 5.4 for this reason. I report it here only for completeness and to flag the re-run.

---

## 6. Discussion

### 6.1 What v2 Confirms

The ceiling effect is the most robust finding across both studies. At 30 tasks and at 250 tasks, with two track types and with five, the absolute rubric gap between Brain and brainless is about one tenth of a point on a 10-point scale. The underlying model already knows the procedural patterns the keyword-based Brain recalls, so recalling them adds little. Scaling the benchmark did not change this. If anything, the larger sample makes the near-parity more credible, because it is no longer attributable to small-sample noise.

### 6.2 What v2 Overturns or Weakens

The first paper's most quotable number was the 63.3 percent pairwise preference. This follow-up shows that number was fragile in two ways. It shrinks to 53.8 percent at scale, and it rests on a pairwise protocol whose position bias has grown to 74.4 percent. The position-controlled analysis is the key correction: pooled across tracks, with the Brain in the disfavored position, the preference reverses to 37 percent. The honest statement is that this benchmark does not show a general pairwise advantage for the keyword-based Brain. It shows a track-specific one.

The cross-domain transfer claim weakens further. Track A was built precisely to test transfer to 40 novel domains, and in the fair comparison the Brain wins 21 percent of the time. The anti-pattern track is worse for the Brain (8 percent). These are the capabilities a procedural memory is supposed to deliver, and the keyword-based implementation does not deliver them here.

### 6.3 The One Durable Signal

Track E is the result worth carrying forward. A preference that survives a 74 percent position bias (74 percent Brain wins in the disfavored position) is not noise. Same-domain recall produces consistently more preferable outputs in a long sequential workload. The caveat from Section 5.5 stands: this is a level offset, not a learning curve, and its cause could still be context injection rather than the specific content of recalled skills. But it is the strongest evidence in either paper that persistent memory does something useful, and it points the next experiments at long-horizon, same-domain workloads rather than one-shot cross-domain transfer.

### 6.4 Why the Position Bias Dominates the Story

It would be easy to report the raw 53.8 percent and the strong raw Track D and E numbers and call the follow-up a partial success. The 74.4 percent position bias makes that dishonest. Any pairwise result from this judge, on this model, must be position-controlled or counterbalanced before it means anything. The first paper recommended counterbalanced evaluation as future work. This follow-up promotes it from a nice-to-have to a precondition: without it, the pairwise protocol on this model is not a measurement instrument.

---

## 7. Threats to Validity

1. **Position bias (dominant).** At 74.4 percent first-position preference, the raw pairwise numbers are unreliable. The position-controlled analysis mitigates this but halves the effective sample per track, widening the uncertainty on each track estimate.

2. **Pipeline-length and context-injection confound.** As in the first study, the Brain condition adds agent steps and injects recalled context into the application prompt. Any surviving advantage, including Track E, could stem from extra context rather than skill recall specifically. An ablation with a length-matched brainless pipeline is still needed.

3. **Single model, single run, self-evaluation.** All outputs come from one local model on one run, judged by the same model family. Non-determinism is uncontrolled, and self-preference is possible. Multiple runs with mean and standard deviation, and a judge from a different model family, would strengthen every number here.

4. **Mechanisms not under test.** The semantic embedder and LLM-powered abstraction were not enabled. This study cannot speak to whether those upgrades help. It can only say that the keyword-based v1-class Brain does not show a general advantage at scale.

5. **Track C confound.** The routing track ran on a since-corrected GraphScout and is excluded from pooled conclusions.

6. **Unparseable judge outputs.** 13 brain and 3 brainless rubric outputs and one pairwise comparison were unparseable. These are dropped, not imputed, which slightly reduces the effective sample.

---

## 8. Revised Future Work

The first paper's future-work list stands, with reordered priorities driven by these results:

1. **Counterbalanced pairwise evaluation is now mandatory, not optional.** Every pair must be run twice with swapped positions, or the pairwise protocol on this model should be abandoned in favor of rubric-only or a different judge.

2. **Re-run Track C after the GraphScout fixes.** The brain-assisted routing claim is currently untestable from this data.

3. **Enable the mechanisms before claiming they fail.** Configure the sentence-transformer embedder and wire LLM-powered abstraction into the learn step, then re-run at least Tracks A and B (cross-domain transfer and anti-pattern avoidance), which are where the keyword Brain failed most clearly and where semantic recall should help most.

4. **Focus on long-horizon same-domain workloads.** Track E is where the signal lives. Extend it (longer sequences, harder accumulation) and add a length-matched control to isolate recall from context injection.

5. **Multiple runs and a cross-family judge** to put error bars on every figure and remove the self-evaluation caveat.

---

## 9. Conclusion

This follow-up scaled the OrKa Brain evaluation from 30 tasks to 250 across five track types and re-examined the pairwise protocol that produced the first paper's headline. The result is a correction more than an advance. The ceiling effect is confirmed and strengthened: at scale, absolute rubric quality is near-identical between the Brain and a stateless baseline (plus 0.12 on 10). The raw pairwise preference shrank from 63.3 to 53.8 percent, and a 74.4 percent position bias means even that smaller number cannot be read directly. Position-controlled, the pooled preference reverses to favor the stateless baseline, with one exception: the longitudinal same-domain track, where the Brain is preferred 74 percent of the time even from the disfavored position, although without the upward learning curve the track was designed to show.

The keyword-based Brain, evaluated honestly and at scale, does not demonstrate the cross-domain transfer or anti-pattern avoidance it was built to provide. It demonstrates one thing: in a long, same-domain workload, recalling prior context yields consistently and slightly more preferable outputs. Whether the semantic-retrieval and abstraction upgrades change that picture is the next experiment, and it is now clear which tracks to run it on. The first paper said the plumbing works and the question is whether better mechanisms fill it usefully. This paper narrows the question: the plumbing works, the keyword fill does not help in general, and the only place it helps is the place the next study should push hardest.

---

## Appendix A: Reproduction

```bash
orka-start                    # RedisStack with search module
# LM Studio with openai/gpt-oss-20b on localhost:1234
cd examples/benchmark_v2

# Execute both conditions (brain and brainless) across all tracks
python run_benchmark_v2.py --include-baseline

# Score existing results with the local judge (resumable)
python judge_benchmark.py --output-tag local --skip-existing

# Aggregate into a report
python aggregate_benchmark.py --judge-tag local
```

The aggregator supports `--exclude-tracks C` to drop the confounded routing track from overall figures.

## Appendix B: Raw v2 Aggregates

### B.1 Overall Rubric (parseable denominators)

| Condition | n_scored | Overall mean |
|-----------|---------:|-------------:|
| Brain | 237 | 8.39 |
| Brainless | 246 | 8.27 |

### B.2 Per-Track Rubric Overall

| Track | Brain | Brainless | Delta |
|-------|------:|----------:|------:|
| A | 9.29 | 9.22 | +0.07 |
| B | 9.23 | 9.29 | -0.06 |
| C | 5.94 | 5.57 | +0.37 |
| D | 8.61 | 8.50 | +0.11 |
| E | 8.86 | 8.73 | +0.13 |

### B.3 Pairwise (raw, majority vote, n=249)

| | Brain | Brainless | Tie |
|---|------:|----------:|----:|
| Overall | 134 | 104 | 11 |
| Stronger Reasoning | 133 | 101 | 15 |
| More Complete | 135 | 100 | 14 |
| More Trustworthy | 135 | 104 | 10 |

### B.4 Position Bias and Fair Estimate

| Metric | Value |
|--------|------:|
| First-position (A) selection rate | 74.4% (527/708) |
| Brain win rate, raw (all tracks) | 53.8% |
| Brain win rate, fair (Brain in B), tracks A,B,D,E | 37% (38/103) |
| Track E Brain win rate, fair (Brain in B) | 74% (17/23) |

### B.5 Configuration

| Parameter | Value |
|-----------|-------|
| Model (execution and judge) | openai/gpt-oss-20b (LM Studio, localhost:1234) |
| Embedder | not configured (keyword Jaccard recall) |
| Redis | RedisStack on port 6380 |
| Tasks | 250 (5 tracks x 50) |
| Conditions | brain, brainless (Redis flushed between) |
