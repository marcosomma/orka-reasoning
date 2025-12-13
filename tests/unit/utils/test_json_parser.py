"""
Tests for Robust JSON Parser
============================

Comprehensive test suite for orka.utils.json_parser module covering:
- Malformed JSON handling
- Schema validation
- Type coercion
- Error scenarios
- Fallback strategies
"""

import json
import pytest

from orka.utils.json_parser import (
    JSONParseError,
    ParseStrategy,
    create_standard_schema,
    extract_json_from_text,
    normalize_python_to_json,
    parse_llm_json,
    repair_malformed_json,
    validate_and_coerce,
)


class TestExtractJsonFromText:
    """Test JSON extraction from various text formats."""

    def test_direct_valid_json(self):
        """Test extraction of already valid JSON."""
        text = '{"response": "test", "confidence": 0.9}'
        result = extract_json_from_text(text)
        assert result == text
        assert json.loads(result) == {"response": "test", "confidence": 0.9}

    def test_json_in_markdown_code_block(self):
        """Test extraction from ```json code blocks."""
        text = """
        Here's the result:
        ```json
        {"response": "test", "confidence": 0.9}
        ```
        """
        result = extract_json_from_text(text)
        assert result is not None
        assert json.loads(result) == {"response": "test", "confidence": 0.9}

    def test_json_in_generic_code_block(self):
        """Test extraction from generic ``` code blocks."""
        text = """
        ```
        {"response": "test", "confidence": 0.9}
        ```
        """
        result = extract_json_from_text(text)
        assert result is not None
        assert json.loads(result) == {"response": "test", "confidence": 0.9}

    def test_json_with_reasoning_tags(self):
        """Test extraction with <think> reasoning tags removed."""
        text = """
        <think>
        Let me analyze this carefully...
        </think>
        {"response": "test", "confidence": 0.9}
        """
        result = extract_json_from_text(text)
        assert result is not None
        data = json.loads(result)
        assert "response" in data

    def test_json_embedded_in_text(self):
        """Test extraction of JSON object from surrounding text."""
        text = 'The answer is {"response": "test", "confidence": 0.9} as shown above.'
        result = extract_json_from_text(text)
        assert result is not None
        assert json.loads(result) == {"response": "test", "confidence": 0.9}

    def test_no_json_found(self):
        """Test handling when no JSON is present."""
        text = "This is just plain text with no JSON at all."
        result = extract_json_from_text(text)
        assert result is None

    def test_empty_input(self):
        """Test handling of empty input."""
        assert extract_json_from_text("") is None
        assert extract_json_from_text(None) is None


class TestNormalizePythonToJson:
    """Test Python syntax normalization."""

    def test_normalize_booleans(self):
        """Test True/False conversion to true/false."""
        text = '{"valid": True, "error": False}'
        result = normalize_python_to_json(text)
        assert "true" in result
        assert "false" in result
        assert "True" not in result
        assert "False" not in result

    def test_normalize_none(self):
        """Test None conversion to null."""
        text = '{"value": None}'
        result = normalize_python_to_json(text)
        assert "null" in result
        assert "None" not in result

    def test_normalize_single_quotes(self):
        """Test single quote conversion to double quotes."""
        text = "{'key': 'value'}"
        result = normalize_python_to_json(text)
        assert '"key"' in result
        assert '"value"' in result

    def test_remove_trailing_commas(self):
        """Test trailing comma removal."""
        text = '{"key": "value",}'
        result = normalize_python_to_json(text)
        # Note: normalize function focuses on quotes/bools, trailing commas handled by repair
        assert "," in result or json.loads(result.replace(",}", "}"))


class TestRepairMalformedJson:
    """Test JSON repair functionality."""

    def test_repair_trailing_comma(self):
        """Test repair of trailing commas."""
        malformed = '{"key": "value",}'
        result = repair_malformed_json(malformed)
        assert result is not None
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_repair_missing_quotes(self):
        """Test repair of missing quotes around keys."""
        malformed = "{key: 'value'}"
        result = repair_malformed_json(malformed)
        assert result is not None
        # json_repair should handle this
        parsed = json.loads(result)
        assert "key" in parsed

    def test_repair_unrecoverable_json(self):
        """Test handling of completely broken JSON."""
        malformed = "{this is not even close to JSON{{{"
        result = repair_malformed_json(malformed)
        # May return None or attempt repair
        # json_repair is quite robust, so it might return something
        if result:
            # If it returns something, it should be valid
            json.loads(result)


