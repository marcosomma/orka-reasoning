# The Memory Binding Problem in AI Agent Systems: Two Benchmarks, 530 Tasks, and Why Recall Is the Wrong Bottleneck

**Marco Somma**
Independent Researcher, Barcelona, Spain
Creator of OrKa (Orchestrator Kit Agents)
GitHub: https://github.com/marcosomma/orka-reasoning
DOI (v1 benchmark): https://doi.org/10.5281/zenodo.19227514

---

## Abstract

The current discourse around agent memory assumes that recall is the primary bottleneck: if the agent can retrieve the right memory, it will use it well. This paper argues that the real bottleneck is binding, the architectural linkage between memory types. I present two iterative benchmarks evaluating a procedural skill memory system within the OrKa agent orchestration framework. Benchmark v1 (30 tasks, 2 tracks, OrKa 0.9.15) produced an ambiguous positive result: 60.7% pairwise win rate but only +0.10 rubric delta on a 10-point scale. Community feedback identified five confounds. Benchmark v2 (250 tasks, 5 tracks, 500 runs, OrKa 0.9.16) addressed these with improved skill abstraction, a stricter recall threshold, and a judge model separate from the executor, and produced a more precise negative result: rubric deltas of -0.03 to +0.06 depending on the evaluation pass, with zero out of 250 tasks self-reporting use of the recalled skill. Two evaluation passes of the same judge model (run on different dates with identical configuration) produced divergent per-track scores, which is itself evidence of evaluation instability in LLM-as-judge methods. Both passes agreed on the overall finding: procedural memory alone produces marginal gains because the base model already possesses the procedural patterns being recalled. The system contains a fully built but entirely disconnected episodic memory subsystem. This architectural gap mirrors the hippocampal binding problem in cognitive neuroscience: separate memory stores that never share an index produce memories that cannot compound. The paper proposes a binding architecture linking procedural skills to their application episodes and describes the recursive loop that would enable genuine knowledge compounding. The principal limitations are single-researcher execution, a single model family, local-only inference, and persistent evaluation bias in pairwise comparison.

---

## 1. Introduction

The current discourse around agent memory is dominated by retrieval. RAG pipelines, vector search, embedding similarity, semantic reranking. The implicit assumption running through most published work is that if the agent can find the right memory, it will use it well. The bottleneck, in this framing, is recall quality. Build a better retriever and the agent gets smarter.

This paper questions that assumption. I present evidence from two iterative benchmarks, totalling 530 tasks and over 1,000 execution runs, showing that a procedural skill memory system can recall skills with reasonable fidelity and the agent will still ignore them. Not because retrieval failed, but because the recalled memory is too impoverished to change behaviour. A procedure without its application history is a recipe without its cook's notes. The information that would make it useful, what happened last time this procedure was tried, what failed, what had to be adapted, is stored nowhere.

The research question is direct: does a persistent procedural memory system improve agent task performance, and if so, under what conditions and through what mechanism?

