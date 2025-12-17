# Failover Node

**Type:** `failover`  
**Category:** Control Flow Node  
**Version:** v0.9.4+

## Overview

The Failover Node executes child agents sequentially until one succeeds, providing resilience and fallback strategies for workflows.

## Basic Configuration

```yaml
- id: resilient_search
  type: failover
  children:
    - id: primary_search
      type: duckduckgo
      prompt: "{{ input }}"
    
    - id: backup_memory
      type: memory-reader
      namespace: knowledge
      prompt: "{{ input }}"
    
    - id: final_fallback
      type: openai-answer
      prompt: "Answer from training: {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `children` | list[object] | List of agent configurations |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | float | `60.0` | Total timeout for all attempts |

## Usage Examples

### Example 1: Search with Fallbacks

```yaml
- id: search_with_fallback
  type: failover
  children:
    - id: web_search
      type: duckduckgo
      params:
        num_results: 5
      prompt: "{{ input }}"
      timeout: 15.0
    
    - id: memory_fallback
      type: memory-reader
      namespace: knowledge_base
      params:
        limit: 10
      prompt: "{{ input }}"
      timeout: 10.0
    
    - id: llm_fallback
      type: openai-answer
      model: gpt-4o
      prompt: "Based on training knowledge: {{ input }}"
      timeout: 30.0
```

### Example 2: Multi-Model Fallback

```yaml
- id: llm_with_fallback
  type: failover
  children:
    - id: try_local
      type: local_llm
      provider: lm_studio
      model: "llama3:8b"
      model_url: "http://localhost:1234"
      prompt: "{{ input }}"
      timeout: 30.0
    
    - id: try_cloud_cheap
      type: openai-answer
      model: gpt-3.5-turbo
      prompt: "{{ input }}"
      timeout: 20.0
    
    - id: try_cloud_premium
      type: openai-answer
      model: gpt-4o
      prompt: "{{ input }}"
      timeout: 30.0
```

### Example 3: Validation with Recovery

```yaml
- id: validated_processing
  type: failover
  children:
    - id: try_fast_method
      type: openai-answer
      model: gpt-3.5-turbo
      temperature: 0.3
      prompt: "{{ input }}"
    
    - id: try_accurate_method
      type: openai-answer
      model: gpt-4
      temperature: 0.2
      prompt: "Carefully: {{ input }}"
    
    - id: manual_override
      type: openai-answer
      model: gpt-4
      temperature: 0.1
      system_prompt: "Use extreme caution and verify all facts."
      prompt: "Critical task: {{ input }}"
```

### Example 4: Memory Hierarchy

```yaml
- id: hierarchical_memory
  type: failover
  children:
    - id: recent_memory
      type: memory-reader
      namespace: recent_conversations
      params:
        limit: 5
        similarity_threshold: 0.9
        enable_temporal_ranking: true
      prompt: "{{ input }}"
    
    - id: semantic_memory
      type: memory-reader
      namespace: knowledge_base
      params:
        limit: 10
        similarity_threshold: 0.75
      prompt: "{{ input }}"
    
    - id: broad_memory
      type: memory-reader
      namespace: all_data
      params:
        limit: 20
        similarity_threshold: 0.6
      prompt: "{{ input }}"
```

## Best Practices

### 1. Order by Preference

```yaml
# ✅ GOOD: Best option first, fallbacks follow
children:
  - id: preferred_method    # Fastest, cheapest
  - id: backup_method       # Slower, more expensive
  - id: last_resort         # Slowest, most expensive

# ❌ BAD: Random order
children:
  - id: expensive_method
  - id: cheap_method
  - id: medium_method
```

### 2. Appropriate Timeouts

```yaml
# Individual timeouts for each child
children:
  - id: fast_attempt
    timeout: 10.0
  - id: medium_attempt
    timeout: 30.0
  - id: slow_attempt
    timeout: 60.0

# Overall failover timeout
- id: failover
  type: failover
  timeout: 120.0  # Sum of all individual timeouts + buffer
```

### 3. Meaningful Fallbacks

```yaml
# ✅ GOOD: Each fallback is genuinely useful
children:
  - id: specific_source
  - id: broader_source
  - id: general_knowledge

# ❌ BAD: Same thing repeated
children:
  - id: search1
  - id: search2  # Same as search1
  - id: search3  # Same as search1
```

## Integration Patterns

### With Router

```yaml
- id: classifier
  type: openai-classification
  options: [urgent, normal]
  prompt: "{{ input }}"

- id: router
  type: router
  params:
    decision_key: classifier
    routing_map:
      "urgent": [no_failover_needed]
      "normal": [use_failover]

- id: use_failover
  type: failover
  children:
    - id: cheap_method
    - id: expensive_method
```

### In Loops

```yaml
- id: resilient_loop
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: improver_with_failover
        type: failover
        children:
          - id: try_local
            type: local_llm
            prompt: "Improve: {{ input }}"
          - id: use_cloud
            type: openai-answer
            prompt: "Improve: {{ input }}"
      - id: scorer
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| All children fail | None succeed | Add more fallbacks or fix logic |
| Slow execution | All children timeout | Reduce individual timeouts |
| Expensive costs | Typically uses last child (evaluate for your workflow) | Fix earlier children |
| No output | Missing children | Add at least one child |

## Related Documentation

- [Router Node](./router.md)
- [Fork and Join Nodes](./fork-and-join.md)
- [Error Handling Guide](../error-handling.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.6.0**: Initial release

