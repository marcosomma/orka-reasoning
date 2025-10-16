# OpenAI Answer Builder Agent

**Type:** `openai-answer`  
**Category:** LLM Agent  
**Version:** v0.9.4+

## Overview

The OpenAI Answer Builder agent generates comprehensive text responses using OpenAI's language models. It's ideal for content generation, question answering, summarization, and any task requiring natural language understanding and generation.

## Basic Configuration

```yaml
- id: answer_builder
  type: openai-answer
  model: gpt-4o
  temperature: 0.7
  prompt: "Answer this question: {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier for the agent |
| `type` | string | Must be `openai-answer` |
| `prompt` | string | Template for the prompt with variables |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gpt-4o` | OpenAI model to use |
| `temperature` | float | `0.7` | Creativity (0.0-2.0) |
| `max_tokens` | int | `1000` | Maximum response length |
| `system_prompt` | string | - | System message for context |
| `top_p` | float | `1.0` | Nucleus sampling parameter |
| `frequency_penalty` | float | `0.0` | Reduce repetition (-2.0 to 2.0) |
| `presence_penalty` | float | `0.0` | Encourage new topics (-2.0 to 2.0) |
| `timeout` | float | `30.0` | Request timeout in seconds |
| `queue` | string | `orka:main` | Queue for processing |

## Model Options

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `gpt-4o` | General purpose, balanced | Fast | Medium |
| `gpt-4` | Complex reasoning, accuracy | Slow | High |
| `gpt-4-turbo` | Long context, comprehensive | Medium | High |
| `gpt-3.5-turbo` | Simple tasks, speed | Very Fast | Low |
| `gpt-4o-mini` | Lightweight, fast responses | Very Fast | Very Low |

## Temperature Guide

```yaml
# Factual/Precise (0.0-0.3)
temperature: 0.2  # For facts, calculations, code

# Balanced (0.4-0.7)
temperature: 0.7  # General conversation, Q&A

# Creative (0.8-1.5)
temperature: 1.2  # Creative writing, brainstorming
```

## Usage Examples

### Example 1: Simple Q&A

```yaml
- id: qa_agent
  type: openai-answer
  model: gpt-4o
  temperature: 0.3
  prompt: |
    Answer this question accurately and concisely:
    {{ input }}
```

### Example 2: Contextualized Response

```yaml
- id: contextual_answer
  type: openai-answer
  model: gpt-4o
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "You are an expert technical writer."
  prompt: |
    Context: {{ previous_outputs.memory_search }}
    Search Results: {{ previous_outputs.web_search }}
    
    Question: {{ input }}
    
    Provide a comprehensive answer using the context and search results.
    Include citations and examples.
```

### Example 3: Structured Output

```yaml
- id: structured_answer
  type: openai-answer
  model: gpt-4o
  temperature: 0.2
  prompt: |
    Analyze the following and provide structured output:
    {{ input }}
    
    Format:
    SUMMARY: <one sentence>
    KEY_POINTS: <bullet list>
    RECOMMENDATIONS: <numbered list>
    CONFIDENCE: <0.0-1.0>
```

### Example 4: Multi-Stage Processing

```yaml
- id: stage1_draft
  type: openai-answer
  model: gpt-4o
  temperature: 0.8
  prompt: "Create a draft answer for: {{ input }}"

- id: stage2_refine
  type: openai-answer
  model: gpt-4o
  temperature: 0.3
  prompt: |
    Refine and improve this draft:
    {{ previous_outputs.stage1_draft }}
    
    Make it more accurate, clear, and professional.
```

### Example 5: With System Prompt

```yaml
- id: expert_advisor
  type: openai-answer
  model: gpt-4
  temperature: 0.5
  max_tokens: 1500
  system_prompt: |
    You are a senior software architect with 20 years of experience.
    You provide detailed, practical advice with real-world examples.
    You consider scalability, maintainability, and best practices.
  prompt: |
    Technical Challenge: {{ input }}
    Current Context: {{ previous_outputs.context }}
    
    Provide your expert recommendation.
```

## Template Variables

All standard OrKa template variables are available:

```yaml
prompt: |
  # Input
  {{ input }}                              # Original user input
  
  # Previous outputs
  {{ previous_outputs.agent_id }}          # Specific agent output
  {{ previous_outputs }}                   # All outputs
  
  # Helpers
  {{ get_agent_response('agent_id') }}     # Safe access
  {{ get_input() }}                        # Alternative input access
  
  # Utilities
  {{ now() }}                              # Current timestamp
  {{ loop_number }}                        # If in loop
```

## Best Practices

### 1. Temperature Selection

```yaml
# Factual tasks
- id: fact_checker
  type: openai-answer
  temperature: 0.1  # Low for consistency
  prompt: "Verify this fact: {{ input }}"

# Creative tasks
- id: story_writer
  type: openai-answer
  temperature: 1.0  # High for creativity
  prompt: "Write a story about: {{ input }}"
```

### 2. Prompt Engineering

