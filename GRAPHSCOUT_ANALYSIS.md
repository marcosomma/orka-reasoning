# GraphScout Validated Loop - Analysis Report
**Date:** November 13, 2025  
**Workflow:** `examples/graph_scout_validated_loop.yml`  
**Query:** "Is this workflow actually working?"

## Executive Summary

**Status:** ❌ NOT WORKING AS EXPECTED

The Graph Scout validated loop is **not executing the expected flow**. All 5 loops complete with scores near zero (0.0-0.1321) and the workflow never executes any agent paths. The path_executor fails with error: `"GraphScout decision 'shortlist' cannot be executed automatically."`

---

## Expected Flow vs Actual Flow

### ✅ Expected Flow
```
1. GraphScout analyzes query and returns BEST PATH (commit_path decision)
   ├─> Should return: ["search_agent", "response_builder"] or similar
   └─> Decision type: "commit_path" or "commit_next"

2. PathExecutor EXECUTES the validated path
   ├─> Runs each agent in sequence
   ├─> Collects results from execution
   └─> Returns execution results

3. PathValidator VALIDATES the execution results
   ├─> Evaluates if the EXECUTED path produced good results
   ├─> Scores based on boolean criteria
   └─> Returns validation_score

4. Loop Decision:
   ├─> IF score >= 0.5 threshold: ✅ DONE (execute path_executor at top level)
   └─> IF score < 0.5: 🔁 CONTINUE (GraphScout gets feedback, tries again)
```

### ❌ Actual Flow (What's Happening)
```
1. GraphScout returns SHORTLIST (multiple candidates, no commitment)
   ├─> Returns: decision="shortlist", target=[list of 5 candidates]
   └─> Does NOT commit to a specific path

2. PathExecutor FAILS to execute
   ├─> Sees decision type "shortlist"
   ├─> Cannot execute a shortlist automatically
   └─> Returns: error="GraphScout decision 'shortlist' cannot be executed automatically"

3. PathValidator validates the SHORTLIST (not execution results!)
   ├─> Sees a list of candidates (not an executed path)
   ├─> Evaluates: "This is not a complete workflow"
   └─> Returns: validation_score=0.0 (all 15 criteria fail)

4. Loop continues with score=0.0
   ├─> Never reaches 0.5 threshold
   ├─> Repeats 5 times with same problem
   └─> Max loops reached, workflow ends with threshold_met=false
```

---

## Root Causes

### 1. ❌ GraphScout Returns "shortlist" Instead of "commit_path"

**File:** `orka/orchestrator/decision_engine.py`

**Problem:** The decision engine returns "shortlist" when the score margin between top candidates is < commit_margin (0.1 by default).

**Code Flow:**
```python
# Line 63-74: Try to find terminal paths first
if self.require_terminal:
    terminal_paths = self._find_terminal_paths(scored_candidates, context)
    if terminal_paths:
        # This SHOULD happen but doesn't
        return self._create_decision("commit_path", ...)

# Line 89: Multiple candidates case
score_margin = top_score - second_score

# Line 97-100: High confidence path
if score_margin >= dynamic_margin:
    return await self._handle_high_confidence_decision(...)  # commit_path

# Line 102-105: Low confidence - SHORTLIST
return await self._handle_low_confidence_decision(...)  # shortlist ❌
```

**Why it fails:**
1. **Terminal path detection is not finding response_builder paths**
   - Config has `require_terminal: true` in the YAML
   - Decision engine looks for paths ending with response_builder
   - But `_is_response_builder()` check is failing
   - Falls back to margin-based decision
   
2. **Score margins are too small**
   - All candidates have very similar scores (0.608-0.612)
   - Margin between top two is ~0.001
   - This is < commit_margin (0.1)
   - Result: "shortlist" decision

**Evidence from logs:**
```
'reasoning': 'Close competition with margin 0.001 - returning top 5 options'
'decision': 'shortlist'
'candidates_evaluated': 6
'top_score': 0.61145
```

