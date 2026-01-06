# Execution Invariants Validation Guide

## Overview

The Execution Invariants Validator provides deterministic checks for orchestrator execution correctness. These are **execution facts**, not semantic judgments—when invariants fail, the system is objectively broken regardless of output quality.

This is the foundation for reliable runtime health checks and canary integration tests.

## Core Concept: Facts vs. Interpretations

**Before invariants**:
- LLM discovers violations by examining outputs
- LLM judges whether violations matter
- Correlated failure: degraded runtime → degraded evaluator

**With invariants**:
- Validator computes violations deterministically
- LLM explains violations from hard facts
- Decoupled: invariant checks work even if LLM fails

## Validated Invariants

### 1. Fork/Join Integrity

**What it checks**:
- Every ForkNode has a corresponding JoinNode
- Join received results from all forked branches
- No branch was silently dropped

**When it fails**:
```python
{
  "fork_join_integrity": {
    "status": "FAIL",
    "violations": [
      "Fork 'parallel_paths' has no matching join node",
      "Fork 'data_pipeline' missing results from branches: ['branch_b', 'branch_c']"
    ]
  }
}
```

**Why it matters**: Missing joins or incomplete branches mean data loss. This is never acceptable, regardless of whether final output looks good.

### 2. Routing Validity

**What it checks**:
- Router target nodes exist in graph
- Target nodes are reachable from router position
- No dangling or circular router references

**When it fails**:
```python
{
  "routing_integrity": {
    "status": "FAIL",
    "violations": [
      "Router 'content_router' selected non-existent target 'review_agent'",
      "Router 'safety_gate' selected target 'processor' with no direct edge"
    ]
  }
}
```

**Why it matters**: Invalid routing means workflow execution path is broken. System will hang or produce nonsense.

### 3. Cycle Detection

**What it checks**:
- No node appears multiple times in execution path
- Exception: nodes explicitly marked `reentrant` (e.g., loop internals)
- Cycles are not fabricated to satisfy terminal requirements

**When it fails**:
```python
{
  "cycle_detection": {
    "status": "FAIL",
    "cycles_found": [
      ["router", "processor", "validator", "router"],
      ["analyzer", "feedback", "analyzer"]
    ],
    "violations": [
      "Unexpected cycle: node 'router' appears 3 times",
      "Unexpected cycle: node 'analyzer' appears 2 times"
    ]
  }
}
```

**Why it matters**: Unexpected cycles indicate wrong routing, infinite loops, or GraphScout path fabrication. These are execution bugs, not feature behavior.

### 4. Tool Call Integrity

**What it checks**:
- Tool call errors are propagated, not ignored
- Failed tool calls result in appropriate error handling
- No execution continues after critical tool failures

**When it fails**:
```python
{
  "tool_integrity": {
    "status": "FAIL",
    "violations": [
      "Tool error in node 'search_agent' was swallowed, execution continued",
      "Tool call failed in 'validation_step' but no error handling occurred"
    ]
  }
}
```

**Why it matters**: Swallowed tool errors lead to incomplete data and wrong decisions downstream. System appears to work but produces garbage.

### 5. Schema Compliance

**What it checks**:
- Agent outputs match their declared `structured_output` schema
- Required fields are present
- Type constraints are satisfied
- No schema/prompt mismatches (like expecting object but schema says string)

**When it fails**:
```python
{
  "schema_compliance": {
    "status": "FAIL",
    "violations": [
      "Node 'final_assessment' produced output violating declared schema",
      "Node 'data_extractor' missing required field 'confidence'"
    ]
  }
}
```

**Why it matters**: Schema violations mean format contracts are broken. Downstream agents can't parse input, causing cascading failures.

### 6. Depth Constraints

**What it checks**:
- Path depth does not exceed configured `max_depth`
- GraphScout candidate paths respect depth limits
- Depth calculation is consistent with configuration

**When it fails**:
```python
{
  "depth_compliance": {
    "status": "FAIL",
    "violations": [
      "Path depth 5 exceeds max_depth 3",
      "GraphScout candidate depth 7 exceeds max_depth 3"
    ]
  }
}
```

**Why it matters**: Depth violations indicate routing regressions or constraint enforcement failures. System ignores configured limits.

## Usage Patterns

### Pattern 1: Self-Assessment Workflow (Runtime Health Check)

Use invariants as deterministic gates before LLM evaluation:

```yaml
agents:
  # 1. Run your test workflow
  - id: test_execution
    type: ...  # Your workflow under test

  # 2. Collect deterministic invariants
  - id: invariant_collector
    type: local_llm  # Or custom Python agent
    prompt: |
      Analyze execution artifacts and compute hard invariants:
      {{ execution_trace }}
      
      Return JSON with deterministic facts:
      {
        "fork_join_integrity": {"status": "PASS/FAIL", "violations": [...]},
        "routing_integrity": {"status": "PASS/FAIL", "violations": [...]},
        "cycle_detection": {"status": "PASS/FAIL", "cycles_found": [...], "violations": [...]},
        "tool_integrity": {"status": "PASS/FAIL", "violations": [...]},
        "schema_compliance": {"status": "PASS/FAIL", "violations": [...]},
        "depth_compliance": {"status": "PASS/FAIL", "violations": [...]},
        "critical_failures_detected": boolean
      }
    temperature: 0.0  # Deterministic

  # 3. LLM interprets facts (does NOT discover them)
  - id: diagnostic_assessment
    type: local_llm
    prompt: |
      You are a diagnostic agent. Your job is INTERPRETATION, not discovery.
      
      HARD FACTS (deterministically validated):
      {{ get_agent_response('invariant_collector') }}
      
      CRITICAL RULE: If critical_failures_detected = true, you MUST
      set overall_health = "Poor" regardless of output quality.
      
      Explain each violation, cluster symptoms, suggest fixes.
    temperature: 0.0  # Greedy evaluation

  # 4. Fail hard on critical violations
  - id: health_gate
    type: local_llm
    prompt: |
      Invariants: {{ get_agent_response('invariant_collector') }}
      Assessment: {{ get_agent_response('diagnostic_assessment') }}
      
      Rules:
      1. If assessment invalid JSON: FAIL ("evaluator_invalid_output")
      2. If invariants.critical_failures_detected: FAIL ("runtime_degraded")
      3. If assessment.overall_health = "Poor": FAIL ("poor_health_rating")
      4. Otherwise: PASS
      
      Return: {"status": "PASS/FAIL", "reason": "...", "exit_code": 0/1}
```

**Key design**: Invariants computed BEFORE LLM sees them. LLM explains, not discovers.

### Pattern 2: CI/CD Integration

Use as automated gate after changes:

```bash
#!/bin/bash
# Run self-assessment workflow
orka run examples/self_assessment/system_self_assessment.yml "test input"

# Extract exit code from health_gate agent
EXIT_CODE=$(jq -r '.agents.health_gate.exit_code' < orka_output.json)

# Fail CI if health check failed
if [ "$EXIT_CODE" != "0" ]; then
  echo "Runtime health check FAILED"
  jq '.agents.invariant_collector' < orka_output.json
  exit 1
fi

echo "Runtime health check PASSED"
```

### Pattern 3: Production Monitoring

Inject invariant checks into main orchestrator execution:

```python
from orka.orchestrator.execution_invariants import ExecutionInvariantsValidator

# After orchestrator.run()
validator = ExecutionInvariantsValidator({
    "max_depth": config.get("max_depth"),
    "allow_reentrant_nodes": config.get("reentrant_nodes", [])
})

execution_data = {
    "nodes_executed": orchestrator.execution_history,
    "fork_groups": orchestrator.fork_group_manager.get_state(),
    "router_decisions": orchestrator.router_log,
    "tool_calls": orchestrator.tool_call_log,
    "structured_outputs": orchestrator.schema_validation_log,
    "graph_structure": orchestrator.graph
}

invariants = validator.validate(execution_data)

if invariants.has_critical_failures:
    logger.error("Execution invariant violations detected")
    for violation in invariants.all_violations:
        logger.error(f"[{violation.category}] {violation.message}")
    
    # Telemetry / alerting
    metrics.increment("orka.invariant_violations", tags={
        "categories": [v.category for v in invariants.all_violations]
    })
```

## Configuration

`ExecutionInvariantsValidator` accepts optional config:

```python
config = {
    # Nodes allowed to appear multiple times (e.g., loop internals)
    "allow_reentrant_nodes": ["loop_iteration", "retry_handler"],
    
    # Maximum allowed path depth (None = no limit)
    "max_depth": 5,
    
    # Treat tool warnings as errors
    "strict_tool_errors": False
}

validator = ExecutionInvariantsValidator(config)
```

## Best Practices

### 1. Separate Worker and Judge Models

**Problem**: Same model for system under test and evaluator → correlated failure.

