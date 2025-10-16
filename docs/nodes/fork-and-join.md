# Fork and Join Nodes

**Types:** `fork` + `join`  
**Category:** Control Flow Nodes  
**Version:** v0.9.4+

## Overview

Fork and Join nodes enable parallel processing in workflows. Fork splits execution into multiple concurrent branches, while Join waits for completion and combines results.

## Fork Node

### Basic Configuration

```yaml
- id: parallel_processing
  type: fork
  targets:
    - [agent1]
    - [agent2]
    - [agent3]
  mode: parallel
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `targets` | list[list[string]] | - | Lists of agent IDs to execute in parallel |
| `mode` | string | `parallel` | Execution mode |
| `timeout` | float | `60.0` | Maximum wait time |

## Join Node

### Basic Configuration

```yaml
- id: combine_results
  type: join
  prompt: |
    Combine results:
    Agent1: {{ previous_outputs.agent1 }}
    Agent2: {{ previous_outputs.agent2 }}
    Agent3: {{ previous_outputs.agent3 }}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | Template for combining results |
| `timeout` | float | Processing timeout |

## Usage Examples

### Example 1: Parallel Analysis

```yaml
- id: fork_analysis
  type: fork
  targets:
    - [sentiment_analyzer]
    - [topic_classifier]
    - [quality_scorer]
    - [toxicity_checker]
  mode: parallel

- id: sentiment_analyzer
  type: openai-classification
  options: [positive, negative, neutral]
  prompt: "Sentiment: {{ input }}"

- id: topic_classifier
  type: openai-classification
  options: [tech, business, science]
  prompt: "Topic: {{ input }}"

- id: quality_scorer
  type: openai-answer
  prompt: "Rate quality 0-10: {{ input }}"

- id: toxicity_checker
  type: openai-binary
  prompt: "Contains toxic content? {{ input }}"

- id: join_analysis
  type: join
  prompt: |
    Comprehensive analysis:
    
    Sentiment: {{ previous_outputs.sentiment_analyzer }}
    Topic: {{ previous_outputs.topic_classifier }}
    Quality: {{ previous_outputs.quality_scorer }}
    Toxic: {{ previous_outputs.toxicity_checker }}
    
    Provide summary assessment.
```

### Example 2: Multi-Source Search

```yaml
- id: fork_search
  type: fork
  targets:
    - [memory_search]
    - [web_search]
    - [rag_search]

- id: memory_search
  type: memory-reader
  namespace: knowledge
  params:
    limit: 10
  prompt: "{{ input }}"

- id: web_search
  type: duckduckgo
  params:
    num_results: 5
  prompt: "{{ input }}"

- id: rag_search
  type: rag
  params:
    top_k: 10
  prompt: "{{ input }}"

- id: join_search
  type: join
  prompt: |
    Synthesize from all sources:
    
    Memory: {{ previous_outputs.memory_search }}
    Web: {{ previous_outputs.web_search }}
    RAG: {{ previous_outputs.rag_search }}
    
    Create comprehensive answer for: {{ input }}
```

### Example 3: Multi-Model Evaluation

```yaml
- id: fork_models
  type: fork
  targets:
    - [llama_model]
    - [mistral_model]
    - [gpt_model]

- id: llama_model
  type: local_llm
  provider: ollama
  model: "llama3:8b"
  model_url: "http://localhost:11434/api/generate"
  prompt: "{{ input }}"

- id: mistral_model
  type: local_llm
  provider: ollama
  model: "mistral:7b"
  model_url: "http://localhost:11434/api/generate"
  prompt: "{{ input }}"

- id: gpt_model
  type: openai-answer
  model: gpt-4o
  prompt: "{{ input }}"

- id: join_models
  type: join
  prompt: |
    Compare and synthesize the best answer:
    
    Llama: {{ previous_outputs.llama_model }}
    Mistral: {{ previous_outputs.mistral_model }}
    GPT: {{ previous_outputs.gpt_model }}
    
    Provide the most accurate, comprehensive response.
```

### Example 4: Validation Pipeline