### 2. ❌ PathExecutor Cannot Execute Shortlists

**File:** `orka/nodes/path_executor_node.py`

**Problem:** PathExecutor explicitly rejects "shortlist" decisions.

**Code:** Lines 314-326
```python
if decision_type and decision_type not in {"commit_next", "commit_path"}:
    logger.error(
        f"PathExecutor '{self.node_id}': Decision '{decision_type}' is not executable "
        f"for path_source '{path_variant}'."
    )
    return [], (
        f"GraphScout decision '{decision_type}' cannot be executed automatically. "
        "Awaiting validated path."
    )
```

**Why it fails:**
- PathExecutor only accepts `commit_next` or `commit_path` decisions
- When it receives `shortlist`, it immediately returns error
- No fallback to "pick best from shortlist"
- Workflow breaks here

### 3. ❌ Path Validator Validates Wrong Thing

**File:** `examples/graph_scout_validated_loop.yml`

**Problem:** The orchestrator sequence validates the GraphScout DECISION, not the EXECUTION RESULTS.

**Current Sequence (internal_workflow):**
```yaml
agents: [path_proposer, path_validator_moderate]
```

**What happens:**
1. `path_proposer` (GraphScout) returns: `{decision: "shortlist", target: [...]}`
2. `path_validator_moderate` receives GraphScout's shortlist
3. Validator sees: "Here's a list of 5 candidate nodes"
4. Validator evaluates: ❌ "This is not a complete workflow"
5. Result: All 15 boolean criteria fail → score = 0.0

**Evidence from logs:**
```json
{
  "validation_score": 0.0,
  "overall_assessment": "REJECTED",
  "failed_criteria": [
    "completeness.has_all_required_steps",
    "completeness.addresses_all_query_aspects",
    ... ALL 15 criteria ...
  ],
  "rationale": "The proposed path lists several generic agents that do not directly 
                address the user's question... lacks required steps, fails to cover 
                the query, does not provide fallbacks..."
}
```

### 4. ❌ Loop Never Makes Progress

**Problem:** Because PathExecutor never executes anything, the loop repeats the same pattern 5 times.

**Loop Results:**
```
Loop 1: score=0.1132 (PathValidator rejects shortlist)
Loop 2: score=0.0    (PathValidator rejects shortlist)
Loop 3: score=0.1321 (PathValidator rejects shortlist)
Loop 4: score=0.0    (PathValidator rejects shortlist)
Loop 5: score=0.0    (PathValidator rejects shortlist)
Final: threshold_met=false, loops_completed=5
```

**Why no improvement:**
- GraphScout receives "past_loops" feedback
- But the feedback is about validator rejecting a shortlist
- GraphScout doesn't understand it should commit to a path
- It keeps returning shortlist with similar scores
- No learning or adaptation occurs

---

## Detailed Issues

### Issue A: Response Builder Detection Fails

**File:** `orka/orchestrator/decision_engine.py:196-242`

The `_is_response_builder()` method checks if a node can emit final responses:

```python
def _is_response_builder(self, node_id: str, context: Dict[str, Any]) -> bool:
    # Check 1: Capabilities (most reliable)
    if hasattr(node_obj, "capabilities"):
        if "answer_emit" in capabilities or "response_generation" in capabilities:
            return True  # ✅
    
    # Check 2: Name patterns
    response_builder_patterns = [
        "response_builder", "answer_builder", "final_response",
        "llm_response", "openai_response"
    ]
    if pattern in node_id_lower:
        return True  # ✅
```

**Why it fails:**
1. The workflow has `response_builder` agent defined
2. But GraphScout might not be seeing it in `graph_state.nodes`
3. Or the capabilities are not properly set
4. Terminal path detection fails → falls back to margin-based decision

### Issue B: All Candidates Have Similar Scores

