# Memory Writer Node

**Type:** `memory-writer`  
**Category:** Memory Agent  
**Version:** v0.9.4+

## Overview

The Memory Writer stores information with **RedisStack HNSW vector indexing** for lightning-fast retrieval (50,000 writes/sec throughput). Features intelligent decay management, automatic classification, and semantic indexing.

## Basic Configuration

```yaml
- id: memory_store
  type: memory-writer
  namespace: conversations
  params:
    vector: true
    metadata:
      source: "user_input"
  prompt: "{{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier |
| `type` | string | Must be `memory-writer` |
| `namespace` | string | Storage namespace |
| `prompt` | string | Content to store |

### Optional Parameters (in `params`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vector` | bool | `true` | Enable HNSW semantic indexing |
| `metadata` | object | `{}` | Custom metadata |
| `memory_type` | string | auto | `short_term` or `long_term` |
| `timeout` | float | `10.0` | Write timeout |

### Decay Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `decay_config.enabled` | bool | `true` | Enable decay |
| `decay_config.default_short_term_hours` | float | `2` | Short-term TTL |
| `decay_config.default_long_term_hours` | float | `168` | Long-term TTL (1 week) |

## Usage Examples

### Example 1: Basic Storage

```yaml
- id: store_interaction
  type: memory-writer
  namespace: user_sessions
  params:
    vector: true
    metadata:
      timestamp: "{{ now() }}"
  prompt: |
    User: {{ input }}
    Response: {{ previous_outputs.answer }}
```

### Example 2: With Custom Metadata

```yaml
- id: store_with_metadata
  type: memory-writer
  namespace: knowledge_base
  params:
    vector: true
    metadata:
      source: "web_search"
      confidence: "{{ previous_outputs.validator.confidence }}"
      topic: "{{ previous_outputs.classifier }}"
      verified: true
  prompt: |
    Question: {{ input }}
    Answer: {{ previous_outputs.answer }}
    Sources: {{ previous_outputs.search.sources }}
```

### Example 3: Custom Decay Settings

```yaml
- id: critical_memory
  type: memory-writer
  namespace: critical_events
  params:
    vector: true
    metadata:
      priority: "critical"
  decay_config:
    enabled: true
    default_long_term_hours: 4320  # 180 days
  prompt: "Critical event: {{ input }}"

- id: temporary_cache
  type: memory-writer
  namespace: temp_cache
  params:
    vector: false  # No semantic search needed
  decay_config:
    enabled: true
    default_short_term_hours: 0.5  # 30 minutes
  prompt: "Temp data: {{ input }}"
```

### Example 4: Memory Presets

```yaml
# Sensory memory - 5 minutes
- id: sensory_write
  type: memory-writer
  memory_preset: "sensory"
  namespace: raw_input
  prompt: "{{ input }}"

# Episodic memory - 90 days
- id: episodic_write
  type: memory-writer
  memory_preset: "episodic"
  namespace: experiences
  params:
    metadata:
      interaction_type: "{{ previous_outputs.classifier }}"
  prompt: |
    Experience: {{ input }}
    Outcome: {{ previous_outputs.result }}

# Meta memory - 180 days
- id: meta_write
  type: memory-writer
  memory_preset: "meta"
  namespace: system_insights
  params:
    metadata:
      loops_ran: "{{ loop_number }}"
      final_score: "{{ score }}"
  prompt: |
    System reflection:
    {{ previous_outputs.analysis }}
```

### Example 5: Conditional Storage

```yaml
- id: quality_check
  type: openai-binary
  prompt: "Is this worth storing? {{ previous_outputs.answer }}"

- id: storage_router
  type: router
  params:
    decision_key: quality_check
    routing_map:
      "true": [store_memory]
      "false": [skip_storage]

- id: store_memory
  type: memory-writer
  namespace: validated_content
  params:
    vector: true
    metadata:
      quality_approved: true
  prompt: "{{ previous_outputs.answer }}"
```

## Memory Presets

| Preset | TTL | Vector | Use Case |
|--------|-----|--------|----------|
| `sensory` | 5 min | ✅ | Raw input buffering |
| `working` | 2 hours | ✅ | Active task context |
| `semantic` | 30 days | ✅ | Facts/knowledge |
| `procedural` | 60 days | ✅ | Skills/processes |
| `episodic` | 90 days | ✅ | Experiences/interactions |
| `meta` | 180 days | ✅ | System insights |

## Output Format

```python
{
    "memory_id": "mem_abc123",
    "namespace": "conversations",
    "stored_at": "2025-10-16T12:00:00Z",
    "expires_at": "2025-10-23T12:00:00Z",
    "memory_type": "long_term",
    "vector_indexed": true
}
```

