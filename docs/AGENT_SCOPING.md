# Agent Scoping in OrKa

## Critical Rule: Top-Level vs Internal Workflow Agents

### Agent Visibility Rules

1. **Top-Level Agents** (defined in main `agents` list):
   - Visible to GraphScout for path discovery
   - Accessible to PathExecutor for execution
   - Available in orchestrator's global agent registry
   - Can be referenced by any agent in the workflow

2. **Internal Workflow Agents** (inside loop/fork `internal_workflow`):
   - Scoped ONLY to that workflow
   - NOT visible to GraphScout outside that workflow
   - NOT accessible to PathExecutor outside that workflow
   - Only accessible within the same internal workflow context

### Correct Pattern for Validated Execution

```yaml
agents:
  - id: validation_loop
    type: loop
    internal_workflow:
      agents:
        - id: path_proposer      # Proposer
        - id: path_validator     # Validator
        # DO NOT define execution agents here!
  
  # Execution agents at TOP LEVEL
  - id: search_agent           # ✓ Visible to GraphScout & PathExecutor
  - id: analysis_agent         # ✓ Visible to GraphScout & PathExecutor
  
  - id: path_executor
    type: path_executor
    path_source: validation_loop.response.result.path_proposer.target
```

### Common Mistake

```yaml
# ❌ WRONG - will cause "Agent not found" errors
agents:
  - id: validation_loop
    internal_workflow:
      agents:
        - id: path_proposer
        - id: path_validator
        - id: search_agent      # ✗ NOT visible to top-level path_executor!
  
  - id: path_executor           # Will fail to find search_agent
```

## Why This Matters

### GraphScout Agent Discovery

GraphScout discovers agents by:
1. Getting the orchestrator's global agent registry (`orchestrator.agents`)
2. Filtering agents based on capabilities and type
3. Building candidate paths from discovered agents

**Problem**: If execution agents are inside `internal_workflow`, they don't exist in the global registry when GraphScout runs outside that workflow.

### PathExecutor Agent Execution

PathExecutor executes agents by:
1. Extracting agent IDs from the validated path
2. Looking up each agent in `orchestrator.agents`
3. Executing each agent in sequence

**Problem**: If agents were defined inside a loop's `internal_workflow`, PathExecutor at the top level cannot find them.

## Best Practices

### 1. Separate Validation from Execution Agents

```yaml
agents:
  - id: validation_loop
    type: loop
    internal_workflow:
      agents:
        # ONLY validation workflow agents here
        - id: path_proposer      # Proposes paths
        - id: path_validator     # Validates paths
  
  # Execution agents at top level
  - id: search_agent
  - id: analysis_agent
  - id: memory_reader
  - id: memory_writer
  - id: response_builder
  
  # PathExecutor can now access all execution agents
  - id: path_executor
    type: path_executor
```

### 2. Keep Orchestrator Sequence Clean

Don't add execution agents to the main orchestrator sequence if they're meant to be discovered/executed dynamically:

```yaml
orchestrator:
  id: validated-execution
  strategy: sequential
  agents:
    - validation_loop         # ✓ In sequence
    - path_executor          # ✓ In sequence
    - final_report           # ✓ In sequence
    # DON'T add search_agent, analysis_agent here!
    # They should be in the agents list but NOT in the execution sequence
```

### 3. Document Agent Purpose

Add comments to clarify agent scoping:

```yaml
agents:
  # ===== VALIDATION LOOP =====
  - id: validation_loop
    type: loop
    # ...
  
  # ===== EXECUTION AGENTS (Top Level) =====
  # These agents are available for GraphScout to discover
  # and PathExecutor to execute. They are NOT in the
  # orchestrator sequence, so they won't auto-execute.
  
  - id: search_agent
    type: duckduckgo
    capabilities: [data_retrieval, web_search]
  
  - id: analysis_agent
    type: local_llm
    capabilities: [reasoning, analysis]
```

## Troubleshooting

### Error: "Agent 'X' not found in orchestrator"

**Cause**: Agent is defined inside a loop's `internal_workflow` but PathExecutor is trying to execute it from top-level.

**Solution**: Move the agent definition to the top-level `agents` list.

### Error: GraphScout returns empty shortlist

**Cause**: No agents are visible to GraphScout because they're all scoped inside internal workflows.

**Solution**: Define execution agents at top-level so GraphScout can discover them.

### Agents execute twice

**Cause**: Execution agents are both in the orchestrator sequence AND referenced by PathExecutor.

**Solution**: Remove execution agents from the orchestrator's `agents` list in the main orchestrator configuration. They should be defined in the global `agents` list but not in the execution sequence.

## Examples

See these working examples:
- `examples/graph_scout_validated_loop.yml` - Complete validated execution pattern
- `examples/graphscout_path_executor.yml` - PathExecutor with proper agent scoping
- `examples/graphscout_validate_then_execute.yml` - Validation before execution

## Related Documentation

- [GraphScout Agent Guide](GRAPH_SCOUT_AGENT.md)
- [Path Executor Node](nodes/path-executor.md)
- [Loop Node](nodes/loop.md)
- [YAML Configuration Guide](YAML_CONFIGURATION.md)