**Evidence:**
```
'memory_reader':  score=0.61145
'memory_writer':  score=0.61095  (difference: 0.0005)
'search_agent':   score=0.6084   (difference: 0.0006)
'analysis_agent': score=0.5922   (difference: 0.0162)
```

**Why this happens:**
- All agents are generic utilities (memory, search, analysis)
- None directly answers "Is this workflow working?"
- LLM evaluation can't distinguish which is better
- All get similar low scores
- Margin is < commit_margin → shortlist

### Issue C: Top-Level path_executor Never Runs

**From YAML:**
```yaml
orchestrator:
  agents:
    - path_discovery_loop      # ✅ Runs (loops 5 times)
    - path_executor            # ❌ Never runs (no valid path)
    - final_execution          # ✅ Runs (reports failure)
```

**Why path_executor never executes:**
1. It expects: `path_discovery_loop.response.result.path_proposer.target`
2. But path_proposer returns: `{decision: "shortlist", target: [candidates]}`
3. path_executor's `_extract_decision()` rejects shortlist
4. Returns error instead of results
5. Top-level path_executor configuration:
   ```yaml
   path_source: path_discovery_loop.response.result.path_proposer.target
   ```
   This expects a LIST of agent IDs to execute, but gets a shortlist decision structure

---

## Solution Plan

### Fix 1: Make GraphScout Commit to Best Path (Even with Low Margin)

**Options:**

**A. Lower commit_margin in YAML:**
```yaml
params:
  commit_margin: 0.05  # From 0.1 → 0.05 (more aggressive)
```

**B. Add fallback in decision_engine.py:**
```python
# If margin is low but we have a clear top scorer, commit anyway
if score_margin < dynamic_margin:
    if top_score >= 0.6:  # Absolute threshold
        # Commit to best option even with low margin
        return await self._handle_high_confidence_decision(top_candidate, ...)
```

**C. Force commit if require_terminal:**
```python
if self.require_terminal:
    terminal_paths = self._find_terminal_paths(scored_candidates, context)
    if not terminal_paths and scored_candidates:
        # No terminal found, but we need a decision
        # Pick best candidate and create a commit_next decision
        top = scored_candidates[0]
        return self._create_decision("commit_next", top["node_id"], ...)
```

### Fix 2: PathExecutor Should Handle Shortlists

**File:** `orka/nodes/path_executor_node.py`

**Change:** Instead of rejecting shortlist, pick the best candidate:

```python
def _extract_decision(self, decision_container, previous_outputs, resolved_obj):
    decision_type = ...  # Extract decision
    
    if decision_type == "shortlist":
        # Pick best candidate from shortlist
        if isinstance(resolved_obj, list) and resolved_obj:
            best_candidate = resolved_obj[0]  # Already sorted by score
            agent_path = self._parse_agent_list([best_candidate])
            logger.info(f"PathExecutor: Selected best from shortlist: {agent_path}")
            return agent_path, None
    
    if decision_type and decision_type not in {"commit_next", "commit_path", "shortlist"}:
        # Reject other decision types
        return [], "Cannot execute decision type: " + decision_type
```

### Fix 3: Fix the Workflow Structure

**Current problem:** path_validator validates GraphScout's decision, not execution results.

**Option A: Change internal_workflow order:**
```yaml
internal_workflow:
  agents:
    - path_proposer           # GraphScout
    # Remove path_validator from here!
    # It should validate AFTER execution, not before
```

**Option B: Add intermediate execution in loop:**
```yaml
internal_workflow:
  agents:
    - path_proposer           # GraphScout decides path
    - path_executor_internal  # Execute the path
    - path_validator          # Validate execution results
```

But this creates circular dependency (path_executor inside loop that uses path_executor).

