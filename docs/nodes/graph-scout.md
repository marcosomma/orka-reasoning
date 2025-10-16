# Graph Scout Agent

**Type:** `graph-scout`  
**Category:** Intelligent Routing Node  
**Version:** v0.9.3+ (NEW)

## Overview

Graph Scout is an intelligent workflow graph inspection agent that automatically discovers, evaluates, and executes the best sequence of agents for any input. It uses LLM-powered reasoning to find optimal paths through your workflow.

## Basic Configuration

```yaml
- id: smart_router
  type: graph-scout
  params:
    k_beam: 5
    max_depth: 3
    commit_margin: 0.15
    cost_budget_tokens: 1000
    latency_budget_ms: 2000
    safety_threshold: 0.8
  prompt: "Find best path for: {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | Description of the goal |

### Optional Parameters (in `params`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `k_beam` | int | `5` | Top-k candidate paths |
| `max_depth` | int | `3` | Maximum path depth |
| `commit_margin` | float | `0.15` | Confidence threshold for single path |
| `cost_budget_tokens` | int | `1000` | Token budget limit |
| `latency_budget_ms` | int | `2000` | Latency budget (ms) |
| `safety_threshold` | float | `0.8` | Safety assessment threshold |
| `timeout` | float | `60.0` | Discovery timeout |

## Decision Types

GraphScout makes one of three decisions:

1. **`commit_next`**: High confidence single path → Execute immediately
2. **`shortlist`**: Multiple good options → Execute all sequentially
3. **`no_path`**: No suitable path → Fallback to response builder

## Usage Examples

### Example 1: Dynamic Workflow Routing

```yaml
orchestrator:
  id: dynamic-system
  strategy: sequential
  agents: [graph_scout, process_result]

agents:
  - id: graph_scout
    type: graph-scout
    params:
      k_beam: 5
      max_depth: 4
      commit_margin: 0.15
    prompt: |
      Find optimal agent sequence for: {{ input }}
      
      Available agents:
      - memory_reader: Search stored knowledge
      - web_search: Get current information
      - analyzer: Deep analysis
      - validator: Check quality
      - answer_builder: Generate response

  - id: process_result
    type: openai-answer
    prompt: |
      GraphScout decision: {{ previous_outputs.graph_scout.decision }}
      Path: {{ previous_outputs.graph_scout.path }}
      Result: {{ previous_outputs.graph_scout.result }}
      
      Provide final response.
```

### Example 2: Self-Discovery Workflow

```yaml
- id: self_discovery
  type: graph-scout
  params:
    k_beam: 3
    max_depth: 5
    cost_budget_tokens: 2000
    latency_budget_ms: 5000
  prompt: |
    Self-discover the best approach for: {{ input }}
    
    Consider:
    - Information gathering needs
    - Analysis requirements
    - Validation steps
    - Output format
```

### Example 3: Adaptive Q&A System

```yaml
- id: adaptive_qa
  type: graph-scout
  params:
    k_beam: 4
    max_depth: 3
    safety_threshold: 0.85
  prompt: |
    Determine best path to answer: {{ input }}
    
    Options:
    1. Memory-first (fast, cached knowledge)
    2. Web-search (current information)
    3. Deep-analysis (complex reasoning)
    4. Multi-perspective (comprehensive view)
    
    Consider accuracy, speed, and cost.
```

## Key Features

### 1. Intelligent Path Discovery

Graph Scout automatically finds optimal agent sequences without manual routing logic.

### 2. Memory-Aware Routing

Positions memory agents optimally:
- Memory readers at the beginning
- Memory writers at the end
- Maximizes context availability

### 3. Multi-Agent Execution

When `shortlist` decision is made, executes ALL shortlisted agents sequentially for comprehensive results.

### 4. Budget & Safety Control

Respects token budgets, latency constraints, and safety thresholds to prevent expensive or risky paths.

## Output Format

```python
{
    "decision": "shortlist",  # or "commit_next", "no_path"
    "path": ["memory_reader", "analyzer", "answer_builder"],
    "confidence": 0.89,
    "reasoning": "Path explanation...",
    "result": "Combined execution results",
    "agents_executed": ["memory_reader", "analyzer", "answer_builder"],
    "execution_time_ms": 1523
}
```

## Best Practices

### 1. Clear Goal Description

```yaml
# ✅ GOOD: Specific goal
prompt: |
  Find best path to:
  - Answer technical question about {{ input }}
  - Verify information accuracy
  - Provide citations

