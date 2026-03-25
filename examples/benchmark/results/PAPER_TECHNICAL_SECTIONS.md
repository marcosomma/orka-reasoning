# Procedural Skill Memory for LLM Agent Systems: Architecture, Benchmark, and Honest Limits of a First Implementation

**Marco Somma**
Independent Researcher, Barcelona, Spain
Creator of OrKa (Orchestrator Kit Agents)

---

## Abstract

Current AI agent systems operate primarily as stateless executors: they do not retain procedural experience across tasks. I propose five desirable properties for experience-driven agent systems and present OrKa Brain, an open-source prototype that implements a procedural skill memory loop (learn, persist, retrieve, apply, feedback, decay) within a YAML-based LLM agent orchestration framework. I evaluate the system on a 30-task benchmark across two tracks (cross-domain transfer and same-domain accumulation) using an LLM-as-judge evaluation protocol. Results show a consistent but modest advantage for the Brain-augmented condition: 63.3% pairwise win rate, with the strongest signal in perceived trustworthiness (19/28 wins). Absolute rubric deltas remain small (+0.10 overall on a 10-point scale), revealing a ceiling effect: the underlying LLM already possesses the procedural knowledge the Brain recalls. The current implementation uses rule-based keyword extraction rather than semantic understanding, and the benchmark carries significant confounds (unequal pipeline lengths, single model, single run). I report both the positive signals and the negative ones, identify the bottlenecks, and outline the architectural slots designed for progressive upgrade.

---

## 1. Introduction

### 1.1 The Statelessness Problem

Large language models generate coherent text, write code, and reason through multi-step problems. Yet current LLM-based agent systems share a structural limitation: they are *stateless across invocations*. Each workflow starts fresh. No experience persists. No feedback loop refines future performance based on past outcomes.

A useful analogy comes from human economic history. Hunting requires genuine intelligence (pattern recognition, spatial reasoning, improvisation) but each hunt is largely independent. Agriculture introduced a qualitatively different dynamic: *delayed feedback loops*. The farmer acts now, evaluates later, and modifies the environment to encode accumulated knowledge for the next cycle. Intelligence stops being a momentary capability and becomes infrastructure.

This analogy is motivating, not a claim. I do not argue that the system presented here achieves "farming-phase AI." I use the analogy to identify a structural gap: current multi-agent orchestrators (CrewAI, LangChain, AutoGen) do not accumulate procedural experience across invocations. Each workflow starts from zero. The question this paper explores is whether a persistent skill memory loop can begin to close that gap, and what happens when it does.

### 1.2 Five Desirable Properties for Experience-Driven Agent Systems

I propose five properties that an experience-driven agent system should aim for. These are design goals, not proven requirements. No claim is made that all five are necessary, that this list is exhaustive, or that achieving them guarantees improved outcomes.

1. **Long feedback loops.** The system should act, observe outcomes, and incorporate that feedback into future behavior across a time horizon longer than a single invocation.

2. **Persistent memory.** Useful state should survive across sessions, not just within a conversation window. Memory should be durable, queryable, and managed (not unbounded growth).

3. **Reusable skill from experience.** The system should extract transferable procedures from concrete execution traces, not merely store raw transcripts.

4. **Cross-domain transfer.** A procedure learned in one domain should be retrievable and applicable in a structurally similar but semantically different domain.

5. **Compounding over time.** Performance should improve as experience accumulates. Unused or unsuccessful patterns should decay.

No single component is novel in isolation. Episodic memory systems exist (MemGPT/Letta). Skill libraries exist (Voyager, in Minecraft). Reflection mechanisms exist (Reflexion). Classical cognitive architectures have procedural memory (ACT-R, SOAR). The combination of all five in a general-purpose LLM agent framework is, to my knowledge, underexplored, but this claim is difficult to verify exhaustively and should not be read as a strong novelty statement.

### 1.3 Contribution

This paper makes three contributions:

1. A *checklist* of five desirable properties for experience-driven agent systems, intended as a design guide rather than a theoretical framework.

2. *OrKa Brain*, an open-source prototype of a procedural skill memory loop (learn, persist, retrieve, apply, feedback, decay) integrated into the OrKa agent orchestration framework. The current implementation uses rule-based extraction and keyword-based retrieval.

