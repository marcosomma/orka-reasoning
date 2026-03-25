# OrKa Brain — Procedural Skill Memory

> **Since:** v0.9.15  
> **Status:** 🟢 Stable  
> **Related:** [Agents](agents.md) | [Memory System](MEMORY_SYSTEM_GUIDE.md) | [Architecture](architecture.md) | [INDEX](index.md)

The Brain is OrKa's **executional learning engine**. It observes how agents solve tasks, abstracts the reasoning into domain-agnostic *skills*, and re-applies those skills when structurally similar problems appear — even in completely unrelated domains.

Traditional LLM agents start from scratch every time. The Brain gives OrKa workflows a **procedural memory**: a growing library of reusable problem-solving patterns that improve with use and decay when neglected.

---

## Table of Contents

- [Why It Matters](#why-it-matters)
- [Core Concepts](#core-concepts)
  - [Skills](#skills)
  - [Context Features](#context-features)
  - [Transfer Candidates](#transfer-candidates)
- [Lifecycle](#lifecycle)
  - [Learn](#1-learn)
  - [Recall](#2-recall)
  - [Apply](#3-apply)
  - [Feedback](#4-feedback)
- [Architecture](#architecture)
  - [Module Map](#module-map)
  - [Brain](#brain)
  - [ContextAnalyzer](#contextanalyzer)
  - [SkillGraph](#skillgraph)
  - [SkillTransferEngine](#skilltransferengine)
- [YAML Workflow Configuration](#yaml-workflow-configuration)
  - [Agent Type: brain](#agent-type-brain)
  - [Operations](#operations)
  - [Minimal Example](#minimal-example)
  - [Full Workflow Example](#full-workflow-example)
- [Skill TTL and Expiry](#skill-ttl-and-expiry)
  - [TTL Formula](#ttl-formula)
  - [Renewal Policy](#renewal-policy)
  - [Cleanup](#cleanup)
- [Transfer Scoring](#transfer-scoring)
  - [Scoring Weights](#scoring-weights)
  - [Structural Similarity](#structural-similarity)
  - [Semantic Similarity](#semantic-similarity)
  - [Transfer Track Record](#transfer-track-record)
  - [Confidence](#confidence)
- [Skill Deduplication](#skill-deduplication)
- [Redis Storage Layout](#redis-storage-layout)
- [Graph Relationships](#graph-relationships)
- [Programmatic API](#programmatic-api)
- [TUI Dashboard](#tui-dashboard)
- [Running the Demo](#running-the-demo)
- [Testing](#testing)
- [FAQ](#faq)

---

## Why It Matters

Consider an agent that learns to diagnose medical conditions through a structured process: *gather symptoms → form hypotheses → test each hypothesis → eliminate unlikely causes → conclude*. That **pattern** is not specific to medicine — it is the same abstract procedure a software debugger uses: *gather error reports → form hypotheses → reproduce each → eliminate → root-cause*.

The Brain captures this insight automatically. It:

1. **Abstracts** domain-specific reasoning into domain-agnostic procedure steps.
2. **Stores** those abstract skills in a persistent knowledge graph.
3. **Matches** new tasks to known skills via structural and semantic similarity.
4. **Adapts** the recalled skill for the new domain, suggesting concrete modifications.
5. **Learns from feedback** — successful transfers increase skill confidence; failures decrease it.

Over time, the agent builds a growing repertoire of problem-solving patterns, quantifiably improving performance on novel tasks without additional fine-tuning.

---

## Core Concepts

### Skills

A **Skill** (`orka.brain.Skill`) is the fundamental knowledge unit. It represents an abstract, transferable capability:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | UUID. |
| `name` | `str` | Human-readable name (e.g., "Analysis via Decomposition"). |
| `description` | `str` | What the skill does, described abstractly. |
| `procedure` | `list[SkillStep]` | Ordered abstract steps — the "how". |
| `preconditions` | `list[SkillCondition]` | What must be true for this skill to apply. |
| `postconditions` | `list[SkillCondition]` | What is true after successful application. |
| `source_context` | `dict` | Abstract features of the context where the skill was first learned. |
| `transfer_history` | `list[SkillTransferRecord]` | Record of every cross-context application. |
| `confidence` | `float` | Overall reliability (0.0–1.0). Grows with success, decays with failure. |
| `usage_count` | `int` | Total applications. |
| `success_rate` | `float` | Fraction of successful applications. |
| `tags` | `list[str]` | Semantic tags for categorization and search. |
| `expires_at` | `str` | ISO 8601 UTC timestamp. Empty = never expires. |

**SkillStep** — a single abstract action:

```python
SkillStep(
    action="decompose input into constituent parts",
    description="Break the problem into smaller, independent sub-problems",
    order=0,
    parameters={},
    is_optional=False,
)
```

**SkillCondition** — a precondition or postcondition predicate:

```python
SkillCondition(
    predicate="input is decomposable",
    description="The input must consist of multiple independent components",
    required=True,
)
```

### Context Features

A **ContextFeatures** (`orka.brain.ContextFeatures`) object describes *what kind* of problem you are facing, abstractly. It deliberately strips away domain-specific details so that structurally similar tasks in different domains match:

| Field | Description | Example Values |
|---|---|---|
| `task_structures` | What structural patterns the task involves. | `decomposition`, `sequential`, `parallel`, `aggregation`, `comparison`, `transformation`, `filtering`, `routing`, `iteration`, `validation` |
| `cognitive_patterns` | What kinds of thinking are needed. | `analysis`, `synthesis`, `evaluation`, `generation`, `classification`, `extraction`, `reasoning`, `planning`, `optimization`, `abstraction` |
| `input_shape` | Abstract input format. | `single_text`, `long_text`, `list`, `structured`, `unknown` |
| `output_shape` | Abstract output format. | `text`, `structured`, `list`, `boolean`, `numeric` |
| `complexity` | Estimated complexity (1–10). | Computed from structure/pattern count + agent count. |
| `domain_hints` | Domain-specific terms for boosting in-domain matches. | `["medical_diagnosis"]`, `["code_review"]` |
| `abstract_goal` | One-sentence description. | `"Apply analysis and reasoning using decomposition and sequential on single_text input producing text output"` |

### Transfer Candidates

When the Brain recalls skills for a new context, it returns **TransferCandidate** objects:

```python
TransferCandidate(
    skill=<Skill>,
    structural_score=0.72,   # Task shape similarity
    semantic_score=0.65,     # Embedding/keyword similarity
    transfer_score=0.80,     # Historical transfer success rate
    confidence_score=0.75,   # Skill's overall confidence
    combined_score=0.72,     # Weighted combination
    adaptations={            # Suggested modifications
        "input_adaptation": {"from": "long_text", "to": "structured"},
        "complexity": "Target is simpler — some steps may be unnecessary",
    },
    reasoning="Skill 'Diagnosis via Decomposition' shares structures: decomposition, sequential. ...",
)
```

---

## Lifecycle

The Brain operates on a continuous **Learn → Recall → Apply → Feedback** cycle:

```
┌──────────────────────────────────────────────────────────────────┐
│                    Brain Lifecycle                                │
│                                                                  │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌───────┐│
│    │  LEARN  │─────►│ RECALL  │─────►│  APPLY  │─────►│FEEDBACK││
│    └────┬────┘      └─────────┘      └─────────┘      └───┬───┘│
│         │                                                  │     │
│         │           ┌──────────────┐                       │     │
│         └──────────►│  Skill Graph │◄──────────────────────┘     │
│                     └──────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
```

### 1. Learn

An LLM solves a task in Domain A. The Brain observes the execution trace and abstracts it into a domain-agnostic skill.

**What happens internally:**

1. The `ContextAnalyzer` extracts abstract features from the execution context (task structures, cognitive patterns, I/O shapes, complexity).
2. The `Brain._extract_procedure()` converts execution trace steps into abstract `SkillStep` objects.
3. Pre/postconditions are derived from the context features and outcome quality.
4. The Brain checks for existing similar skills (see [Skill Deduplication](#skill-deduplication)). If one exists, it **reinforces** it (increments usage count, renews TTL) instead of creating a duplicate.
5. A new `Skill` is created, its TTL is set, and it is persisted to the `SkillGraph` in Redis.
6. A learning event is logged to OrKa's memory for traceability.

**Input requirements:**

```python
execution_trace = {
    "steps": [
        {"action": "gather symptoms", "result": "success"},
        {"action": "form hypotheses", "result": "success"},
        {"action": "test each hypothesis", "result": "success"},
    ],
    "agents": ["analyzer_agent"],
    "strategy": "sequential",
}

context = {
    "domain": "medical_diagnosis",
    "task": "diagnose patient condition",
    "input": "patient symptoms description",
}

outcome = {
    "success": True,
    "quality": 0.90,  # 0.0-1.0
}
```

### 2. Recall

A new task arrives in Domain B. The Brain searches its skill graph for skills that match the new context structurally and semantically.

**What happens internally:**

1. The `ContextAnalyzer` extracts features from the new context.
2. The `SkillTransferEngine` retrieves all non-expired skills from the graph.
3. Each skill is scored against the target context on four dimensions (structural, semantic, transfer record, confidence).
4. Candidates above `min_score` are returned, ranked by combined score.
5. Each candidate includes suggested adaptations and human-readable reasoning.
6. Lazy cleanup of expired skills runs at most once per hour.

### 3. Apply

The recalled skill's abstract procedure guides the LLM in solving the Domain B task. An LLM agent in the workflow receives the skill's steps, adaptations, and score, then produces a domain-specific solution following the transferred pattern.

This phase happens entirely in the YAML workflow — a `local_llm` or `openai-*` agent receives the recalled skill via Jinja2 template variables and adapts it.

### 4. Feedback

After applying the transferred skill, the workflow records whether the application succeeded or failed:

- **Successful transfer:** Skill confidence increases (+5% of remaining headroom), success rate updates, TTL renews, a `SkillTransferRecord` is appended.
- **Failed transfer:** Skill confidence decreases (-10% of current value), success rate updates, TTL is **not** renewed.

This feedback loop is critical: it lets the Brain learn which skills are genuinely transferable and which are domain-specific.

---

## Architecture

### Module Map

```
orka/brain/
├── __init__.py          # Public API exports
├── brain.py             # Brain — top-level orchestrator
├── context_analyzer.py  # ContextAnalyzer + ContextFeatures
├── skill.py             # Skill, SkillStep, SkillCondition, SkillTransferRecord
├── skill_graph.py       # SkillGraph — Redis-backed knowledge graph
└── transfer_engine.py   # SkillTransferEngine + TransferCandidate

orka/agents/
└── brain_agent.py       # BrainAgent — orchestrator-compatible wrapper
```

### Brain

`orka.brain.Brain` is the top-level entry point. It composes the other three components and exposes the public API:

```python
from orka.brain import Brain

brain = Brain(memory=redis_memory_logger, embedder=optional_embedder, llm_client=optional_llm)

# Learn
skill = await brain.learn(execution_trace, context, outcome)

# Recall
candidates = await brain.recall(context, top_k=5, min_score=0.3)

# Feedback
await brain.feedback(skill_id, context, success=True, adaptations={})

# Introspection
summary = await brain.get_skill_summary()
skills = await brain.get_skills()
skill = await brain.get_skill(skill_id)

# Maintenance
result = brain.cleanup_expired_skills()  # → {"deleted": 3, "checked": 42}
```

### ContextAnalyzer

`orka.brain.ContextAnalyzer` transforms raw execution contexts into abstract `ContextFeatures`. It operates in **rule-based mode** by default (no LLM needed), detecting task structures and cognitive patterns via keyword matching against a curated dictionary:

| Structure | Trigger Keywords |
|---|---|
| `decomposition` | break down, split, decompose, divide, parts, components |
| `sequential` | then, step by step, first, next, after, sequence, pipeline |
| `parallel` | simultaneously, parallel, concurrent, fork |
| `aggregation` | combine, merge, aggregate, join, collect, summarize |
| `comparison` | compare, versus, difference, contrast |
| `transformation` | convert, transform, translate, map, rewrite |
| `filtering` | filter, select, extract, pick, remove, exclude |
| `routing` | route, direct, if, decide, branch, choose |
| `iteration` | repeat, loop, iterate, until, converge, refine |
| `validation` | validate, verify, check, confirm, ensure, test, assess |

Cognitive patterns are detected with similar keyword dictionaries for `analysis`, `synthesis`, `evaluation`, `generation`, `classification`, `extraction`, `reasoning`, `planning`, `optimization`, and `abstraction`.

The orchestrator strategy (`sequential`, `parallel`) is also incorporated if present in the context metadata.

### SkillGraph

`orka.brain.SkillGraph` is the Redis-backed persistent store for skills and their inter-relationships. It provides:

- **CRUD**: `save_skill()`, `get_skill()`, `delete_skill()`, `list_skills()`.
- **Tag index**: `find_by_tag()` for filtering skills by semantic tags.
- **Graph edges**: `add_edge()`, `get_edges()`, `get_related_skills()` with BFS traversal.
- **TTL**: Redis native key expiry via `EXPIRE` for automatic eviction, plus application-level `cleanup_expired_skills()` for index cleanup.

See [Redis Storage Layout](#redis-storage-layout) for key naming details.

### SkillTransferEngine

`orka.brain.SkillTransferEngine` is the matching intelligence. It:

1. Analyzes the target context into `ContextFeatures`.
2. Retrieves all non-expired skills from the `SkillGraph`.
3. Scores each skill against the target on four dimensions.
4. Generates human-readable reasoning and adaptation suggestions.
5. Returns the top-k candidates above the minimum score.

See [Transfer Scoring](#transfer-scoring) for scoring details.

---

## YAML Workflow Configuration

### Agent Type: brain

The `brain` agent type is OrKa's orchestrator-compatible wrapper around the Brain engine.

```yaml
- id: brain_learn
  type: brain
  operation: learn
  prompt: "{{ previous_outputs.llm_agent }}"
```

### Operations

| Operation | Description | Key Input Fields | Key Output Fields |
|---|---|---|---|
| `learn` | Extract a skill from an LLM's reasoning trace | `response`, `steps`, `confidence`, `domain`, `task`, `skill_name` | `skill_id`, `skill_name`, `skill_steps`, `skill_tags`, `confidence` |
| `recall` | Find applicable skills for a new context | `domain`, `task`, `top_k`, `min_score` | `skill_id`, `skill_name`, `skill_steps`, `combined_score`, `structural_score`, `semantic_score`, `adaptations`, `all_candidates` |
| `feedback` | Record whether a transferred skill succeeded | `skill_id`, `success`, `domain`, `task`, `adaptations` | `skill_name`, `transfer_count`, `transfer_success`, `confidence` |

### Minimal Example

A three-agent workflow that learns from Domain A and recalls for Domain B:

```yaml
orchestrator:
  id: brain-demo
  strategy: sequential
  agents: [llm_solve, brain_learn, brain_recall]

agents:
  - id: llm_solve
    type: local_llm
    prompt: |
      Solve this task step by step: {{ input }}
      Return JSON with "response", "steps", "domain", "task", "confidence".
    params:
      provider: lm_studio
      model_url: "http://localhost:1234"
      model: "openai/gpt-oss-20b"

  - id: brain_learn
    type: brain
    operation: learn
    prompt: "{{ previous_outputs.llm_solve }}"

  - id: brain_recall
    type: brain
    operation: recall
    prompt: |
      {
        "domain": "new_domain",
        "task": "new task description"
      }
```

### Full Workflow Example

The reference workflow (`examples/brain_skill_transfer_workflow.yml`) implements the complete lifecycle with 8 agents:

```
Phase 1 — Learn from Domain A:
  domain_a_reasoner  →  brain_learn  →  domain_a_result
       (LLM)           (Brain)          (LLM summary)

Phase 2 — Transfer to Domain B:
  domain_b_context  →  brain_recall  →  domain_b_applier  →  brain_feedback  →  domain_b_result
      (LLM)            (Brain)           (LLM apply)         (Brain)            (LLM report)
```

**Phase 1** — The LLM (`domain_a_reasoner`) analyzes a medical diagnosis task, producing structured JSON with reasoning steps. The `brain_learn` agent extracts an abstract skill. The `domain_a_result` agent summarizes what was learned.

**Phase 2** — A new LLM (`domain_b_context`) describes a software debugging task. The `brain_recall` agent finds the medical diagnosis skill (which has structural overlap: decomposition + sequential + analysis + reasoning). The `domain_b_applier` receives the recalled skill and explicitly adapts each step to the debugging domain. The `brain_feedback` agent records whether the transfer was deemed successful. The `domain_b_result` agent produces a final validation report.

Run it with:

```bash
orka run examples/brain_skill_transfer_workflow.yml \
  "$(cat examples/inputs/brain_transfer_input.json)"
```

---

## Skill TTL and Expiry

Skills are not permanent. Unused skills decay and are eventually deleted, preventing the knowledge graph from growing unboundedly and keeping only actively useful knowledge.

### TTL Formula

$$\text{TTL}_{\text{hours}} = 168 \times (1 + \log_2(\max(1,\; \text{usage\_count}))) \times (0.5 + \text{confidence})$$

Where:
- **168 hours** (1 week) is the base TTL.
- **Usage scaling** via $\log_2$: a skill used 8 times lives $4\times$ longer than a skill used once.
- **Confidence scaling**: a skill with confidence 1.0 lives $3\times$ longer than one with confidence 0.0.

| Usage Count | Confidence | Effective TTL |
|---|---|---|
| 1 | 0.50 | 168h (1 week) |
| 1 | 0.90 | 235h (10 days) |
| 4 | 0.70 | 403h (17 days) |
| 8 | 0.80 | 655h (27 days) |
| 16 | 0.90 | 1,176h (49 days) |

### Renewal Policy

- **Successful usage** → TTL is **renewed** (extended from now).
- **Failed usage** → TTL is **not renewed** (continues to count down).

This means actively successful skills live indefinitely, while skills that stop being useful naturally expire.

### Cleanup

Expired skills are removed in three ways:

1. **Redis native TTL**: When a skill is saved, its Redis key gets a `EXPIRE` TTL matching the skill's `expires_at`. Redis itself will evict the key after expiry.
2. **Lazy application cleanup**: During `recall()`, the Brain runs `cleanup_expired_skills()` at most once per hour. This handles index entries and graph edges that Redis native TTL doesn't clean up.
3. **On-demand**: Call `brain.cleanup_expired_skills()` programmatically to force immediate cleanup. Returns `{"deleted": N, "checked": M}`.

**Backward compatibility**: Skills created before TTL was introduced have `expires_at = ""` and never expire.

---

## Transfer Scoring

When the Brain recalls skills for a new context, each candidate is scored on four dimensions:

### Scoring Weights

| Dimension | Weight | Measures |
|---|---|---|
| **Structural** | 0.35 | Task shape similarity (Jaccard on structures + patterns + shape matching) |
| **Semantic** | 0.25 | Meaning similarity (vector embeddings or keyword overlap) |
| **Transfer** | 0.25 | Historical transfer success rate (0.5 if no history) |
| **Confidence** | 0.15 | Skill's overall reliability score |

$$\text{combined} = 0.35 \cdot S_{\text{structural}} + 0.25 \cdot S_{\text{semantic}} + 0.25 \cdot S_{\text{transfer}} + 0.15 \cdot S_{\text{confidence}}$$

### Structural Similarity

Computed via `ContextFeatures.similarity_to()`:

- **Task structures** (weight 0.35): Jaccard similarity on `task_structures` sets.
- **Cognitive patterns** (weight 0.35): Jaccard similarity on `cognitive_patterns` sets.
- **Input shape** (weight 0.15): Exact match bonus.
- **Output shape** (weight 0.15): Exact match bonus.

### Semantic Similarity

Two modes:

1. **Embeddings** (when an embedder is provided): Encodes skill and target context into vectors (e.g., via `sentence-transformers/all-MiniLM-L6-v2`), computes cosine similarity, normalizes to [0, 1].
2. **Keyword overlap** (fallback): Jaccard similarity on tokenized `to_embedding_text()` representations.

### Transfer Track Record

- If the skill **has** transfer history: uses `transfer_success_rate` (successful transfers / total transfers).
- If the skill has **no** transfer history: defaults to 0.5 (neutral — neither penalized nor boosted).

### Confidence

The skill's `confidence` field (0.0–1.0), which evolves over time:

- **Successful use**: `confidence += 0.05 × (1.0 - confidence)` — diminishing returns as confidence approaches 1.0.
- **Failed use**: `confidence -= 0.10 × confidence` — proportional decay.

A new skill starts at confidence = `min(0.7, 0.5 + quality × 0.2)`.

---

## Skill Deduplication

Before creating a new skill, the Brain checks the existing graph for duplicates using a two-tier strategy:

1. **Exact fingerprint** (fast path): SHA-256 hash of canonical context features (sorted structures, patterns, shapes, goal). If two skills have the same fingerprint, they are considered identical.

2. **Structural similarity** (fallback): If no fingerprint match, compute `ContextFeatures.similarity_to()` for every existing skill. If the best match scores ≥ 0.70, that skill is **reinforced** instead of creating a duplicate — its `usage_count` increments, `success_rate` updates, and TTL renews.

This prevents the skill graph from filling with near-duplicate entries while still allowing genuinely different skills to coexist.

---

## Redis Storage Layout

All Brain data is stored in Redis under the `orka:brain:` namespace:

| Key Pattern | Type | Contents |
|---|---|---|
| `orka:brain:skill:{id}` | String (JSON) | Full serialized Skill object |
| `orka:brain:skill_index` | Hash | `{skill_id: skill_name}` for fast enumeration |
| `orka:brain:tags:{tag}` | Set | Skill IDs that have this tag |
| `orka:brain:edges:{skill_id}` | Set (JSON entries) | Outgoing graph edges from this skill |

**Redis requirements:**
- RedisStack is recommended (for future vector search support).
- Standard Redis works for all current functionality.
- Start with `orka-start` or provide `REDIS_URL` environment variable.

---

## Graph Relationships

Skills can be connected through typed directed edges:

| Relation | Meaning |
|---|---|
| `DERIVES_FROM` | Skill B is a refinement of Skill A |
| `COMPOSED_OF` | Skill C is built from Skills A and B |
| `SPECIALIZES` | Skill B is a domain-specific version of Skill A |
| `TRANSFERRED_TO` | Skill A was successfully applied in a new context |
| `CONFLICTS_WITH` | Skills A and B are mutually exclusive approaches |
| `COMPLEMENTS` | Skills A and B work well together |

Edges are bidirectional (reverse edges are stored automatically). Graph traversal uses BFS with configurable `max_depth`:

```python
related = skill_graph.get_related_skills(skill_id, relation="COMPLEMENTS", max_depth=2)
```

---

## Programmatic API

### Creating a Brain

```python
from orka.brain import Brain

# With Redis memory logger (standard usage)
brain = Brain(memory=redis_memory_logger)

# With optional embedder for semantic search
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer("all-MiniLM-L6-v2")
brain = Brain(memory=redis_memory_logger, embedder=embedder)
```

### Learning a Skill

```python
skill = await brain.learn(
    execution_trace={
        "steps": [
            {"action": "gather evidence", "result": "success"},
            {"action": "form hypothesis", "result": "success"},
            {"action": "test hypothesis", "result": "success"},
            {"action": "draw conclusion", "result": "success"},
        ],
        "agents": ["analyzer"],
        "strategy": "sequential",
    },
    context={
        "domain": "scientific_research",
        "task": "validate experimental results",
    },
    outcome={"success": True, "quality": 0.85},
    skill_name="Hypothesis Testing",  # optional
)
# skill.id → "a1b2c3d4-..."
# skill.procedure → [SkillStep(...), SkillStep(...), ...]
# skill.confidence → 0.67
```

### Recalling Skills

```python
candidates = await brain.recall(
    context={
        "domain": "software_qa",
        "task": "validate that the new feature works correctly",
    },
    top_k=3,
    min_score=0.3,
)

for c in candidates:
    print(f"{c.skill.name}: {c.combined_score:.2f}")
    print(f"  Reasoning: {c.reasoning}")
    print(f"  Adaptations: {c.adaptations}")
```

### Providing Feedback

```python
await brain.feedback(
    skill_id=candidates[0].skill.id,
    context={"domain": "software_qa", "task": "feature validation"},
    success=True,
    adaptations={"input_adaptation": {"from": "long_text", "to": "structured"}},
)
```

### Introspection

```python
summary = await brain.get_skill_summary()
# {
#   "total_skills": 12,
#   "transferable_skills": 5,
#   "avg_confidence": 0.72,
#   "total_transfers": 18,
#   "top_skills": [{"name": "...", "usage_count": 8, ...}, ...]
# }
```

### Direct Graph Operations

```python
from orka.brain import SkillGraph

graph = brain.skill_graph

# List all skills
skills = graph.list_skills()

# Find by tag
analysis_skills = graph.find_by_tag("analysis")

# Add graph relationship
graph.add_edge(skill_a.id, "COMPLEMENTS", skill_b.id)

# Traverse graph
related = graph.get_related_skills(skill_a.id, max_depth=2)

# Clean up expired
result = graph.cleanup_expired_skills()
print(f"Removed {result['deleted']} of {result['checked']} skills")
```

---

## TUI Dashboard

The OrKa TUI (`orka memory watch`) includes a **Brain Skills** tab showing:

- **Skills table**: Name, confidence, usage count, success rate, transfers, tags, TTL (color-coded: green = months, yellow = weeks, red = days, bold red = expiring in <24h).
- **Skill detail panel**: Full procedure steps, pre/postconditions, transfer history, TTL detail.
- **Header counters**: Total skills, transferable skills, expiring-soon count.

---

## Running the Demo

A standalone demo script runs 10 scenarios without Redis or an LLM, using an in-memory store:

```bash
python examples/brain_skill_transfer_demo.py
```

It learns 3 skills (Decompose-Analyze-Synthesize, Validate-Classify-Route, Iterative Refinement) and then tests recall accuracy across 7 different domains:

| Scenario | Domain | Expected Skill |
|---|---|---|
| Code Review | software_engineering | Decompose-Analyze-Synthesize |
| Content Moderation | content_safety | Validate-Classify-Route |
| Code Optimization | performance_engineering | Iterative Refinement |
| Financial Analysis | finance | Decompose-Analyze-Synthesize |
| API Gateway | infrastructure | Validate-Classify-Route |
| Essay Grading | education | Iterative Refinement |
| Incident Response | operations | Decompose-Analyze-Synthesize |

---

## Testing

Brain-related tests are in:

- `tests/unit/brain/test_brain.py` — Brain engine learn/recall/feedback + TTL.
- `tests/unit/brain/test_skill_graph.py` — Graph CRUD, edges, tag indexing, TTL cleanup.
- `tests/unit/agents/test_brain_agent.py` — BrainAgent operations and full lifecycle.
- `tests/unit/tui/test_brain_skills_screen.py` — TUI TTL formatting and display.

Run them with:

```bash
pytest tests/unit/brain/ tests/unit/agents/test_brain_agent.py -v
```

---

## FAQ

**Q: Does the Brain require an LLM?**  
A: No. The `ContextAnalyzer` works in rule-based mode by default. An LLM is only needed for the reasoning agents in the workflow (the `local_llm` / `openai-*` agents that produce execution traces and apply recalled skills). An `llm_client` can optionally be passed to the `Brain` constructor for richer context analysis in future versions.

**Q: Does the Brain require Redis?**  
A: Yes, for production use. The `SkillGraph` uses Redis for persistent storage. For demos and tests, an in-memory fake store can be used (see `examples/brain_skill_transfer_demo.py`).

**Q: What embedding model is used?**  
A: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) is recommended. If no embedder is provided, semantic matching falls back to keyword overlap (Jaccard similarity on tokenized text).

**Q: How is "cross-domain transfer" different from regular retrieval?**  
A: Regular RAG retrieval finds documents that mention similar terms. The Brain finds *procedural patterns* that match structurally, even when the domains share zero vocabulary. A medical diagnosis skill can transfer to software debugging because both follow decomposition → hypothesis → testing → conclusion — despite having no words in common.

**Q: What happens to skills created before TTL was introduced?**  
A: They have `expires_at = ""` and never expire. They continue to work exactly as before.

**Q: Can I disable TTL?**  
A: Don't call `renew_ttl()` and leave `expires_at` empty. However, the standard `Brain.learn()` flow always sets a TTL.

**Q: How do I inspect the Brain's knowledge?**  
A: Use `orka memory watch` (TUI) for a visual dashboard, or call `await brain.get_skill_summary()` programmatically.

---

← [Memory System](MEMORY_SYSTEM_GUIDE.md) | [📚 INDEX](index.md) | [Agents](agents.md) →