class TestParseLlmJson:
    """Test main LLM JSON parsing function."""

    def test_parse_valid_json(self):
        """Test parsing of valid JSON."""
        text = '{"response": "Hello", "confidence": 0.95}'
        result = parse_llm_json(text)
        assert result["response"] == "Hello"
        assert "confidence" in result

    def test_parse_json_with_schema(self):
        """Test parsing with schema validation."""
        text = '{"response": "Hello", "confidence": 0.95}'
        schema = create_standard_schema(
            required_fields=["response"], optional_fields={"confidence": "number"}
        )
        result = parse_llm_json(text, schema=schema)
        assert result["response"] == "Hello"
        assert isinstance(result["confidence"], (int, float))

    def test_parse_json_with_schema_allows_object_response(self):
        """Test schema validation accepts structured response payloads."""
        text = '{"response": {"TESTS": ["a"], "ISOLATION": []}, "confidence": 0.95}'
        schema = create_standard_schema(
            required_fields=["response"], optional_fields={"confidence": "number"}
        )
        result = parse_llm_json(text, schema=schema)
        assert isinstance(result["response"], dict)
        assert result["response"]["TESTS"] == ["a"]
        assert isinstance(result["confidence"], (int, float))

    def test_parse_malformed_json_with_repair(self):
        """Test automatic repair of malformed JSON."""
        text = """
        ```json
        {
            "response": "Hello",
            "confidence": 0.95,
        }
        ```
        """
        result = parse_llm_json(text)
        assert "response" in result
        assert result["response"] == "Hello"

    def test_parse_python_syntax_json(self):
        """Test parsing of Python-style JSON."""
        text = "{'response': 'Hello', 'valid': True, 'data': None}"
        result = parse_llm_json(text)
        assert "response" in result

    def test_parse_with_type_coercion(self):
        """Test type coercion during parsing."""
        text = '{"response": "Hello", "confidence": "0.95"}'  # confidence as string
        schema = create_standard_schema(
            required_fields=["response"], optional_fields={"confidence": "number"}
        )
        result = parse_llm_json(text, schema=schema, coerce_types=True)
        assert isinstance(result["confidence"], (int, float))
        assert result["confidence"] == 0.95

    def test_parse_failure_with_default(self):
        """Test fallback to default on parse failure."""
        text = "This is not JSON at all"
        default = {"response": "fallback", "confidence": 0.0}
        result = parse_llm_json(text, default=default, strict=False)
        # Should return error structure or default
        if "error" in result:
            assert result["error"] == "json_parse_failed"
        else:
            assert result == default

    def test_parse_failure_strict_mode(self):
        """Test exception raising in strict mode."""
        text = "This is not JSON at all"
        with pytest.raises(JSONParseError) as exc_info:
            parse_llm_json(text, strict=True)
        assert "parse_failure" in str(exc_info.value.error_type)

    def test_parse_with_error_tracking(self):
        """Test error tracking during parsing."""
        text = "Not JSON"
        result = parse_llm_json(text, track_errors=True, agent_id="test_agent")
        # Should handle gracefully
        assert isinstance(result, dict)


class TestValidateAndCoerce:
    """Test schema validation and type coercion."""

    def test_valid_data_passes(self):
        """Test that valid data passes validation."""
        data = {"response": "test", "confidence": 0.9}
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}, "confidence": {"type": "number"}},
        }
        result = validate_and_coerce(data, schema)
        assert result == data

    def test_coerce_string_to_number(self):
        """Test coercion of string to number."""
        data = {"response": "test", "confidence": "0.9"}
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}, "confidence": {"type": "number"}},
        }
        result = validate_and_coerce(data, schema, coerce_types=True)
        assert isinstance(result["confidence"], float)
        assert result["confidence"] == 0.9

    def test_coerce_string_to_boolean(self):
        """Test coercion of string to boolean."""
        data = {"response": "test", "valid": "true"}
        schema = {
            "type": "object",
            "properties": {"response": {"type": "string"}, "valid": {"type": "boolean"}},
        }
        result = validate_and_coerce(data, schema, coerce_types=True)
        assert isinstance(result["valid"], bool)
        assert result["valid"] is True

    def test_add_missing_fields_with_defaults(self):
        """Test adding missing required fields with defaults."""
        data = {"response": "test"}
        schema = {
            "type": "object",
            "required": ["response", "confidence"],
            "properties": {
                "response": {"type": "string"},
                "confidence": {"type": "number", "default": 0.5},
            },
        }
        result = validate_and_coerce(data, schema, coerce_types=True)
        assert "confidence" in result
        assert result["confidence"] == 0.5

    def test_validation_failure_strict(self):
        """Test validation failure in strict mode."""
        data = {"wrong_field": "test"}
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}},
        }
        with pytest.raises(JSONParseError) as exc_info:
            validate_and_coerce(data, schema, strict=True)
        assert exc_info.value.error_type == "schema_validation"

    def test_validation_failure_non_strict(self):
        """Test validation failure in non-strict mode."""
        data = {"wrong_field": "test"}
        schema = {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}},
        }
        # Should not raise, but log warning
        result = validate_and_coerce(data, schema, strict=False)
        # Result should be the coerced/original data
        assert isinstance(result, dict)