3. An *empirical evaluation* on a 30-task benchmark, reporting both positive signals (consistent pairwise preference) and negative signals (flat rubric scores, ceiling effect, untested failure path), with a discussion of confounds and a roadmap for progressive enhancement.

---

## 2. Related Work

### 2.1 Agent Memory Systems

**MemGPT / Letta** (Packer et al., 2023) introduces a virtual memory management system for LLMs, enabling persistent context across conversations. The memory is *episodic*: it stores conversation segments and retrieved documents. It does not extract procedural abstractions or support cross-domain transfer of learned skills.

**Voyager** (Wang et al., 2023) builds a skill library for Minecraft agents, storing executable JavaScript functions that can be retrieved for new tasks. This is genuine procedural memory, but scoped to a single environment (Minecraft) and storing code rather than abstract transferable procedures.

**Reflexion** (Shinn et al., 2023) implements self-reflection, storing verbal feedback about task failures. The memory is evaluative (what went wrong) rather than procedural (how to do it differently). It does not persist across sessions or transfer across domains.

**Generative Agents** (Park et al., 2023) simulate human-like memory with retrieval, reflection, and planning. Memory is primarily narrative and social, not procedural. The system does not extract reusable skills or compound performance over time.

### 2.2 Cognitive Architectures

**ACT-R** (Anderson et al., 2004) and **SOAR** (Laird, 2012) are classical cognitive architectures with explicit procedural memory in the form of production rules. These systems predate LLMs and operate on symbolic representations. They demonstrate that procedural memory is a well-established concept in cognitive science but have not been integrated with modern language model capabilities.

### 2.3 The Gap

The combination of *procedural skill persistence*, *cross-domain retrieval*, *feedback-driven calibration*, and *temporal management* in a general-purpose LLM agent framework appears underexplored, though absence of evidence is not evidence of absence. Table 1 summarizes the landscape as I understand it.

**Table 1: Memory Capabilities in Existing Agent Systems**

| System | Memory Type | Procedural | Cross-Domain | Feedback Loop | Temporal Decay | General-Purpose |
|--------|------------|:----------:|:------------:|:-------------:|:--------------:|:---------------:|
| MemGPT | Episodic | No | No | No | No | Yes |
| Voyager | Code library | Partial | No | No | No | No (Minecraft) |
| Reflexion | Verbal feedback | No | No | Partial | No | Yes |
| ACT-R/SOAR | Production rules | Yes | Limited | Yes | No | No (pre-LLM) |
| RAG systems | Document chunks | No | No | No | No | Yes |
| **OrKa Brain** | **Procedural skills** | **Yes** | **Attempted** | **Yes** | **Yes** | **Yes** |

---

## 3. System Architecture

### 3.1 Overview

OrKa Brain is a procedural skill memory module within the OrKa agent orchestration framework. OrKa is a YAML-first system where workflows are defined declaratively and executed by composing typed agents (LLM, memory, search, brain, router, etc.) in sequential or parallel pipelines. Brain integrates into this pipeline as three agent steps: `brain_learn`, `brain_recall`, and `brain_feedback`.

The skill memory loop operates as follows:

```
Input Task
    |
    v
[task_reasoner]  -- LLM produces step-by-step analysis
    |
    v
[brain_learn]    -- Extract abstract skill from reasoning
    |
    v
[brain_recall]   -- Retrieve applicable skills from memory
    |
    v
[task_applier]   -- LLM solves task, guided by recalled skill
    |
    v
[brain_feedback] -- Record transfer success/failure
    |
    v
[task_result]    -- Format structured output
```

Skills persist in Redis across invocations. The feedback step adjusts confidence scores and builds transfer history records, creating a potential compounding mechanism (though in this benchmark, feedback never recorded a failure, so compounding was not fully exercised).

### 3.2 Skill Data Model

A skill is represented as a structured object with the following fields:

```
Skill:
  id:                UUID
  name:              str   (auto-generated from cognitive pattern + structure + domain)
  description:       str   (abstract goal + first 3 step actions)
  domain:            str   (source domain)
  steps:             [SkillStep]  (action, description, expected_outcome)
  preconditions:     [SkillCondition]  (input_shape, task_structure guards)
  postconditions:    [SkillCondition]  (output_shape, quality threshold)
  confidence:        float  (0.0-1.0, starts at min(0.7, 0.5 + quality * 0.2))
  usage_count:       int
  transfer_history:  [{source_domain, target_domain, success, timestamp}]
  created_at:        ISO 8601 timestamp
  updated_at:        ISO 8601 timestamp
  expires_at:        ISO 8601 timestamp (TTL)
```

