# RAG (Retrieval-Augmented Generation)

**Type:** `rag`

## Overview

RAG is implemented by `RAGNode` and is configured via **top-level fields** on the agent entry.

Older examples that put RAG settings under `params:` are not compatible with the current `AgentFactory` wiring.

## Basic Configuration

```yaml
- id: knowledge_qa
  type: rag
  top_k: 10
  score_threshold: 0.75
  timeout: 30.0
  prompt: "Answer: {{ input }}"
```

Supported fields (non-exhaustive):
- `top_k` (default `5`)
- `score_threshold` (default `0.7`)
- `timeout` (default `30.0`)
- `max_concurrency` (default `10`)

See also:
- [YAML Configuration](../YAML_CONFIGURATION.md)

<!--

## Usage Examples

### Example 1: Knowledge Base Q&A

```yaml
- id: kb_qa
  type: rag
  params:
    top_k: 10
    score_threshold: 0.75
    rerank: true
  prompt: |
    Answer this question using the knowledge base:
    {{ input }}
    
    Provide accurate, well-sourced answers.
```

### Example 2: Technical Documentation

```yaml
- id: docs_qa
  type: rag
  params:
    top_k: 15
    score_threshold: 0.8
  prompt: |
    Based on technical documentation:
    Question: {{ input }}
    
    Provide:
    - Direct answer
    - Code examples if relevant
    - Links to documentation sections
```

### Example 3: Multi-Stage RAG

```yaml
- id: initial_retrieval
  type: rag
  params:
    top_k: 20
    score_threshold: 0.65
  prompt: "{{ input }}"

- id: filter_results
  type: openai-answer
  model: gpt-4o
  temperature: 0.2
  prompt: |
    Filter these retrieved documents for relevance:
    {{ previous_outputs.initial_retrieval }}
    
    Question: {{ input }}
    
    Select top 5 most relevant.

- id: final_answer
  type: openai-answer
  model: gpt-4
  prompt: |
    Using filtered documents:
    {{ previous_outputs.filter_results }}
    
    Answer: {{ input }}
```

### Example 4: RAG with Verification

```yaml
- id: rag_search
  type: rag
  params:
    top_k: 10
    score_threshold: 0.75
    rerank: true
  prompt: "{{ input }}"

- id: verify_completeness
  type: openai-binary
  prompt: |
    Retrieved docs: {{ previous_outputs.rag_search }}
    Question: {{ input }}
    
    Is this sufficient to answer the question?

- id: router
  type: router
  params:
    decision_key: verify_completeness
    routing_map:
      "true": [generate_answer]
      "false": [web_search, combine_sources]

- id: generate_answer
  type: openai-answer
  prompt: |
    Using knowledge base:
    {{ previous_outputs.rag_search }}
    
    Answer: {{ input }}
```

## Output Format

```python
{
    "retrieved_docs": [
        {
            "content": "Document content...",
            "score": 0.89,
            "metadata": {
                "source": "doc_name.pdf",
                "page": 15
            }
        },
        # ... more documents
    ],
    "num_docs": 10,
    "answer": "Generated answer based on retrieved documents"
}
```

## Best Practices

### 1. Appropriate top_k

```yaml
# Quick answers
params:
  top_k: 5
  score_threshold: 0.85

# Comprehensive research
params:
  top_k: 20
  score_threshold: 0.7
```

### 2. Score Thresholds

```yaml
# High precision (few, very relevant docs)
params:
  score_threshold: 0.85

# Balanced
params:
  score_threshold: 0.75

# High recall (many, possibly less relevant)
params:
  score_threshold: 0.6
```

### 3. Re-ranking for Quality

```yaml
# Enable re-ranking for better relevance
params:
  top_k: 20
  score_threshold: 0.7
  rerank: true  # Improves result quality
```

## Integration Patterns

### RAG + Web Search Hybrid

```yaml
- id: fork_sources
  type: fork
  targets:
    - [rag_search]
    - [web_search]

- id: rag_search
  type: rag
  params:
    top_k: 10
    score_threshold: 0.75
  prompt: "{{ input }}"

- id: web_search
  type: duckduckgo
  params:
    num_results: 5
  prompt: "{{ input }}"

- id: synthesize
  type: join
  prompt: |
    Internal knowledge: {{ previous_outputs.rag_search }}
    External sources: {{ previous_outputs.web_search }}
    
    Combine for comprehensive answer to: {{ input }}
```