## Best Practices

### 1. Namespace Organization

```yaml
# ✅ GOOD: Organized by purpose
namespace: user_conversations
namespace: verified_facts
namespace: error_logs
namespace: system_metrics

# ❌ BAD: Generic naming
namespace: data
namespace: misc
```

### 2. Meaningful Metadata

```yaml
# ✅ GOOD: Rich metadata
params:
  metadata:
    source: "web_search"
    confidence: 0.92
    topic: "AI orchestration"
    verified: true
    timestamp: "{{ now() }}"

# ❌ BAD: Minimal metadata
params:
  metadata:
    saved: true
```

### 3. Appropriate Decay

```yaml
# Short-lived data
decay_config:
  default_short_term_hours: 0.5  # 30 min cache

# Important knowledge
decay_config:
  default_long_term_hours: 2160  # 90 days

# Critical records
decay_config:
  default_long_term_hours: 8760  # 1 year
```

### 4. Vector Indexing Strategy

```yaml
# Enable for semantic search
params:
  vector: true  # Conversations, knowledge, Q&A

# Disable for exact-match only
params:
  vector: false  # Logs, metrics, temporary cache
```

## Performance

- **Write Throughput:** 50,000/sec with HNSW
- **Indexing Latency:** Sub-millisecond
- **Storage:** Efficient compression

## Integration Patterns

### With Validation

```yaml
- id: answer
  type: openai-answer
  prompt: "{{ input }}"

- id: validate
  type: validate_and_structure
  prompt: "Validate: {{ previous_outputs.answer }}"

- id: store_validated
  type: memory-writer
  namespace: validated_answers
  params:
    vector: true
    metadata:
      validation_passed: true
      confidence: "{{ previous_outputs.validate.confidence }}"
  prompt: |
    Q: {{ input }}
    A: {{ previous_outputs.answer }}
    Validation: {{ previous_outputs.validate }}
```

### Multi-Namespace Storage

```yaml
# Store in multiple places
- id: fork_storage
  type: fork
  targets:
    - [store_conversation]
    - [store_knowledge]
    - [store_analytics]

- id: store_conversation
  type: memory-writer
  namespace: conversations
  params:
    vector: true
  decay_config:
    default_long_term_hours: 168  # 1 week
  prompt: "{{ input }}: {{ previous_outputs.answer }}"

- id: store_knowledge
  type: memory-writer
  namespace: knowledge_base
  params:
    vector: true
  decay_config:
    default_long_term_hours: 2160  # 90 days
  prompt: "{{ previous_outputs.structured.content }}"

- id: store_analytics
  type: memory-writer
  namespace: analytics
  params:
    vector: false
    metadata:
      tokens_used: "{{ previous_outputs.answer.usage.total_tokens }}"
  decay_config:
    default_short_term_hours: 24
  prompt: "Stats: {{ previous_outputs | tojson }}"
```

### Feedback Loop Storage

```yaml
- id: improvement_loop
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents: [improver, scorer]

- id: store_final_result
  type: memory-writer
  namespace: improved_answers
  params:
    vector: true
    metadata:
      iterations: "{{ previous_outputs.improvement_loop.loops_completed }}"
      final_score: "{{ previous_outputs.improvement_loop.final_score }}"
  prompt: |
    Original: {{ input }}
    Final: {{ previous_outputs.improvement_loop.response }}
    Iterations: {{ previous_outputs.improvement_loop.loops_completed }}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Slow writes | Basic Redis | Use `redisstack` backend |
| Memory not found later | Vector not enabled | Set `vector: true` |
| Memory expires too fast | Short decay time | Increase TTL hours |
| Storage overflow | No decay | Enable decay cleanup |
| Missing metadata | Not provided | Add comprehensive metadata |

## Configuration

### Global Setup

```yaml
orchestrator:
  memory:
    enabled: true
    backend: redisstack
    config:
      redis_url: redis://localhost:6380/0
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
      importance_rules:
        critical_info: 3.0
        user_feedback: 2.5
```

## Environment Variables

```bash
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
```

## Related Documentation

- [Memory Reader Node](./memory-reader.md)
- [Memory System Guide](../MEMORY_SYSTEM_GUIDE.md)
- [Memory Presets](../memory-presets.md)
- [Validate and Structure Agent](../agents/validate-and-structure.md)

## Version History

- **v0.9.4**: Current with RedisStack HNSW
- **v0.9.0**: Added presets
- **v0.8.0**: Improved decay
- **v0.7.0**: Initial release