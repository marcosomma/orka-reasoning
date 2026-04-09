# Benchmark v2 Fix Plan — Brain Skill System & Evaluation Methodology

**Date:** 2026-04-09
**Context:** Benchmark v2 results (250 tasks, 500 runs, 750 judge evaluations) show brain winning 59% of pairwise comparisons but only +0.03 overall rubric delta. Root-cause analysis identified five concrete problems: three in the brain skill system, two in the benchmark methodology.

---

## TL;DR — Five Problems, Five Fixes

| # | Problem | Where | Severity | Fix |
|---|---------|-------|----------|-----|
| 1 | Skills store verbatim answers, not abstract patterns | `brain_agent.py` L148–160, `brain.py` L625–660 | **Critical** | Extract domain-agnostic procedural templates |
| 2 | Recall threshold too low (min_score=0.0 at agent level) | `brain_agent.py` L233 | **High** | Raise to 0.5 + add per-component minimums |
| 3 | Same LLM judges its own output (rubric compression) | `run_benchmark_v2.py` (monolithic) | **Medium** | Split into 3 scripts: execute → judge → aggregate; pluggable judge workflows |
| 4 | Track C tests routing, not brain transfer | `brain_track_c.yml`, dataset | **Medium** | Redesign or report separately |
| 5 | Brainless gets two-pass advantage (no single-pass baseline) | `brainless_track_*.yml` | **Low** | Add single-pass control condition |

---

## Problem 1 — Skills Are Verbatim, Not Abstract

### Diagnosis

When `brain_agent.py` receives a learn operation, it falls into this path for most benchmark tasks (lines 148–160):

```python
# No structured steps available → split response text into sentences
source = reasoning if len(reasoning) > len(response_text) else response_text
sentences = [
    s.strip()
    for s in source.replace("\n", ". ").split(". ")
    if len(s.strip()) > 20
]
steps_raw = [{"action": s, "result": "success"} for s in sentences[:10]]
```

This takes the **literal LLM response text**, splits it on period boundaries, and stores the first 10 sentences as "skill steps." The result is a skill like:

```
Skill: procedural:general:evaluation-sequential
Steps:
  "Domain: software_architecture"
  "Task: Review the authentication service for a healthcare portal."
  "Stateless JWT verification violated by per-request DB lookup..."
  "Refresh token rotation race condition..."
```

This is not a transferable abstraction. It's a copy of a prior answer. When recalled for a caching architecture task (semantic_score: 0.024), it injects irrelevant JWT-specific text into the prompt, degrading reasoning quality.

### Root Cause

`_extract_procedure()` in `brain.py` (L625–660) does have the right structure for handling structured `steps` dicts — extracting `action`, `description`, `parameters`. But the LLM output rarely contains structured `steps`. The fallback in `brain_agent.py` treats raw response text as steps, which defeats the purpose.

### Fix: Two-Stage Abstraction

#### Stage A — LLM-Assisted Abstraction (brain_agent.py)

Replace the sentence-splitting fallback with an LLM call that extracts abstract procedural patterns:

**File:** `orka/agents/brain_agent.py`, lines 145–160

```python
# BEFORE (current):
sentences = [s.strip() for s in source.replace("\n", ". ").split(". ") if len(s.strip()) > 20]
steps_raw = [{"action": s, "result": "success"} for s in sentences[:10]]

# AFTER (proposed):
steps_raw = await self._abstract_procedure(source, payload.get("domain", "general"))
```

New method `_abstract_procedure()`:

```python
async def _abstract_procedure(self, text: str, domain: str) -> list[dict]:
    """Extract abstract, domain-agnostic procedure steps from LLM output.
    
    Instead of storing verbatim sentences, ask the LLM to generalize
    the procedure into transferable steps with slot-fillers.
    """
    # If the text already has structured steps, use them directly
    # Otherwise, use heuristic abstraction
    
    # Heuristic approach (no extra LLM call, fast):
    # 1. Detect action verbs and normalize them
    # 2. Replace domain-specific nouns with abstract placeholders
    # 3. Preserve the procedural skeleton
    
    # Derived from frequency analysis of 100 real brain outputs.
    # Organized by cognitive category for maintainability.
    ACTION_VERBS = {
        # Discovery & investigation (top: identify=22, collect=7, gather=6)
        "identify", "detect", "discover", "investigate", "inspect",
        "explore", "scan", "survey", "probe", "research",
        # Data acquisition (collect=7, gather=6, extract=5, catalog=3)
        "collect", "gather", "extract", "fetch", "retrieve",
        "parse", "catalog", "inventory", "compile", "mine",
        # Analysis & evaluation (assess=7, evaluate=3, review=6, audit=6)
        "analyze", "evaluate", "assess", "review", "audit",
        "diagnose", "profile", "benchmark", "measure", "quantify",
        "examine", "interpret", "characterize", "study",
        # Planning & design (design=11, define=19, plan=4, establish=4)
        "design", "define", "plan", "establish", "architect",
        "outline", "draft", "formulate", "specify", "scope",
        "schedule", "prioritize", "budget", "allocate", "assign",
        # Creation & implementation (implement=28, create=10, develop=3)
        "implement", "create", "build", "construct", "develop",
        "generate", "produce", "compose", "synthesize", "author",
        "introduce", "provision", "configure", "set",
        # Transformation & processing (normalize=2, refactor=2, migrate=1)
        "transform", "convert", "translate", "normalize", "standardize",
        "adapt", "modify", "refactor", "restructure", "migrate",
        "deduplicate", "merge", "consolidate", "aggregate", "align",
        # Validation & verification (validate=14, verify=3, test=3)
        "validate", "verify", "check", "confirm", "test",
        "assert", "ensure", "certify", "reconcile", "audit",
        # Classification & organization (classify=2, map=6, select=2)
        "classify", "categorize", "group", "cluster", "sort",
        "rank", "label", "tag", "index", "organize",
        "map", "segment", "partition", "select", "filter",
        # Computation & modeling (compute=plan, estimate=plan, model=plan)
        "compute", "calculate", "estimate", "derive", "simulate",
        "model", "predict", "forecast", "project", "interpolate",
        # Optimization & improvement (optimize=1, refine=1, iterate=5)
        "optimize", "improve", "enhance", "tune", "calibrate",
        "adjust", "refine", "streamline", "iterate",
        # Communication & documentation (document=20, summarize=3, report=3)
        "document", "summarize", "report", "present", "explain",
        "describe", "annotate", "communicate", "recommend", "propose",
        "suggest", "provide", "offer",
        # Mitigation & resolution
        "mitigate", "resolve", "fix", "patch", "repair",
        "remediate", "address", "correct", "recover", "restore",
        # Execution & deployment (deploy=7, run=2, automate=3)
        "deploy", "execute", "run", "launch", "invoke",
        "trigger", "activate", "initiate", "automate", "perform",
        # Integration & composition (integrate=5, load=2)
        "integrate", "combine", "unify", "connect", "link",
        "load", "ingest", "import", "export",
        # Monitoring & observation (monitor=6, instrument=2, train=2)
        "monitor", "observe", "track", "trace", "instrument",
        "log", "watch",
        # Learning & iteration (train=2, apply=3, update=2)
        "train", "apply", "update", "replace", "rollback",
        "conduct", "prepare",
    }
    # IMPORTANT!!!  This list need to be globally available so new helper _abstract_action() can reuse it without hardcoding.
    
    abstract_steps = []
    for sentence in text.replace("\n", ". ").split(". "):
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        # Find leading action verb
        words = sentence.split()
        verb = words[0].lower().rstrip(":.,-")
        if verb in ACTION_VERBS:
            # Keep the abstract action, drop domain specifics
            abstract_steps.append({
                "action": f"{verb} [component/entity]",
                "result": "identified findings",
                "description": sentence,  # Keep original for context
            })
        elif any(v in sentence.lower() for v in ACTION_VERBS):
            # Action verb embedded in sentence
            for v in ACTION_VERBS:
                if v in sentence.lower():
                    abstract_steps.append({
                        "action": f"{v} [target]",
                        "result": "processed result",
                        "description": sentence,
                    })
                    break
        
        if len(abstract_steps) >= 8:
            break
    
    # No abstract steps found — do NOT create generic filler.
    # Generic procedures pollute the skill graph with noise that
    # structurally matches everything but teaches nothing.
    # Return empty → brain.learn() will bail out ("Could not extract
    # procedure from trace") and skip skill creation entirely.
    if not abstract_steps:
        logger.warning(
            "No actionable procedure could be abstracted from text (%d chars). "
            "Skipping skill creation.",
            len(text),
        )
        return []
    
    return abstract_steps
```

#### Stage B — Improve _extract_procedure in brain.py

**File:** `orka/brain/brain.py`, lines 625–660

Add pattern-based abstraction when steps come as text sentences:

```python
def _extract_procedure(self, trace: dict[str, Any]) -> list[SkillStep]:
    steps: list[SkillStep] = []
    raw_steps = trace.get("steps", [])

    for i, step in enumerate(raw_steps):
        if isinstance(step, dict):
            action = step.get("action", step.get("agent_id", f"step_{i}"))
            description = step.get("description", step.get("result", ""))
            # NEW: Abstract the action if it looks like a verbatim sentence
            if len(str(action)) > 80:
                action = self._abstract_action(action)
            steps.append(
                SkillStep(
                    action=str(action),
                    description=str(description),
                    order=i,
                    parameters=step.get("parameters", {}),
                    is_optional=step.get("optional", False),
                )
            )
        elif isinstance(step, str):
            action = self._abstract_action(step) if len(step) > 80 else step
            steps.append(SkillStep(action=action, description=step, order=i))
    # ... rest unchanged
```

