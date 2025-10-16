# Binary Agent

**Type:** `binary`  
**Category:** Simple Decision Agent  
**Version:** v0.9.4+

## Overview

The Binary Agent performs simple, rule-based true/false decisions without LLM inference. It's fast, free, and suitable for pattern matching and basic conditional logic.

**Note:** For complex reasoning, use [`openai-binary`](./openai-binary.md) instead.

## Basic Configuration

```yaml
- id: has_email
  type: binary
  prompt: "Contains email? {{ input }}"
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier |
| `type` | string | Must be `binary` |
| `prompt` | string | Question to evaluate |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | float | `10.0` | Processing timeout |
| `queue` | string | `orka:main` | Processing queue |

## Output Format

Returns a string: `"true"` or `"false"`

```python
{
    "response": "true"  # or "false"
}
```

## Usage Examples

### Example 1: Pattern Matching

```yaml
- id: contains_keyword
  type: binary
  prompt: "Contains 'urgent'? {{ input }}"

- id: has_url
  type: binary
  prompt: "Contains http:// or https://? {{ input }}"

- id: is_question
  type: binary
  prompt: "Ends with question mark? {{ input }}"
```

### Example 2: Simple Routing

```yaml
- id: is_empty
  type: binary
  prompt: "Is input empty? {{ input }}"

- id: router
  type: router
  params:
    decision_key: is_empty
    routing_map:
      "true": [handle_empty]
      "false": [process_input]
```

### Example 3: Length Check

```yaml
- id: is_long
  type: binary
  prompt: "Is length > 1000 characters? {{ input }}"
```

## When to Use Binary vs OpenAI-Binary

| Use Case | Use `binary` | Use `openai-binary` |
|----------|--------------|---------------------|
| Pattern matching | ✅ | ❌ |
| Keyword detection | ✅ | ❌ |
| Length checks | ✅ | ❌ |
| Format validation | ✅ | ❌ |
| Complex reasoning | ❌ | ✅ |
| Context understanding | ❌ | ✅ |
| Nuanced decisions | ❌ | ✅ |
| Quality assessment | ❌ | ✅ |

## Best Practices

```yaml
# ✅ GOOD: Simple, objective checks
- id: has_data
  type: binary
  prompt: "Has data? {{ previous_outputs.search }}"

# ❌ BAD: Complex reasoning (use openai-binary instead)
- id: is_appropriate
  type: binary
  prompt: "Is this content appropriate for children? {{ input }}"
```

## Performance

- **Speed:** Instant (no API calls)
- **Cost:** Free
- **Reliability:** 100% deterministic

## Limitations

- No context understanding
- No semantic reasoning
- Simple pattern matching only
- Limited to basic conditionals

## Related Documentation

- [OpenAI Binary Agent](./openai-binary.md) - For complex decisions
- [Router Node](../nodes/router.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.1.0**: Initial release

