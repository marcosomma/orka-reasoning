<!-- 0b340806-9831-42d0-9c0e-5aa2db28ee34 9a1b672d-58aa-4636-85e4-211e5832492a -->
# PathExecutor Complete Bug Fix Plan

## Executive Summary

Found **12 bugs** across PathExecutor implementation (from 37 example executions):

**CRITICAL** (must fix immediately):

- Bug #1: RuntimeWarning (2 examples failing completely)
- Bug #9: **Trace bloat** (loop data grows exponentially - 100KB → 1.6MB)

**HIGH** (quality/functionality issues):

- Bug #2: Agent duplication (maintenance burden)
- Bug #3: Empty results (3 examples return no data)

**MEDIUM** (user experience issues):

- Bug #4-7: YAML syntax, cost confusion, JSON parsing, empty prompts

**LOW** (monitoring):

- Bug #8: DuckDuckGo compatibility

**Target**: 37/37 success (100%), traces < 100KB each

---

## Bug Priority Matrix

| Bug # | Severity | Impact | Files | Status |

|-------|----------|--------|-------|--------|

| #9 | CRITICAL | Trace bloat exponential growth | 2 | Must fix |

| #1 | CRITICAL | 2 examples completely fail | 4 | Must fix |

| #3 | HIGH | 3 examples return empty | 4 | Must fix |

| #2 | HIGH | Duplication across examples | 3 | Must fix |

| #6 | MEDIUM | JSON parsing failures | 2 | Fix soon |

| #5 | MEDIUM | Cost calculation confusion | 2 | Fix soon |

| #4 | MEDIUM | YAML syntax error | 1 | Easy fix |

| #7 | LOW | Empty formatted_prompt | 1 | Polish |

| #8 | LOW | DuckDuckGo monitoring | 1 | Monitor |

---

## CRITICAL FIXES

### Bug #9: Trace Bloat - Recursive Nesting ⚠️ **FIX FIRST**

**Symptom**: Loop traces grow from 100KB to 1.6MB due to recursive data inclusion

**Root Cause**: `past_loops` stores FULL results causing O(2^N) growth

**Fix**: Store only summaries in `past_loops`

```python
# orka/nodes/loop_node.py
past_loop = {
    "loop_number": N,
    "score": 0.85,
    "insights": "short text",  # NOT full result
    "mistakes": "short text"
}
```

**Files**: `orka/nodes/loop_node.py`, `orka/memory/base_logger.py`

---

### Bug #1: RuntimeWarning Import Issues ⚠️ **BLOCKS 2 EXAMPLES**

**Symptom**: `graphscout_path_executor.yml` and `path_executor_demo.yml` fail with import warnings

**Fix**: Lazy load PathExecutorNode in agent_factory.py

**Files**: `orka/orchestrator/agent_factory.py`, `orka/orka_cli.py`

---

## HIGH PRIORITY FIXES

### Bug #3: Empty Results - Path Not Found

3 examples return "No data available" - path_source doesn't match structure

**Fix**: Make PathExecutor try multiple path variants

**Files**: `orka/nodes/path_executor_node.py` + 3 example files

### Bug #2: Agent Duplication

Agents defined twice (internal_workflow + top level) - 100+ lines duplicated

**Fix**: Remove duplicates, GraphScout uses main agent pool

**Files**: 3 example YAMLs

---

## MEDIUM PRIORITY FIXES

### Bug #6: JSON Parsing Failures

LLMs return Python dict syntax (`'key': True`) instead of JSON

**Fix**: Normalize responses (replace quotes, True/False/None)

**Files**: `orka/agents/llm_agents.py`

### Bug #5: Cost Calculation Confusion

Local models show $0.0007 costs (infrastructure) confusing users

**Fix**: Default to $0.00, add opt-in via environment variable

**Files**: `orka/agents/local_llm_agents.py`

### Bug #4: YAML Syntax Error

`plan_validator_complex.yml` line 409 indentation

**Fix**: One-line indent fix

---

## Implementation Order

**Phase 1** (Day 1 - Critical):

1. Bug #9: Trace bloat fix (prevents disk/memory issues)
2. Bug #1: Import warnings (unblocks 2 examples)

**Phase 2** (Day 1 - High Priority):

3. Bug #3: Path extraction (fixes 3 examples)
4. Bug #2: Remove duplication (cleanup)

**Phase 3** (Day 2 - Polish):

5. Bugs #4-7: User experience improvements

---

## Files to Modify (16 total)

**Core (9 files)**:

- `orka/nodes/loop_node.py` - **CRITICAL** trace bloat
- `orka/memory/base_logger.py` - Enable deduplication
- `orka/nodes/path_executor_node.py` - Robust path extraction
- `orka/orchestrator/agent_factory.py` - Fix imports
- `orka/orka_cli.py` - Import order
- `orka/agents/llm_agents.py` - JSON normalization
- `orka/agents/local_llm_agents.py` - Cost defaults
- `orka/orchestrator/simplified_prompt_rendering.py` - formatted_prompt
- `orka/nodes/__init__.py` - Verify exports

**Examples (7 files)**:

- `examples/graphscout_path_executor.yml` - Duplicates, imports, paths
- `examples/path_executor_demo.yml` - Import fix
- `examples/graph_scout_validated_loop.yml` - Path fix, duplicates
- `examples/graph_scout_with_plan_validator_loop.yml` - Path fix, duplicates
- `examples/plan_validator_simple.yml` - Path fix
- `examples/plan_validator_complex.yml` - YAML indent + duplicates
- `examples/plan_validator_boolean_scoring.yml` - Path verification

---

## Success Metrics

- ✅ 37/37 examples pass (100% success)
- ✅ Trace files < 100KB each (vs 1+ MB currently)
- ✅ No RuntimeWarnings
- ✅ No "No data available" messages
- ✅ No code duplication
- ✅ Clear cost reporting
- ✅ Valid JSON parsing (>90% success)

---

## Testing Strategy

**Per-Bug Testing**: Run affected examples, verify fix, check no regression

**Integration**: Run all 37 examples after each phase

**Validation Checklist**:

- [ ] Trace bloat fixed (loop traces < 100KB)
- [ ] Import warnings resolved
- [ ] All path_source extractions work
- [ ] No agent duplication
- [ ] JSON parsing > 90% success
- [ ] Cost defaultsto $0.00 for local models
- [ ] All YAML files valid