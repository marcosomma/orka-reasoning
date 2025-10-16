# OpenAI Classification Agent

**Type:** `openai-classification`  
**Category:** LLM Agent  
**Version:** v0.9.4+

## Overview

The OpenAI Classification Agent uses LLM reasoning to classify input into one of several predefined categories. It's more sophisticated than the deprecated `classification` agent, providing context-aware categorization with confidence scoring.

## Basic Configuration

```yaml
- id: topic_classifier
  type: openai-classification
  model: gpt-4o
  options: [tech, science, business, politics, entertainment]
  prompt: "Classify this text: {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier for the agent |
| `type` | string | Must be `openai-classification` |
| `options` | list[string] | List of possible categories |
| `prompt` | string | Classification instructions |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gpt-4o` | OpenAI model to use |
| `temperature` | float | `0.3` | Low for consistency |
| `system_prompt` | string | - | Context for classification |
| `timeout` | float | `30.0` | Request timeout in seconds |
| `queue` | string | `orka:main` | Processing queue |

## Output Format

Returns one of the predefined options as a string:

```python
{
    "response": "tech",  # One of the options
    "confidence": 0.92,
    "reasoning": "Contains technical terms and code examples..."
}
```

## Usage Examples

### Example 1: Topic Classification

```yaml
- id: topic_classifier
  type: openai-classification
  model: gpt-4o
  temperature: 0.2
  options: [
    "technology",
    "science",
    "health",
    "business",
    "politics",
    "entertainment",
    "sports",
    "other"
  ]
  prompt: |
    Classify the following text into one of the categories.
    Choose the MOST relevant category.
    
    Text: {{ input }}
```

### Example 2: Intent Classification

```yaml
- id: intent_classifier
  type: openai-classification
  model: gpt-4o
  temperature: 0.3
  options: [
    "question",
    "command",
    "complaint",
    "feedback",
    "greeting",
    "farewell"
  ]
  prompt: |
    What is the user's intent?
    
    User message: {{ input }}
    
    Context: {{ previous_outputs.memory_search }}
```

### Example 3: Sentiment Classification

```yaml
- id: sentiment_analyzer
  type: openai-classification
  model: gpt-4o
  temperature: 0.3
  options: ["very_negative", "negative", "neutral", "positive", "very_positive"]
  system_prompt: "You are an expert sentiment analyst."
  prompt: |
    Analyze the sentiment of this text:
    
    {{ input }}
    
    Consider:
    - Emotional tone
    - Word choice
    - Overall message
    - Context clues
```

### Example 4: Priority Classification

```yaml
- id: priority_classifier
  type: openai-classification
  model: gpt-4o
  temperature: 0.2
  options: ["critical", "high", "medium", "low"]
  prompt: |
    Classify the priority level of this support ticket:
    
    Ticket: {{ input }}
    
    Criteria:
    - CRITICAL: System down, data loss, security breach
    - HIGH: Major feature broken, affecting many users
    - MEDIUM: Minor bug, workaround available
    - LOW: Enhancement request, cosmetic issue
```

### Example 5: Content Type Classification

```yaml
- id: content_type
  type: openai-classification
  model: gpt-4o
  temperature: 0.3
  options: [
    "factual_question",
    "how_to_guide",
    "opinion_request",
    "creative_writing",
    "code_help",
    "troubleshooting",
    "general_chat"
  ]
  prompt: |
    What type of content/request is this?
    
    Input: {{ input }}
    
    Choose the category that best describes the user's need.
```

## Routing with Classification

Classification agents are commonly used with routers for conditional logic:

```yaml
- id: intent_classifier
  type: openai-classification
  options: ["question", "command", "feedback"]
  prompt: "{{ input }}"

- id: intent_router
  type: router
  params:
    decision_key: intent_classifier
    routing_map:
      "question": [search_answer, provide_response]
      "command": [execute_command, confirm_action]
      "feedback": [store_feedback, thank_user]
    fallback_route: [general_handler]
```

## Best Practices

### 1. Clear Category Definitions

```yaml
# ✅ GOOD: Well-defined, non-overlapping categories
options: ["bug_report", "feature_request", "question", "documentation"]
prompt: |
  Classify this GitHub issue:
  {{ input }}
  
  Definitions:
  - bug_report: Something is broken or not working
  - feature_request: Request for new functionality
  - question: Asking how to use existing features
  - documentation: Issues with docs or examples

# ❌ BAD: Vague, overlapping categories
options: ["problem", "request", "other"]
```

### 2. Appropriate Number of Categories