New helper:

```python
# Verb normalization map — maps synonyms to a canonical form.
# Keys MUST be a subset of ACTION_VERBS (from _abstract_procedure).
# When implementing, import ACTION_VERBS as a module-level constant
# shared between brain_agent.py and brain.py so both use the same set.
_ACTION_VERB_CANONICAL = {
    # discovery synonyms → canonical
    "review": "evaluate", "check": "validate", "find": "identify",
    "inspect": "evaluate", "examine": "analyze", "study": "analyze",
    "research": "investigate", "probe": "investigate",
    # creation synonyms → canonical
    "build": "construct", "create": "generate", "produce": "generate",
    "compose": "generate", "author": "generate", "develop": "implement",
    # mitigation synonyms → canonical
    "fix": "mitigate", "patch": "mitigate", "repair": "mitigate",
    "correct": "mitigate", "remediate": "mitigate",
    # optimization synonyms → canonical
    "improve": "optimize", "enhance": "optimize", "tune": "optimize",
    "refine": "optimize", "streamline": "optimize",
    # validation synonyms → canonical
    "test": "validate", "verify": "validate", "confirm": "validate",
    "assert": "validate", "ensure": "validate",
    # execution synonyms → canonical
    "deploy": "execute", "run": "execute", "launch": "execute",
    "invoke": "execute", "trigger": "execute",
}

def _abstract_action(self, text: str) -> str:
    """Reduce a verbose sentence to an abstract action phrase."""
    words = text.strip().split()
    if not words:
        return "process"
    verb = words[0].lower().rstrip(":.,-()")
    verb = self._ACTION_VERB_CANONICAL.get(verb, verb)
    # Return "verb [target]" pattern
    if len(words) > 3:
        return f"{verb} [target]"
    return text
```

> **Note:** `ACTION_VERBS` (the full ~170-verb set) and `_ACTION_VERB_CANONICAL` (the normalization map) should be defined as module-level constants in a shared location (e.g., `orka/brain/constants.py`) and imported by both `brain_agent.py` and `brain.py`. This ensures a single source of truth — adding a verb to one place covers both detection and normalization.

#### Stage C — SkillStep Validation Schema

`SkillStep` currently has **zero validation** on the `action` field — any string is accepted, which is how verbatim sentences got stored in the first place. Adding a lightweight validation layer in the dataclass prevents regression.

**File:** `orka/brain/skill.py`, in `SkillStep`

```python
MAX_ACTION_LENGTH = 60  # Abstract actions should be concise

@dataclass
class SkillStep:
    action: str
    description: str = ""
    order: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    is_optional: bool = False

    def __post_init__(self) -> None:
        """Validate action field to prevent verbatim sentence storage."""
        if len(self.action) > MAX_ACTION_LENGTH:
            logger.warning(
                "SkillStep action exceeds %d chars (%d): '%s…'. "
                "This may indicate verbatim text instead of an abstract action.",
                MAX_ACTION_LENGTH,
                len(self.action),
                self.action[:40],
            )
            # Truncate to max length + ellipsis as a safety net.
            # The abstraction layer should catch this upstream,
            # but this prevents unbounded storage.
            self.action = self.action[:MAX_ACTION_LENGTH - 1] + "…"
```

This is a **warning + truncate** strategy, not a hard error, so existing code that hasn't been refactored yet won't crash — but the warning surfaces the problem in logs, and the truncation prevents noise from polluting the skill graph.

#### TUI Compatibility

`orka memory watch` (BrainSkillsScreen in `orka/tui/textual_screens.py`) renders `action` as plain cyan text with no length assumptions or format parsing:

```python
step_text = f"  {order}. [cyan]{action}[/cyan]{optional}"
if desc:
    step_text += f"\n     [dim]{desc}[/dim]"
```

**No TUI changes required.** Short `"verb [target]"` actions will display correctly. The `description` field (which preserves the original verbose text) renders as dim secondary text underneath, so no information is lost in the UI.

### Acceptance Criteria

- [ ] No skill procedure step longer than 60 characters
- [ ] Skills from different domains (e.g., JWT auth vs caching) stored with the **same procedure skeleton** if they share the same cognitive pattern
- [ ] `SkillStep.__post_init__` warns and truncates actions exceeding 60 chars
- [ ] Existing unit tests pass; new tests cover abstraction edge cases and SkillStep validation
- [ ] Benchmark re-run shows differentiated procedure steps, not verbatim LLM text