**SkillStep** captures individual procedural actions (what to do, why, expected result). **SkillCondition** captures preconditions and postconditions as typed predicates.

### 3.3 Skill Extraction (learn)

The `learn` operation takes an execution context (task description, execution trace, outcome) and produces a Skill object through five deterministic extraction steps:

1. **Context analysis.** A rule-based analyzer scans the task description for keywords mapped to cognitive patterns (e.g., "analyze", "examine" -> `analysis`) and task structures (e.g., "break down", "split" -> `decomposition`). Ten cognitive patterns and ten task structures are recognized, each defined by a curated keyword list.

2. **Procedure extraction.** The execution trace's steps are mapped one-to-one into SkillStep objects. The action description is preserved verbatim from the trace.

3. **Precondition extraction.** Input shape (single text, list, structured) and detected task structures are converted into typed predicates.

4. **Postcondition extraction.** Output shape and outcome quality become postcondition predicates.

5. **Deduplication.** A fingerprint hash of sorted tags is compared against existing skills. If Jaccard similarity with an existing skill exceeds 0.7, the existing skill's usage count is incremented and its TTL is renewed instead of creating a duplicate.

**Transparency note.** The `learn` operation is entirely deterministic. No LLM is invoked during skill extraction. The procedure steps are verbatim copies of the execution trace actions, not abstractions generated by the LLM. The context analyzer uses hardcoded keyword matching, not semantic understanding. This is an intentional design choice for the v1 implementation: it prioritizes reproducibility and debuggability over sophistication. Section 7.2 discusses the planned upgrade to LLM-powered abstraction.

### 3.4 Skill Retrieval (recall)

The `recall` operation finds applicable skills for a target task through four-dimensional scoring:

1. **Structural score (weight: 0.35).** Jaccard similarity between the target's detected cognitive patterns and task structures and those of the candidate skill.

2. **Semantic score (weight: 0.25).** When an embedding model is provided, cosine similarity between sentence-transformer encodings of the skill and target context. When no embedder is configured (the default), falls back to Jaccard similarity on bag-of-words tokenization.

3. **Transfer history score (weight: 0.25).** Success rate from the skill's transfer history (`successes / total_transfers`), defaulting to 0.5 when no history exists.

4. **Confidence score (weight: 0.15).** The skill's current confidence value.

Retrieval is a full scan of all stored skills followed by scoring and top-k selection. The current implementation does not use vector indexes or inverted indexes for candidate retrieval.

**Transparency note.** Without an embedding model (the default configuration), the structural and semantic dimensions both reduce to keyword-set Jaccard arithmetic. The scoring system is designed to accommodate real embeddings as a drop-in upgrade without changing the retrieval interface. The full-scan retrieval is adequate for the current skill counts (tens to hundreds) but would require indexing for production-scale deployments.

### 3.5 Feedback and Confidence Calibration

The `brain_feedback` agent records whether a recalled skill was successfully applied in the target context. On success, the skill's confidence is incremented by 0.05 and a positive transfer record is appended. On failure, confidence is decremented by 0.10 and a negative record is appended. This asymmetric update penalizes failures more heavily than it rewards successes, implementing conservative calibration.

### 3.6 Temporal Decay (TTL)

Each skill has a computed time-to-live based on usage and confidence:

$$TTL = 168h \times (1 + \log_2(\max(1, usage\_count))) \times (0.5 + confidence)$$

The base TTL is one week (168 hours). Heavily used, high-confidence skills live longer (up to ~37 days at 9 uses and 79% confidence). Rarely used or low-confidence skills decay within 8 days. Only successful usage renews the TTL. Expired skills are hard-deleted from Redis during periodic cleanup.

### 3.7 Skill Graph

Skills are stored in Redis as JSON objects and organized via:

- **Name index** (Redis hash): maps skill IDs to names for quick lookup.
- **Tag sets** (Redis sets): each tag maintains a set of skill IDs, enabling tag-based queries.
- **Bidirectional edges** (Redis sets): skills with co-occurring tags are linked, enabling BFS traversal for related skill discovery.

