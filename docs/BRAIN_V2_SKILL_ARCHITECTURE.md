# Brain v2 — Skill Architecture Redesign

## Problem Diagnosis

The current Brain stores **cognitive meta-patterns** the LLM already knows:

| Current Skill Name | Why It's Useless |
|---|---|
| `Analysis via Decomposition (text_analysis)` | Every LLM knows "break things down" |
| `Reasoning via Sequential (code_review)` | "Think step-by-step" is a default prompt strategy |
| `Evaluation via Validation (testing)` | "Check correctness" is trivially known |

**Root cause**: The `ContextAnalyzer` keyword-matches abstract terms
(`decomposition`, `analysis`, `sequential`) from a fixed vocabulary of 10
task structures × 10 cognitive patterns. This produces a **100-cell grid** of
names that are all interchangeable from the LLM's perspective.

The `to_embedding_text()` output is equally generic:
```
"Apply analysis and synthesis on single_text producing structured 
 | structures: decomposition, aggregation 
 | patterns: analysis, synthesis 
 | input: single_text | output: structured"
```

This embeds close to *every* analytical task — no discrimination power.

---

## What the Brain Should Store Instead

The Brain should store knowledge **the LLM cannot derive from its weights**:

### 1. Execution Recipes (Graph Skills)

**What**: Specific OrKa agent compositions that succeeded for a task type.

```yaml
skill:
  name: "security-audit:multi-scanner-parallel"
  type: execution_recipe
  recipe:
    pattern: fork-join
    agents:
      - {id: sast_scanner, type: local_llm, role: static-analysis}
      - {id: dep_checker, type: duckduckgo, role: vulnerability-lookup}
      - {id: secret_scanner, type: local_llm, role: credential-detection}
    join_strategy: merge-by-severity
    total_agents: 4
    avg_latency_ms: 3200
    success_rate: 0.91
  embedding_text: >
    security audit vulnerability scan static analysis
    credential detection dependency check parallel fork-join
    code review application security OWASP
```

**Why valuable**: The LLM knows *what* a security audit is, but not *which
OrKa agents to compose and how* for your specific deployment.

### 2. Prompt Templates That Worked

**What**: Actual prompt fragments/structures that produced quality output.

```yaml
skill:
  name: "vet-diagnosis:differential-reasoning-template"
  type: prompt_template
  template_fragments:
    system: "You are a veterinary diagnostician. Use the DAMNIT-V mnemonic..."
    reasoning_frame: |
      1. List presenting signs
      2. Generate differential diagnoses (>=5)
      3. For each: assign likelihood (%), cite supporting/opposing evidence
      4. Recommend diagnostic tests ordered by information value per cost
    output_schema:
      differentials: [{name, likelihood_pct, supporting, opposing}]
      recommended_tests: [{test, rationale, expected_findings}]
  embedding_text: >
    veterinary diagnosis differential DAMNIT-V mnemonic
    clinical signs presenting complaints diagnostic tests
    likelihood probability animal patient assessment
```

**Why valuable**: The specific prompt structure + output schema that worked is
deployment-specific knowledge.

### 3. Parameter Configurations

**What**: Model/temperature/token settings that worked for task types.

```yaml
skill:
  name: "financial-analysis:conservative-reasoning-config"
  type: parameter_config
  config:
    model: "llama-3.1-70b"
    temperature: 0.15
    max_tokens: 4096
    system_prompt_style: "structured-analytical"
    json_mode: true
  context_match: "financial|regulatory|compliance|risk"
  quality_achieved: 0.89
  embedding_text: >
    financial analysis risk assessment regulatory compliance
    conservative low temperature structured output JSON
    quantitative reasoning numerical precision
```

### 4. GraphScout Path Discoveries

**What**: Optimal workflow paths discovered by GraphScout at runtime.

```yaml
skill:
  name: "path:content-moderation→classifier+safety→summarizer"
  type: graph_path
  path:
    nodes: [classifier_agent, safety_checker, summarizer]
    edges: [{from: classifier, to: safety, type: sequential},
            {from: safety, to: summarizer, type: sequential}]
    score: 0.87
    budget_used: {tokens: 450, latency_ms: 2100}
  context_match: "content moderation user-generated text policy"
  embedding_text: >
    content moderation policy violation detection classification
    safety check user generated content text filtering
    summarize findings report
```