### Files to Change

| File | What Changes |
|------|-------------|
| `orka/brain/constants.py` | **NEW** — Shared `ACTION_VERBS` set + `ACTION_VERB_CANONICAL` map |
| `orka/agents/brain_agent.py` | Replace sentence-splitting with `_abstract_procedure()`, import from constants |
| `orka/brain/brain.py` | Add `_abstract_action()` helper using shared constants, update `_extract_procedure()` |
| `orka/brain/skill.py` | Add `__post_init__` validation: warn + truncate actions > 60 chars |
| `tests/unit/agents/test_brain_agent.py` | Test abstraction quality |
| `tests/unit/brain/test_brain.py` | Test `_abstract_action()` |
| `tests/unit/brain/test_skill.py` | Test `SkillStep` validation (truncation, warning) |
| `orka/tui/textual_screens.py` | **No changes needed** — renders action as plain text |

### Estimated Impact

Track E pairwise win rate should increase from 80% to 85%+ as skill recall becomes genuinely useful rather than noise. Track A should see the biggest improvement — cross-domain transfer only works if skills are domain-agnostic.

---

## Problem 2 — Recall Threshold Too Low

### Diagnosis

In `brain_agent.py` line 233, the recall call passes `min_score=0.0`:

```python
candidates = await brain.recall(
    context=context,
    top_k=int(payload.get("top_k", 3)),
    min_score=float(payload.get("min_score", 0.0)),  # ← No floor!
    ...
)
```

The transfer engine's own default is 0.3, but the agent overrides it to 0.0. This means every skill in the graph is a candidate, even with a combined_score of 0.05. The benchmark showed `semantic_score: 0.024` passing through.

Additionally, there's no per-component minimum. A skill can score 0.0 on semantic similarity and 0.5 on structural similarity and still pass — meaning "it looks like the same kind of task but is about something completely unrelated."

### Fix

#### A — Raise the default floor in brain_agent.py

**File:** `orka/agents/brain_agent.py`, line 233

```python
# BEFORE:
min_score=float(payload.get("min_score", 0.0)),

# AFTER:
min_score=float(payload.get("min_score", 0.5)),
```

#### B — Add per-component minimums in transfer_engine.py

**File:** `orka/brain/transfer_engine.py`, in `_score_skill()` method

Add a semantic floor check: if the semantic_score is below 0.1, the skill is off-topic regardless of structural match. Return a zeroed candidate so it gets filtered by the combined minimum.

```python
def _score_skill(self, skill, target_features, target_context):
    source_features = ContextFeatures.from_dict(skill.source_context)
    structural = target_features.similarity_to(source_features)
    semantic = self._compute_semantic_similarity(skill, target_features)
    
    # NEW: Semantic floor — if content is unrelated, don't transfer
    if semantic < 0.1 and structural < 0.6:
        return TransferCandidate(
            skill=skill,
            structural_score=structural,
            semantic_score=semantic,
            transfer_score=0.0,
            confidence_score=0.0,
            combined_score=0.0,
            adaptations={},
            reasoning="Filtered: semantic similarity too low for meaningful transfer.",
        )
    
    # ... rest unchanged
```

#### C — Make threshold configurable via YAML

Allow workflow authors to set `min_score` in the agent config:

```yaml
- id: brain_recall
  type: brain
  operation: recall
  params:
    min_score: 0.5
    top_k: 3
```

### Acceptance Criteria

- [ ] Default `min_score` is 0.5 (not 0.0)
- [ ] Skills with `semantic_score < 0.1` AND `structural_score < 0.6` never recalled
- [ ] Benchmark re-run: Track A recall rate should drop from 100% to ~40-60% (only genuinely relevant skills recalled)
- [ ] Graceful degradation: when no skill passes threshold, pipeline behaves like brainless (no crash, clean no-skill message)
- [ ] YAML-configurable threshold

### Files to Change

| File | What Changes |
|------|-------------|
| `orka/agents/brain_agent.py` | Change default min_score from 0.0 → 0.5, read from params |
| `orka/brain/transfer_engine.py` | Add semantic floor logic in `_score_skill()` |
| `tests/unit/brain/test_transfer_engine.py` | Test floor filtering |
| `tests/unit/agents/test_brain_agent.py` | Test default threshold |

### Estimated Impact

This single change should eliminate noise injection. The -0.05 reasoning_quality deficit disappears because the LLM is no longer given irrelevant prior answers. Track A's rubric delta should swing from -0.05 to positive.

---

## Problem 3 — Same LLM Judges Its Own Output

### Diagnosis

