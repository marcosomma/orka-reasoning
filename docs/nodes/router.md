# Router Node

**Type:** `router`  
**Category:** Control Flow Node  
**Version:** v0.9.4+

## Overview

The Router Node dynamically routes execution to different agent paths based on previous agent outputs, enabling conditional workflow logic and decision trees.

## Basic Configuration

```yaml
- id: content_router
  type: router
  params:
    decision_key: classifier
    routing_map:
      "question": [search, answer]
      "command": [execute, confirm]
      "feedback": [store, thank]
```

## Parameters

### Required Parameters (in `params`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `decision_key` | string | Agent ID whose output determines routing |
| `routing_map` | object | Map of values to agent lists |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fallback_route` | list | `[]` | Default route if no match |
| `timeout` | float | `10.0` | Routing timeout |

## Usage Examples

### Example 1: Intent-Based Routing

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
      "command": [validate_command, execute_action]
      "feedback": [store_feedback, send_thanks]
    fallback_route: [general_handler]
```

### Example 2: Binary Decision Routing

```yaml
- id: needs_search
  type: openai-binary
  prompt: "Needs web search? {{ input }}"

- id: search_router
  type: router
  params:
    decision_key: needs_search
    routing_map:
      "true": [web_search, answer_from_web]
      "false": [answer_from_memory]
```

### Example 3: Multi-Stage Routing

```yaml
- id: stage1_classifier
  type: openai-classification
  options: ["technical", "business", "general"]
  prompt: "{{ input }}"

- id: stage1_router
  type: router
  params:
    decision_key: stage1_classifier
    routing_map:
      "technical": [technical_subcategory]
      "business": [business_subcategory]
      "general": [general_handler]

- id: technical_subcategory
  type: openai-classification
  options: ["bug", "feature", "question"]
  prompt: "{{ input }}"

- id: stage2_router
  type: router
  params:
    decision_key: technical_subcategory
    routing_map:
      "bug": [bug_handler, notify_team]
      "feature": [feature_validator, roadmap_check]
      "question": [docs_search, provide_answer]
```

### Example 4: Quality Gates

```yaml
- id: quality_check
  type: openai-binary
  prompt: "Quality sufficient? {{ previous_outputs.answer }}"

- id: quality_gate
  type: router
  params:
    decision_key: quality_check
    routing_map:
      "true": [publish, notify_success]
      "false": [improve_content, recheck]
```

### Example 5: Priority Routing

```yaml
- id: priority_classifier
  type: openai-classification
  options: ["critical", "high", "normal", "low"]
  prompt: "{{ input }}"

- id: priority_router
  type: router
  params:
    decision_key: priority_classifier
    routing_map:
      "critical": [immediate_action, alert_team, escalate]
      "high": [schedule_soon, assign_lead]
      "normal": [queue_normal, auto_assign]
      "low": [queue_backlog]
    fallback_route: [triage_manually]
```

## Complex Routing Patterns

### Nested Routing

```yaml
# Level 1: Content type
- id: content_type
  type: openai-classification
  options: ["text", "code", "data"]
  prompt: "{{ input }}"

- id: level1_router
  type: router
  params:
    decision_key: content_type
    routing_map:
      "text": [text_handler]
      "code": [code_handler]
      "data": [data_handler]

# Level 2: Text-specific routing
- id: text_sentiment
  type: openai-classification
  options: ["positive", "negative", "neutral"]
  prompt: "{{ input }}"

- id: text_router
  type: router
  params:
    decision_key: text_sentiment
    routing_map:
      "positive": [thank_user, store_testimonial]
      "negative": [escalate_issue, apologize]
      "neutral": [standard_response]
```

### Confidence-Based Routing

```yaml
- id: classifier
  type: openai-classification
  options: ["cat_a", "cat_b", "cat_c"]
  prompt: "{{ input }}"

- id: confidence_evaluator
  type: openai-binary
  prompt: |
    Classification: {{ previous_outputs.classifier }}
    Confidence: {{ previous_outputs.classifier.confidence }}
    Is confidence > 0.85?

- id: confidence_router
  type: router
  params:
    decision_key: confidence_evaluator
    routing_map:
      "true": [proceed_with_classification]
      "false": [manual_review, request_clarification]
```

## Best Practices

### 1. Clear Routing Logic

```yaml
# ✅ GOOD: Explicit, documented routing
- id: well_documented_router
  type: router
  params:
    decision_key: user_intent
    routing_map:
      "buy": [product_search, show_pricing, checkout_flow]
      "support": [ticket_create, assign_agent]
      "info": [faq_search, provide_details]
    fallback_route: [ask_clarification]

# ❌ BAD: Unclear routing
- id: confusing_router
  type: router
  params:
    decision_key: something
    routing_map:
      "a": [x, y]
      "b": [z]
```