**Option C: Simplify to GraphScout only in loop:**
```yaml
internal_workflow:
  agents:
    - path_proposer           # Just GraphScout

# Then at top level:
orchestrator:
  agents:
    - path_discovery_loop     # Gets best path from GraphScout
    - path_validator          # Validate the proposed path
    - path_executor           # Execute if validation passes
```

### Fix 4: Improve Response Builder Detection

**File:** `orka/orchestrator/decision_engine.py`

**Add better detection:**
```python
def _is_response_builder(self, node_id: str, context: Dict[str, Any]) -> bool:
    # Existing checks...
    
    # NEW: Check orchestrator's agent configs directly
    orchestrator = context.get("orchestrator")
    if orchestrator and hasattr(orchestrator, "agent_cfgs"):
        for agent_cfg in orchestrator.agent_cfgs:
            if agent_cfg.get("id") == node_id:
                # Check type
                agent_type = agent_cfg.get("type", "").lower()
                if "local_llm" in agent_type or "openai" in agent_type:
                    # Check capabilities
                    caps = agent_cfg.get("capabilities", [])
                    if "answer_emit" in caps or "response_generation" in caps:
                        return True
                    # Check if it has answer_emit patterns in prompt
                    prompt = agent_cfg.get("prompt", "")
                    if "provide comprehensive response" in prompt.lower():
                        return True
    
    return False  # Existing checks...
```

---

## Recommended Fix Strategy

### Phase 1: Quick Fix (Minimal Changes)

**Change 1:** Lower commit_margin in YAML:
```yaml
path_proposer:
  params:
    commit_margin: 0.05  # More aggressive commitment
```

**Change 2:** Make PathExecutor handle shortlist:
```python
# In path_executor_node.py, _extract_decision()
if decision_type == "shortlist":
    # Pick best from shortlist
    best = resolved_obj[0] if isinstance(resolved_obj, list) else resolved_obj
    return self._parse_agent_list([best]), None
```

### Phase 2: Proper Fix (Structural)

**Change 1:** Remove path_validator from internal loop:
```yaml
internal_workflow:
  agents:
    - path_proposer  # Just GraphScout
```

**Change 2:** Validate at top level AFTER seeing GraphScout's choice:
```yaml
orchestrator:
  agents:
    - path_discovery_loop         # Get best path
    - path_preview_validator      # NEW: Validate proposed path structure
    - path_executor               # Execute if valid
    - result_validator            # NEW: Validate execution results
```

**Change 3:** Fix decision engine to always commit when require_terminal=true:
```python
if self.require_terminal:
    # Always return a commit decision, never shortlist
    if terminal_paths:
        return commit_path
    else:
        # Pick best single agent
        return commit_next
```

### Phase 3: Better Path Scoring

**Problem:** All agents score similarly because none directly answer the query.

**Solution:** Improve LLM evaluation prompt to better understand the workflow:
- The query is "Is this workflow working?"
- This is a META query about the workflow itself
- Best answer comes from analyzing past_loops and execution history
- The `analysis_agent` with past_loops context is the right choice
- GraphScout should score this higher

---

## Summary

**What's broken:**
1. ✅ GraphScout returns "shortlist" (indecisive)
2. ✅ PathExecutor rejects shortlist (can't execute)
3. ✅ PathValidator validates the shortlist instead of execution results
4. ✅ Loop repeats without progress (no learning)

**Quick fix:**
- Lower commit_margin → force GraphScout to commit
- Make PathExecutor accept shortlist → pick best candidate

**Proper fix:**
- Restructure workflow: GraphScout in loop (no validator)
- Validate at top level AFTER GraphScout chooses
- Improve response builder detection
- Better LLM evaluation for meta-queries

**Test after fixes:**
```bash
orka run .\examples\graph_scout_validated_loop.yml "Is this workflow actually working?"
```

Expected result:
- GraphScout commits to a path (commit_next or commit_path)
- PathExecutor executes the path
- Agents run and return results
- PathValidator validates execution results
- Score > 0.5 threshold
- Workflow completes successfully