```yaml
# ✅ GOOD: 3-10 categories (optimal)
options: ["positive", "negative", "neutral"]

# ⚠️ WARNING: Too many categories (>15) reduces accuracy
options: ["cat1", "cat2", ... "cat20"]  # Hard to distinguish

# Use hierarchical classification instead:
- id: broad_category
  type: openai-classification
  options: ["technology", "non_technology"]

- id: tech_subcategory
  type: openai-classification
  options: ["ai", "cloud", "security", "mobile"]
  # Only runs if broad_category == "technology"
```

### 3. Temperature Settings

```yaml
# Strict classification (consistent results)
- id: strict_classifier
  type: openai-classification
  temperature: 0.0
  options: ["spam", "not_spam"]
  prompt: "{{ input }}"

# Nuanced classification (allow some variation)
- id: nuanced_classifier
  type: openai-classification
  temperature: 0.4
  options: ["urgent", "normal", "low_priority"]
  prompt: "{{ input }}"
```

### 4. Provide Examples

```yaml
- id: classifier_with_examples
  type: openai-classification
  model: gpt-4o
  temperature: 0.2
  options: ["technical", "sales", "support"]
  prompt: |
    Classify this email into one category:
    
    Email: {{ input }}
    
    Examples:
    - "How do I configure SSL?" → technical
    - "What are your pricing options?" → sales
    - "My account is locked" → support
```

## Hierarchical Classification

For complex categorization, use multiple stages:

```yaml
# Stage 1: Broad classification
- id: broad_category
  type: openai-classification
  model: gpt-3.5-turbo  # Fast and cheap
  temperature: 0.2
  options: ["content", "technical", "administrative"]
  prompt: "Broad category for: {{ input }}"

# Stage 2: Detailed classification based on broad category
- id: content_subcategory
  type: openai-classification
  model: gpt-4o
  temperature: 0.3
  options: ["blog_post", "tutorial", "case_study", "news"]
  prompt: |
    This is content-related: {{ input }}
    What specific type of content?

- id: technical_subcategory
  type: openai-classification
  model: gpt-4o
  temperature: 0.3
  options: ["bug", "feature", "optimization", "security"]
  prompt: |
    This is technical: {{ input }}
    What specific type of technical issue?
```

## Multi-Label Classification

For items that can belong to multiple categories:

```yaml
# Approach 1: Multiple binary classifiers
- id: is_urgent
  type: openai-binary
  prompt: "Is this urgent? {{ input }}"

- id: is_technical
  type: openai-binary
  prompt: "Is this technical? {{ input }}"

- id: is_customer_facing
  type: openai-binary
  prompt: "Is this customer-facing? {{ input }}"

# Approach 2: Parse multiple labels from answer
- id: multi_label
  type: openai-answer
  model: gpt-4o
  temperature: 0.2
  prompt: |
    Select ALL applicable labels for: {{ input }}
    
    Available labels:
    - urgent
    - technical
    - customer_facing
    - requires_manager
    - needs_documentation
    
    Return as comma-separated list: label1, label2, label3
```

## Confidence-Based Routing

```yaml
- id: classifier
  type: openai-classification
  options: ["cat_a", "cat_b", "cat_c"]
  prompt: "{{ input }}"

- id: confidence_check
  type: openai-binary
  prompt: |
    Classification: {{ previous_outputs.classifier }}
    Confidence: {{ previous_outputs.classifier.confidence }}
    
    Is confidence > 0.8?

- id: router
  type: router
  params:
    decision_key: confidence_check
    routing_map:
      "true": [process_classification]
      "false": [human_review]
```

## Performance Optimization

### Model Selection

```yaml
# Simple, well-defined categories - use cheap model
- id: simple_classifier
  type: openai-classification
  model: gpt-3.5-turbo  # 10x cheaper
  options: ["spam", "not_spam"]
  prompt: "{{ input }}"

# Complex, nuanced categories - use advanced model
- id: complex_classifier
  type: openai-classification
  model: gpt-4  # More accurate
  options: ["satire", "news", "opinion", "analysis", "editorial"]
  prompt: "{{ input }}"
```

### Caching Classifications

```yaml
- id: check_cache
  type: memory-reader
  namespace: classifications
  params:
    similarity_threshold: 0.95
  prompt: "{{ input }}"

- id: classify_or_cache
  type: router
  params:
    decision_key: check_cache
    routing_map:
      "found": [return_cached]
      "not_found": [classify, cache_result]

- id: classify
  type: openai-classification
  options: ["cat1", "cat2", "cat3"]
  prompt: "{{ input }}"

- id: cache_result
  type: memory-writer
  namespace: classifications
  params:
    vector: true
  prompt: "{{ input }}: {{ previous_outputs.classify }}"
```

