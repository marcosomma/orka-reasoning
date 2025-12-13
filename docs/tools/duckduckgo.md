# DuckDuckGo Search Tool

**Type:** `duckduckgo`

## Overview

Performs web searches using DuckDuckGo via the optional `ddgs` dependency.

Current codepath uses the agent `prompt` as the query; YAML `params` shown in older examples are **not** consumed by the implementation.

## Basic Configuration

```yaml
- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
```

See also:
- [YAML Configuration](../YAML_CONFIGURATION.md)

<!--

## Usage Examples

### Example 1: Basic Search

```yaml
- id: simple_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5
    region: "us-en"
    safe_search: "moderate"
```

### Example 2: Recent News Search

```yaml
- id: news_search
  type: duckduckgo
  prompt: "latest news about {{ input }}"
  params:
    num_results: 8
    time_range: "d"  # Last 24 hours
    region: "us-en"
```

### Example 3: Research Search

```yaml
- id: research_search
  type: duckduckgo
  prompt: "academic research {{ input }}"
  params:
    num_results: 10
    safe_search: "strict"
    region: "wt-wt"  # Worldwide
```

### Example 4: Search with Answer Generation

```yaml
- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5

- id: synthesize_answer
  type: openai-answer
  model: gpt-4o
  prompt: |
    Based on these search results:
    {{ previous_outputs.web_search }}
    
    Question: {{ input }}
    
    Provide a comprehensive, accurate answer with citations.
```

### Example 5: Conditional Search

```yaml
- id: check_memory
  type: memory-reader
  namespace: knowledge
  prompt: "{{ input }}"

- id: memory_sufficient
  type: openai-binary
  prompt: |
    Memory: {{ previous_outputs.check_memory }}
    Question: {{ input }}
    Is memory sufficient?

- id: router
  type: router
  params:
    decision_key: memory_sufficient
    routing_map:
      "true": [answer_from_memory]
      "false": [web_search, answer_from_web]

- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 8
    time_range: "w"
```

## Output Format

```python
{
    "results": [
        {
            "title": "Page Title",
            "url": "https://example.com/page",
            "snippet": "Preview text from the page...",
            "source": "example.com"
        },
        # ... more results
    ],
    "num_results": 5,
    "query": "original search query"
}
```

Access in templates:

```yaml
prompt: |
  Search results for "{{ previous_outputs.web_search.query }}":
  
  {% for result in previous_outputs.web_search.results %}
  {{ loop.index }}. {{ result.title }}
     Source: {{ result.source }}
     {{ result.snippet }}
     URL: {{ result.url }}
  
  {% endfor %}
```

## Region Codes

Common region codes:

| Code | Region |
|------|--------|
| `us-en` | United States (English) |
| `uk-en` | United Kingdom |
| `ca-en` | Canada (English) |
| `au-en` | Australia |
| `de-de` | Germany |
| `fr-fr` | France |
| `es-es` | Spain |
| `it-it` | Italy |
| `jp-jp` | Japan |
| `cn-zh` | China |
| `wt-wt` | Worldwide |

## Time Range Options

| Value | Meaning |
|-------|---------|
| `"d"` | Last day (24 hours) |
| `"w"` | Last week |
| `"m"` | Last month |
| `"y"` | Last year |

## Best Practices

### 1. Optimize Result Count

```yaml
# Quick overview
params:
  num_results: 3

# Standard search
params:
  num_results: 5

# Comprehensive research
params:
  num_results: 10
```

### 2. Time-Sensitive Queries

```yaml
# Breaking news
- id: breaking_news
  type: duckduckgo
  prompt: "breaking news {{ input }}"
  params:
    num_results: 8
    time_range: "d"

# Historical information
- id: historical_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5
    # No time_range for all-time results
```

### 3. Query Formulation

```yaml
# ✅ GOOD: Specific, targeted queries
prompt: "latest research on {{ topic }} 2025"
prompt: "how to {{ task }} step by step"
prompt: "{{ product }} review comparison"

# ❌ BAD: Too vague or general
prompt: "{{ input }}"  # If input is just one word
prompt: "information"
```

### 4. Safe Search Settings

```yaml
# Public/general audience
params:
  safe_search: "strict"

# Standard filtering
params:
  safe_search: "moderate"

# Unrestricted (use with caution)
params:
  safe_search: "off"
```

## Integration Patterns

### With Memory Fallback