---

## 4. Experimental Evaluation

### 4.1 Benchmark Design

I evaluate OrKa Brain against a stateless baseline on a 30-task benchmark across two tracks:

**Track A: Cross-Domain Transfer (10 tasks).** Three *learn* phases teach the Brain procedural patterns in distinct domains (text analysis, customer support, creative writing). Seven *recall* phases test whether those patterns transfer to unrelated domains (code review, content moderation, code optimization, financial analysis, API infrastructure, education, DevOps incident response). Each recall task is structurally similar to one of the learned patterns but semantically different.

**Track B: Same-Domain Accumulation (20 tasks).** Twenty veterinary diagnostic cases run sequentially. Each case exercises the full cognitive loop. The Brain condition accumulates domain-specific skills across the sequence. The baseline restarts from zero each time.

### 4.2 Conditions

**Brain condition (6-agent pipeline):**
`task_reasoner -> brain_learn -> brain_recall -> task_applier -> brain_feedback -> task_result`

**Brainless condition (3-agent pipeline):**
`task_reasoner -> task_applier -> task_result`

The `task_reasoner` prompt is identical in both conditions. The `task_applier` prompt in the Brain condition includes recalled skill information; in the Brainless condition it explicitly states "You have NO prior experience with similar tasks and NO recalled skills." The `task_result` prompt and output format are identical.

**Confound acknowledgment.** The Brain condition includes three additional agent steps (brain_learn, brain_recall, brain_feedback), which means the input is processed by the LLM more times. Any observed improvement could be partially attributed to additional processing passes rather than skill recall itself. Section 6 discusses this limitation.

### 4.3 LLM Configuration

All experiments use a single local model via LM Studio:

| Parameter | Value |
|-----------|-------|
| Model | openai/gpt-oss-20b |
| Provider | LM Studio (localhost:1234) |
| Temperature | 0.3 (execution), 0.1 (judge) |
| Environment | Offline, no API calls |
| Redis | RedisStack on port 6380 |

### 4.4 Evaluation Protocol

I employ two complementary LLM-as-judge evaluation methods:

**Rubric scoring.** An independent judge scores each output on six dimensions (1-10 scale): *Reasoning Quality*, *Structural Completeness*, *Depth of Analysis*, *Actionability*, *Domain Adaptability*, and *Confidence Calibration*. The judge sees one output at a time and is blind to the condition.

**Pairwise comparison.** A judge sees both outputs side by side (randomized A/B labeling) and answers three preference questions: *Stronger Reasoning*, *More Structurally Complete*, *More Trustworthy*. The judge does not know which output is Brain-augmented.

Redis brain keys are flushed between conditions to prevent cross-contamination. The brainless condition runs first.

### 4.5 Execution

The full benchmark was executed via an automated Python runner script:

| Phase | Duration |
|-------|----------|
| Brainless (30 tasks) | 517s (8.6 min) |
| Brain (30 tasks) | 595s (9.9 min) |
| Rubric judge (60 evaluations) | 293s (4.9 min) |
| Pairwise judge (28 comparisons) | 126s (2.1 min) |
| **Total** | **1531s (25.5 min)** |

The Brain condition took 15% longer than the Brainless condition, reflecting the overhead of three additional agent steps per task.

---

## 5. Results

### 5.1 Rubric Scores: Marginal Absolute Difference

**Table 2: Mean Rubric Scores by Condition (N=30 tasks)**

| Dimension | Brain | Brainless | Delta |
|-----------|------:|----------:|------:|
| Reasoning Quality | 7.82 | 7.54 | +0.28 |
| Structural Completeness | 8.25 | 8.29 | -0.04 |
| Depth of Analysis | 6.43 | 6.43 | 0.00 |
| Actionability | 8.00 | 7.96 | +0.04 |
| Domain Adaptability | 8.43 | 8.32 | +0.11 |
| Confidence Calibration | 7.68 | 7.64 | +0.04 |
| **Overall** | **7.80** | **7.70** | **+0.10** |

The overall delta is +0.10 on a 10-point scale. Reasoning Quality shows the largest positive delta (+0.28). Structural Completeness shows a marginal negative delta (-0.04). Depth of Analysis is identical.