```yaml
# ✅ GOOD: Clear, specific, structured
prompt: |
  ROLE: You are a technical documentation expert.
  
  CONTEXT: {{ previous_outputs.search }}
  
  TASK: Explain {{ input }} to a beginner.
  
  REQUIREMENTS:
  - Use simple language
  - Include examples
  - Provide analogies
  - Keep under 300 words

# ❌ BAD: Vague, no structure
prompt: "Tell me about {{ input }}"
```

### 3. Error Handling

```yaml
- id: safe_answer
  type: openai-answer
  timeout: 60.0  # Longer timeout for complex tasks
  prompt: |
    {% if previous_outputs.search %}
    Based on: {{ previous_outputs.search }}
    {% else %}
    Using general knowledge only.
    {% endif %}
    
    Answer: {{ input }}
```

### 4. Token Management

```yaml
# Short responses
- id: brief_answer
  type: openai-answer
  max_tokens: 150
  prompt: "Briefly: {{ input }}"

# Long-form content
- id: detailed_answer
  type: openai-answer
  max_tokens: 4000
  model: gpt-4-turbo  # Better for long content
  prompt: "Comprehensively explain: {{ input }}"
```

## Output Format

The agent returns a dictionary with:

```python
{
    "response": "The generated text response",
    "model": "gpt-4o",
    "usage": {
        "prompt_tokens": 120,
        "completion_tokens": 350,
        "total_tokens": 470
    },
    "finish_reason": "stop"  # or "length", "content_filter"
}
```

Access in templates:

```yaml
prompt: |
  Previous answer: {{ previous_outputs.answer_builder.response }}
  Tokens used: {{ previous_outputs.answer_builder.usage.total_tokens }}
```

## Performance Optimization

### Model Selection

```yaml
# High-volume, simple tasks
- id: classifier
  type: openai-answer
  model: gpt-3.5-turbo  # 10x cheaper, 5x faster
  max_tokens: 50

# Critical, complex reasoning
- id: analyzer
  type: openai-answer
  model: gpt-4  # Most accurate
  temperature: 0.2
```

### Caching Strategy

```yaml
# Check memory first
- id: memory_check
  type: memory-reader
  namespace: cached_answers

# Only call LLM if needed
- id: router
  type: router
  params:
    decision_key: memory_check
    routing_map:
      "found": [return_cached]
      "not_found": [llm_answer, cache_result]
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Timeout errors | Complex prompt, slow model | Increase `timeout`, use faster model |
| Token limit exceeded | Response too long | Reduce `max_tokens`, simplify prompt |
| Inconsistent outputs | High temperature | Lower `temperature` to 0.1-0.3 |
| Repetitive text | No penalties | Add `frequency_penalty: 0.5` |
| Incomplete responses | Hit token limit | Increase `max_tokens` or use turbo model |

### Debug Configuration

```yaml
- id: debug_answer
  type: openai-answer
  model: gpt-4o
  temperature: 0.3
  max_tokens: 500
  timeout: 120.0  # Extra time for debugging
  prompt: |
    DEBUG MODE
    Input: {{ input }}
    Context: {{ previous_outputs | tojson }}
    
    Provide detailed answer with reasoning.
```

## Cost Optimization

```yaml
# Use cheaper model for initial draft
- id: draft
  type: openai-answer
  model: gpt-3.5-turbo  # Cheap
  temperature: 0.7
  prompt: "Draft answer: {{ input }}"

# Use expensive model only for refinement
- id: refine
  type: openai-answer
  model: gpt-4  # Expensive but accurate
  temperature: 0.3
  max_tokens: 800
  prompt: "Improve this draft: {{ previous_outputs.draft }}"
```

## Integration Examples

### With Memory

```yaml
- id: memory_search
  type: memory-reader
  namespace: knowledge

- id: answer_with_memory
  type: openai-answer
  model: gpt-4o
  prompt: |
    Relevant memories: {{ previous_outputs.memory_search }}
    Question: {{ input }}
    
    Answer using the memories when relevant.
```

### With Web Search

```yaml
- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"

- id: answer_from_web
  type: openai-answer
  model: gpt-4o
  prompt: |
    Search results: {{ previous_outputs.web_search }}
    Question: {{ input }}
    
    Synthesize a comprehensive answer from the search results.
```

### In Loops

```yaml
- id: iterative_improver
  type: loop
  max_loops: 3
  score_threshold: 0.85
  score_extraction_pattern: "QUALITY:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: improver
        type: openai-answer
        model: gpt-4o
        temperature: 0.5
        prompt: |
          Improve this answer: {{ input }}
          {% if has_past_loops() %}
          Previous attempts: {{ get_past_loops() }}
          {% endif %}
          
          End with: QUALITY: X.XX
```

## Environment Variables

```bash
# Required
export OPENAI_API_KEY=sk-...

# Optional
export OPENAI_ORG_ID=org-...
export OPENAI_API_BASE=https://api.openai.com/v1  # Custom endpoint
```

## Related Documentation

- [OpenAI Binary Agent](./openai-binary.md)
- [OpenAI Classification Agent](./openai-classification.md)
- [Local LLM Agent](./local-llm.md)
- [Loop Node](../nodes/loop.md)
- [Memory Integration](../memory-integration-guide.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.9.0**: Added support for GPT-4o
- **v0.8.0**: Initial release