# ❌ BAD: Vague goal
prompt: "Do something with {{ input }}"
```

### 2. Appropriate Budgets

```yaml
# Simple tasks
params:
  cost_budget_tokens: 500
  latency_budget_ms: 1000

# Complex tasks
params:
  cost_budget_tokens: 5000
  latency_budget_ms: 10000
```

### 3. Reasonable Depth

```yaml
# Quick decisions
params:
  max_depth: 2

# Comprehensive workflows
params:
  max_depth: 5
```

## Integration Patterns

### With Memory

```yaml
- id: graph_scout_with_memory
  type: graph-scout
  params:
    k_beam: 5
    max_depth: 4
  prompt: |
    Optimal path for: {{ input }}
    
    Memory context: {{ previous_outputs.memory_search }}
    
    Consider what's already known vs what needs discovery.
```

### With Validation

```yaml
- id: discover_path
  type: graph-scout
  params:
    k_beam: 3
    max_depth: 3
  prompt: "Find path for: {{ input }}"

- id: validate_result
  type: openai-binary
  prompt: |
    GraphScout result: {{ previous_outputs.discover_path }}
    Is this satisfactory?

- id: router
  type: router
  params:
    decision_key: validate_result
    routing_map:
      "true": [finalize]
      "false": [manual_processing]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Always "no_path" | No suitable agents found | Add more agent options |
| Slow discovery | High k_beam or max_depth | Reduce parameters |
| Budget exceeded | Paths too expensive | Increase budget or simplify |
| Poor path selection | Vague prompt | Provide clearer goal description |

## Advanced Example

```yaml
orchestrator:
  id: intelligent-orchestrator
  strategy: sequential
  agents: [context_builder, graph_scout, result_processor]

agents:
  - id: context_builder
    type: openai-answer
    model: gpt-4o
    temperature: 0.3
    prompt: |
      Analyze what's needed for: {{ input }}
      
      Consider:
      - Information requirements
      - Processing complexity
      - Quality expectations
      - Time constraints

  - id: graph_scout
    type: graph-scout
    params:
      k_beam: 5
      max_depth: 4
      commit_margin: 0.15
      cost_budget_tokens: 3000
      latency_budget_ms: 5000
      safety_threshold: 0.85
    prompt: |
      Based on context analysis:
      {{ previous_outputs.context_builder }}
      
      Discover optimal agent sequence for: {{ input }}
      
      Available capabilities:
      - memory_reader: Fast, cached knowledge
      - web_search: Current, real-time information
      - deep_analyzer: Complex reasoning
      - multi_perspective: Comprehensive views
      - validator: Quality assurance
      - fact_checker: Accuracy verification
      
      Select path balancing speed, accuracy, and cost.

  - id: result_processor
    type: openai-answer
    model: gpt-4o
    temperature: 0.3
    prompt: |
      GraphScout discovered path:
      Decision: {{ previous_outputs.graph_scout.decision }}
      Agents: {{ previous_outputs.graph_scout.agents_executed }}
      Confidence: {{ previous_outputs.graph_scout.confidence }}
      
      Results: {{ previous_outputs.graph_scout.result }}
      
      Synthesize final comprehensive response for: {{ input }}
```

## Related Documentation

- [Router Node](./router.md)
- [Workflow Architecture](../architecture.md)
- [Graph Scout Guide](../GRAPH_SCOUT_AGENT.md)

## Version History

- **v0.9.4**: Current stable
- **v0.9.3**: Initial GraphScout release