**These deltas are not statistically meaningful.** At N=30 with this variance, a 0.10-point difference falls well within noise. I do not claim statistical significance.

### 5.2 Pairwise Comparison: Consistent Qualitative Preference

**Table 3: Pairwise Wins by Condition (Overall Preference)**

| Winner | Track A (n=10) | Track B (n=20) | Combined (n=30) |
|--------|---:|---:|---:|
| Brain | 7 | 12 | **19** (63.3%) |
| Brainless | 2 | 7 | **9** (30.0%) |
| Tie | 1 | 1 | **2** (6.7%) |

**Table 4: Pairwise Wins by Question (Combined)**

| Question | Brain | Brainless | Tie |
|----------|------:|----------:|----:|
| Stronger Reasoning | 18 | 10 | 0 |
| More Complete | 17 | 10 | 1 |
| More Trustworthy | 19 | 9 | 0 |

The pairwise judge preferred Brain outputs in 63.3% of comparisons. The advantage is consistent across all three quality dimensions. Trustworthiness shows the strongest signal (67.9% brain preference). Track A shows a stronger effect (70% brain wins) than Track B (60% brain wins).

**Position bias caveat.** Position A was preferred in 60.7% of decisive verdicts regardless of condition. This is a known artifact of pairwise LLM judges. Some brainless wins may reflect position bias when brainless was assigned to position A. A counterbalanced design (running each pair twice with swapped positions) would yield a more robust signal.

### 5.3 Rubric vs Pairwise Divergence

The rubric and pairwise evaluations tell different stories: rubric sees near-parity while pairwise sees a 2:1 preference. This divergence is well-documented in LLM evaluation literature. Pairwise comparison is more sensitive to relative quality differences that fall below the granularity of absolute integer scales. When both outputs score 8/10 on reasoning quality, they appear tied in the rubric. But side-by-side, one may demonstrate noticeably more coherent structure, which the pairwise judge detects.

I consider both signals valid. The rubric establishes that both conditions produce competent output in the 7-8 range. The pairwise establishes that when directly compared, Brain outputs are more often preferred.

### 5.4 Track A: Cross-Domain Transfer

**Table 5: Track A Per-Task Rubric Scores**

| Task | Domain | Expected Transfer | Brain | Brainless | Delta |
|------|--------|-------------------|------:|----------:|------:|
| a_01 (learn) | Text Analysis | - | 7.50 | 8.17 | -0.67 |
| a_02 (learn) | Customer Support | - | 7.83 | 4.17 | **+3.66** |
| a_03 (learn) | Creative Writing | - | 6.83 | 4.50 | **+2.33** |
| a_04 (recall) | Code Review | Decompose-Analyze-Synthesize | 8.00 | 8.17 | -0.17 |
| a_05 (recall) | Content Moderation | Validate-Classify-Route | 8.50 | 7.83 | +0.67 |
| a_06 (recall) | Code Optimization | Iterative Refinement | 8.17 | 9.17 | -1.00 |
| a_07 (recall) | Financial Analysis | Decompose-Analyze-Synthesize | 7.30 | 8.17 | -0.87 |
| a_08 (recall) | API Infrastructure | Validate-Classify-Route | 8.33 | 8.17 | +0.16 |
| a_09 (recall) | Education | Iterative Refinement | 8.33 | 1.33 | **+7.00** |
| a_10 (recall) | DevOps | Decompose-Analyze-Synthesize | 8.17 | 8.17 | 0.00 |

**Mean delta: +1.11** (heavily influenced by outliers).

Three tasks dominate the aggregate: a_02 (+3.66), a_03 (+2.33), and a_09 (+7.00). In the a_09 case, the brainless condition produced a catastrophic failure (overall score 1.33), likely a generation failure rather than a quality difference. Excluding a_09, the mean delta drops to +0.46.

Among the seven *recall* tasks (a_04 through a_10), where cross-domain transfer is directly tested, results are mixed: Brain wins 3, Brainless wins 2, ties 2. The mean recall-only delta is +0.83, again dominated by the a_09 outlier. Excluding a_09, recall-only delta is -0.20.

**Interpretation.** The rubric data does not show a clear cross-domain transfer advantage. The tasks where Brain and Brainless both succeed, they score comparably. The variance is driven by occasional generation failures in one condition or the other, not by systematic quality differences attributable to skill recall. The pairwise judge, however, preferred Brain in 7 of 10 Track A comparisons, suggesting qualitative differences the rubric does not capture.