### RAG with Memory

```yaml
- id: check_recent_qa
  type: memory-reader
  namespace: qa_cache
  params:
    similarity_threshold: 0.95
  prompt: "{{ input }}"

- id: cache_router
  type: router
  params:
    decision_key: check_recent_qa
    routing_map:
      "found": [return_cached]
      "not_found": [rag_search, generate_answer, cache_result]

- id: rag_search
  type: rag
  params:
    top_k: 10
    score_threshold: 0.75
    rerank: true
  prompt: "{{ input }}"

- id: generate_answer
  type: openai-answer
  prompt: |
    Knowledge: {{ previous_outputs.rag_search }}
    Question: {{ input }}
    
    Generate answer.

- id: cache_result
  type: memory-writer
  namespace: qa_cache
  params:
    vector: true
  decay_config:
    enabled: true
    default_long_term_hours: 168
  prompt: |
    Q: {{ input }}
    A: {{ previous_outputs.generate_answer }}
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No documents retrieved | Threshold too high | Lower score_threshold |
| Irrelevant documents | Threshold too low | Raise score_threshold |
| Slow responses | Large top_k | Reduce top_k value |
| Poor answer quality | Bad retrieval | Enable rerank |

## Advanced Example: Enterprise Knowledge System

```yaml
orchestrator:
  id: enterprise-rag
  strategy: sequential
  agents: [
    query_analysis,
    rag_retrieval,
    result_validation,
    answer_generation,
    quality_check,
    store_interaction
  ]

agents:
  - id: query_analysis
    type: openai-answer
    model: gpt-4o
    temperature: 0.2
    prompt: |
      Analyze this query:
      {{ input }}
      
      Determine:
      - Query type (factual, how-to, troubleshooting)
      - Required information depth
      - Expected answer format

  - id: rag_retrieval
    type: rag
    params:
      top_k: 15
      score_threshold: 0.75
      rerank: true
    prompt: |
      Retrieve relevant documents for:
      {{ input }}
      
      Query analysis: {{ previous_outputs.query_analysis }}

  - id: result_validation
    type: openai-answer
    model: gpt-4o
    temperature: 0.2
    prompt: |
      Validate retrieved documents:
      {{ previous_outputs.rag_retrieval }}
      
      For query: {{ input }}
      
      Check:
      - Relevance
      - Completeness
      - Accuracy
      - Currency
      
      Provide validation report.

  - id: answer_generation
    type: openai-answer
    model: gpt-4
    temperature: 0.3
    prompt: |
      Generate comprehensive answer:
      
      Query: {{ input }}
      Query type: {{ previous_outputs.query_analysis }}
      Retrieved docs: {{ previous_outputs.rag_retrieval }}
      Validation: {{ previous_outputs.result_validation }}
      
      Requirements:
      - Accurate and complete
      - Well-structured
      - Include citations
      - Professional tone

  - id: quality_check
    type: openai-binary
    model: gpt-4o
    temperature: 0.1
    prompt: |
      Does this answer meet quality standards?
      
      Answer: {{ previous_outputs.answer_generation }}
      Original query: {{ input }}
      
      Standards:
      ✓ Accurate information
      ✓ Complete response
      ✓ Proper citations
      ✓ Clear language

  - id: store_interaction
    type: memory-writer
    namespace: enterprise_qa
    params:
      vector: true
      metadata:
        query_type: "{{ previous_outputs.query_analysis }}"
        quality_approved: "{{ previous_outputs.quality_check }}"
        num_sources: "{{ previous_outputs.rag_retrieval.num_docs }}"
    decay_config:
      enabled: true
      default_long_term_hours: 720  # 30 days
    prompt: |
      Enterprise Q&A Record:
      Question: {{ input }}
      Answer: {{ previous_outputs.answer_generation }}
      Sources: {{ previous_outputs.rag_retrieval.retrieved_docs | map(attribute='metadata.source') | list }}
      Quality: {{ previous_outputs.quality_check }}
```

## Related Documentation

- [Memory (Agent)](../nodes/memory.md)
- [DuckDuckGo Tool](./duckduckgo.md)
- [OpenAI Answer Agent](../agents/openai-answer.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.8.0**: Added re-ranking support
- **v0.7.0**: Initial release

-->