### 2. Always Provide Fallback

```yaml
# ✅ GOOD: Has fallback for unexpected values
params:
  routing_map:
    "known_value_1": [handler1]
    "known_value_2": [handler2]
  fallback_route: [default_handler, log_unknown]

# ❌ BAD: No fallback (will error on unexpected value)
params:
  routing_map:
    "value1": [handler1]
    "value2": [handler2]
```

### 3. Validate Decision Values

```yaml
# Ensure decision_key agent returns expected values
- id: classifier
  type: openai-classification
  options: ["option_a", "option_b", "option_c"]  # Must match routing_map keys
  prompt: "{{ input }}"

- id: router
  type: router
  params:
    decision_key: classifier
    routing_map:
      "option_a": [handler_a]
      "option_b": [handler_b]
      "option_c": [handler_c]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No route taken | Decision value doesn't match keys | Add fallback_route or fix decision values |
| Wrong path taken | Decision_key refers to wrong agent | Verify agent ID |
| Router crashes | Missing routing_map | Add routing_map parameter |
| "true"/"false" not working | String case mismatch | Use lowercase: "true", "false" |

## Integration Patterns

### With Memory Validation

```yaml
- id: memory_search
  type: memory-reader
  namespace: knowledge
  prompt: "{{ input }}"

- id: memory_validator
  type: openai-binary
  prompt: "Sufficient? {{ previous_outputs.memory_search }}"

- id: route_by_memory
  type: router
  params:
    decision_key: memory_validator
    routing_map:
      "true": [answer_from_memory]
      "false": [web_search, answer_from_web, store_new_knowledge]
```

### With Parallel Processing

```yaml
- id: complexity_check
  type: openai-classification
  options: ["simple", "complex"]
  prompt: "{{ input }}"

- id: complexity_router
  type: router
  params:
    decision_key: complexity_check
    routing_map:
      "simple": [quick_answer]
      "complex": [fork_analysis, join_results, comprehensive_answer]

- id: fork_analysis
  type: fork
  targets:
    - [research_agent]
    - [analysis_agent]
    - [validation_agent]
```

### With Loops

```yaml
- id: quality_loop
  type: loop
  max_loops: 5
  score_threshold: 0.9
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    agents: [improver, scorer]

- id: final_quality_check
  type: openai-binary
  prompt: "Meets standards? {{ previous_outputs.quality_loop }}"

- id: publish_router
  type: router
  params:
    decision_key: final_quality_check
    routing_map:
      "true": [publish, notify_success]
      "false": [manual_review]
```

## Advanced Example: Multi-Criteria Routing

```yaml
orchestrator:
  id: smart-routing-system
  strategy: sequential
  agents: [analyze_request, priority_router]

agents:
  - id: analyze_request
    type: openai-answer
    model: gpt-4o
    temperature: 0.2
    prompt: |
      Analyze this request and provide routing decision:
      {{ input }}
      
      Consider:
      - Urgency (critical, high, normal, low)
      - Type (technical, business, support, sales)
      - Complexity (simple, moderate, complex)
      - User tier (enterprise, pro, free)
      
      Output format:
      URGENCY: <level>
      TYPE: <type>
      COMPLEXITY: <level>
      TIER: <tier>
      ROUTE_TO: <destination>

  - id: extract_route
    type: openai-classification
    options: [
      "enterprise_technical",
      "enterprise_business",
      "priority_support",
      "standard_queue",
      "self_service",
      "sales_team"
    ]
    prompt: |
      Based on analysis:
      {{ previous_outputs.analyze_request }}
      
      Choose best route.

  - id: priority_router
    type: router
    params:
      decision_key: extract_route
      routing_map:
        "enterprise_technical": [
          assign_senior_engineer,
          sla_4hour,
          notify_account_manager
        ]
        "enterprise_business": [
          route_to_csm,
          schedule_meeting,
          prepare_report
        ]
        "priority_support": [
          assign_support_lead,
          sla_24hour
        ]
        "standard_queue": [
          auto_assign,
          sla_72hour
        ]
        "self_service": [
          knowledge_base_search,
          suggested_articles,
          feedback_form
        ]
        "sales_team": [
          lead_qualification,
          route_to_sales,
          schedule_demo
        ]
      fallback_route: [manual_triage, alert_supervisor]
```

## Related Documentation

- [OpenAI Classification Agent](../agents/openai-classification.md)
- [OpenAI Binary Agent](../agents/openai-binary.md)
- [Fork Node](./fork.md)
- [Failover Node](./failover.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.7.0**: Added fallback_route
- **v0.5.0**: Initial release