### 5.5 Track B: Same-Domain Accumulation

**Table 6: Track B Accumulation Trend Analysis**

| Segment | Brain Mean | Brainless Mean | Brain - Brainless |
|---------|----------:|---------------:|------------------:|
| Cases 1-5 | 6.77 | 8.26 | -1.49 |
| Cases 6-10 | 8.49 | 8.33 | +0.16 |
| Cases 11-15 | 8.03 | 8.23 | -0.20 |
| Cases 16-20 | 8.23 | 8.03 | +0.20 |

The Brain condition shows an improvement from the first quintile (6.77) to the last (8.23), a gain of +1.46 points. The Brainless condition shows slight degradation from 8.26 to 8.03 (-0.23 points).

However, the first-quintile Brain average is suppressed by a catastrophic failure on b_03 (score: 1.33). Excluding b_03, the first-quintile Brain average rises to 8.13, reducing the apparent improvement to +0.10.

**Interpretation.** There is a weak accumulation signal: Brain trends slightly upward while Brainless trends slightly downward. The late-stage advantage (cases 16-20, delta +0.20) is consistent with accumulated experience providing marginal benefit. But the effect is small and the early-stage deficit (driven by one outlier) makes the trend appear more dramatic than it is.

### 5.6 Skill Inventory

After processing all 30 tasks, the Brain accumulated 21 distinct skills with the following characteristics:

| Metric | Value |
|--------|-------|
| Skills created | 21 |
| Skills deduplicated (merged) | 9 (30 tasks - 21 skills) |
| Total transfers recorded | 30 |
| Average confidence | 72% |
| Confidence range | 69% - 79% |
| TTL range | 8 - 37 days |
| Success rate | 100% (all transfers marked successful) |

Most-used skills:

| Skill | Uses | Confidence | TTL | Transfers |
|-------|-----:|----------:|----:|----------:|
| Evaluation via Validation | 9 | 79% | 37d | 8 |
| Extraction via Routing | 8 | 78% | 35d | 5 |
| Evaluation via Filtering | 6 | 76% | 31d | 4 |
| Generation via Comparison | 5 | 75% | 28d | 4 |

The TTL formula produces visible, sensible differentiation: heavily used skills earn longer lifespans. Deduplication successfully consolidated 30 task-level procedures into 21 distinct skills.

The 100% success rate is a limitation: the feedback mechanism never recorded a failure, preventing confidence from decreasing. This means the "learns from mistakes" capability of the architecture is untested in this benchmark.

---

## 6. Discussion

### 6.1 What the Results Show

The benchmark provides three findings, all of which should be read with the confounds in Section 6.2 in mind:

**Finding 1: The loop runs end-to-end.** Skills are learned, persisted, retrieved across domains, applied, and tracked with feedback. TTL decay and deduplication function as designed. 21 distinct skills emerged from 30 tasks with a working transfer history. This establishes that the architecture is *implementable*. It does not, by itself, establish that the architecture is *useful*.

**Finding 2: The quality advantage is small and ambiguous.** The pairwise judge preferred Brain outputs 63.3% of the time, with the strongest signal in trustworthiness. The rubric shows near-parity (+0.10 overall). Both evaluation methods agree that both conditions produce competent output. The pairwise preference is a real signal, but its cause is ambiguous: it could reflect skill recall, additional context injection, or simply pipeline length effects.

**Finding 3: The LLM already knows what the Brain recalls.** The marginal rubric deltas, especially the zero delta on Depth of Analysis, suggest a ceiling effect. The underlying LLM (gpt-oss-20b) has already internalized procedural patterns like decompose-analyze-synthesize and validate-classify-route through pre-training. The Brain is recalling knowledge the LLM already possesses. Its contribution, if any, is prompting the LLM to *apply* that knowledge more consistently, not teaching it something new.

### 6.2 Confounding Variables

**Pipeline length.** The Brain condition uses 6 agents (3 LLM calls) while the Brainless condition uses 3 agents (3 LLM calls). Although both make the same number of LLM calls, the Brain pipeline injects recalled skill data into the `task_applier` prompt, providing additional context. Some improvement may stem from this context enrichment rather than the specific content of recalled skills.

