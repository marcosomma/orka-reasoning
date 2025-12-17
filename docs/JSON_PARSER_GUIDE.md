# Robust JSON Parsing for LLM Outputs

**Version:** 1.0.0  
**Status:** Stable — production criteria defined  

Assumptions: The parser handles common LLM formatting issues; does not guarantee correction of all malformed responses. Proof: `tests/unit/utils/test_json_parser.py` and related integration tests.
**Last Updated:** November 22, 2025

## Overview

OrKa v1.0.0 introduces a robust JSON parsing system designed to handle common LLM output formats. This system aims to provide robust handling; see 'Assumptions & Coverage' for limits and required validation steps:

- **Automatic JSON repair** for common syntax errors
- **Schema validation** with detailed error messages
- **Type coercion** to match expected formats
- **Multiple fallback strategies** for resilience
- **Comprehensive error tracking** for debugging

## The Problem

LLM responses are inherently unpredictable and may contain:

- **Malformed JSON**: Trailing commas, missing quotes, Python-style syntax
- **Mixed formats**: JSON embedded in markdown, reasoning tags, or plain text
- **Type mismatches**: Strings instead of numbers, inconsistent boolean formats
- **Schema violations**: Missing required fields, unexpected structures

Previously, these issues could silently break validation or scoring pipelines. The new system provides defensive handling for all these scenarios.

## Key Features

### 1. Automatic JSON Extraction

The parser can extract JSON from various text formats:

```python
from orka.utils.json_parser import parse_llm_json

# Handles markdown code blocks
response = """
Here's the result:
```json
{"response": "test", "confidence": 0.9}
```
"""
result = parse_llm_json(response)
# → {"response": "test", "confidence": 0.9}

# Handles reasoning tags
response = """
<think>Let me analyze this...</think>
{"response": "answer"}
"""
result = parse_llm_json(response)
# → {"response": "answer"}
```

### 2. Schema Validation

Validate LLM outputs against expected structures:

```python
from orka.utils.json_parser import parse_llm_json, create_standard_schema

# Define expected schema
schema = create_standard_schema(
    required_fields=["response", "confidence"],
    optional_fields={"internal_reasoning": "string"}
)

# Parse with validation
result = parse_llm_json(
    llm_response,
    schema=schema,
    strict=True  # Raise exception on validation failure
)
```

### 3. Type Coercion

Automatically fix type mismatches:

```python
# LLM returns confidence as string
response = '{"response": "test", "confidence": "0.95"}'

schema = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "confidence": {"type": "number"}
    }
}

result = parse_llm_json(response, schema=schema, coerce_types=True)
# → {"response": "test", "confidence": 0.95}
#    Note: confidence is now a float, not a string
```

### 4. Error Tracking

Track parsing failures for monitoring:

```python
result = parse_llm_json(
    llm_response,
    track_errors=True,
    agent_id="my_agent",
    strict=False  # Don't raise, return fallback
)

if "error" in result:
    print(f"Parsing failed: {result['message']}")
    print(f"Strategies attempted: {result['strategies_attempted']}")
```

### 5. Actionable Error Messages

When parsing fails, you get detailed context:

```python
from orka.utils.json_parser import JSONParseError

try:
    result = parse_llm_json(bad_json, strict=True)
except JSONParseError as e:
    print(f"Error type: {e.error_type}")
    print(f"Attempted fixes: {e.attempted_fixes}")
    print(f"Original text: {e.original_text}")
    print(f"Schema errors: {e.schema_errors}")
```

## API Reference

### `parse_llm_json(text, schema=None, strict=False, coerce_types=True, default=None, track_errors=False, agent_id="unknown")`

Main entry point for parsing LLM JSON responses.

**Parameters:**

- `text` (str): Raw text from LLM
- `schema` (dict, optional): JSONSchema to validate against
- `strict` (bool): If True, raise exception on failure (default: False)
- `coerce_types` (bool): Attempt to fix type mismatches (default: True)
- `default` (dict, optional): Fallback value if parsing fails
- `track_errors` (bool): Log detailed error information (default: False)
- `agent_id` (str): Agent ID for error tracking (default: "unknown")

**Returns:** Parsed JSON as dictionary

