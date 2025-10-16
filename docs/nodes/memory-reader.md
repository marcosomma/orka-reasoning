# Memory Reader Node

**Type:** `memory-reader`  
**Category:** Memory Agent  
**Version:** v0.9.4+

## Overview

The Memory Reader performs semantic search and retrieval using **RedisStack HNSW indexing** with sub-millisecond vector search performance (100x faster than basic Redis). It combines semantic similarity, keyword matching, and temporal ranking for intelligent memory retrieval.

## Basic Configuration

```yaml
- id: memory_search
  type: memory-reader
  namespace: knowledge_base
  params:
    limit: 10
    similarity_threshold: 0.8
    enable_context_search: true
  prompt: "Find: {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier |
| `type` | string | Must be `memory-reader` |
| `namespace` | string | Memory namespace to search |
| `prompt` | string | Search query |

### Optional Parameters (in `params`)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `10` | Max memories to return |
| `similarity_threshold` | float | `0.7` | Min relevance (0.0-1.0) |
| `enable_context_search` | bool | `false` | Use conversation history |
| `context_weight` | float | `0.4` | Context importance (0.0-1.0) |
| `temporal_weight` | float | `0.3` | Recency importance (0.0-1.0) |
| `enable_temporal_ranking` | bool | `false` | Boost recent memories |
| `memory_type_filter` | string | - | Filter: `short_term` or `long_term` |
| `memory_category_filter` | string | - | Filter by category |
| `timeout` | float | `10.0` | Search timeout |

## Performance

- **Search Latency:** 0.5-5ms (vs 50-200ms with basic Redis)
- **Throughput:** 100x faster with HNSW indexing
- **Accuracy:** Sub-millisecond semantic search

## Usage Examples

### Example 1: Basic Semantic Search

```yaml
- id: knowledge_search
  type: memory-reader
  namespace: knowledge_base
  params:
    limit: 5
    similarity_threshold: 0.8
  prompt: "{{ input }}"
```

### Example 2: Context-Aware Search

```yaml
- id: contextual_search
  type: memory-reader
  namespace: conversations
  params:
    limit: 10
    similarity_threshold: 0.7
    enable_context_search: true
    context_weight: 0.4        # 40% weight for conversation context
    temporal_weight: 0.3       # 30% weight for recency
    enable_temporal_ranking: true
  prompt: |
    Find relevant memories for: {{ input }}
    
    Consider conversation history and recent context.
```

### Example 3: Filtered Search

```yaml
- id: filtered_search
  type: memory-reader
  namespace: knowledge_base
  params:
    limit: 15
    similarity_threshold: 0.75
    memory_type_filter: "long_term"    # Only long-term memories
    memory_category_filter: "facts"     # Only facts category
  prompt: "{{ input }}"
```

### Example 4: Broad vs Narrow Search

```yaml
# Broad search - cast wide net
- id: broad_search
  type: memory-reader
  namespace: all_knowledge
  params:
    limit: 20
    similarity_threshold: 0.6           # Lower threshold
    enable_temporal_ranking: false      # Don't bias to recent
  prompt: "{{ input }}"

# Narrow search - precise matches
- id: narrow_search
  type: memory-reader
  namespace: technical_docs
  params:
    limit: 5
    similarity_threshold: 0.9           # High threshold
    memory_type_filter: "long_term"
  prompt: "{{ input }}"
```

### Example 5: Multi-Namespace Search

```yaml
- id: fork_search
  type: fork
  targets:
    - [search_conversations]
    - [search_knowledge]
    - [search_procedures]

- id: search_conversations
  type: memory-reader
  namespace: conversations
  params:
    limit: 5
    similarity_threshold: 0.8
  prompt: "{{ input }}"

- id: search_knowledge
  type: memory-reader
  namespace: knowledge_base
  params:
    limit: 10
    similarity_threshold: 0.75
  prompt: "{{ input }}"

- id: search_procedures
  type: memory-reader
  namespace: procedures
  params:
    limit: 3
    similarity_threshold: 0.85
  prompt: "{{ input }}"

- id: combine_searches
  type: join
  prompt: |
    Combine search results:
    Conversations: {{ previous_outputs.search_conversations }}
    Knowledge: {{ previous_outputs.search_knowledge }}
    Procedures: {{ previous_outputs.search_procedures }}
```

## Memory Presets

Use presets for pre-configured settings:

```yaml
- id: episodic_search
  type: memory-reader
  memory_preset: "episodic"  # 7 days, limit=8, threshold=0.6
  namespace: experiences
  prompt: "{{ input }}"

- id: semantic_search
  type: memory-reader
  memory_preset: "semantic"  # 30 days, limit=10, threshold=0.75
  namespace: knowledge
  prompt: "{{ input }}"