**Position bias.** Position A was preferred 60.7% of the time in pairwise evaluation. This inflates whichever condition happened to be assigned to position A more often. Counterbalanced evaluation (running each pair twice with swapped positions) would address this.

**Single model, single run.** Results are from one model (gpt-oss-20b) on one run. LLM outputs are non-deterministic even at temperature 0.3. Multiple runs with mean and standard deviation reporting would strengthen the evidence.

**100% feedback success.** The feedback mechanism never recorded a failure, preventing the system from demonstrating error-correction behavior. A more granular feedback mechanism that can assess transfer quality (not just task success) is needed.

### 6.3 What Can and Cannot Be Claimed

It would be easy to cherry-pick the a_09 result (+7.00 delta) and the 70% Track A pairwise win rate and present them as proof of cross-domain transfer. I choose not to do that. The a_09 result is a brainless generation failure, not a brain success story. The rubric data shows near-parity once outliers are removed.

What the results *do* support:

1. **The architecture is implementable and runs reliably.** The skill memory loop completes end-to-end without failures across 30 tasks. Skills persist, deduplicate, decay, and transfer. This is an engineering result, not a cognitive one.

2. **A detectable pairwise signal exists, but its cause is ambiguous.** The 63.3% pairwise win rate is above chance, but the confounds (pipeline length, position bias, single run) make it impossible to attribute this to skill recall specifically.

3. **The bottleneck is abstraction, not plumbing.** The loop works. What limits the system is that skills are stored as verbatim copies of execution trace actions rather than generalized, domain-independent procedures. The context analyzer uses keyword matching, not comprehension. These are implementation limitations of a v1 prototype.

### 6.4 The Ceiling Effect Hypothesis

The most important insight from this benchmark is the *ceiling effect*: the underlying LLM already possesses the procedural knowledge the Brain recalls. Patterns like "decompose, analyze, synthesize" and "validate, classify, route" are well-represented in the LLM's training data. Telling the LLM to use a pattern it already knows provides marginal benefit.

This predicts that the Brain's advantage would be larger in two scenarios:

- **Tasks outside the LLM's training distribution,** where the LLM lacks pre-trained procedural knowledge and must rely on recalled skills.
- **With LLM-powered skill abstraction,** where learned skills encode genuinely novel procedural insights rather than copies of pre-trained patterns.

Both predictions are testable and constitute the next phase of this research.

---

## 7. Limitations and Future Work

### 7.1 Current Limitations

1. **Rule-based context analysis.** The context analyzer uses hardcoded keyword lists (10 categories, ~6 keywords each) rather than semantic understanding. It maps "break down" and "split" to `decomposition` via string matching, not comprehension.

2. **Verbatim procedure extraction.** Skill steps are copied directly from execution traces. No abstraction, generalization, or domain-stripping occurs. A skill learned from "analyze each section for key findings" stores that literal string, not a generalized "apply independent analysis to each part."

3. **Default retrieval lacks embeddings.** Without a configured sentence-transformer, the semantic score dimension falls back to bag-of-words Jaccard, making it functionally identical to the structural score.

4. **Full-scan retrieval.** All skills are loaded from Redis and scored individually. This is O(n) and will not scale beyond hundreds of skills.

5. **Single model evaluation.** All results are from one local model. Testing with diverse models (different architectures, sizes, and providers) would establish generalizability.

6. **No statistical significance testing.** With N=30 and the observed variance, formal significance tests would not pass. A larger task set or multiple runs are needed.

### 7.2 Planned Enhancements

The architecture is explicitly designed for progressive enhancement in three areas:

**LLM-powered skill abstraction.** Replace verbatim trace copying in `learn()` with an LLM call that receives the execution trace and produces a domain-independent procedural description. The `llm_client` parameter already exists in the constructor and is accepted by `ContextAnalyzer`; it needs to be wired into the extraction pipeline.

**Embedding-based retrieval.** The `TransferEngine` already accepts an optional embedder parameter. Providing a `sentence-transformers` model would activate real cosine similarity for the semantic dimension, making cross-domain retrieval genuinely semantic rather than keyword-based.

**Indexed retrieval.** Replace the full-scan approach with Redis vector search (`FT.SEARCH`) using pre-computed skill embeddings. This would make retrieval sub-linear and production-scalable.

