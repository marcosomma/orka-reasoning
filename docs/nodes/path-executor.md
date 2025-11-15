# PathExecutor Node 🚀

## Overview

The **PathExecutorNode** dynamically executes agent sequences determined at runtime. It enables the "validate-then-execute" pattern by taking validated agent paths (from validation loops, GraphScout decisions, or manual configurations) and actually executing them.

**Key Use Cases:**
- Execute validated paths from PlanValidator + GraphScout loops
- Run dynamically selected agent sequences
- Implement conditional agent execution
- Enable runtime workflow determination

**Core Benefits:**
- **Dynamic Execution**: Paths determined during workflow execution
- **Validation Integration**: Seamlessly works with validation loops
- **Result Accumulation**: Automatic context passing between agents
- **Error Resilience**: Configurable failure handling

## Configuration

```yaml
- id: path_executor
  type: path_executor
  path_source: "validated_path"          # Required: dot-notation path to agent list
  on_agent_failure: "continue"           # Optional: "continue" or "abort" (default: "continue")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path_source` | string | `"validated_path"` | Dot-notation path to agent list in `previous_outputs` |
| `on_agent_failure` | string | `"continue"` | Failure handling: `"continue"` (log and continue) or `"abort"` (stop execution) |

### Path Source Examples

The `path_source` parameter uses dot notation to navigate `previous_outputs`:

```yaml
# Simple key reference
path_source: graphscout_router

# Nested path from validation loop
path_source: validation_loop.response.result.graphscout_router

# Direct field access
path_source: graphscout_router.target

# Deep nested path
path_source: loop.response.result.plan_proposer.response.path
```

## Path Data Formats

PathExecutor can extract agent lists from various formats:

### Format 1: Direct List
```json
["agent1", "agent2", "agent3"]
```

### Format 2: GraphScout Format (with `target` field)
```json
{
  "decision": "agent",
  "target": ["agent1", "agent2", "agent3"],
  "confidence": 0.92,
  "reasoning": "..."
}
```

### Format 3: Alternative Format (with `path` field)
```json
{
  "path": ["agent1", "agent2", "agent3"],
  "reasoning": "..."
}
```

## Output Structure

PathExecutor returns:

```json
{
  "executed_path": ["agent1", "agent2", "agent3"],
  "results": {
    "agent1": { "response": "..." },
    "agent2": { "response": "..." },
    "agent3": { "response": "..." }
  },
  "status": "success",  // "success", "partial", or "error"
  "errors": []          // Present only if errors occurred
}
```

### Status Values

- **`success`**: All agents executed successfully
- **`partial`**: Some agents failed with `on_agent_failure: continue`
- **`error`**: Execution stopped due to error with `on_agent_failure: abort`

## Usage Patterns

### Pattern 1: Validate-Then-Execute

```yaml
agents:
  # Phase 1: Validation loop
  - id: validation_loop
    type: loop
    max_loops: 3
    score_threshold: 0.85
    internal_workflow:
      agents:
        - graphscout_router    # Proposes paths
        - path_validator       # Validates paths
  
  # Phase 2: Execute validated path
  - id: path_executor
    type: path_executor
    path_source: validation_loop.response.result.graphscout_router.target
    on_agent_failure: continue
  
  # Phase 3: Summarize results
  - id: summary
    type: local_llm
    prompt: |
      Validation score: {{ previous_outputs.validation_loop.final_score }}
      Executed: {{ previous_outputs.path_executor.executed_path }}
      Results: {{ previous_outputs.path_executor.results }}
```

### Pattern 2: Direct GraphScout Execution

```yaml
agents:
  # GraphScout proposes path
  - id: graphscout_router
    type: graph-scout
    # ... GraphScout configuration ...
  
  # Execute proposed path
  - id: path_executor
    type: path_executor
    path_source: graphscout_router
    on_agent_failure: abort
```

### Pattern 3: Conditional Execution

```yaml
agents:
  # LLM decides path based on input
  - id: decision_maker
    type: local_llm
    prompt: |
      Analyze input and return path:
      {{ input }}
      
      Return JSON: {"target": ["agent1", "agent2"]}
  
  # Execute decided path
  - id: path_executor
    type: path_executor
    path_source: decision_maker.target
    on_agent_failure: continue
```

## Error Handling

### Continue Mode (default)

```yaml
- id: path_executor
  type: path_executor
  path_source: some_path
  on_agent_failure: continue  # Log error and continue with next agent
```