```yaml
- id: search_with_fallback
  type: failover
  children:
    - id: try_web
      type: duckduckgo
      prompt: "{{ input }}"
      timeout: 15.0
    
    - id: try_memory
      type: memory-reader
      namespace: knowledge
      prompt: "{{ input }}"
```

### Multi-Source Synthesis

```yaml
- id: fork_sources
  type: fork
  targets:
    - [web_search]
    - [memory_search]

- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5

- id: memory_search
  type: memory-reader
  namespace: knowledge
  prompt: "{{ input }}"

- id: synthesize
  type: join
  prompt: |
    Web results: {{ previous_outputs.web_search }}
    Memory: {{ previous_outputs.memory_search }}
    
    Combine for comprehensive answer.
```

### Search and Store

```yaml
- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5

- id: generate_answer
  type: openai-answer
  prompt: |
    Search results: {{ previous_outputs.web_search }}
    Question: {{ input }}
    
    Generate answer.

- id: store_knowledge
  type: memory-writer
  namespace: web_knowledge
  params:
    vector: true
    metadata:
      source: "web_search"
      search_query: "{{ input }}"
  prompt: |
    Q: {{ input }}
    A: {{ previous_outputs.generate_answer }}
    Sources: {{ previous_outputs.web_search.results | map(attribute='url') | list }}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No results found | Query too specific | Broaden search terms |
| Timeout errors | Network issues | Increase timeout, check connection |
| Irrelevant results | Vague query | Make query more specific |
| Too many results | Broad query | Reduce num_results, refine query |
| Rate limiting | Too many requests | Add delays between searches |

## Performance Optimization

### Caching Strategy

```yaml
# Check cache first
- id: check_cache
  type: memory-reader
  namespace: search_cache
  params:
    similarity_threshold: 0.95  # Exact match
  prompt: "{{ input }}"

- id: cache_router
  type: router
  params:
    decision_key: check_cache
    routing_map:
      "found": [return_cached]
      "not_found": [web_search, cache_result]

- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
  params:
    num_results: 5

- id: cache_result
  type: memory-writer
  namespace: search_cache
  params:
    vector: true
  decay_config:
    enabled: true
    default_short_term_hours: 24  # Cache for 24 hours
  prompt: |
    Query: {{ input }}
    Results: {{ previous_outputs.web_search | tojson }}
```

## Advanced Example: Research Pipeline

```yaml
orchestrator:
  id: research-pipeline
  strategy: sequential
  agents: [
    query_optimizer,
    web_search,
    result_filter,
    synthesize_findings,
    store_research
  ]

agents:
  - id: query_optimizer
    type: openai-answer
    model: gpt-4o
    temperature: 0.3
    prompt: |
      Optimize this search query for better results:
      {{ input }}
      
      Make it:
      - More specific
      - Include relevant keywords
      - Target authoritative sources

  - id: web_search
    type: duckduckgo
    prompt: "{{ previous_outputs.query_optimizer }}"
    params:
      num_results: 10
      safe_search: "strict"
      time_range: "y"  # Last year

  - id: result_filter
    type: openai-answer
    model: gpt-4o
    temperature: 0.2
    prompt: |
      Filter these search results for quality and relevance:
      {{ previous_outputs.web_search }}
      
      Original question: {{ input }}
      
      Select top 5 most relevant and authoritative results.

  - id: synthesize_findings
    type: openai-answer
    model: gpt-4
    temperature: 0.4
    prompt: |
      Synthesize research findings:
      
      Question: {{ input }}
      Optimized query: {{ previous_outputs.query_optimizer }}
      Filtered results: {{ previous_outputs.result_filter }}
      
      Provide:
      1. Executive summary
      2. Key findings
      3. Supporting evidence
      4. Citations
      5. Recommendations for further research

  - id: store_research
    type: memory-writer
    namespace: research_database
    params:
      vector: true
      metadata:
        research_date: "{{ now() }}"
        query: "{{ input }}"
        num_sources: "{{ previous_outputs.web_search.num_results }}"
    decay_config:
      enabled: true
      default_long_term_hours: 2160  # 90 days
    prompt: |
      Research Report:
      Query: {{ input }}
      Findings: {{ previous_outputs.synthesize_findings }}
      Sources: {{ previous_outputs.web_search.results | map(attribute='url') | list }}
```

## Related Documentation

- [Memory (Agent)](../nodes/memory.md)
- [OpenAI Answer Agent](../agents/openai-answer.md)
- [Failover Node](../nodes/failover.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.8.0**: Added time_range filtering
- **v0.6.0**: Initial release

-->