```

| Preset | TTL | Limit | Threshold | Use Case |
|--------|-----|-------|-----------|----------|
| `sensory` | 5 min | 5 | 0.5 | Raw inputs |
| `working` | 2 hours | 6 | 0.6 | Active tasks |
| `semantic` | 30 days | 10 | 0.75 | Facts/knowledge |
| `procedural` | 60 days | 8 | 0.8 | Skills/processes |
| `episodic` | 90 days | 8 | 0.6 | Experiences |
| `meta` | 180 days | 12 | 0.7 | System insights |

## Output Format

```python
{
    "memories": [
        {
            "content": "Memory content here...",
            "similarity_score": 0.92,
            "metadata": {
                "timestamp": "2025-10-16T12:00:00Z",
                "namespace": "knowledge_base",
                "memory_type": "long_term",
                "category": "facts"
            },
            "id": "mem_abc123"
        }
    ],
    "num_results": 5,
    "search_query": "original query",
    "namespace": "knowledge_base"
}
```

Access in templates:

```yaml
prompt: |
  Found {{ previous_outputs.memory_search.num_results }} memories:
  {% for memory in previous_outputs.memory_search.memories %}
  - {{ memory.content }} (score: {{ memory.similarity_score }})
  {% endfor %}
```

## Threshold Guide

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.95-1.0 | Exact/near-exact matches | Duplicate detection |
| 0.85-0.94 | Very similar | Fact verification |
| 0.75-0.84 | Clearly related | Knowledge retrieval |
| 0.65-0.74 | Somewhat related | Exploratory search |
| 0.50-0.64 | Loosely related | Broad context |
| < 0.50 | Weak connection | Not recommended |

## Best Practices

### 1. Namespace Organization

```yaml
# ✅ GOOD: Specific namespaces
namespace: user_conversations
namespace: technical_documentation
namespace: error_logs

# ❌ BAD: Too generic
namespace: data
namespace: stuff
```

### 2. Appropriate Thresholds

```yaml
# High threshold for facts
- id: fact_search
  type: memory-reader
  namespace: verified_facts
  params:
    similarity_threshold: 0.85

# Lower threshold for exploration
- id: related_search
  type: memory-reader
  namespace: general_knowledge
  params:
    similarity_threshold: 0.65
```

### 3. Limit Based on Use Case

```yaml
# Few high-quality results
params:
  limit: 3
  similarity_threshold: 0.9

# Many results for context
params:
  limit: 20
  similarity_threshold: 0.7
```

### 4. Context-Aware Search

```yaml
- id: contextual_search
  type: memory-reader
  namespace: conversations
  params:
    enable_context_search: true
    context_weight: 0.4           # Balance with similarity
    temporal_weight: 0.3          # Recent matters
    enable_temporal_ranking: true
  prompt: "{{ input }}"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No results found | Threshold too high | Lower to 0.6-0.7 |
| Too many irrelevant results | Threshold too low | Raise to 0.8+ |
| Slow searches | Basic Redis backend | Use `redisstack` backend |
| Missing recent memories | No temporal ranking | Enable `enable_temporal_ranking: true` |
| Stale results | Decay not enabled | Enable memory decay |

## Integration Patterns

### With Binary Decision

```yaml
- id: memory_search
  type: memory-reader
  namespace: knowledge
  params:
    limit: 5
    similarity_threshold: 0.8
  prompt: "{{ input }}"

- id: has_sufficient_info
  type: openai-binary
  prompt: |
    Memories found: {{ previous_outputs.memory_search }}
    Query: {{ input }}
    
    Is this sufficient to answer?

- id: router
  type: router
  params:
    decision_key: has_sufficient_info
    routing_map:
      "true": [answer_from_memory]
      "false": [search_web]
```

### With Failover

```yaml
- id: search_with_fallback
  type: failover
  children:
    - id: try_memory
      type: memory-reader
      namespace: knowledge
      params:
        limit: 10
        similarity_threshold: 0.85
      prompt: "{{ input }}"
    
    - id: fallback_search
      type: duckduckgo
      prompt: "{{ input }}"
```

### In Loops

```yaml
- id: iterative_search
  type: loop
  max_loops: 3
  score_threshold: 0.9
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: refined_search
        type: memory-reader
        namespace: knowledge
        params:
          limit: 10
          similarity_threshold: 0.7
        prompt: |
          Iteration {{ loop_number }}
          Original: {{ input }}
          {% if has_past_loops() %}
          Previous attempts: {{ get_past_loops() }}
          {% endif %}
      
      - id: evaluate
        type: openai-answer
        prompt: |
          Rate search quality (0.0-1.0):
          {{ previous_outputs.refined_search }}
          SCORE: X.XX
```

## Configuration

### Global Memory Setup

```yaml
orchestrator:
  memory:
    enabled: true
    backend: redisstack  # 100x faster
    config:
      redis_url: redis://localhost:6380/0
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
```

## Environment Variables

```bash
# RedisStack (recommended)
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# Memory decay
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
```

## Related Documentation

- [Memory Writer Node](./memory-writer.md)
- [Memory System Guide](../MEMORY_SYSTEM_GUIDE.md)
- [Memory Presets](../memory-presets.md)
- [RedisStack Setup](../redis-stack-setup.md)

## Version History

- **v0.9.4**: Current version with RedisStack HNSW
- **v0.9.0**: Added context-aware search
- **v0.8.0**: Added memory presets
- **v0.7.0**: Initial release

