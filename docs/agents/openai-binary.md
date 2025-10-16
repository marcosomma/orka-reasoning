# OpenAI Binary Agent

**Type:** `openai-binary`  
**Category:** LLM Agent  
**Version:** v0.9.4+

## Overview

The OpenAI Binary Agent performs sophisticated true/false decisions using OpenAI's language models. Unlike the simple `binary` agent, this agent uses LLM reasoning to understand context, nuance, and complex criteria for binary classification.

## Basic Configuration

```yaml
- id: content_safe
  type: openai-binary
  model: gpt-4o
  prompt: "Is this content appropriate for work? {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier for the agent |
| `type` | string | Must be `openai-binary` |
| `prompt` | string | Question to evaluate as true/false |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gpt-4o` | OpenAI model to use |
| `temperature` | float | `0.2` | Low for consistency |
| `system_prompt` | string | - | Context for decision-making |
| `timeout` | float | `30.0` | Request timeout in seconds |
| `queue` | string | `orka:main` | Processing queue |

## Output Format

Returns a string: `"true"` or `"false"` (lowercase strings)

```python
{
    "response": "true",  # or "false"
    "reasoning": "Content is professional and appropriate...",
    "confidence": 0.95
}
```

## Usage Examples

### Example 1: Content Moderation

```yaml
- id: is_safe
  type: openai-binary
  model: gpt-4o
  temperature: 0.1  # Very consistent
  prompt: |
    Is this content safe for all audiences?
    
    Content: {{ input }}
    
    Consider:
    - Profanity or offensive language
    - Violence or disturbing imagery
    - Adult themes
    - Discriminatory content
    
    Answer: true (safe) or false (unsafe)
```

### Example 2: Quality Assessment

```yaml
- id: meets_quality
  type: openai-binary
  model: gpt-4o
  temperature: 0.2
  prompt: |
    Does this answer meet quality standards?
    
    Answer: {{ previous_outputs.answer }}
    Original Question: {{ input }}
    
    Quality criteria:
    - Accurate information
    - Complete response
    - Clear explanation
    - Proper citations
    
    Return true if ALL criteria are met, false otherwise.
```

### Example 3: Fact Verification

```yaml
- id: is_factual
  type: openai-binary
  model: gpt-4
  temperature: 0.1
  system_prompt: "You are a fact-checker with access to extensive knowledge."
  prompt: |
    Is this statement factually accurate?
    
    Statement: {{ input }}
    
    Verify against known facts. Return true only if definitely accurate.
```

### Example 4: Classification Decision

```yaml
- id: needs_web_search
  type: openai-binary
  model: gpt-4o
  temperature: 0.2
  prompt: |
    Does answering this question require current web information?
    
    Question: {{ input }}
    Memory found: {{ previous_outputs.memory_search }}
    
    Return true if:
    - Question is about recent events
    - Memory is insufficient
    - Current data needed
    
    Return false if memory contains sufficient information.
```

### Example 5: Sentiment Analysis

```yaml
- id: is_positive
  type: openai-binary
  model: gpt-4o
  temperature: 0.3
  prompt: |
    Is the sentiment of this text positive?
    
    Text: {{ input }}
    
    Consider overall tone, word choice, and emotional content.
    Return true for positive, false for negative or neutral.
```

## Routing Based on Binary Decision

Binary agents are commonly used with routers:

```yaml
- id: quality_check
  type: openai-binary
  prompt: "Is this high quality? {{ input }}"

- id: quality_router
  type: router
  params:
    decision_key: quality_check
    routing_map:
      "true": [publish, notify_success]
      "false": [improve, recheck]
```

## Best Practices

### 1. Clear Decision Criteria

```yaml
# ✅ GOOD: Specific criteria
prompt: |
  Is this code production-ready?
  
  Code: {{ input }}
  
  Check:
  ✓ No syntax errors
  ✓ Has error handling
  ✓ Includes comments
  ✓ Follows style guide
  
  Return true ONLY if all checks pass.

# ❌ BAD: Vague criteria
prompt: "Is this code good? {{ input }}"
```