**Behavior:**
- Failed agents get `{"error": "..."}` in results
- Execution continues with remaining agents
- Status becomes `"partial"` if any failures
- All errors collected in `errors` list

**Use when:**
- Failures are recoverable
- Partial results are valuable
- You want maximum coverage

### Abort Mode

```yaml
- id: path_executor
  type: path_executor
  path_source: some_path
  on_agent_failure: abort  # Stop on first failure
```

**Behavior:**
- Execution stops at first failure
- Only pre-failure agents in results
- Status becomes `"error"`
- Errors list contains failure description

**Use when:**
- Failures are critical
- Dependent agent chain (each needs previous success)
- Enterprise/production workflows requiring safety

## Complete Examples

### Example 1: Basic Usage

```yaml
name: "PathExecutor Basic Demo"

agents:
  - id: path_proposer
    type: local_llm
    prompt: |
      Recommend agent path for: {{ input }}
      Return JSON: {"target": ["web_search", "analyzer", "summarizer"]}
  
  - id: path_executor
    type: path_executor
    path_source: path_proposer.target
    on_agent_failure: continue
  
  # Agent definitions
  - id: web_search
    type: duckduckgo
  
  - id: analyzer
    type: local_llm
    prompt: "Analyze: {{ previous_outputs.web_search.results }}"
  
  - id: summarizer
    type: local_llm
    prompt: "Summarize: {{ previous_outputs.analyzer.response }}"
```

### Example 2: Enterprise Workflow

```yaml
name: "Enterprise Validated Execution"

agents:
  # Validation loop with strict boolean scoring
  - id: design_validation_loop
    type: loop
    max_loops: 5
    score_threshold: 0.88
    scoring:
      preset: strict
    internal_workflow:
      agents:
        - graphscout_architect
        - design_validator_strict
  
  # Execute with abort on failure (enterprise safety)
  - id: path_executor
    type: path_executor
    path_source: design_validation_loop.response.result.graphscout_architect.target
    on_agent_failure: abort
  
  # Executive summary
  - id: executive_summary
    type: local_llm
    prompt: |
      # Enterprise Execution Report
      
      Validation Score: {{ previous_outputs.design_validation_loop.final_score }}
      Execution Status: {{ previous_outputs.path_executor.status }}
      Completed Agents: {{ previous_outputs.path_executor.results | length }}
```

### Example 3: GraphScout Integration

```yaml
name: "GraphScout + PathExecutor"

agents:
  # GraphScout routes intelligently
  - id: graphscout_router
    type: graph-scout
    params:
      k_beam: 5
      max_depth: 3
      require_terminal: true
    prompt: |
      Select optimal path for: {{ input }}
      
      Available: web_search, analyzer, validator, generator
  
  # Execute GraphScout's selected path
  - id: path_executor
    type: path_executor
    path_source: graphscout_router
    on_agent_failure: continue
  
  # Quality check
  - id: quality_review
    type: local_llm
    prompt: |
      Review execution:
      Path: {{ previous_outputs.graphscout_router.target }}
      Confidence: {{ previous_outputs.graphscout_router.confidence }}
      Status: {{ previous_outputs.path_executor.status }}
```

## Advanced Topics

### Accessing Execution Results

```yaml
- id: result_analyzer
  type: local_llm
  prompt: |
    # Execution Analysis
    
    ## Path Executed
    {{ previous_outputs.path_executor.executed_path }}
    
    ## Status
    {{ previous_outputs.path_executor.status }}
    
    ## Individual Agent Results
    {% for agent_id, result in previous_outputs.path_executor.results.items() %}
    ### {{ agent_id }}
    {% if 'error' in result %}
    FAILED: {{ result.error }}
    {% else %}
    SUCCESS: {{ result.response }}
    {% endif %}
    {% endfor %}
    
    ## Errors (if any)
    {% if previous_outputs.path_executor.errors %}
    {{ previous_outputs.path_executor.errors }}
    {% endif %}
```

### Nested Path Extraction

For deeply nested validation loop outputs:

```yaml
# Validation loop structure:
# validation_loop
#   └── response
#       └── result
#           └── plan_proposer
#               └── response
#                   └── path: ["agent1", "agent2"]

- id: path_executor
  type: path_executor
  path_source: validation_loop.response.result.plan_proposer.response.path
```

### Conditional Execution Based on Validation