```yaml
- id: fork_validation
  type: fork
  targets:
    - [grammar_check]
    - [fact_check]
    - [plagiarism_check]
    - [style_check]

- id: grammar_check
  type: openai-binary
  prompt: "Grammar correct? {{ input }}"

- id: fact_check
  type: openai-binary
  prompt: "Facts accurate? {{ input }}"

- id: plagiarism_check
  type: openai-binary
  prompt: "Original content? {{ input }}"

- id: style_check
  type: openai-binary
  prompt: "Style appropriate? {{ input }}"

- id: join_validation
  type: join
  prompt: |
    Validation summary:
    Grammar: {{ previous_outputs.grammar_check }}
    Facts: {{ previous_outputs.fact_check }}
    Originality: {{ previous_outputs.plagiarism_check }}
    Style: {{ previous_outputs.style_check }}
    
    Overall verdict: Pass/Fail with explanation.
```

### Example 5: Nested Fork-Join

```yaml
# Outer fork for main categories
- id: outer_fork
  type: fork
  targets:
    - [process_category_a]
    - [process_category_b]

# Category A: Inner fork for sub-tasks
- id: category_a_fork
  type: fork
  targets:
    - [a_task1]
    - [a_task2]

- id: a_join
  type: join
  prompt: "Combine A: {{ previous_outputs }}"

# Category B: Inner fork for sub-tasks
- id: category_b_fork
  type: fork
  targets:
    - [b_task1]
    - [b_task2]

- id: b_join
  type: join
  prompt: "Combine B: {{ previous_outputs }}"

# Outer join for final result
- id: outer_join
  type: join
  prompt: |
    Final synthesis:
    Category A: {{ previous_outputs.a_join }}
    Category B: {{ previous_outputs.b_join }}
```

## Best Practices

### 1. Independent Parallel Tasks

```yaml
# ✅ GOOD: Independent tasks that can run in parallel
- id: fork_independent
  type: fork
  targets:
    - [sentiment]      # Doesn't depend on others
    - [topic]          # Doesn't depend on others
    - [quality]        # Doesn't depend on others

# ❌ BAD: Sequential dependencies (don't parallelize)
- id: fork_dependent
  type: fork
  targets:
    - [step1]
    - [step2_needs_step1]  # Depends on step1!
    - [step3_needs_step2]  # Depends on step2!
```

### 2. Timeout Management

```yaml
# Set appropriate timeouts
- id: fork_with_timeout
  type: fork
  timeout: 120.0  # 2 minutes for all branches
  targets:
    - [fast_task]     # Completes in 10s
    - [slow_task]     # Completes in 60s
    - [medium_task]   # Completes in 30s
```

### 3. Join Prompt Design

```yaml
# ✅ GOOD: Structured combination
- id: good_join
  type: join
  prompt: |
    Synthesize results systematically:
    
    1. Sentiment: {{ previous_outputs.sentiment }}
    2. Topic: {{ previous_outputs.topic }}
    3. Quality: {{ previous_outputs.quality }}
    
    Overall assessment: [your analysis]

# ❌ BAD: Vague combination
- id: bad_join
  type: join
  prompt: "Combine stuff: {{ previous_outputs }}"
```

### 4. Error Handling

```yaml
# Use failover within fork branches
- id: fork_resilient
  type: fork
  targets:
    - [branch1_with_failover]
    - [branch2_with_failover]

- id: branch1_with_failover
  type: failover
  children:
    - id: try_primary
      type: openai-answer
      prompt: "{{ input }}"
    - id: use_backup
      type: local_llm
      prompt: "{{ input }}"
```

## Performance Considerations

### Speed vs Resources

```yaml
# More parallelism = faster but more resources
- id: high_parallelism
  type: fork
  targets:
    - [task1]
    - [task2]
    - [task3]
    - [task4]
    - [task5]  # 5 concurrent API calls

# Fewer branches = slower but more economical
- id: low_parallelism
  type: fork
  targets:
    - [task1]
    - [task2]  # 2 concurrent calls
```

### API Rate Limits

```yaml
# Be mindful of rate limits
- id: respect_limits
  type: fork
  targets:
    - [call1]  # OpenAI API
    - [call2]  # OpenAI API
    - [call3]  # OpenAI API
  # Don't exceed provider's concurrent request limits
```