### 2. Temperature Settings

```yaml
# Strict, consistent decisions
- id: rule_check
  type: openai-binary
  temperature: 0.0  # Absolutely consistent
  prompt: "Does this violate policy X? {{ input }}"

# Balanced judgment
- id: quality_assess
  type: openai-binary
  temperature: 0.3  # Allow some nuance
  prompt: "Is this well-written? {{ input }}"
```

### 3. Provide Context

```yaml
# Include relevant context
- id: is_relevant
  type: openai-binary
  model: gpt-4o
  prompt: |
    Context: {{ previous_outputs.topic }}
    User query: {{ input }}
    
    Is this query relevant to the context?
    
    Background information:
    {{ previous_outputs.memory_search }}
```

### 4. Handle Edge Cases

```yaml
- id: safe_binary_check
  type: openai-binary
  prompt: |
    Question: {{ input }}
    
    If uncertain, err on the side of caution and return false.
    Only return true if you are confident.
```

## Multi-Stage Decision Making

```yaml
# Stage 1: Quick initial check
- id: preliminary_check
  type: openai-binary
  model: gpt-3.5-turbo  # Fast and cheap
  temperature: 0.2
  prompt: "Quick check: Is this obviously spam? {{ input }}"

# Stage 2: Detailed analysis (only if needed)
- id: detailed_check
  type: openai-binary
  model: gpt-4  # More thorough
  temperature: 0.1
  prompt: |
    Detailed analysis required.
    Content: {{ input }}
    Preliminary result: {{ previous_outputs.preliminary_check }}
    
    Perform comprehensive spam detection.
```

## Complex Boolean Logic

### AND Logic (All Must Be True)

```yaml
- id: check_grammar
  type: openai-binary
  prompt: "Is grammar correct? {{ input }}"

- id: check_length
  type: openai-binary
  prompt: "Is length appropriate (100-500 words)? {{ input }}"

- id: check_tone
  type: openai-binary
  prompt: "Is tone professional? {{ input }}"

# Combine with router
- id: all_checks_router
  type: router
  params:
    decision_key: check_grammar
    routing_map:
      "true": [check_length_router]
      "false": [reject]
```

### OR Logic (Any Can Be True)

```yaml
- id: needs_update
  type: openai-binary
  prompt: |
    Does this content need updating for ANY of these reasons?
    - Outdated information
    - Broken links
    - Deprecated references
    - New developments available
    
    Content: {{ input }}
```

## Performance Optimization

### Model Selection

```yaml
# Simple decisions - use cheap model
- id: simple_check
  type: openai-binary
  model: gpt-3.5-turbo  # 10x cheaper
  prompt: "Is this English text? {{ input }}"

# Complex reasoning - use advanced model
- id: complex_check
  type: openai-binary
  model: gpt-4  # More accurate
  prompt: |
    Complex ethical assessment...
    {{ input }}
```

### Caching Decisions

```yaml
# Cache common decisions in memory
- id: cached_check
  type: memory-reader
  namespace: binary_decisions
  params:
    similarity_threshold: 0.95  # Exact matches
  prompt: "{{ input }}"

- id: router
  type: router
  params:
    decision_key: cached_check
    routing_map:
      "found": [return_cached]
      "not_found": [compute_binary, cache_result]

- id: compute_binary
  type: openai-binary
  prompt: "{{ input }}"

- id: cache_result
  type: memory-writer
  namespace: binary_decisions
  prompt: "{{ input }}: {{ previous_outputs.compute_binary }}"
```

## Error Handling

```yaml
- id: safe_binary
  type: failover
  children:
    - id: primary_check
      type: openai-binary
      model: gpt-4o
      prompt: "{{ input }}"
      timeout: 15.0
    
    - id: fallback_check
      type: binary  # Simple rule-based fallback
      prompt: "{{ input }}"
```