`judge_rubric_workflow.yml` uses `gpt-oss-20b` (the same local model) as the rubric evaluator. When a model evaluates its own outputs, two biases emerge:

1. **Anchoring** — The judge has the same capability ceiling as the producer. It can't detect flaws it would also make.
2. **Score compression** — All outputs "look reasonable" to a peer-level judge, compressing the range (both brain and brainless scored 7.8-7.9 overall).

The pairwise comparison is less affected because it's a relative judgment ("which is better?") rather than an absolute score.

### Fix: Decouple Judgment From Execution

The deeper problem is architectural: `run_benchmark_v2.py` bundles execution (Phases 1–2) and evaluation (Phases 3–4) into a single monolithic script. This is why Phase 3's Redis crash required a custom resume script, and why switching judges means editing the benchmark runner or building yet another one-off.

**The fix is to split the benchmark into three independent scripts:**

```
run_benchmark_v2.py      → Phase 1+2 only: run brain/brainless, write results to disk
judge_benchmark.py       → Phase 3: score results with any judge workflow (pluggable)
aggregate_benchmark.py   → Phase 4: read judge scores, compute aggregates, generate report
```

Each script works on the shared `results/` directory as its contract. They can be run independently, re-run, or swapped without touching the others.

#### A — Create `judge_benchmark.py` (standalone judge runner)

**File:** `examples/benchmark_v2/judge_benchmark.py`

```
usage: judge_benchmark.py [options]

Score existing benchmark results using a pluggable judge workflow.

options:
  --results-dir PATH        Results directory (default: ./results)
  --judge-workflow PATH     YAML workflow for rubric judging (default: judge_rubric_workflow.yml)
  --pairwise-workflow PATH  YAML workflow for pairwise judging (default: judge_pairwise_workflow.yml)
  --output-tag TAG          Subdirectory tag for results (default: "local")
                            e.g. "local" → results/judge_rubric_local/
                                 "gpt4"  → results/judge_rubric_gpt4/
  --track A|B|C|D|E         Score a single track (default: all)
  --skip-existing           Skip already-scored task IDs
  --concurrency N           Max parallel judge calls (default: 1)
  --verbose                 Print per-task scores
```

Core design:
- Reads `results/brain/*.json` and `results/brainless/*.json` from disk
- For each task, renders the rubric prompt and calls the specified judge workflow via `Orchestrator`
- Writes results to `results/judge_rubric_{tag}/brain/` and `results/judge_rubric_{tag}/brainless/`
- Pairwise results go to `results/judge_pairwise_{tag}/`
- `--output-tag` is the key: run with `--output-tag local` for local model, `--output-tag gpt4` for external, results coexist on disk
- `--skip-existing` enables resume after interruption (checks disk for existing files)
- No Redis dependency for the judge step (enforces `ORKA_FORCE_BASIC_REDIS=true` unless the workflow needs it)

This means re-scoring with an external judge is just:

```bash
# Local model (default)
python judge_benchmark.py --output-tag local

# GPT-4 as judge
python judge_benchmark.py --judge-workflow judge_rubric_gpt4.yml \
                          --pairwise-workflow judge_pairwise_gpt4.yml \
                          --output-tag gpt4

# Claude as judge
python judge_benchmark.py --judge-workflow judge_rubric_claude.yml \
                          --output-tag claude --concurrency 5
```

#### B — Create `aggregate_benchmark.py` (standalone aggregation)

**File:** `examples/benchmark_v2/aggregate_benchmark.py`

```
usage: aggregate_benchmark.py [options]

Aggregate judge scores and generate benchmark report.

options:
  --results-dir PATH     Results directory (default: ./results)
  --judge-tag TAG        Which judge results to aggregate (default: "local")
  --exclude-tracks A,C   Comma-separated tracks to exclude from overall aggregates
  --output PATH          Report output file (default: results/benchmark_v2_report_{tag}.json)
  --compare-tags t1,t2   Compare two judge tags side-by-side (e.g. "local,gpt4")
```

Core design:
- Reads from `results/judge_rubric_{tag}/` and `results/judge_pairwise_{tag}/`
- Computes per-track and overall rubric averages, pairwise win rates, deltas
- `--exclude-tracks` removes tracks from the overall aggregate (solves Problem 4 cleanly)
- `--compare-tags local,gpt4` generates a side-by-side report showing how much the judge model matters
- Outputs `benchmark_v2_report_{tag}.json`

This means Track C exclusion is just:

```bash
python aggregate_benchmark.py --exclude-tracks C --judge-tag local
```

And comparing local vs external judge is:

```bash
python aggregate_benchmark.py --compare-tags local,gpt4
```

#### C — Create judge workflow variants