### 5. Failure Anti-Patterns

**What**: Configurations/paths that failed, to avoid repeating.

```yaml
skill:
  name: "anti:local_llm:long-context-summarization"
  type: anti_pattern
  failure:
    what_failed: "local_llm agent with input > 8k tokens"
    why: "Model context window exceeded, output truncated"
    domain: "document summarization"
    severity: critical
  avoid_when: "input_length > 8000 AND agent_type == local_llm"
  embedding_text: >
    long document summarization context window exceeded truncated
    local LLM token limit overflow large input text
```

---

## New Skill Taxonomy

### Skill Types Enum

```python
class SkillType(str, Enum):
    EXECUTION_RECIPE = "execution_recipe"   # Agent composition graph
    PROMPT_TEMPLATE  = "prompt_template"     # Prompt structure that worked
    PARAMETER_CONFIG = "parameter_config"    # Model/temp/token settings
    GRAPH_PATH       = "graph_path"          # GraphScout-discovered path
    ANTI_PATTERN     = "anti_pattern"        # What NOT to do
    DOMAIN_HEURISTIC = "domain_heuristic"   # Domain-specific rules
    # DEPRECATED: procedural (old generic patterns)
```

### Naming Convention

**Old**: `{CognitivePattern} via {TaskStructure} ({domain})`  
**New**: `{type}:{domain}:{specifics}`

Examples:
- `recipe:code-review:parallel-linter+scanner→merge`
- `prompt:vet-diagnosis:differential-with-DAMNIT-V`
- `config:financial:conservative-T0.15-70b`
- `path:moderation→classifier→safety→report`
- `anti:local-llm:context-overflow-on-long-docs`
- `heuristic:api-design:rest-versioning-rules`

**Why this is better for vector search**:
1. The `:` prefix acts as a namespace filter (can pre-filter by type)
2. Domain terms are concrete, not abstract ("vet-diagnosis" vs "analysis")
3. Specifics contain actionable keywords the LLM would use when asking

---

## Improved Embedding Text

### Current Problem

`to_embedding_text()` produces generic descriptors:
```
Analysis via Decomposition | Analyze concepts | decomposition, analysis
| decompose input | aggregate results | input is structured
```

This is equidistant from almost every task.

### Proposed Solution: Structured Semantic Anchors

```python
def to_embedding_text(self) -> str:
    """Produce embedding text with high semantic discrimination."""
    parts = []

    # 1. WHAT: concrete task description (not abstract)
    parts.append(self.task_description)  # "Review Python code for security vulnerabilities"

    # 2. HOW: agent composition (OrKa-specific knowledge)
    if self.type == SkillType.EXECUTION_RECIPE:
        agent_names = [a["id"] for a in self.recipe["agents"]]
        parts.append(f"agents: {' → '.join(agent_names)}")
        parts.append(f"pattern: {self.recipe['pattern']}")

    # 3. DOMAIN: concrete domain terms
    parts.extend(self.domain_keywords)  # ["python", "security", "OWASP", "CVE"]

    # 4. OUTCOME: what the skill produces
    parts.append(f"produces: {self.output_description}")

    # 5. ANTI-SIGNALS: what this is NOT (negative anchors)
    if self.anti_signals:
        parts.append(f"not: {', '.join(self.anti_signals)}")

    return " ".join(parts)
```

### Key Principle: Embed What's Unique, Not What's Universal

| Layer | Old (generic) | New (specific) |
|---|---|---|
| Task | "analysis" | "review Python code for SQL injection patterns" |
| Method | "decomposition" | "fork: sast_scanner + dep_checker + secret_scanner" |
| Domain | "code_review" | "application security, OWASP Top 10, CVE database" |
| Output | "structured" | "severity-ranked finding list with remediation steps" |

---

## GraphScout ↔ Brain Integration

### Workflow: Brain-Assisted Path Discovery