**Raises:** `JSONParseError` if strict=True and parsing fails

### `create_standard_schema(required_fields=None, optional_fields=None)`

Create a standard JSONSchema for common LLM response patterns.

**Parameters:**

- `required_fields` (list): Required field names (default: ["response"])
- `optional_fields` (dict): Optional field names to types (default: {"confidence": "number", "internal_reasoning": "string"})

**Returns:** JSONSchema dictionary

### `validate_and_coerce(data, schema, coerce_types=True, strict=False)`

Validate JSON data against schema and optionally coerce types.

**Parameters:**

- `data` (dict): Parsed JSON data
- `schema` (dict): JSONSchema specification
- `coerce_types` (bool): Attempt to fix type mismatches (default: True)
- `strict` (bool): If True, raise exception on validation failure (default: False)

**Returns:** Validated (and potentially coerced) data

**Raises:** `JSONParseError` if strict=True and validation fails

## Integration Guide

### For Agent Developers

If you're creating a new agent that parses LLM responses:

```python
from orka.agents.base_agent import BaseAgent
from orka.utils.json_parser import parse_llm_json, create_standard_schema

class MyAgent(BaseAgent):
    async def _run_impl(self, ctx):
        # Call your LLM
        llm_response = await self.call_llm(prompt)
        
        # Define expected schema
        schema = create_standard_schema(
            required_fields=["response", "action"],
            optional_fields={"confidence": "number"}
        )
        
        # Parse with robust handling
        result = parse_llm_json(
            llm_response,
            schema=schema,
            strict=False,  # Don't break workflow on parse failures
            coerce_types=True,
            track_errors=True,
            agent_id=self.agent_id
        )
        
        # Handle parsing failures gracefully
        if "error" in result:
            logger.warning(f"JSON parsing failed: {result['message']}")
            # Return fallback response
            return {"response": "Failed to parse LLM output", "error": True}
        
        return result
```

### Updating Existing Agents

The new parser is already integrated into:

- ✅ `OpenAIAnswerBuilder` (llm_agents.py)
- ✅ `ValidationAndStructuringAgent` (validation_and_structuring_agent.py)
- ✅ `SmartPathEvaluator` (dry_run_engine.py)
- ✅ `BooleanEvaluationParser` (plan_validator/boolean_parser.py)

To update other agents:

1. Import the new parser:
   ```python
   from orka.utils.json_parser import parse_llm_json
   ```

2. Replace manual JSON parsing:
   ```python
   # Old approach
   try:
       result = json.loads(llm_response)
   except json.JSONDecodeError:
       result = fallback_value
   
   # New approach
   result = parse_llm_json(
       llm_response,
       strict=False,
       default=fallback_value
   )
   ```

3. Add schema validation:
   ```python
   from orka.utils.json_parser import create_standard_schema
   
   schema = create_standard_schema(
       required_fields=["response"],
       optional_fields={"confidence": "number"}
   )
   
   result = parse_llm_json(llm_response, schema=schema)
   ```

## Common Use Cases

### Case 1: Simple Response Parsing

```python
# Just parse and extract, handle errors gracefully
result = parse_llm_json(llm_response, strict=False)
response_text = result.get("response", "Failed to get response")
```

### Case 2: Validated Structured Output

```python
# Ensure specific structure
schema = {
    "type": "object",
    "required": ["decision", "reasoning"],
    "properties": {
        "decision": {"type": "boolean"},
        "reasoning": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    }
}

result = parse_llm_json(
    llm_response,
    schema=schema,
    strict=True,  # Fail fast on validation errors
    coerce_types=True
)
```

### Case 3: Production Monitoring

```python
# Track all parsing failures for analysis
result = parse_llm_json(
    llm_response,
    track_errors=True,
    agent_id=self.agent_id,
    strict=False
)

# Log to monitoring system
if "error" in result:
    monitoring.log_parsing_failure(
        agent_id=self.agent_id,
        error_type=result["error"],
        strategies=result["strategies_attempted"]
    )
```

## Error Handling Best Practices

### 1. Use Strict Mode for Critical Paths