## Integration Patterns

### With Routing

```yaml
- id: classifier
  type: openai-classification
  options: [simple, complex]
  prompt: "{{ input }}"

- id: router
  type: router
  params:
    decision_key: classifier
    routing_map:
      "simple": [simple_handler]
      "complex": [fork_complex, join_complex]

- id: fork_complex
  type: fork
  targets:
    - [deep_analysis]
    - [research]
    - [validation]

- id: join_complex
  type: join
  prompt: "Combine complex analysis: {{ previous_outputs }}"
```

### With Loops

```yaml
- id: iterative_fork
  type: loop
  max_loops: 3
  score_threshold: 0.9
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: fork_perspectives
        type: fork
        targets:
          - [perspective1]
          - [perspective2]
          - [perspective3]
      
      - id: join_perspectives
        type: join
        prompt: "Combine: {{ previous_outputs }}"
      
      - id: scorer
        type: openai-answer
        prompt: "Rate combined result: SCORE: X.XX"
```

### With Memory

```yaml
- id: fork_memory_ops
  type: fork
  targets:
    - [read_memories]
    - [process_input]

- id: read_memories
  type: memory-reader
  namespace: knowledge
  prompt: "{{ input }}"

- id: process_input
  type: openai-answer
  prompt: "Initial thoughts: {{ input }}"

- id: join_with_memory
  type: join
  prompt: |
    Combine fresh analysis with historical context:
    
    Historical: {{ previous_outputs.read_memories }}
    Current: {{ previous_outputs.process_input }}
    
    Synthesize comprehensive response.
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Timeout errors | Branches too slow | Increase timeout or optimize agents |
| Missing outputs | Agent ID mismatch | Verify agent IDs in targets |
| Sequential execution | Wrong configuration | Check `mode: parallel` |
| Join receives partial data | Some branches failed | Add error handling with failover |

## Advanced Example: Comprehensive Content Pipeline

```yaml
orchestrator:
  id: content-pipeline
  strategy: sequential
  agents: [
    initial_analysis,
    fork_processing,
    sentiment,
    quality,
    seo_check,
    plagiarism,
    join_results,
    final_decision
  ]

agents:
  - id: initial_analysis
    type: openai-answer
    model: gpt-4o
    prompt: "Quick analysis: {{ input }}"

  - id: fork_processing
    type: fork
    timeout: 90.0
    targets:
      - [sentiment]
      - [quality]
      - [seo_check]
      - [plagiarism]

  - id: sentiment
    type: openai-classification
    options: [very_positive, positive, neutral, negative, very_negative]
    prompt: "Sentiment: {{ input }}"

  - id: quality
    type: openai-answer
    model: gpt-4
    temperature: 0.2
    prompt: |
      Rate content quality (0.0-1.0):
      {{ input }}
      
      Criteria: accuracy, clarity, depth, structure
      Output: QUALITY_SCORE: X.XX

  - id: seo_check
    type: openai-answer
    prompt: |
      SEO analysis for: {{ input }}
      
      Check:
      - Keyword optimization
      - Meta description quality
      - Heading structure
      - Readability
      
      Score 0.0-1.0: SEO_SCORE: X.XX

  - id: plagiarism
    type: openai-binary
    prompt: |
      Is this original content?
      {{ input }}
      
      Check for signs of plagiarism or duplicate content.

  - id: join_results
    type: join
    prompt: |
      Comprehensive content assessment:
      
      SENTIMENT: {{ previous_outputs.sentiment }}
      QUALITY: {{ previous_outputs.quality }}
      SEO: {{ previous_outputs.seo_check }}
      ORIGINALITY: {{ previous_outputs.plagiarism }}
      
      Provide overall recommendation: APPROVE/REJECT/REVISE

  - id: final_decision
    type: openai-classification
    options: [approve, reject, revise]
    prompt: |
      Based on assessment: {{ previous_outputs.join_results }}
      
      Final decision?
```

## Related Documentation

- [Router Node](./router.md)
- [Loop Node](./loop.md)
- [Failover Node](./failover.md)
- [Parallel Processing Guide](../parallel-processing-guide.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.7.0**: Improved timeout handling
- **v0.5.0**: Initial release