The current local judge uses `openai/gpt-oss-20b` — the same model that produces the answers. The **default local judge** should use a different local model to break the self-evaluation loop. DeepSeek R1 (reasoning model, 8B, available via LM Studio) is ideal: different architecture, strong at evaluation, fits in VRAM alongside the producer model.

**File:** `examples/benchmark_v2/judge_rubric_workflow.yml` (UPDATE existing — new default local judge)

```yaml
orchestrator:
  id: bench-v2-judge-rubric
  strategy: sequential
  agents:
    - rubric_judge

agents:
  - id: rubric_judge
    type: local_llm
    prompt: |
      {{ rubric_prompt }}
    params:
      provider: lm_studio
      model_url: "http://localhost:1234"
      model: "deepseek/deepseek-r1-0528-qwen3-8b"
      temperature: 0.1
```

> **Rationale:** DeepSeek R1 is a reasoning-specialist model — it excels at structured evaluation and scoring rubrics. Using a different model family (DeepSeek vs GPT-oss) as judge breaks the anchoring bias where a model can't detect flaws it would also make. Both models run locally via LM Studio, so no API keys needed.

**File:** `examples/benchmark_v2/judge_pairwise_workflow.yml` (UPDATE existing — same model switch)

Same change: replace `model: "openai/gpt-oss-20b"` → `model: "deepseek/deepseek-r1-0528-qwen3-8b"`.

**File:** `examples/benchmark_v2/judge_rubric_gpt4.yml` (NEW — optional external judge)

```yaml
orchestrator:
  id: judge-rubric-gpt4
  strategy: sequential
  agents:
    - rubric_judge

agents:
  - id: rubric_judge
    type: openai-gpt-4
    prompt: |
      {{ rubric_prompt }}
    params:
      model: gpt-4-turbo
      temperature: 0.1
      max_tokens: 1000
```

**File:** `examples/benchmark_v2/judge_rubric_claude.yml` (NEW — optional external judge)

```yaml
orchestrator:
  id: judge-rubric-claude
  strategy: sequential
  agents:
    - rubric_judge

agents:
  - id: rubric_judge
    type: anthropic
    prompt: |
      {{ rubric_prompt }}
    params:
      model: claude-sonnet-4-20250514
      temperature: 0.1
      max_tokens: 1000
```

Similarly for pairwise variants (GPT-4, Claude).

> **Judge hierarchy:** Local DeepSeek R1 (default, free, fast) → GPT-4/Claude (optional, for validation). The `--output-tag` system lets you run all three and compare.

#### D — Refactor `run_benchmark_v2.py` to execution-only

Strip Phases 3–4 from `run_benchmark_v2.py`. It becomes:

```
usage: run_benchmark_v2.py [options] "input"

Run brain and brainless benchmark conditions.

options:
  --results-dir PATH      Results directory (default: ./results)
  --track A|B|C|D|E       Run a single track (default: all)
  --skip-brainless        Skip brainless condition
  --skip-brain            Skip brain condition (for baseline runs)
  --include-baseline      Also run single-pass baseline condition
  --verbose               Print per-task output
```

End-to-end workflow becomes three commands:

```bash
# 1. Execute (hours, LLM-heavy, can crash and resume)
python run_benchmark_v2.py --results-dir results

# 2. Judge with local DeepSeek R1 (default — different model from producer)
python judge_benchmark.py --output-tag local

# 2b. Optionally re-judge with external models for cross-validation
python judge_benchmark.py --judge-workflow judge_rubric_gpt4.yml --output-tag gpt4

# 3. Aggregate (instant, can slice and dice)
python aggregate_benchmark.py --judge-tag local --exclude-tracks C
python aggregate_benchmark.py --compare-tags local,gpt4
```

### Acceptance Criteria

- [ ] `run_benchmark_v2.py` no longer contains judge or aggregation code
- [ ] `judge_benchmark.py` works standalone against any `results/` directory
- [ ] `aggregate_benchmark.py` works standalone against any `judge_rubric_{tag}/` directory
- [ ] `--output-tag` prevents different judge runs from overwriting each other
- [ ] `--skip-existing` enables resume after crash (no more custom resume scripts)
- [ ] `--compare-tags` produces a side-by-side delta report
- [ ] `--exclude-tracks` cleanly removes tracks from aggregates
- [ ] At least two judge workflow variants (local + GPT-4) provided as examples
- [ ] All three scripts can be run independently in any order (after execution)
- [ ] Track E brain-brainless delta should be visibly larger with external judge (hypothesis)

### Files to Create/Change