```python
# In validation or scoring agents where incorrect data is unacceptable
try:
    result = parse_llm_json(response, schema=schema, strict=True)
except JSONParseError as e:
    # Log detailed error for debugging
    logger.error(f"Critical parsing failure: {e.to_dict()}")
    # Fail the workflow or retry
    raise
```

### 2. Use Graceful Degradation for User-Facing Agents

```python
# In answer builders where partial responses are acceptable
result = parse_llm_json(response, strict=False, track_errors=True)

if "error" in result:
    # Return degraded response instead of failing
    return {
        "response": "I encountered an issue formatting my response.",
        "confidence": 0.0,
        "error": True
    }
```

### 3. Provide Defaults for Optional Fields (recommended)

```python
# Ensure your code doesn't break on missing fields
result = parse_llm_json(response)
confidence = result.get("confidence", 0.5)  # Safe default
reasoning = result.get("internal_reasoning", "No reasoning provided")
```

## Testing

Comprehensive test suite covers:

- ✅ Malformed JSON handling
- ✅ Schema validation
- ✅ Type coercion
- ✅ Multiple extraction strategies
- ✅ Error scenarios
- ✅ Real-world LLM response formats

Run tests:

```bash
pytest tests/unit/utils/test_json_parser.py -v
```

## Performance Considerations

- **Fast path**: Valid JSON is parsed immediately (no overhead)
- **Fallback overhead**: Malformed JSON may require multiple parse attempts (~10-50ms)
- **json_repair**: Adds ~5-20ms for complex repairs
- **Schema validation**: Adds ~1-5ms per validation

For high-throughput scenarios, consider:

1. **Prompt engineering**: Guide LLMs to produce valid JSON
2. **Caching**: Cache parsed results when possible
3. **Async parsing**: Use in async contexts for non-blocking behavior

## Migration from Legacy Parsers

If you have existing code using old parsing functions:

### `_parse_json_safely()` → `parse_llm_json()`

```python
# Old
result = _parse_json_safely(json_content)
if not result:
    result = fallback

# New
result = parse_llm_json(json_content, default=fallback, strict=False)
```

### `parse_llm_json_response()` → `parse_llm_json()`

```python
# Old (in llm_agents.py)
result = parse_llm_json_response(response_text, error_tracker, agent_id)

# New (already updated)
# The function now uses the new parser internally
# No changes needed to calling code
```

## Troubleshooting

### Issue: Parser returns error structure instead of data

**Cause:** JSON is too malformed to repair, or schema validation failed

**Solution:**
```python
# Enable error tracking to see what went wrong
result = parse_llm_json(text, track_errors=True, agent_id="debug")
if "error" in result:
    print(f"Parsing failed: {result['message']}")
    print(f"Strategies tried: {result['strategies_attempted']}")
    print(f"Original text: {result['original_text']}")
```

### Issue: Type coercion not working

**Cause:** Schema not provided, or coerce_types=False

**Solution:**
```python
# Ensure schema is provided and coercion is enabled
result = parse_llm_json(
    text,
    schema=your_schema,
    coerce_types=True  # Explicitly enable
)
```

### Issue: Schema validation too strict

**Cause:** LLM output doesn't match expected structure

**Solution:**
```python
# Use lenient schema with fewer required fields
schema = create_standard_schema(
    required_fields=["response"],  # Minimal requirements
    optional_fields={"confidence": "number", "extra_field": "string"}
)

# Or disable strict mode
result = parse_llm_json(text, schema=schema, strict=False)
```

## Future Enhancements

Planned for future versions:

- [ ] Retry logic with prompt adjustment
- [ ] Statistical analysis of parsing failures
- [ ] Custom repair strategies per agent
- [ ] Performance profiling and optimization
- [ ] Integration with LLM provider APIs (e.g., OpenAI JSON mode)

## Support

For issues or questions:

- 📖 Documentation: See this guide and inline docstrings
- 🐛 Bug reports: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📧 Contact: marcosomma.work@gmail.com

## Changelog

### v1.0.0 (2025-11-22)
- ✨ Initial release with robust JSON parsing
- ✨ Schema validation and type coercion
- ✨ Multiple extraction strategies
- ✨ Comprehensive error handling
- ✨ Integration with core agents
- ✨ Full test coverage

---

**Designed for Robustness (see coverage and limitations)**