### 7.3 Future Evaluation

1. **Counterbalanced pairwise evaluation** to control for position bias.
2. **Tasks outside the LLM training distribution** (domain-specific, novel, or procedurally unusual) to test the ceiling effect hypothesis.
3. **Ablation study** with a 6-agent brainless pipeline (adding three no-op agents) to isolate pipeline length effects.
4. **Multiple runs** (3-5) per condition to report mean and standard deviation.
5. **Multiple models** to establish generalizability across architectures.

---

## 8. Conclusion

This paper presents three contributions. First, a checklist of five desirable properties for experience-driven agent systems: long feedback loops, persistent memory, reusable skill from experience, cross-domain transfer, and compounding over time. Second, OrKa Brain, an open-source prototype that implements a procedural skill memory loop within a general-purpose LLM agent framework. Third, an empirical evaluation on 30 tasks that reports both the positive signals (consistent pairwise preference, working persistence and decay, retrieval across domains) and the negative ones (flat rubric scores, ceiling effect, untested failure path, pipeline length confound).

The prototype does not produce dramatically better outcomes than a stateless baseline. The rubric scores are nearly identical. The pairwise preference is real but ambiguous in its cause. The feedback loop never recorded a failure, leaving its error-correction capability untested.

What the work does establish is that the loop itself is buildable and functional. Skills are extracted, persisted, retrieved, applied, and tracked across 30 tasks without failure. The architecture has explicit slots for the components that would make it stronger: LLM-powered abstraction, embedding-based retrieval, and vector-indexed search. Whether filling those slots produces meaningfully better outcomes is an open question.

The farming analogy that motivated this work remains an analogy. This system does not prove a phase transition in AI capability. It shows that the plumbing for persistent procedural memory can be built, that it runs, and that filling it with better mechanisms is the next question worth asking.

---

## Appendix A: Benchmark Reproduction

### Prerequisites

```bash
orka-start                    # Redis with search module
# LM Studio with openai/gpt-oss-20b on localhost:1234
conda activate orka_0.9.12
```

### Full Run

```bash
python scripts/run_benchmark.py --verbose
```

### Partial Runs

```bash
python scripts/run_benchmark.py --track A        # Cross-domain only
python scripts/run_benchmark.py --track B        # Accumulation only
python scripts/run_benchmark.py --judge-only     # Re-evaluate existing results
python scripts/run_benchmark.py --skip-brainless # Re-run brain only
```

### Output Structure

```
results/
  brain/track_{a,b}_NN.json         # Brain condition outputs
  brainless/track_{a,b}_NN.json     # Brainless condition outputs
  judge_rubric/{brain,brainless}/   # Per-task rubric scores
  judge_pairwise/pairwise/          # Per-task pairwise verdicts
  benchmark_report.json             # Aggregated metrics
```

### Source Code

OrKa is open source: `github.com/marcosomma/orka-reasoning`

---

## Appendix B: Raw Aggregate Data

### B.1 Rubric Deltas (Brain minus Brainless, full dataset)

| Dimension | Delta |
|-----------|------:|
| Reasoning Quality | +0.28 |
| Structural Completeness | -0.04 |
| Depth of Analysis | 0.00 |
| Actionability | +0.04 |
| Domain Adaptability | +0.11 |
| Confidence Calibration | +0.04 |
| **Overall** | **+0.10** |

### B.2 Pairwise Results (28 decisive comparisons + 2 ties)

| Question | Brain Wins | Brainless Wins | Ties |
|----------|----------:|---------------:|-----:|
| Stronger Reasoning | 18 | 10 | 0 |
| More Complete | 17 | 10 | 1 |
| More Trustworthy | 19 | 9 | 0 |
| **Overall Preference** | **19** | **9** | **2** |

### B.3 Timing

| Phase | Seconds |
|-------|--------:|
| Brainless execution | 517 |
| Brain execution | 595 |
| Rubric judging | 293 |
| Pairwise judging | 126 |
| **Total** | **1531** |

### B.4 Skill Inventory Summary

| Metric | Value |
|--------|------:|
| Total skills | 21 |
| Total transfers | 30 |
| Mean confidence | 72% |
| Confidence range | 69-79% |
| TTL range | 8-37 days |
| Mean uses per skill | 2.9 |
| Max uses | 9 |