```
                   ┌──────────────┐
User Task ────────►│  GraphScout  │
                   │  Introspect  │
                   └──────┬───────┘
                          │ Available agents/paths
                          ▼
                   ┌──────────────┐
                   │  Brain       │
                   │  Recall      │◄─── "Do I know a recipe for this task type?"
                   └──────┬───────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         Match Found   No Match   Anti-Pattern Found
              │           │           │
              ▼           ▼           ▼
        Boost path    Normal       Penalize path
        score by     GraphScout     score, warn
        recipe       evaluation
        confidence
              │           │           │
              └───────────┼───────────┘
                          ▼
                   ┌──────────────┐
                   │  Execute     │
                   │  Best Path   │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Brain       │
                   │  Learn       │◄─── Store path as execution_recipe or graph_path
                   └──────────────┘
```

### Integration Points

#### 1. Pre-Evaluation Hook (in `graph_scout_agent.py`)

```python
# After introspection, before LLM evaluation
brain_candidates = await brain.recall(
    context={
        "domain": task_domain,
        "task": task_description,
        "available_agents": [a.id for a in available_agents],
    },
    top_k=3,
    min_score=0.4,
)

for candidate in brain_candidates:
    if candidate.skill.type == SkillType.EXECUTION_RECIPE:
        # Boost matching paths
        matching_path = find_path_matching_recipe(candidate.skill, discovered_paths)
        if matching_path:
            matching_path.brain_boost = candidate.combined_score * 0.3

    elif candidate.skill.type == SkillType.ANTI_PATTERN:
        # Penalize matching anti-patterns
        for path in discovered_paths:
            if matches_anti_pattern(candidate.skill, path):
                path.brain_penalty = -0.5
```

#### 2. Post-Execution Hook (after path completes)

```python
# After successful execution via GraphScout-selected path
await brain.learn(
    execution_trace={
        "steps": executed_path.nodes,
        "agents": executed_path.agent_ids,
        "strategy": executed_path.pattern,  # "sequential", "fork-join"
        "duration_ms": execution_time,
        "graphscout_score": selected_path.score,
    },
    context={
        "domain": task_domain,
        "task": task_description,
        "skill_type": "graph_path",
    },
    outcome={
        "success": True,
        "quality": quality_score,
    },
)
```

#### 3. Score Blending (in `path_scoring.py`)

Add a new scoring component:

```python
# Current weights
SCORING_WEIGHTS = {
    "llm": 0.40,        # Was 0.45
    "heuristics": 0.15,  # Was 0.20
    "prior": 0.15,       # Was 0.20
    "cost": 0.10,
    "latency": 0.05,
    "brain": 0.15,       # NEW: Brain skill match
}
```

---

## Better Filtering: Skill Name as First-Pass Filter

### Problem

Currently `find_transferable_skills()` loads ALL skills, scores ALL of them.
With 100+ skills this is slow and noisy.

### Solution: Two-Stage Retrieval

```
Stage 1: Name-based prefix filter (O(1) via Redis SCAN)
    ├── Filter by skill type: "recipe:*", "path:*", "anti:*"
    ├── Filter by domain prefix: "recipe:code-review:*"
    └── Returns: ~5-10 candidates (down from 100+)

Stage 2: Vector similarity on filtered set
    ├── Embed query context
    ├── Compare against candidate embeddings
    └── Returns: ranked top-k with scores
```

### Redis Implementation

```python
# Namespace index (new)
orka:brain:type_index:{skill_type}     → Set of skill_ids
orka:brain:domain_index:{domain}       → Set of skill_ids

# Query flow
def find_skills(self, skill_type=None, domain=None, query_text=None, top_k=5):
    # Stage 1: Set intersection for prefix filtering
    candidate_ids = None
    if skill_type:
        type_ids = redis.smembers(f"orka:brain:type_index:{skill_type}")
        candidate_ids = type_ids
    if domain:
        domain_ids = redis.smembers(f"orka:brain:domain_index:{domain}")
        candidate_ids = candidate_ids & domain_ids if candidate_ids else domain_ids

    # Stage 2: Vector search on filtered candidates
    if query_text and candidate_ids:
        return vector_search(query_text, filter_ids=candidate_ids, top_k=top_k)
    elif candidate_ids:
        return [get_skill(sid) for sid in candidate_ids]
    else:
        return vector_search(query_text, top_k=top_k)  # Full search fallback
```

### Skill Name Tokenization for Search

Add a `search_tokens` field derived from the skill name:

```python
def generate_search_tokens(name: str) -> list[str]:
    """Extract searchable tokens from structured skill name.
    
    'recipe:code-review:parallel-linter+scanner→merge'
    → ['recipe', 'code-review', 'code', 'review', 'parallel',
       'linter', 'scanner', 'merge']
    """
    # Split on : - + → / _
    raw = re.split(r'[:+→/\-_\s]+', name)
    tokens = [t.lower().strip() for t in raw if t.strip()]
    # Add compound terms
    if ':' in name:
        parts = name.split(':')
        tokens.append(parts[0])  # type prefix
        if len(parts) > 1:
            tokens.append(parts[1])  # domain
    return list(set(tokens))
```

These tokens go into a Redis Search TAG field for instant prefix filtering.

---

## Implementation Roadmap

### Phase 1: Skill Type System (no breaking changes)

1. Add `SkillType` enum to `skill.py`
2. Add `skill_type` field to `Skill` dataclass (default: `"procedural"` for backward compat)
3. Add `domain_keywords`, `task_description`, `output_description` fields
4. Update `to_embedding_text()` to use new fields when available
5. Add Redis type/domain indexes to `skill_graph.py`
6. Update `_generate_skill_name()` to use `{type}:{domain}:{specifics}` format

### Phase 2: New Learning Modes

7. Add `learn_recipe()` — learns from successful multi-agent execution traces
8. Add `learn_path()` — learns from GraphScout path discoveries
9. Add `learn_anti_pattern()` — learns from failures
10. Update `BrainAgent` to support `operation: learn_recipe|learn_path|learn_anti`

### Phase 3: GraphScout Integration

11. Inject `Brain` instance into `GraphScoutAgent`
12. Add pre-evaluation Brain recall hook
13. Add `brain` weight to `PathScorer`
14. Add post-execution Brain learn hook
15. Add anti-pattern penalty logic

### Phase 4: Two-Stage Retrieval

16. Add `search_tokens` field + Redis TAG index
17. Update `find_transferable_skills()` with prefix filter → vector search pipeline
18. Add domain auto-detection from query context
19. Performance benchmark: compare old vs new retrieval latency

---

## Example: Full Brain v2 Workflow

```yaml
orchestrator:
  id: brain_v2_demo
  strategy: sequential
  agents: [reasoner, brain_recall, graph_scout, executor, brain_learn]

agents:
  # 1. Understand the task
  - id: reasoner
    type: local_llm
    prompt: |
      Analyze this task and identify:
      - Domain (be specific: "python-security-audit", not "code-review")
      - Required capabilities (what tools/agents are needed)
      - Expected output format
      Task: {{ input }}

  # 2. Check Brain for existing recipes
  - id: brain_recall
    type: brain
    operation: recall
    params:
      skill_types: [execution_recipe, graph_path, parameter_config]
      domain_filter: "{{ previous_outputs.reasoner.result.domain }}"
      top_k: 3
      min_score: 0.5
    prompt: "{{ previous_outputs.reasoner.result }}"

  # 3. GraphScout with Brain boost
  - id: graph_scout
    type: graph-scout
    brain_assisted: true  # NEW: enables Brain score integration
    brain_boost_weight: 0.15
    prompt: |
      Find the best agent path.
      Brain suggests: {{ previous_outputs.brain_recall.result }}
      Task: {{ input }}

  # 4. Execute the chosen path
  - id: executor
    type: path_executor
    prompt: "{{ previous_outputs.graph_scout.result.selected_path }}"

  # 5. Learn from this execution
  - id: brain_learn
    type: brain
    operation: learn_recipe  # NEW: stores as execution_recipe
    prompt: |
      {
        "execution": {{ previous_outputs.executor | tojson }},
        "path": {{ previous_outputs.graph_scout.result | tojson }},
        "domain": "{{ previous_outputs.reasoner.result.domain }}",
        "success": true
      }
```

---

## Metrics to Track

| Metric | Target | How |
|---|---|---|
| Skill discrimination | Avg cosine distance between skills > 0.3 | Monitor embedding spread |
| Retrieval precision | Top-1 recall matches task domain 80%+ | Judge on benchmark tasks |
| Filter reduction | Stage 1 reduces candidates by 80%+ | Log candidate counts |
| GraphScout improvement | Brain-boosted paths win 60%+ vs unboosted | A/B in benchmark |
| Anti-pattern prevention | 0 repeated known failures | Track failure recurrence |