**Solution**:
```yaml
# Worker agents (data processing)
- id: processor
  model: openai/gpt-oss-20b
  temperature: 0.5

# Judge agents (invariant collection, assessment)
- id: invariant_collector
  model: qwen2.5:14b  # Different model family
  temperature: 0.0    # Or at least greedy decoding

- id: diagnostic_assessment
  model: qwen2.5:14b
  temperature: 0.0
```

### 2. Fix Harness Before Trusting It

**Problem**: Schema says `response: string` but prompt demands JSON object → validation failure.

**Solution**: Match schema to actual expected output:
```yaml
params:
  structured_output:
    schema:
      required: [summary, scores, recommendations, health_rating]
      types:
        summary: string
        scores: object
        recommendations: array
        health_rating: string
```

### 3. Fail Hard on Evaluator Errors

**Problem**: Evaluation JSON parse failure logged as warning, test continues.

**Solution**: Add health gate that fails on invalid evaluator output:
```yaml
- id: health_gate
  prompt: |
    If assessment is invalid JSON: FAIL with "evaluator_invalid_output"
    If invariants.critical_failures_detected: FAIL with "runtime_degraded"
    Otherwise: PASS
```

### 4. Deterministic Invariants Before LLM

**Problem**: LLM discovers and judges violations → unreliable.

**Solution**: Compute invariants deterministically, inject as facts:
```yaml
- id: invariant_collector
  temperature: 0.0
  prompt: "Return deterministic facts: fork_join_integrity, routing_integrity, ..."

- id: assessment
  prompt: |
    HARD FACTS (do not discover, only explain):
    {{ get_agent_response('invariant_collector') }}
```

### 5. Use in Regression Detection

Invariants catch regressions that LLMs miss:

- **Wrong routing**: Router chooses non-existent target
- **Missing joins**: Fork has no corresponding join
- **Swallowed errors**: Tool failure ignored, execution continues
- **Schema drift**: Output format changes break contracts
- **Cycles**: Routing fabricates paths with repeated nodes

## Comparison: Before vs. After

### Before Invariants

```
[Test Run]
├─ Fork paths execute
├─ Join aggregates (1 branch missing)
├─ Router chooses target (doesn't exist)
├─ Tool call fails (error swallowed)
├─ LLM assessment: "System performed well, no issues detected" ✓
└─ Health check: PASS
```

**Result**: False green. Logs show failures, test passes.

### After Invariants

```
[Test Run]
├─ Fork paths execute
├─ Join aggregates (1 branch missing)
├─ Router chooses target (doesn't exist)
├─ Tool call fails (error swallowed)
├─ Invariant collector:
│  ├─ fork_join_integrity: FAIL (branch missing)
│  ├─ routing_integrity: FAIL (target doesn't exist)
│  ├─ tool_integrity: FAIL (error swallowed)
│  └─ critical_failures_detected: true
├─ LLM assessment: "Multiple critical failures, system degraded"
└─ Health gate: FAIL (exit_code=1, reason="runtime_degraded")
```

**Result**: Honest failure. Test fails, violations documented.

## Integration with Self-Assessment Workflow

See `examples/self_assessment/system_self_assessment.yml` for full example.

**Key agents**:
1. `invariant_collector`: Computes deterministic facts
2. `final_assessment`: LLM explains facts, does NOT discover them
3. `health_check_gate`: Fails hard on critical violations or evaluator errors

**Execution flow**:
```
test_workflow → invariant_collector → final_assessment → health_check_gate
                     ↓ (facts)              ↓ (explanation)       ↓ (gate)
                  PASS/FAIL             diagnostic text       PASS/FAIL exit code
```

## Limitations and Future Work

**Current limitations**:
- Invariant collection placeholder (LLM simulates deterministic check)
- No automatic integration into main orchestrator
- No telemetry/metrics for production use

**Planned improvements**:
- Native Python agent for invariant_collector (no LLM)
- Automatic instrumentation in execution engine
- Prometheus metrics for invariant violations
- GraphScout-specific checks (budget discrimination, path validity)
- Memory operation consistency checks

## References

- Source: `orka/orchestrator/execution_invariants.py`
- Tests: `tests/unit/orchestrator/test_execution_invariants.py`
- Example: `examples/self_assessment/system_self_assessment.yml`
- Changelog: `changelog/v0.9.14_execution_invariants_validation.md`

## Support

For questions or issues:
- GitHub: https://github.com/marcosomma/orka-reasoning
- Discord: [OrKa Community]
- Email: [Support Contact]