## Error Handling

```yaml
- id: safe_classifier
  type: failover
  children:
    # Primary: LLM classification
    - id: llm_classifier
      type: openai-classification
      model: gpt-4o
      options: ["cat1", "cat2", "cat3"]
      prompt: "{{ input }}"
      timeout: 15.0
    
    # Fallback: Simple rule-based
    - id: rule_classifier
      type: classification  # Legacy agent
      options: ["cat1", "cat2", "cat3"]
      prompt: "{{ input }}"
```

## Integration Examples

### With Memory for Context

```yaml
- id: memory_context
  type: memory-reader
  namespace: user_history
  prompt: "{{ input }}"

- id: contextual_classifier
  type: openai-classification
  model: gpt-4o
  options: ["returning_issue", "new_question", "followup"]
  prompt: |
    User history: {{ previous_outputs.memory_context }}
    Current message: {{ input }}
    
    Classify based on context and history.
```

### With Loops for Confidence Building

```yaml
- id: classification_loop
  type: loop
  max_loops: 3
  score_threshold: 0.9
  score_extraction_pattern: "CONFIDENCE:\\s*([0-9.]+)"
  internal_workflow:
    agents:
      - id: classifier
        type: openai-classification
        options: ["cat1", "cat2", "cat3"]
        prompt: "{{ input }}"
      
      - id: confidence_scorer
        type: openai-answer
        prompt: |
          Classification: {{ previous_outputs.classifier }}
          
          How confident (0.0-1.0)?
          Output: CONFIDENCE: X.XX
```

## Comparison: openai-classification vs classification

| Feature | `openai-classification` | `classification` (deprecated) |
|---------|------------------------|-------------------------------|
| Reasoning | LLM-powered | Rule-based |
| Context | Understands nuance | Simple pattern matching |
| Accuracy | High | Low to medium |
| Speed | Slower (API) | Fast (local) |
| Cost | Per call | Free |
| Status | ✅ Recommended | ⚠️ Deprecated |

## Advanced Example: Multi-Criteria Classification

```yaml
- id: advanced_classifier
  type: openai-classification
  model: gpt-4
  temperature: 0.2
  options: [
    "critical_bug",
    "normal_bug",
    "feature_request",
    "enhancement",
    "question",
    "documentation",
    "duplicate",
    "wont_fix"
  ]
  system_prompt: |
    You are an expert issue triager for a software project.
    Consider severity, impact, and type when classifying.
  prompt: |
    GitHub Issue:
    Title: {{ input.title }}
    Body: {{ input.body }}
    Labels: {{ input.labels }}
    Comments: {{ input.comments }}
    
    Classification criteria:
    
    CRITICAL_BUG:
    - System crashes
    - Data loss
    - Security vulnerability
    - Affects all users
    
    NORMAL_BUG:
    - Feature doesn't work as expected
    - Limited user impact
    - Workaround available
    
    FEATURE_REQUEST:
    - New functionality
    - Doesn't exist yet
    - Clear use case
    
    ENHANCEMENT:
    - Improves existing feature
    - Nice to have
    - Quality of life improvement
    
    QUESTION:
    - "How do I...?"
    - Seeking clarification
    - Not an issue
    
    DOCUMENTATION:
    - Docs are wrong/missing
    - Examples needed
    - Clarification required
    
    DUPLICATE:
    - Already reported
    - Existing issue addresses this
    
    WONT_FIX:
    - By design
    - Out of scope
    - Not feasible
    
    Return the single best category.
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Inconsistent results | High temperature | Lower to 0.1-0.3 |
| Wrong category chosen | Unclear options | Add definitions and examples |
| "other" chosen too often | Categories don't cover input | Add more options or revise |
| Slow classification | Heavy model | Use gpt-3.5-turbo |
| Low confidence | Ambiguous input | Add context or use hierarchical |

## Environment Variables

```bash
# Required
export OPENAI_API_KEY=sk-...

# Optional
export OPENAI_ORG_ID=org-...
```

## Related Documentation

- [OpenAI Binary Agent](./openai-binary.md)
- [OpenAI Answer Agent](./openai-answer.md)
- [Classification Agent (Deprecated)](./classification.md)
- [Router Node](../nodes/router.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.5.6**: Replaced deprecated `classification` agent
- **v0.5.0**: Initial release