The system under study is OrKa Brain, a module within the OrKa agent orchestration framework (https://github.com/marcosomma/orka-reasoning). OrKa is a YAML-first multi-agent system where workflows are defined declaratively and executed by composing typed agents in sequential or parallel pipelines. The Brain module implements a learn-persist-retrieve-apply-feedback-decay loop backed by Redis, with skills stored as structured objects including ordered procedure steps, preconditions, postconditions, confidence scores, transfer history, and usage-based time-to-live. The entire stack runs locally on consumer hardware with no API calls. The framework is open source under the Apache 2.0 license.

The paper is structured as follows. Section 2 covers related work across agent memory systems, the hippocampal binding literature in cognitive science, and evaluation methodology gaps. Section 3 describes Benchmark v1: its design, results, and the five confounds identified through self-analysis and community feedback. Section 4 describes the five methodology changes made between v1 and v2. Section 5 presents the v2 results, including a transparency analysis using two evaluation passes of the same judge model. Section 6 introduces the binding hypothesis: the architectural diagnosis that emerged from the v2 results. Section 7 discusses implications, limitations, and what these findings do and do not claim. Section 8 concludes.

This framing matters. The two benchmarks are not separate experiments bolted together. They form a progression: v1 produced a positive but ambiguous result, external criticism identified specific failure modes, v2 addressed those failure modes and produced a more precise negative result that led to a deeper architectural diagnosis. That arc, from optimistic first result through honest self-correction to a structural insight, is the contribution.

---

## 2. Related Work

### 2.1 Agent Memory Architectures

The dominant approaches to agent memory in current systems fall into three categories, none of which explicitly address the binding problem.

**RAG-style document retrieval.** LangChain (Chase, 2022) and LlamaIndex (Liu, 2022) treat memory as a document retrieval problem. The agent's context is augmented with retrieved text chunks selected by embedding similarity. This is episodic in the loosest sense: the agent can access prior information. But the retrieved content is, as typically deployed, static text rather than structured experience. There is no standard mechanism in these frameworks for the agent to learn from retrieval outcomes or for the retrieval system to improve based on downstream task success, though custom implementations could add such feedback loops.

**Episodic memory stores.** MemGPT (Packer et al., 2023) introduces a virtual memory management system for LLMs, enabling persistent context across conversations by paging information in and out of the context window. The memory is conversational: it stores dialogue segments and retrieved documents. It does not extract procedural abstractions or support cross-domain transfer. Generative Agents (Park et al., 2023) simulate human-like memory with retrieval, reflection, and planning, but the memory is primarily narrative and social, not procedural. Neither system links what the agent knows how to do with what actually happened when it tried.

**Procedural memory and skill libraries.** Voyager (Wang et al., 2023) builds a genuine skill library for Minecraft agents, storing executable JavaScript functions that can be retrieved for new tasks. This is real procedural memory, but scoped to a single environment and storing code rather than abstract transferable procedures. Reflexion (Shinn et al., 2023) implements self-reflection by storing verbal feedback about task failures. The memory is evaluative (what went wrong) rather than procedural (how to do it differently), and it does not persist across sessions. AutoGPT (Richards, 2023) maintains task history but treats it as a log rather than a structured skill store.

The common thread: these systems treat memory types as independent components. Documents are retrieved independently of skills. Skills are stored independently of the episodes of their application. No system, to my knowledge, implements a binding layer that links a procedural skill to the episodic record of its use.

### 2.2 The Memory Binding Problem in Cognitive Science

The binding problem in cognitive science concerns how the brain takes separate memory traces, stored in anatomically distinct systems, and combines them into a unified experience during recall.

The hippocampal memory indexing theory (Teyler and DiScenna, 1986) proposes that the hippocampus does not store memories. It stores the index that links memory traces distributed across cortical regions: procedural traces in the motor cortex, emotional traces in the amygdala, spatial context in the parietal cortex, and semantic facts in the temporal lobe. When recall fires one trace, the hippocampal index fires all linked traces together. This is what makes memory functional. A procedure recalled without its failure history is a recipe recalled without knowing which attempts burned the food.

Eichenbaum (2001) extended this to relational memory binding: the hippocampus encodes relationships between elements of an experience, not just the elements themselves. Squire and Wixted (2011) review the consolidation evidence showing that initially hippocampus-dependent memories gradually become cortex-dependent through repeated reactivation, a process that requires the binding to be intact during the consolidation window.

Tulving (2002) established the foundational distinction between episodic memory (specific events with spatiotemporal context) and semantic memory (general facts without context). Both are declarative, but episodic memory is inherently situated: it carries the circumstances of acquisition. This is precisely what current agent memory systems lack. A skill stored as "identify [target], validate [component], implement [target]" is semantic. It carries no situation. A skill stored alongside "last time we ran this on the ETL pipeline, the date normalizer broke because of mixed ISO/US formats" is episodic. It carries the context that makes the procedure useful.

The AI agent memory field is largely building systems component by component, one store for documents, one for skills, one for conversation, with no binding layer between them. Cognitive neuroscience has understood for decades that the binding, not the storage, is what makes memory functional.

### 2.3 Evaluation Methodology in Agent Memory Research

Most published evaluations of agent memory systems share three weaknesses that this work attempts to address.

First, single-run benchmarks. LLM outputs are non-deterministic. A single execution produces one sample from a distribution, not a reliable estimate of system capability. Both benchmarks reported here are single-run (a limitation I acknowledge), but the v2 benchmark's 250-task sample provides more statistical stability than typical 5-10 task demonstrations.

Second, same-model judge and executor. When the same LLM generates an output and then evaluates it, score compression and self-preference bias are well-documented artefacts (Zheng et al., 2023). v1 used the same model for both. v2 uses a different model for judging than for execution.

Third, happy-path testing. Most evaluations report the conditions under which the system works. They do not systematically test conditions where the system should fail or where the baseline should win. The five-track design in v2, covering cross-domain transfer, anti-pattern avoidance, routing decisions, multi-skill composition, and longitudinal learning, deliberately includes task types where the hypothesis predicts the memory system will not help.

Position bias in pairwise LLM evaluation is a known and persistent confound (Wang et al., 2023b). Both benchmarks randomize position assignment, but the v1 data shows 60.7% position-A preference regardless of condition, and v2 pairwise results diverge from rubric results in a pattern consistent with length bias. This confound is not solved in this work; it is reported.

---

## 3. Benchmark v1: Procedural Memory Under Controlled Conditions

### 3.1 System Architecture

The Brain module operates through a six-agent pipeline:

```
task_reasoner -> brain_learn -> brain_recall -> task_applier -> brain_feedback -> task_result
```

1. **task_reasoner** (local LLM): Analyses the task, produces step-by-step reasoning.
2. **brain_learn** (brain, operation: learn): Extracts an abstract procedural skill from the reasoning trace.
3. **brain_recall** (brain, operation: recall): Searches the skill store for applicable skills given the current task context.
4. **task_applier** (local LLM): Solves the task, with any recalled skill injected into the prompt.
5. **brain_feedback** (brain, operation: feedback): Records whether the recalled skill was successfully applied.
6. **task_result** (local LLM): Formats the structured output.

The brainless baseline uses a three-agent pipeline:

```
task_reasoner -> task_applier -> task_result
```

The `task_reasoner` prompt is identical in both conditions. The `task_applier` prompt in the brainless condition explicitly states "You have NO prior experience with similar tasks and NO recalled skills." The output format is identical.

**Skill schema.** Each skill is a structured object:

- `id`: UUID
- `name`: auto-generated from cognitive pattern, task structure, and domain
- `procedure`: ordered list of `SkillStep` objects (action, description, expected outcome)
- `preconditions` / `postconditions`: typed predicates on input/output shape
- `confidence`: float 0.0-1.0, starts at min(0.7, 0.5 + quality * 0.2)
- `usage_count`, `success_rate`, `transfer_history`: application records
- `expires_at`: computed TTL timestamp

The TTL formula governs skill lifespan:

$$TTL = 168 \times (1 + \log_2(\max(1, \text{usage\_count}))) \times (0.5 + \text{confidence})$$

Base TTL is one week (168 hours). Heavily used, high-confidence skills live up to approximately 37 days. Rarely used or low-confidence skills decay within 8 days. Only successful usage renews the TTL. Expired skills are hard-deleted from Redis during periodic cleanup.

**Skill retrieval** uses four-dimensional scoring:

| Component | Weight | Method |
|-----------|--------|--------|
| Structural | 0.35 | Jaccard similarity on cognitive patterns and task structures |
| Semantic | 0.25 | Cosine similarity on sentence-transformer embeddings (falls back to Jaccard when no embedder configured) |
| Transfer history | 0.25 | Success rate from prior transfers, default 0.5 when no history |
| Confidence | 0.15 | Current skill confidence value |

Full source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/transfer_engine.py

### 3.2 Experimental Design

Benchmark v1 comprised 30 tasks across two tracks, run on OrKa version 0.9.15.

**Track A: Cross-Domain Transfer (10 tasks).** Three learning phases taught procedural patterns in distinct domains (text analysis, customer support, creative writing). Seven recall phases tested whether those patterns transferred to unrelated domains (code review, content moderation, code optimization, financial analysis, API infrastructure, education, DevOps incident response).

**Track B: Same-Domain Accumulation (20 tasks).** Twenty veterinary diagnostic cases ran sequentially. Each case exercised the full brain loop. The brain condition accumulated domain-specific skills across the sequence. The baseline restarted from zero each time.

All tasks ran locally via LM Studio using `openai/gpt-oss-20b` at temperature 0.3 (execution) and 0.1 (judge). Redis brain keys were flushed between conditions to prevent cross-contamination. The brainless condition ran first.

Evaluation used two complementary LLM-as-judge methods: an independent rubric scoring each output on six dimensions (reasoning quality, structural completeness, depth of analysis, actionability, domain adaptability, confidence calibration) on a 1-10 scale, and a blind pairwise comparison with randomized A/B labelling answering three preference questions (stronger reasoning, more complete, more trustworthy).

Full benchmark plan and dataset: https://github.com/marcosomma/orka-reasoning/tree/master/examples/benchmark

### 3.3 Results

**Table 1: v1 Rubric Scores by Condition (N=30)**

| Dimension | Brain | Brainless | Delta |
|-----------|------:|----------:|------:|
| Reasoning Quality | 7.82 | 7.54 | +0.28 |
| Structural Completeness | 8.25 | 8.29 | -0.04 |
| Depth of Analysis | 6.43 | 6.43 | 0.00 |
| Actionability | 8.00 | 7.96 | +0.04 |
| Domain Adaptability | 8.43 | 8.32 | +0.11 |
| Confidence Calibration | 7.68 | 7.64 | +0.04 |
| **Overall** | **7.80** | **7.70** | **+0.10** |

**Table 2: v1 Pairwise Preference (N=28 valid of 30)**

| Question | Brain | Brainless | Tie |
|----------|------:|----------:|----:|
| Stronger Reasoning | 18 | 10 | 0 |
| More Complete | 17 | 10 | 1 |
| More Trustworthy | 19 | 9 | 0 |
| **Overall** | **17** | **9** | **2** |

Brain pairwise win rate: **60.7%** (17 of 28 valid comparisons). Two of 30 pairwise evaluations produced empty preference strings and were excluded from the automated count.

Execution time: brain 595 seconds, brainless 517 seconds (+15.1% overhead).

**Skill inventory after 30 tasks:** 21 distinct skills created, 9 deduplicated (merged into existing skills). Average confidence: 72% (range 69-79%). TTL range: 8-37 days. Success rate: 100%, which is itself a limitation discussed below.

### 3.4 Identified Confounds

This section is what makes the v1 results honest rather than merely positive.

**Confound 1: Pipeline length.** The brain condition runs 6 agents; the brainless condition runs 3. The brain pipeline injects recalled skill data into the `task_applier` prompt, providing additional context. Any observed improvement could be partially or entirely attributed to additional processing passes rather than skill recall itself. This is the most serious confound and it persists into v2.

**Confound 2: Position bias.** Position A was preferred in 60.7% of decisive pairwise verdicts regardless of condition. This is a known artefact of pairwise LLM judges. Position was randomized but the bias was not eliminated.

**Confound 3: Single-run non-determinism.** All results are from one run of one model at temperature 0.3. LLM outputs are stochastic. No standard deviations can be reported from a single sample.

**Confound 4: Outlier sensitivity.** In a 30-task benchmark, individual outliers have outsized influence. Track A task a_09 produced a +7.00 rubric delta driven by a catastrophic brainless failure (score 1.33), not a brain success. Excluding this single task, the Track A recall-only delta drops from +0.83 to -0.20.

**Confound 5: Asymmetric confidence.** The feedback mechanism recorded 100% success across all 30 tasks. Skills could only grow in confidence, never decay from failure. The "learns from mistakes" capability of the architecture was entirely untested.

Community comments on the published article (https://dev.to/marco_somma_a9e88a3063f3/i-tried-to-turn-agent-memory-into-plumbing-instead-of-philosophy-1bpm) independently identified several of these. TechPulse Lab argued that episodic and institutional memory matters more than procedural memory. Nova Elvaris noted the asymmetric confidence problem and suggested adversarial baselines. Kuro argued that knowing when to forget is harder and more important than knowing when to remember. These observations directly shaped the v2 design.

### 3.5 Primary Finding

The model already knew most of what the Brain was recalling. Procedural patterns like "decompose, analyse, synthesise" and "validate, classify, route" are well-represented in LLM training data. The rubric delta of +0.10, with a zero delta on Depth of Analysis, suggests a ceiling effect: the system was recalling knowledge the model already possesses. The pairwise preference is real but its cause is ambiguous, confounded by pipeline length and position bias.

This finding set up the central question for v2: if you fix the abstraction quality, fix the recall threshold, fix the judge independence, and scale up the sample, does the effect get larger or smaller?

---

## 4. Benchmark v2: Methodology Improvements and Extended Design

### 4.1 Five Changes Between v1 and v2

Each change addresses a specific problem identified in v1.

**Change 1: Skill abstraction.** v1 stored verbatim LLM output as skill steps. When the Brain learned from a data engineering task, it stored the literal string "Load CSV files into staging tables using pandas read_csv with error handling." This is a paraphrase of model knowledge, not a transferable abstraction. v2 rewrote the abstraction layer to extract verb-target patterns: "implement [target]", "validate [component]", "trace [target]". A constants module (https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/constants.py) defines approximately 170 action verbs organized by cognitive category, with canonical mappings reducing synonyms to a common vocabulary. A new `_abstract_procedure()` method in the brain agent and `_abstract_action()` in the brain core replaced the sentence-splitting fallback.

**Change 2: Recall threshold.** v1 used an effective minimum score of 0.0, meaning any vaguely related skill could be recalled. v2 raised the default `min_score` and added a semantic floor in the transfer engine: if embedding similarity is below 0.1 AND structural match is below 0.6, the candidate is rejected entirely (returned as a zeroed TransferCandidate). Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/transfer_engine.py

**Change 3: Judge independence from executor.** v1 used the same LLM (openai/gpt-oss-20b) for both execution and evaluation, creating circular bias where the model scored its own output patterns favourably. v2 decoupled execution from judgment. The benchmark was split into three standalone scripts: execution (https://github.com/marcosomma/orka-reasoning/blob/master/examples/benchmark_v2/run_benchmark_v2.py), judging (https://github.com/marcosomma/orka-reasoning/blob/master/examples/benchmark_v2/judge_benchmark.py), and aggregation (https://github.com/marcosomma/orka-reasoning/blob/master/examples/benchmark_v2/aggregate_benchmark.py). The judge model was `qwen/qwen3-coder-30b`, separate from the execution model. To test evaluation stability, a second full judging pass was run with the same judge model on a different date (April 12 versus the initial pass). The two passes used identical prompts, workflows, and temperature (0.1). Any divergence between passes is therefore attributable to LLM non-determinism, not to methodological differences.

**Change 4: Track diversity.** v1 had two tracks within a narrow range. v2 has five:

| Track | Focus | Tasks | Rationale |
|-------|-------|------:|-----------|
| A | Cross-domain skill transfer | 50 | Primary signal: does a data engineering skill help with cybersecurity? |
| B | Anti-pattern avoidance | 50 | Can learned failure patterns transfer to new contexts? |
| C | GraphScout brain-assisted routing | 50 | Do routing history skills improve path selection? |
| D | Multi-skill composition | 50 | Can multiple skill types be composed for complex tasks? |
| E | Longitudinal learning curve | 50 | Does quality improve as skills accumulate over time? |

Full dataset: https://github.com/marcosomma/orka-reasoning/blob/master/examples/benchmark_v2/benchmark_v2_dataset.json

**Change 5: Sample size.** 250 tasks versus 30. 500 total execution runs (brain plus brainless). Up to 1,250 orchestrator calls including judge evaluations.

### 4.2 What Was Deliberately Not Changed

The local execution environment (LM Studio on localhost), the same base execution model (openai/gpt-oss-20b), the same YAML orchestration framework, and the same six-dimension rubric were held constant. Keeping these fixed makes the methodology changes the primary variable.

Notably, the pipeline-length asymmetry was not changed. The brain condition still runs 6 agents; the brainless condition still runs 3. Single-pass baseline workflows were added as an additional control (https://github.com/marcosomma/orka-reasoning/blob/master/examples/benchmark_v2/baseline_track_a.yml), but the primary comparison retains the v1 structure. This confound persists and is acknowledged.

---

## 5. Results

### 5.1 Two Evaluation Passes

A critical transparency point: v2 results were evaluated twice by the same judge model (qwen/qwen3-coder-30b), run on different dates with identical prompts, workflows, and temperature. These are not two independent judges; they are two passes of the same model, and the fact that they produced meaningfully different scores is itself a finding about LLM-as-judge reliability. Pass 1 produced scores in the 4.9-9.1 range across tracks, suggesting reasonable discrimination. Pass 2, run three days later, produced scores of 9.3+/10 with multiple perfect 10.0 dimension averages, indicating score compression and leniency bias. For some tracks, the two passes produced opposite conclusions. Neither pass is preferred; both are presented.

### 5.2 Aggregate Results

**Table 3: v2 Overall Rubric Scores (N=250 per condition)**

| Metric | Pass 1 | Pass 2 |
|--------|-------:|-------:|
| Brain rubric avg | 7.82 | 9.37 |
| Brainless rubric avg | 7.85 | 9.31 |
| **Rubric delta** | **-0.03** | **+0.06** |
| Pairwise brain win rate | 59.2% | 61.6% |
| Pairwise brain wins | 148 / 250 | 151 / 245 |

The rubric delta direction depends on the evaluation pass: Pass 1 shows brain performing marginally worse (-0.03), Pass 2 shows brain performing marginally better (+0.06). Neither delta is practically meaningful at these baseline levels. Both passes agree that pairwise preference favours brain at approximately 60%, consistent with v1. That the same model, same prompts, and same temperature can produce opposite rubric-delta signs three days apart is a caution about the precision ceiling of LLM-as-judge evaluation.

For reference, v1 showed +0.10 rubric delta across 30 tasks. The effect got smaller with more data, not larger.

### 5.3 Per-Track Breakdown

This is the most important table in the paper.

**Table 4: v2 Per-Track Results (Pass 1)**

| Track | Focus | Brain Avg | Brainless Avg | Rubric Delta | Pairwise Win% |
|-------|-------|----------:|--------------:|-------------:|---------------:|
| A | Cross-domain transfer | 8.41 | 8.38 | +0.03 | 54% |
| B | Anti-pattern avoidance | 8.51 | 8.25 | +0.26 | 44% |
| C | Routing decisions | 4.90 | 5.07 | -0.17 | 48% |
| D | Multi-skill composition | 8.64 | 8.61 | +0.03 | 70% |
| E | Longitudinal learning | 9.07 | 8.70 | +0.37 | 80% |

**Table 5: v2 Per-Track Results (Pass 2)**

| Track | Focus | Brain Avg | Brainless Avg | Rubric Delta | Pairwise Win% |
|-------|-------|----------:|--------------:|-------------:|---------------:|
| A | Cross-domain transfer | 9.31 | 9.33 | -0.02 | 60% |
| B | Anti-pattern avoidance | 9.54 | 9.54 | +0.00 | 52% |
| C | Routing decisions | 8.52 | 8.12 | +0.40 | 60% |
| D | Multi-skill composition | 9.57 | 9.49 | +0.08 | 60% |
| E | Longitudinal learning | 9.67 | 9.61 | +0.06 | 76% |

**The Track C divergence.** Track C is the only track where the two passes produce opposite rubric deltas: -0.17 (Pass 1) versus +0.40 (Pass 2). Pass 1 scores Track C substantially lower than all other tracks for both conditions (4.9 and 5.07), while Pass 2 scores it in the 8-9 range like everything else. Since both passes used the same model and configuration, this divergence is pure evaluation noise. Track C cannot serve as evidence for or against any hypothesis.

**What both passes agree on:**
- Overall rubric deltas are marginal (range: -0.03 to +0.06)
- Pairwise preference favours brain at approximately 60%
- Tracks A and D show near-zero rubric deltas
- Track E shows the highest pairwise win rate (76-80%)

**What the passes disagree on:**
- Which tracks show the largest brain advantage (B and E for Pass 1; C for Pass 2)
- Whether brain helps or hurts on Track C
- The absolute quality level (Pass 1: 5-9 range; Pass 2: 8-10 range)

### 5.4 The Pairwise-Rubric Disagreement

Both passes show the same structural pattern: approximately 60% pairwise preference for brain alongside negligible rubric deltas. This disagreement is evidence that length bias is contaminating pairwise results regardless of memory architecture.

Measuring response length across all 500 execution outputs confirms this. Brain responses averaged 7,586 characters versus 6,868 for brainless, a +10.4% difference overall. The per-track breakdown reveals a strong correlation between length delta and pairwise preference:

**Table 6: Response Length and Pairwise Preference by Track**

| Track | Brain Avg Chars | Brainless Avg Chars | Length Delta | Pairwise Win% |
|-------|----------------:|--------------------:|-------------:|---------------:|
| C | 7,086 | 7,307 | -3.0% | 48% |
| B | 5,220 | 5,164 | +1.1% | 44% |
| A | 8,109 | 7,750 | +4.6% | 54% |
| D | 7,649 | 6,360 | +20.3% | 70% |
| E | 9,864 | 7,760 | +27.1% | 80% |

Track E, where brain responses are 27.1% longer, shows 80% pairwise preference. Track C, the only track where brain responses are shorter (-3.0%), shows below-50% pairwise preference. Tracks D and E, where length differences exceed 20%, account for the bulk of the pairwise advantage. Zheng et al. (2023) document that LLM judges systematically prefer longer responses. If we conservatively attribute half the pairwise preference above 50% to length bias, the corrected brain win rate drops from approximately 60% to approximately 55%, well within noise for this sample size.

The rubric does not show this pattern because it scores each dimension independently without comparing the two responses side by side. This is a persistent methodological confound that cannot be resolved by changing the judge model. It can only be resolved by controlling for response length or by using evaluation methods that are length-invariant.

### 5.5 Skill Usage Analysis

The v2 results contain a field, `used_recalled_skill`, in each brain execution output. The value was `false` for all 250 brain tasks. Zero out of 250 tasks self-reported using the recalled skill. The model read the recalled skill, evaluated it, and decided every single time that it was not helpful.

This finding is recorded in the OrKa 0.9.16 changelog: "the 61.6% pairwise win rate is driven by pipeline structure, not skill content."

The skill abstraction changes, meant to produce more transferable patterns, had an unintended effect. v1 skills were too specific (literal LLM paraphrases). v2 skills were too abstract (empty shells like "implement [target]", "validate [component]"). The embedding model saw no meaningful relationship between these two-word patterns and actual tasks. The execution model correctly recognized that "implement [target]" tells it nothing it does not already know.

The sweet spot, genuine transferable knowledge between specificity and vacuity, was not found.

### 5.6 What v2 Ruled Out

Better abstraction alone did not fix the problem. A stricter recall threshold alone did not fix the problem. A larger, more diverse sample confirmed rather than reversed the v1 finding. The marginal pairwise preference is reproducible across both benchmarks and both judges, but its cause is pipeline-structural, not skill-content-related. The model already knows what the Brain recalls.

---

## 6. The Binding Hypothesis

### 6.1 The Architectural Diagnosis

The system built two memory subsystems that never talk to each other.

The **skill system** (fully operational, used in both benchmarks) stores:
- Abstract procedure steps
- Preconditions and postconditions
- Transfer history and confidence scores
- Structural and semantic matching for recall

Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/skill.py

The **episode system** (fully built, tested, integrated into the Brain class, never used in any benchmark) stores:
- Specific task input and outcome
- What worked and what failed
- Root cause analysis for failures
- Actionable lessons learned
- Resource metrics (tokens, latency)
- Links to related episodes

Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/episode.py

Both systems are production-ready. Both have test coverage. Both are integrated into the Brain class. The `record_episode()`, `recall_episodes()`, `EpisodeStore`, and `EpisodeRecall` components all exist (https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/episode_store.py, https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/episode_recall.py).

And they share no information.

The Skill has no `episode_ids` field. The Episode has no `skill_id` field. `brain.learn()` creates a Skill but not an Episode. `brain.recall()` returns Skills but not Episodes. The benchmark workflows run `brain_learn` and `brain_recall`, but never `brain_record_episode` or `brain_recall_episodes`.

Two complete memory systems, sitting in the same codebase, with no binding between them.

### 6.2 The Missing Layer

The diagnosis, expressed as a diagram:

```
Current Architecture:
                                        
  ┌──────────────────┐    ┌──────────────────┐
  │  Procedural Store │    │  Episodic Store   │
  │  (skills)         │    │  (episodes)       │
  │                   │    │                   │
  │  - procedure      │    │  - task_input     │
  │  - preconditions  │    │  - outcome        │
  │  - confidence     │    │  - what_worked    │
  │  - transfer_hist  │    │  - what_failed    │
  │                   │    │  - lessons        │
  └──────────────────┘    └──────────────────┘
           │                        │
           │    ┌──────────────┐    │
           │    │ Binding Layer│    │
           └───>│  (MISSING)   │<───┘
                └──────────────┘
```

The binding layer, the index that would link a procedural skill to the episodes of its application, does not exist. This is the hippocampal gap applied to software architecture.

### 6.3 The Cognitive Science Grounding

The hippocampus does not store memories. It stores the binding index that links memory traces distributed across cortical regions (Teyler and DiScenna, 1986). When recall fires one trace, the binding fires all linked traces together. This is what Eichenbaum (2001) calls relational memory: the hippocampus encodes the relationships between elements of an experience, not the elements themselves.

The distinction Tulving (2002) drew between episodic and semantic memory applies directly. A skill stored as "identify [target], validate [component]" is semantic: a general pattern without context. An episode stored as "last time we ran validation before deduplication on the ETL pipeline, it caught 30% of dirty records that would have been duplicated" is episodic: a specific event with temporal context and causal information.

The analogy to agent memory is precise. A skill recalled without its failure episodes is a procedure recalled without its track record. It cannot update agent behaviour in any meaningful way because it provides no information the model does not already possess. What would make it useful is the situated history: what happened when this skill was applied, what failed, what was adapted, what lesson was drawn. That binding does not exist in the current system.

This is not a retrieval problem. The retrieval works. The scoring works. The matching works. The problem is that what gets retrieved, a bare procedure, is too impoverished to change behaviour.

### 6.4 The Recursive Loop That Would Work

The architecture that would genuinely test the binding hypothesis:

1. **Learn**: Execute a task. Create both a Skill AND an Episode, linked by ID. The skill stores the abstract procedure. The episode stores what actually happened: the specific outcome, what worked, what failed, and the lessons.

2. **Recall**: Find a matching skill. Automatically fetch its associated episodes. Inject both into the solve context. The prompt to the model is not "implement [target]" but:

   > Here is an abstract procedure: implement [target], validate [component], trace [target].
   >
   > This skill has been applied 3 times before:
   > - Data engineering (ETL): Validation before dedup caught 30% of dirty records. Lesson: always validate before any deduplication step.
   > - API integration: Target implementation worked, but tracing missed async callbacks. Lesson: tracing needs to account for async execution paths.
   > - Log analysis: Pattern worked well. Filtering noisy entries before analysis reduced false positives by 40%.

3. **Apply**: The model uses the abstract pattern (transferable) AND the concrete evidence (grounding). It can decide whether the pattern applies based on real outcomes, not just structural similarity.

4. **Record**: On completion, record a new episode for this application. Link it to the skill. The episode chain grows over time.

5. **Update**: Adjust skill confidence based on episode outcome. A skill backed by five successful episodes with clear lessons scores higher than a skill backed by zero episodes.

6. **Compound**: Next recall is richer. It has more episodes, more lessons, more evidence. The loop is genuinely recursive.

This is the design that a v3 benchmark would test. It does not require new systems. The procedural store exists. The episodic store exists. What is needed is the binding: an `episode_ids` field on Skill, a `skill_id` field on Episode, and the wiring in `brain.learn()` and `brain.recall()` to create and fetch both together.

---

## 7. Discussion

### 7.1 Implications for Agent Memory System Design

The field is building memory as retrieval. It should be building memory as binding.

RAG retrieves documents. Skill stores retrieve procedures. Episode stores retrieve event records. But no current system, to my knowledge, implements a binding layer that, when it retrieves a skill, automatically retrieves the situated history of that skill's application. This changes the architecture requirements substantially. You need not just a vector store but a relational index between skill records and episode records, with the episode quality factored into the transfer scoring.

The transition from "store and retrieve" to "bind and compound" is analogous to the transition Squire and Wixted (2011) describe in biological memory consolidation. Initially hippocampus-dependent memories become cortex-dependent through repeated reactivation. The binding must be intact during the consolidation window. For agent memory, this means the link between a skill and its episodes must be maintained and updated throughout the skill's lifecycle. A skill that loses its episodes is a memory that has lost its consolidation pathway.

### 7.2 Where Procedural Memory Does and Does Not Earn Its Keep

Procedural memory does not earn its keep for tasks the model already handles well from pretraining. Analysis, synthesis, decomposition, classification: the model scores 7.5-9.5 on these without any recalled skills. No amount of procedural memory will improve a 9.5/10 response to a 10/10 response.

Procedural memory potentially earns its keep for tasks that require institutional knowledge: routing decisions where the choice depends on what happened last time, domain-specific corrections that emerged from prior failures, failure pattern avoidance where the agent needs to know not just what to do but what went wrong before.

Track C (routing decisions) was hypothesised before v2 as the strongest candidate for memory-driven improvement, because routing choices depend on what happened in previous attempts, information the model cannot derive from its weights. The data does not support this hypothesis: the two evaluation passes produced opposite rubric deltas (-0.17 versus +0.40), making Track C unreliable as evidence in either direction. Routing decisions remain a plausible task type where episodic evidence would provide value, but the current data cannot confirm or deny this. A v3 benchmark would need to test routing with bound episodic context rather than rely on the Track C signal from v2.

The primary evidence for the binding hypothesis is not any single track but the 0/250 skill-usage finding (Section 5.5). The model rejected every recalled skill because bare procedures carry no information it does not already possess. What would change that calculus is episodic context: evidence of what happened when the procedure was previously applied. This is the binding gap the architecture must close.

The community commenters on the v1 article reached a compatible conclusion independently. TechPulse Lab's distinction between "things the model knows but needs reminding" and "things only this system knows from prior runs" is precisely the procedural/episodic boundary that the binding hypothesis formalises.

### 7.3 Honest Limitations

**Single researcher.** All design, implementation, execution, and analysis were done by one person. There is no independent replication.

**Single model family.** All execution used openai/gpt-oss-20b via LM Studio. No cloud API models, no alternative architectures. Results may not generalise to other model families.

**Local-only execution.** No cloud API behaviour, no latency variance from network calls. This improves reproducibility but limits ecological validity.

**Evaluation instability.** Two evaluation passes of the same judge model (same prompts, same temperature, same configuration, different dates) produced opposite per-track conclusions (notably Track C: -0.17 versus +0.40). The overall finding (marginal rubric gains) is robust across passes, but any track-specific claim is pass-dependent. This suggests that LLM-as-judge evaluation, even with judge-executor independence, has a lower reliability ceiling than commonly assumed. The divergence between passes is itself a finding: a single evaluation pass of an LLM judge is insufficient to establish per-track effects at these delta magnitudes.

**Score compression.** Pass 2 produced 9.3+/10 baselines with multiple perfect 10.0 dimension averages, meaning the rubric could not discriminate between conditions. This is a known failure mode of LLM judges that inflate towards the top of the scale. Pass 1 showed better discrimination (4.9-9.1 range).

**Pipeline-length confound.** Despite five methodology improvements between v1 and v2, the pipeline-length asymmetry (6 agents versus 3) persists. Brain responses averaged 7,586 characters versus 6,868 for brainless (+10.4%). The correlation between per-track length delta and pairwise win rate is strong (Table 6): Track E, where brain outputs are 27.1% longer, shows 80% pairwise preference; Track C, where brain outputs are 3.0% shorter, shows 48%. A conservative estimate attributes roughly half the pairwise advantage above 50% to length bias, reducing the corrected preference to approximately 55%.

**The 0/250 usage claim.** The `used_recalled_skill: false` finding across all 250 tasks is based on model self-report. The model may have been influenced by the recalled skill without explicitly acknowledging it. However, the rubric deltas are consistent with the self-report: if skills were being used implicitly, the effect is too small to measure.

### 7.4 What This Paper Does Not Claim

This paper does not claim that procedural memory is useless. It claims that procedural memory built as an isolated store, disconnected from episodic application history, produces marginal gains that are confounded by pipeline-structural effects.

This paper does not claim that RAG is broken. RAG retrieves documents, and document retrieval is valuable for knowledge-intensive tasks. The claim is narrower: that the current generation of agent memory frameworks is missing a binding layer between memory types.

This paper does not claim that the binding hypothesis is proven. It claims that the binding hypothesis is the best explanation for why two benchmarks, totalling 530 tasks, produced consistently marginal results despite five rounds of methodology improvement. The hypothesis is testable and the test architecture is described in Section 6.4.

What this paper does claim is that the real bottleneck in agent memory systems is not recall quality but binding architecture. Procedural and episodic memory built as separate silos cannot compound. The cognitive neuroscience literature has understood binding as the critical mechanism for decades. The AI agent field is largely ignoring this problem because it is building memory systems component by component with no binding layer between them.

---

## 8. Conclusion

This paper presents two iterative benchmarks evaluating a procedural skill memory system within the OrKa agent orchestration framework. Benchmark v1 (30 tasks, OrKa 0.9.15) produced an ambiguous positive result: 60.7% pairwise preference, +0.10 rubric delta, but five identified confounds that made the cause of the positive signal unclear. Community feedback sharpened the diagnosis. Benchmark v2 (250 tasks, 5 tracks, OrKa 0.9.16) addressed the criticism with improved skill abstraction, a stricter recall threshold, a judge model separate from the executor, and substantially greater diversity, and produced a more precise negative result: marginal rubric deltas across two evaluation passes of the same judge (which themselves diverged, revealing evaluation instability), zero tasks self-reporting use of recalled skills, and the conclusion that the ~60% pairwise preference is pipeline-structural, not skill-content-driven.

The finding is this: the real bottleneck in agent memory is not recall quality but binding architecture. The OrKa codebase contains a fully operational procedural memory system and a fully built episodic memory system, and they share no information. A skill recalled without its application episodes provides no information the model cannot derive from its own weights. Only when procedural memory is bound to episodic evidence, when a recalled skill carries the situated history of its prior applications, can the system provide genuinely novel information to the model.

The next step is a v3 benchmark testing the explicit binding architecture described in Section 6.4: hippocampal-style indexing linking skills to their episode histories, with recall that returns both the abstract procedure and its concrete application record. The code changes are surprisingly small; the binding infrastructure (episode storage, recall, and scoring) already exists in the codebase. What is needed is the wiring.

Memory in AI systems is not a solved problem dressed up in a retrieval framework. It is an open architectural problem. This paper is one attempt to locate where the gap actually is. The data, code, and benchmark results are publicly available for verification, replication, or rebuttal.

---

## References

Anderson, J.R., Bothell, D., Byrne, M.D., Douglass, S., Lebiere, C. and Qin, Y. (2004). An Integrated Theory of the Mind. *Psychological Review*, 111(4), 1036-1060.

Chase, H. (2022). LangChain. https://github.com/langchain-ai/langchain

Eichenbaum, H. (2001). The hippocampus and declarative memory: cognitive mechanisms and neural codes. *Behavioural Brain Research*, 127(1-2), 199-207.

Laird, J.E. (2012). *The Soar Cognitive Architecture*. MIT Press.

Liu, J. (2022). LlamaIndex. https://github.com/run-llama/llama_index

Packer, C., Fang, V., Patwardhan, S.G., Lin, K., Wooders, S. and Gonzalez, J.E. (2023). MemGPT: Towards LLMs as Operating Systems. *arXiv:2310.08560*.

Park, J.S., O'Brien, J.C., Cai, C.J., Morris, M.R., Liang, P. and Bernstein, M.S. (2023). Generative Agents: Interactive Simulacra of Human Behavior. *UIST 2023*. *arXiv:2304.03442*.

Richards, T. (2023). Auto-GPT. https://github.com/Significant-Gravitas/AutoGPT

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K. and Yao, S. (2023). Reflexion: Language Agents with Verbal Reinforcement Learning. *NeurIPS 2023*. *arXiv:2303.11366*.

Squire, L.R. and Wixted, J.T. (2011). The Cognitive Neuroscience of Human Memory Since H.M. *Annual Review of Neuroscience*, 34, 259-288.

Teyler, T.J. and DiScenna, P. (1986). The hippocampal memory indexing theory. *Behavioral Neuroscience*, 100(2), 147-154.

Tulving, E. (2002). Episodic Memory: From Mind to Brain. *Annual Review of Psychology*, 53, 1-25.

Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L. and Anandkumar, A. (2023). Voyager: An Open-Ended Embodied Agent with Large Language Models. *arXiv:2305.16291*.

Wang, P., Li, L., Chen, L., Zhu, D., Lin, B., Cao, Y., Liu, Q., Liu, T. and Sui, Z. (2023b). Large Language Models are not Fair Evaluators. *arXiv:2305.17926*.

Zheng, L., Chiang, W., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E.P., Zhang, H., Gonzalez, J.E. and Stoica, I. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023*. *arXiv:2306.05685*.

---

## Appendix A: Benchmark v1 Data

Full task definitions, raw scores, and judge transcripts are available at:
- Zenodo: https://doi.org/10.5281/zenodo.19227514
- GitHub: https://github.com/marcosomma/orka-reasoning/tree/master/examples/benchmark/results

**v1 execution parameters:**

| Parameter | Value |
|-----------|-------|
| OrKa version | 0.9.15 |
| Model | openai/gpt-oss-20b |
| Provider | LM Studio (localhost:1234) |
| Temperature | 0.3 (execution), 0.1 (judge) |
| Redis | RedisStack on port 6380 |
| Date | 2026-03-25 |

## Appendix B: Benchmark v2 Data

Full task definitions (250 tasks across 5 tracks), per-task rubric and pairwise results for both judge models, and execution outputs are available at:
- GitHub: https://github.com/marcosomma/orka-reasoning/tree/master/examples/benchmark_v2

**v2 execution parameters:**

| Parameter | Value |
|-----------|-------|
| OrKa version | 0.9.16 |
| Execution model | openai/gpt-oss-20b |
| Judge model (both passes) | qwen/qwen3-coder-30b |
| Judge Pass 1 date | 2026-04-09 |
| Judge Pass 2 date | 2026-04-12 |
| Provider | LM Studio (localhost:1234) |
| Temperature | 0.3 (execution), 0.1 (judge) |
| Redis | RedisStack on port 6380 |
| Date | 2026-04-09 (execution), 2026-04-12 (Pass 2) |

**Reproduction commands:**

```bash
# Execute benchmark
cd examples/benchmark_v2
python run_benchmark_v2.py --verbose

# Run judge evaluation
python judge_benchmark.py --output-tag local

# Aggregate results
python aggregate_benchmark.py --judge-tag local
```

## Appendix C: OrKa Brain Architecture Reference

### Skill Schema (full)

```python
@dataclass
class Skill:
    id: str                                    # UUID
    name: str                                  # Auto-generated
    description: str                           # Abstract goal
    skill_type: str                            # "recipe", "anti_pattern", "path"
    procedure: List[SkillStep]                 # Ordered abstract steps
    preconditions: List[SkillCondition]        # Input guards
    postconditions: List[SkillCondition]       # Output guards
    source_context: Dict[str, Any]             # ContextFeatures where learned
    transfer_history: List[SkillTransferRecord]# Cross-context applications
    confidence: float                          # 0.0-1.0
    usage_count: int
    success_rate: float
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    expires_at: str                            # ISO 8601 or empty (no expiry)
```

Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/skill.py

### TTL Formula

$$TTL = 168 \times (1 + \log_2(\max(1, \text{usage\_count}))) \times (0.5 + \text{confidence})$$

### Transfer Scoring Weights

| Component | Weight |
|-----------|-------:|
| Structural similarity | 0.35 |
| Semantic similarity | 0.25 |
| Transfer history | 0.25 |
| Confidence | 0.15 |

Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/transfer_engine.py

### Episode Schema

```python
@dataclass
class Episode:
    id: str
    timestamp: datetime
    task_input: str
    task_domain: str
    task_type: str
    agents_used: List[str]
    strategy: str
    model: str
    context_features: Dict
    success: bool
    quality_score: float
    outcome_summary: str
    what_worked: List[str]
    what_failed: List[str]
    failure_analysis: Optional[str]
    lessons: List[str]
    tokens_used: int
    latency_ms: float
    related_episode_ids: List[str]
    supersedes_id: Optional[str]
```

Source: https://github.com/marcosomma/orka-reasoning/blob/master/orka/brain/episode.py

### Key Source Files Changed Between v1 and v2

| File | Change |
|------|--------|
| `orka/brain/constants.py` | NEW: action verb vocabulary, canonical mappings |
| `orka/brain/brain.py` | Added `_abstract_action()` |
| `orka/agents/brain_agent.py` | Added `_abstract_procedure()`, raised `min_score` |
| `orka/brain/transfer_engine.py` | Added semantic floor rejection filter |
| `orka/brain/skill.py` | Added `SkillStep.__post_init__` length validation |
| `examples/benchmark_v2/run_benchmark_v2.py` | Execution-only (decoupled from judging) |
| `examples/benchmark_v2/judge_benchmark.py` | NEW: standalone judge runner |
| `examples/benchmark_v2/aggregate_benchmark.py` | NEW: standalone aggregation |

All changes are committed and publicly visible in the repository history at https://github.com/marcosomma/orka-reasoning.