| File | Purpose |
|------|---------|
| `examples/benchmark_v2/judge_benchmark.py` | **NEW** — Standalone judge runner with pluggable workflows |
| `examples/benchmark_v2/aggregate_benchmark.py` | **NEW** — Standalone aggregation and reporting |
| `examples/benchmark_v2/judge_rubric_workflow.yml` | **UPDATE** — Switch local judge from `gpt-oss-20b` to `deepseek-r1-0528-qwen3-8b` |
| `examples/benchmark_v2/judge_pairwise_workflow.yml` | **UPDATE** — Same model switch for pairwise judge |
| `examples/benchmark_v2/judge_rubric_gpt4.yml` | **NEW** — GPT-4 rubric judge workflow (optional external) |
| `examples/benchmark_v2/judge_pairwise_gpt4.yml` | **NEW** — GPT-4 pairwise judge workflow (optional external) |
| `examples/benchmark_v2/judge_rubric_claude.yml` | **NEW** — Claude rubric judge workflow (optional external) |
| `examples/benchmark_v2/run_benchmark_v2.py` | **REFACTOR** — Strip Phases 3–4, execution only |
| `examples/benchmark_v2/resume_phase3.py` | **DELETE** — No longer needed, `judge_benchmark.py --skip-existing` replaces it |

### Estimated Impact

Beyond solving the "same LLM judges itself" problem, this architectural split:
- Eliminates the class of bugs where judge failures corrupt execution state
- Enables A/B testing of judge models with zero re-execution cost
- Makes Track C exclusion a CLI flag instead of a code change
- Replaces ad-hoc resume scripts with built-in `--skip-existing`
- Allows community contributors to add judge providers (Gemini, Mistral, etc.) by adding a YAML file

---

## Problem 4 — Track C Tests Routing, Not Brain Transfer

### Diagnosis

Track C (GraphScout Brain-Assisted Routing) measures whether brain path knowledge improves routing decisions. But the underlying agent graph contains only customer support agents (`ticket_classifier`, `knowledge_base_search`, `response_drafter`, `quality_checker`, `escalation_handler`, `account_recovery`).

The tasks include enterprise-grade technical questions about Azure AD SAML 2.0, OAuth redirect vulnerabilities, TLS downgrade attacks — topics that none of these agents can answer. Both brain and brainless scored ~5/10 because:

1. GraphScout routed to `account_recovery → knowledge_base_search` (best available, still wrong)
2. The LLM couldn't produce useful answers regardless of routing
3. Brain learned "empty path" anti-patterns, not useful skills

This measures the **LLM's knowledge ceiling + routing quality**, not brain skill transfer.

### Fix: Two Options

#### Option A — Redesign Track C tasks to match available agents (Recommended)

Replace the current Track C dataset with tasks that the customer support agent graph **can** answer — routing quality differences become visible:

- Password reset flows (→ account_recovery)
- FAQ questions (→ knowledge_base_search)
- Response drafting for common issues (→ response_drafter → quality_checker)
- Escalation decisions (→ escalation_handler)

Brain's advantage: learned path skills tell it "password reset → account_recovery → quality_checker" is better than "password reset → knowledge_base_search → response_drafter."

**Files to change:**
- `examples/benchmark_v2/benchmark_v2_dataset.json` — Replace Track C tasks (IDs 101-150)
- `examples/benchmark_v2/harden_track_c.py` — Update validation

#### Option B — Report Track C separately

Keep Track C but exclude it from brain-vs-brainless comparison. Report it as a routing-quality benchmark instead. Add a note in the report:

```json
"track_c_note": "Track C measures GraphScout routing quality, not brain skill transfer. Both conditions face the same LLM knowledge ceiling on enterprise security questions. Scores are reported for completeness but excluded from brain-vs-brainless aggregate."
```

**Files to change:**
- `examples/benchmark_v2/run_benchmark_v2.py` — Exclude Track C from overall aggregation
- `examples/benchmark_v2/resume_phase3.py` — Same

### Acceptance Criteria

- [ ] Track C tasks are answerable by the available agents (Option A) OR Track C excluded from aggregates (Option B)
- [ ] Overall brain-brainless rubric delta recalculated without Track C noise
- [ ] Expected overall rubric delta without Track C: from -0.03 to +0.10–0.15

---

## Problem 5 — No Single-Pass Baseline

### Diagnosis

The current brainless condition runs: `task_reasoner → task_applier` (two LLM passes). The brain condition runs: `task_reasoner → brain_learn → brain_recall → task_applier` (two LLM passes + brain ops).

Both get two LLM passes. The benchmark measures the marginal value of brain **on top of** iterative refinement. This is a harder bar than: "does brain+one-pass beat no-brain+one-pass?"

### Fix: Add Single-Pass Control

Create `baseline_track_*.yml` workflows that run only one LLM pass:

```yaml
# baseline_track_e.yml
orchestrator:
  id: bench-v2-baseline-track-e
  strategy: sequential
  agents:
    - task_solver

agents:
  - id: task_solver
    type: local_llm
    prompt: |
      You are a senior software architect. Solve this task.
      TASK: {{ input.task | default(input) }}
      Return JSON with:
      - "response": your complete solution
      - "confidence": 0.0-1.0
      - "internal_reasoning": your approach
    params:
      provider: lm_studio
      model_url: "http://localhost:1234"
      model: "openai/gpt-oss-20b"
      temperature: 0.3
```

Then update `run_benchmark_v2.py` to support a third condition: `--include-baseline`.

### Acceptance Criteria

- [ ] Single-pass baseline workflows for tracks A, B, D, E
- [ ] Benchmark runner supports `--include-baseline` flag
- [ ] Report includes three-way comparison: baseline vs brainless vs brain
- [ ] Expected: brain >> baseline (significant delta), brain > brainless (moderate delta)

### Files to Create/Change

| File | Purpose |
|------|---------|
| `examples/benchmark_v2/baseline_track_a.yml` | Single-pass baseline for Track A |
| `examples/benchmark_v2/baseline_track_b.yml` | Single-pass baseline for Track B |
| `examples/benchmark_v2/baseline_track_d.yml` | Single-pass baseline for Track D |
| `examples/benchmark_v2/baseline_track_e.yml` | Single-pass baseline for Track E |
| `examples/benchmark_v2/run_benchmark_v2.py` | Add `--include-baseline` condition |

### Estimated Impact

This is primarily an evaluation methodology improvement. It won't change brain's actual performance but will provide a stronger narrative: "Brain with one pass outperforms no-brain with two passes" is more compelling than "Brain with two passes slightly outperforms no-brain with two passes."

---

## Implementation Order

```
Phase 1 — Decouple & Quick Wins
├── 1a. Split benchmark into 3 scripts (Problem 3)         ← ~4h, architectural fix
│   ├── judge_benchmark.py (standalone judge runner)
│   ├── aggregate_benchmark.py (standalone aggregation)
│   └── Strip Phases 3-4 from run_benchmark_v2.py
├── 1b. Create GPT-4/Claude judge workflow YAMLs            ← ~30min, YAML only
├── 1c. Exclude Track C via --exclude-tracks (Problem 4B)   ← free, built into 1a
└── 1d. Re-score existing results with external judge       ← ~1h, just run judge_benchmark.py

Phase 2 — Core Brain Fixes  
├── 2a. Raise min_score default to 0.5 (Problem 2A)       ← ~30min, one-line change
├── 2b. Add semantic floor in transfer engine (Problem 2B) ← ~1h, small change + tests
├── 2c. Abstract procedure extraction (Problem 1A)         ← ~3h, significant refactor
└── 2d. Abstract action helper in brain.py (Problem 1B)    ← ~1h, new helper + tests

Phase 3 — Benchmark Methodology Improvements
├── 3a. Single-pass baseline workflows (Problem 5)         ← ~2h, new YAML + runner update
├── 3b. Redesign Track C dataset (Problem 4A)              ← ~3h, new tasks + validation
└── 3c. Full re-run with all fixes                         ← ~8h wall clock (automated)
```

### Priority Assessment

| Fix | Impact on Results | Effort | Priority |
|-----|-------------------|--------|----------|
| Split benchmark into 3 scripts (1a) | Critical — enables all other eval fixes | 4h | **P0** |
| Raise min_score (2a) | High — eliminates noise injection | 30min | **P0** |
| Semantic floor (2b) | High — prevents off-topic recalls | 1h | **P0** |
| Abstract procedures (2c) | Critical — fixes core skill quality | 3h | **P1** |
| External judge re-score (1d) | High — reveals true deltas | 1h | **P1** |
| Exclude Track C (1c) | Medium — cleaner aggregate numbers | free | **P1** |
| Single-pass baseline (3a) | Medium — stronger narrative | 2h | **P2** |
| Redesign Track C (3b) | Medium — long-term benchmark quality | 3h | **P2** |

---

## Expected Outcome After All Fixes

| Metric | Current | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|
| Overall rubric Δ | -0.03 | +0.15–0.25 | +0.20–0.35 |
| Track A rubric Δ | +0.03 | +0.15–0.25 | +0.20–0.30 |
| Track E rubric Δ | +0.37 | +0.50–0.70 | +0.60–0.80 |
| Track E pairwise | 80% | 85%+ | 85%+ |
| Reasoning quality Δ | -0.05 | +0.05–0.10 | +0.05–0.10 |
| Track C score | ~5/10 | excluded | 7/10+ (redesigned) |

The theory is validated by Tracks D and E even now. These fixes remove the noise that's masking the signal in the other tracks.