```yaml
agents:
  - id: validation_loop
    type: loop
    score_threshold: 0.85
    # ... validation config ...
  
  # Only execute if validated
  - id: conditional_executor
    type: router
    condition: "{{ previous_outputs.validation_loop.threshold_met }}"
    routes:
      - condition: true
        target: path_executor
      - condition: false
        target: rejection_handler
  
  - id: path_executor
    type: path_executor
    path_source: validation_loop.response.result.graphscout.target
    on_agent_failure: abort
```

## Comparison with Other Approaches

### PathExecutor vs. GraphScout Direct Execution

| Aspect | PathExecutor | GraphScout Direct |
|--------|--------------|-------------------|
| **When Routing** | After validation | Real-time |
| **Validation** | Explicit validation loop | Optional LLM evaluation |
| **Use Case** | High-stakes, validated workflows | Dynamic real-time routing |
| **Overhead** | Higher (validation first) | Lower (immediate execution) |
| **Auditability** | Full trace (validation + execution) | Execution trace only |
| **Best For** | Enterprise, critical systems | Interactive, adaptive systems |

### PathExecutor vs. Manual Sequential Agents

| Aspect | PathExecutor | Manual Sequential |
|--------|--------------|-------------------|
| **Flexibility** | Dynamic paths at runtime | Static paths at config time |
| **Validation** | Can validate before execution | No validation |
| **Configuration** | Minimal (path_source) | Explicit agent list |
| **Complexity** | Higher (indirection) | Lower (direct) |
| **Best For** | Adaptive workflows | Fixed workflows |

## Best Practices

### 1. Use Descriptive Path Sources

```yaml
# Good: Clear what is being executed
path_source: validation_loop.response.result.graphscout_router.target

# Bad: Unclear source
path_source: loop.result
```

### 2. Choose Appropriate Failure Mode

```yaml
# Use 'abort' for critical enterprise workflows
on_agent_failure: abort

# Use 'continue' for exploratory/research workflows
on_agent_failure: continue
```

### 3. Log and Monitor Execution

```yaml
- id: execution_monitor
  type: local_llm
  prompt: |
    Monitor execution:
    Status: {{ previous_outputs.path_executor.status }}
    {% if previous_outputs.path_executor.status != 'success' %}
    ALERT: Execution issues detected!
    Errors: {{ previous_outputs.path_executor.errors }}
    {% endif %}
```

### 4. Validate Paths Before Execution

```yaml
# Recommended: Validate first
agents:
  - validation_loop
  - path_executor
  - summary

# Not recommended: Execute without validation
agents:
  - path_proposer
  - path_executor
```

### 5. Handle Edge Cases

```yaml
- id: safety_wrapper
  type: local_llm
  prompt: |
    {% if 'path_executor' not in previous_outputs %}
    ERROR: PathExecutor did not run (likely path_source not found)
    {% elif previous_outputs.path_executor.status == 'error' %}
    CRITICAL: Execution failed
    Errors: {{ previous_outputs.path_executor.errors }}
    {% else %}
    SUCCESS: {{ previous_outputs.path_executor.results | length }} agents completed
    {% endif %}
```

## Troubleshooting

### Issue: "No previous_outputs available"

**Cause:** PathExecutor running before path_source agent
**Solution:** Ensure path_source agent runs first in orchestrator sequence

### Issue: "Key 'X' not found in path"

**Cause:** Invalid path_source dot notation
**Solution:** Verify path with test run, check previous_outputs structure

### Issue: "Could not extract agent list"

**Cause:** Path data not in expected format (list or dict with target/path)
**Solution:** Ensure path_source points to valid agent list format

### Issue: Agents executing even when validation fails

**Cause:** PathExecutor not checking validation threshold
**Solution:** Use Router to conditionally execute PathExecutor based on validation

### Issue: "Agent 'X' not found in orchestrator"

**Cause:** Agent in path not defined in configuration
**Solution:** Ensure all agents in potential paths are defined

## See Also

- [Graph Scout Agent](../GRAPH_SCOUT_AGENT.md) - Intelligent routing
- [Plan Validator](../agents/plan-validator.md) - Path validation with boolean scoring
- [Loop Node](loop.md) - Validation loops
- [GraphScout Execution Modes](../GRAPHSCOUT_EXECUTION_MODES.md) - Execution patterns

## Examples Repository

Full working examples:
- `examples/path_executor_demo.yml` - Basic PathExecutor usage
- `examples/graphscout_path_executor.yml` - GraphScout + PathExecutor integration
- `examples/graphscout_validate_then_execute.yml` - Complete validate-then-execute pattern
- `examples/plan_validator_complex.yml` - Enterprise workflow with PathExecutor

