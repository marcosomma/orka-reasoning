# Validate and Structure Agent

**Type:** `validate_and_structure`  
**Category:** Validation Agent  
**Version:** v0.9.4+

## Overview

The Validate and Structure Agent validates answers for correctness and structures them into memory objects with metadata and schema validation.

## Basic Configuration

```yaml
- id: validator
  type: validate_and_structure
  model: gpt-4o-mini
  prompt: "Validate: {{ previous_outputs.answer }}"
  store_structure: |
    {
      "topic": "main topic",
      "confidence": "0.0-1.0",
      "key_points": ["point1", "point2"]
    }
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Unique identifier |
| `type` | string | Must be `validate_and_structure` |
| `prompt` | string | Validation instructions |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `gpt-4o-mini` | OpenAI model |
| `store_structure` | string | - | JSON schema template |
| `schema` | object | - | JSON schema for validation |
| `temperature` | float | `0.2` | Low for consistency |
| `timeout` | float | `30.0` | Processing timeout |

## Usage Examples

### Example 1: Answer Validation

```yaml
- id: answer_validator
  type: validate_and_structure
  model: gpt-4o-mini
  temperature: 0.1
  prompt: |
    Validate this answer:
    Question: {{ input }}
    Answer: {{ previous_outputs.answer }}
    
    Check for:
    - Accuracy
    - Completeness
    - Relevance
    - Citations
  store_structure: |
    {
      "is_valid": true/false,
      "confidence": 0.0-1.0,
      "issues": ["list of problems"],
      "approved_for_storage": true/false
    }
```

### Example 2: Structured Memory Storage

```yaml
- id: structure_for_memory
  type: validate_and_structure
  model: gpt-4o-mini
  prompt: |
    Structure this interaction for long-term memory:
    
    User: {{ input }}
    Response: {{ previous_outputs.answer }}
    Context: {{ previous_outputs.search }}
  store_structure: |
    {
      "summary": "one sentence summary",
      "topic": "main topic",
      "keywords": ["keyword1", "keyword2"],
      "confidence": 0.85,
      "metadata": {
        "sources": ["source1", "source2"],
        "validated": true,
        "timestamp": "{{ now() }}"
      }
    }
```

### Example 3: Quality Assurance

```yaml
- id: qa_validator
  type: validate_and_structure
  model: gpt-4
  temperature: 0.1
  schema:
    type: object
    properties:
      passes_qa: { type: boolean }
      quality_score: { type: number, minimum: 0, maximum: 1 }
      issues_found: { type: array, items: { type: string } }
      recommendations: { type: array, items: { type: string } }
    required: ["passes_qa", "quality_score"]
  prompt: |
    Quality assurance check:
    {{ previous_outputs.content }}
    
    Validate against quality standards.
```

## Output Format

Returns structured JSON matching the schema:

```python
{
    "response": {
        "topic": "AI orchestration",
        "confidence": 0.92,
        "key_points": ["YAML config", "Memory system", "Agent types"],
        "metadata": {
            "validated": true,
            "timestamp": "2025-10-16T12:00:00Z"
        }
    },
    "validation_passed": true
}
```

## Integration with Memory

```yaml
- id: structure_data
  type: validate_and_structure
  prompt: "Structure: {{ previous_outputs.answer }}"
  store_structure: |
    {
      "content": "{{ previous_outputs.answer }}",
      "metadata": { "validated": true }
    }

- id: store_structured
  type: memory-writer
  namespace: validated_knowledge
  params:
    vector: true
  prompt: "{{ previous_outputs.structure_data.response | tojson }}"
```

## Related Documentation

- [Memory Writer Node](../nodes/memory-writer.md)
- [OpenAI Answer Agent](./openai-answer.md)

## Version History

- **v0.9.4**: Current stable version
- **v0.6.0**: Initial release