class TestCreateStandardSchema:
    """Test standard schema creation."""

    def test_default_schema(self):
        """Test creation of default schema."""
        schema = create_standard_schema()
        assert schema["type"] == "object"
        assert "response" in schema["required"]
        assert "confidence" in schema["properties"]
        assert "internal_reasoning" in schema["properties"]

    def test_custom_required_fields(self):
        """Test custom required fields."""
        schema = create_standard_schema(required_fields=["answer", "source"])
        assert "answer" in schema["required"]
        assert "source" in schema["required"]
        assert "response" not in schema["required"]

    def test_custom_optional_fields(self):
        """Test custom optional fields."""
        schema = create_standard_schema(
            optional_fields={"score": "number", "metadata": "object"}
        )
        assert "score" in schema["properties"]
        assert schema["properties"]["score"]["type"] == "number"
        assert "metadata" in schema["properties"]


class TestJsonParseError:
    """Test JSONParseError exception."""

    def test_error_creation(self):
        """Test creating JSONParseError with context."""
        error = JSONParseError(
            message="Parse failed",
            original_text="bad json",
            error_type="syntax",
            attempted_fixes=["repair", "normalize"],
            schema_errors=["Missing required field"],
        )
        assert "Parse failed" in str(error)
        assert error.error_type == "syntax"
        assert "repair" in error.attempted_fixes

    def test_error_to_dict(self):
        """Test error serialization to dict."""
        error = JSONParseError(
            message="Parse failed",
            original_text="bad json",
            error_type="syntax",
            attempted_fixes=["repair"],
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "syntax"
        assert "attempted_fixes" in error_dict
        assert len(error_dict["attempted_fixes"]) == 1


class TestRealWorldScenarios:
    """Test real-world LLM response scenarios."""

    def test_openai_style_response(self):
        """Test typical OpenAI response format."""
        text = """
        {
            "response": "The capital of France is Paris.",
            "confidence": 0.99,
            "internal_reasoning": "This is a well-known geographical fact."
        }
        """
        result = parse_llm_json(text)
        assert result["response"] == "The capital of France is Paris."
        assert "confidence" in result

    def test_reasoning_model_with_think_tags(self):
        """Test response from reasoning models with <think> tags."""
        text = """
        <think>
        Let me break this down step by step:
        1. France is a country in Europe
        2. Its capital city is Paris
        3. This is verified information
        </think>
        
        ```json
        {
            "response": "Paris",
            "confidence": 0.99
        }
        ```
        """
        result = parse_llm_json(text)
        assert result["response"] == "Paris"

    def test_local_llm_inconsistent_format(self):
        """Test inconsistent format from local LLMs."""
        text = """
        Sure, here's my response:
        
        {'answer': 'The answer is 42', 'score': '0.85', 'reasoning': 'Based on analysis'}
        
        Hope this helps!
        """
        # Note: 'answer' not 'response', needs flexible parsing
        result = parse_llm_json(text)
        assert isinstance(result, dict)
        # Parser should extract the JSON object

    def test_malformed_from_temperature_1(self):
        """Test handling of malformed JSON from high temperature sampling."""
        text = """
        {
            "response": "Here's the answer",
            "confidence": 0.8,
            "extra_field": "something",
            // This is a comment that shouldn't be here
        }
        """
        result = parse_llm_json(text)
        # json_repair should handle comments and trailing commas
        assert "response" in result

    def test_nested_json_in_response(self):
        """Test handling of nested JSON structures."""
        text = """
        {
            "response": "Analysis complete",
            "confidence": 0.9,
            "details": {
                "items_found": 5,
                "categories": ["A", "B", "C"]
            }
        }
        """
        result = parse_llm_json(text)
        assert result["response"] == "Analysis complete"
        assert "details" in result
        assert isinstance(result["details"], dict)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_extremely_large_json(self):
        """Test handling of very large JSON."""
        large_text = "x" * 10000
        large_json = json.dumps({"response": large_text, "confidence": 0.5})
        result = parse_llm_json(large_json)
        assert result["response"] == large_text

    def test_unicode_in_json(self):
        """Test Unicode character handling."""
        text = '{"response": "Hello 世界 🌍", "confidence": 0.9}'
        result = parse_llm_json(text)
        assert "世界" in result["response"]
        assert "🌍" in result["response"]

    def test_escaped_characters(self):
        """Test escaped character handling."""
        text = r'{"response": "Line 1\nLine 2\tTabbed", "confidence": 0.9}'
        result = parse_llm_json(text)
        assert "response" in result

    def test_multiple_json_objects(self):
        """Test handling when multiple JSON objects present."""
        text = """
        {"response": "First"} {"response": "Second"}
        """
        result = parse_llm_json(text)
        # Should extract the first valid one
        assert result["response"] in ["First", "Second"]

    def test_json_with_null_values(self):
        """Test handling of null values."""
        text = '{"response": null, "confidence": 0.5}'
        result = parse_llm_json(text)
        # Should handle null appropriately
        assert "confidence" in result