## Integration Patterns

### With Classification

```yaml
# First classify, then validate
- id: classifier
  type: openai-classification
  options: [spam, phishing, legitimate]
  prompt: "{{ input }}"

- id: validate_classification
  type: openai-binary
  prompt: |
    Classification: {{ previous_outputs.classifier }}
    Content: {{ input }}
    
    Is this classification correct?
```

### With Loops

```yaml
- id: quality_loop
  type: loop
  max_loops: 5
  score_threshold: 0.9
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: improver
        type: openai-answer
        prompt: "Improve: {{ input }}"
      
      - id: quality_gate
        type: openai-binary
        prompt: |
          Is this good enough?
          {{ previous_outputs.improver }}
          
          Return true to continue, false to stop and refine.
```

### With Memory Validation

```yaml
- id: memory_search
  type: memory-reader
  namespace: facts

- id: verify_memory
  type: openai-binary
  prompt: |
    Retrieved from memory: {{ previous_outputs.memory_search }}
    
    Is this information:
    1. Still accurate?
    2. Complete enough to answer?
    3. Not outdated?
    
    Return true only if ALL conditions met.

- id: router
  type: router
  params:
    decision_key: verify_memory
    routing_map:
      "true": [use_memory]
      "false": [search_web]
```

## Comparison: openai-binary vs binary

| Feature | `openai-binary` | `binary` |
|---------|-----------------|----------|
| Reasoning | LLM-powered | Rule-based |
| Context understanding | Yes | No |
| Complexity handling | High | Low |
| Speed | Slower (API call) | Fast (local) |
| Cost | Per call | Free |
| Use case | Complex decisions | Simple checks |

### When to Use Each

```yaml
# Use openai-binary for complex reasoning
- id: ethical_check
  type: openai-binary
  prompt: "Is this ethically acceptable? {{ input }}"

# Use binary for simple pattern matching
- id: has_email
  type: binary
  prompt: "Contains email address? {{ input }}"
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Inconsistent results | High temperature | Set `temperature: 0.0-0.2` |
| Wrong decisions | Vague criteria | Add specific checklist in prompt |
| Slow responses | Heavy model | Use `gpt-3.5-turbo` for simple tasks |
| "true"/"false" not recognized | Format issues | Check router `decision_key` |

## Advanced Example: Multi-Criteria Gate

```yaml
- id: publication_ready
  type: openai-binary
  model: gpt-4
  temperature: 0.1
  system_prompt: |
    You are a publication quality assurance system.
    You must verify ALL criteria before approving.
  prompt: |
    Article: {{ input }}
    
    QUALITY CHECKLIST:
    
    Content Quality:
    [ ] Accurate information
    [ ] Properly cited sources
    [ ] Clear explanations
    [ ] No plagiarism
    
    Technical Quality:
    [ ] Proper grammar
    [ ] Consistent formatting
    [ ] Working links
    [ ] Appropriate length (800-2000 words)
    
    SEO/Metadata:
    [ ] Title optimized
    [ ] Meta description present
    [ ] Keywords included
    [ ] Images have alt text
    
    Legal/Ethical:
    [ ] No copyright violations
    [ ] Proper attributions
    [ ] Privacy compliant
    [ ] No misleading claims
    
    Return true ONLY if ALL items are checked.
    If ANY item fails, return false and explain which failed.
```

## Environment Variables

```bash
# Required
export OPENAI_API_KEY=sk-...

# Optional
export OPENAI_ORG_ID=org-...
```

## Related Documentation

- [Binary Agent (Simple)](./binary.md)
- [OpenAI Classification Agent](./openai-classification.md)
- [Router Node](../nodes/router.md)
- [Failover Node](../nodes/failover.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.8.0**: Initial release

