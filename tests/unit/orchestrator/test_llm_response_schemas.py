"""Unit tests for orka.orchestrator.llm_response_schemas."""

import pytest

from orka.orchestrator.llm_response_schemas import (
    PATH_EVALUATION_SCHEMA,
    PATH_VALIDATION_SCHEMA,
    COMPREHENSIVE_EVALUATION_SCHEMA,
    validate_llm_response,
    validate_path_evaluation,
    validate_path_validation,
    validate_comprehensive_evaluation,
)

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestLLMResponseSchemas:
    """Test suite for LLM response schema validation."""

    def test_path_evaluation_schema_structure(self):
        """Test that PATH_EVALUATION_SCHEMA has correct structure."""
        assert PATH_EVALUATION_SCHEMA["type"] == "object"
        assert "required" in PATH_EVALUATION_SCHEMA
        assert "relevance_score" in PATH_EVALUATION_SCHEMA["required"]
        assert "confidence" in PATH_EVALUATION_SCHEMA["required"]
        assert "reasoning" in PATH_EVALUATION_SCHEMA["required"]
        assert "properties" in PATH_EVALUATION_SCHEMA

    def test_path_validation_schema_structure(self):
        """Test that PATH_VALIDATION_SCHEMA has correct structure."""
        assert PATH_VALIDATION_SCHEMA["type"] == "object"
        assert "required" in PATH_VALIDATION_SCHEMA
        assert "is_valid" in PATH_VALIDATION_SCHEMA["required"]
        assert "confidence" in PATH_VALIDATION_SCHEMA["required"]
        assert "efficiency_score" in PATH_VALIDATION_SCHEMA["required"]
        assert "properties" in PATH_VALIDATION_SCHEMA

    def test_comprehensive_evaluation_schema_structure(self):
        """Test that COMPREHENSIVE_EVALUATION_SCHEMA has correct structure."""
        assert COMPREHENSIVE_EVALUATION_SCHEMA["type"] == "object"
        assert "required" in COMPREHENSIVE_EVALUATION_SCHEMA
        assert "recommended_path" in COMPREHENSIVE_EVALUATION_SCHEMA["required"]
        assert "reasoning" in COMPREHENSIVE_EVALUATION_SCHEMA["required"]
        assert "confidence" in COMPREHENSIVE_EVALUATION_SCHEMA["required"]
        assert "path_evaluations" in COMPREHENSIVE_EVALUATION_SCHEMA["required"]

    def test_validate_llm_response_valid(self):
        """Test validate_llm_response with valid response."""
        schema = {
            "type": "object",
            "required": ["field1", "field2"],
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "number"},
            },
        }
        response = {"field1": "test", "field2": 123}
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is True
        assert error == ""

    def test_validate_llm_response_missing_required_field(self):
        """Test validate_llm_response with missing required field."""
        schema = {
            "type": "object",
            "required": ["field1", "field2"],
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "number"},
            },
        }
        response = {"field1": "test"}  # Missing field2
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "Missing required field: field2" in error

    def test_validate_llm_response_null_required_field(self):
        """Test validate_llm_response with null required field."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string"},
            },
        }
        response = {"field1": None}
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "Required field is null: field1" in error

    def test_validate_llm_response_wrong_type(self):
        """Test validate_llm_response with wrong field type."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string"},
            },
        }
        response = {"field1": 123}  # Should be string
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "wrong type" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_multiple_types_allowed(self):
        """Test validate_llm_response with multiple allowed types."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": ["string", "number"]},
            },
        }
        
        # Test with string
        response1 = {"field1": "test"}
        is_valid1, error1 = validate_llm_response(response1, schema)
        assert is_valid1 is True
        
        # Test with number
        response2 = {"field1": 123}
        is_valid2, error2 = validate_llm_response(response2, schema)
        assert is_valid2 is True

    def test_validate_llm_response_number_minimum(self):
        """Test validate_llm_response with number below minimum."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
        response = {"field1": -0.5}  # Below minimum
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "below minimum" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_number_maximum(self):
        """Test validate_llm_response with number above maximum."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "number", "minimum": 0, "maximum": 1},
            },
        }
        response = {"field1": 1.5}  # Above maximum
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "above maximum" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_string_min_length(self):
        """Test validate_llm_response with string below minLength."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string", "minLength": 5},
            },
        }
        response = {"field1": "test"}  # Length 4, below minimum
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "too short" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_string_enum(self):
        """Test validate_llm_response with string not in enum."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string", "enum": ["low", "medium", "high"]},
            },
        }
        response = {"field1": "invalid"}  # Not in enum
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "not in enum" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_array_min_items(self):
        """Test validate_llm_response with array below minItems."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "array", "minItems": 2},
            },
        }
        response = {"field1": ["item1"]}  # Only 1 item, below minimum
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is False
        assert "too few items" in error.lower()
        assert "field1" in error

    def test_validate_llm_response_extra_fields_allowed(self):
        """Test validate_llm_response allows extra fields not in schema."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string"},
            },
        }
        response = {"field1": "test", "extra_field": "extra"}  # Extra field
        
        is_valid, error = validate_llm_response(response, schema)
        
        assert is_valid is True  # Extra fields are allowed
        assert error == ""

    def test_validate_llm_response_exception_handling(self):
        """Test validate_llm_response handles exceptions gracefully."""
        schema = {
            "type": "object",
            "required": ["field1"],
            "properties": {
                "field1": {"type": "string"},
            },
        }
        # Create a response that might cause issues
        response = {"field1": object()}  # Object type not in python_to_json mapping
        
        is_valid, error = validate_llm_response(response, schema)
        
        # Should handle gracefully
        assert is_valid is False
        assert "error" in error.lower() or "exception" in error.lower() or "wrong type" in error.lower()

    def test_validate_path_evaluation_valid(self):
        """Test validate_path_evaluation with valid response."""
        response = {
            "relevance_score": 0.8,
            "confidence": 0.9,
            "reasoning": "This path is highly relevant",
            "expected_output": "Analysis result",
            "estimated_tokens": 100,
            "estimated_cost": 0.01,
        }
        
        is_valid, error = validate_path_evaluation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_path_evaluation_missing_required(self):
        """Test validate_path_evaluation with missing required field."""
        response = {
            "relevance_score": 0.8,
            "confidence": 0.9,
            # Missing "reasoning"
        }
        
        is_valid, error = validate_path_evaluation(response)
        
        assert is_valid is False
        assert "Missing required field: reasoning" in error

    def test_validate_path_evaluation_score_out_of_range(self):
        """Test validate_path_evaluation with score out of range."""
        response = {
            "relevance_score": 1.5,  # Above maximum of 1.0
            "confidence": 0.9,
            "reasoning": "Test reasoning",
        }
        
        is_valid, error = validate_path_evaluation(response)
        
        assert is_valid is False
        assert "above maximum" in error.lower()
        assert "relevance_score" in error

    def test_validate_path_validation_valid(self):
        """Test validate_path_validation with valid response."""
        response = {
            "is_valid": True,
            "confidence": 0.85,
            "efficiency_score": 0.9,
            "validation_reasoning": "Path is valid and efficient",
            "suggested_improvements": ["Optimize step 2"],
            "risk_assessment": "low",
        }
        
        is_valid, error = validate_path_validation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_path_validation_missing_required(self):
        """Test validate_path_validation with missing required field."""
        response = {
            "is_valid": True,
            "confidence": 0.85,
            # Missing "efficiency_score"
        }
        
        is_valid, error = validate_path_validation(response)
        
        assert is_valid is False
        assert "Missing required field: efficiency_score" in error

    def test_validate_path_validation_wrong_enum(self):
        """Test validate_path_validation with invalid enum value."""
        response = {
            "is_valid": True,
            "confidence": 0.85,
            "efficiency_score": 0.9,
            "risk_assessment": "invalid_risk",  # Not in enum
        }
        
        is_valid, error = validate_path_validation(response)
        
        assert is_valid is False
        assert "not in enum" in error.lower()
        assert "risk_assessment" in error

    def test_validate_comprehensive_evaluation_valid(self):
        """Test validate_comprehensive_evaluation with valid response."""
        response = {
            "recommended_path": ["agent1", "agent2", "agent3"],
            "reasoning": "This path provides the best balance",
            "confidence": 0.95,
            "expected_outcome": "Complete analysis",
            "path_evaluations": [
                {"relevance_score": 0.8, "confidence": 0.9, "reasoning": "Good path"}
            ],
        }
        
        is_valid, error = validate_comprehensive_evaluation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_comprehensive_evaluation_missing_required(self):
        """Test validate_comprehensive_evaluation with missing required field."""
        response = {
            "recommended_path": ["agent1"],
            "reasoning": "Test reasoning",
            "confidence": 0.9,
            # Missing "path_evaluations"
        }
        
        is_valid, error = validate_comprehensive_evaluation(response)
        
        assert is_valid is False
        assert "Missing required field: path_evaluations" in error

    def test_validate_comprehensive_evaluation_empty_path(self):
        """Test validate_comprehensive_evaluation with empty recommended_path."""
        response = {
            "recommended_path": [],  # Empty, but minItems is 1
            "reasoning": "Test reasoning",
            "confidence": 0.9,
            "path_evaluations": [{"relevance_score": 0.8, "confidence": 0.9, "reasoning": "Test"}],
        }
        
        is_valid, error = validate_comprehensive_evaluation(response)
        
        assert is_valid is False
        assert "too few items" in error.lower()
        assert "recommended_path" in error

    def test_validate_comprehensive_evaluation_short_reasoning(self):
        """Test validate_comprehensive_evaluation with reasoning below minLength."""
        response = {
            "recommended_path": ["agent1"],
            "reasoning": "",  # Empty, but minLength is 1
            "confidence": 0.9,
            "path_evaluations": [{"relevance_score": 0.8, "confidence": 0.9, "reasoning": "Test"}],
        }
        
        is_valid, error = validate_comprehensive_evaluation(response)
        
        assert is_valid is False
        assert "too short" in error.lower()
        assert "reasoning" in error

    def test_validate_path_evaluation_with_string_numbers(self):
        """Test validate_path_evaluation accepts string numbers for estimated fields."""
        response = {
            "relevance_score": 0.8,
            "confidence": 0.9,
            "reasoning": "Test reasoning",
            "estimated_tokens": "100",  # String number
            "estimated_cost": "0.01",  # String number
        }
        
        is_valid, error = validate_path_evaluation(response)
        
        # String numbers are allowed for estimated_tokens and estimated_cost
        assert is_valid is True
        assert error == ""

    def test_validate_path_evaluation_with_numeric_numbers(self):
        """Test validate_path_evaluation accepts numeric numbers for estimated fields."""
        response = {
            "relevance_score": 0.8,
            "confidence": 0.9,
            "reasoning": "Test reasoning",
            "estimated_tokens": 100,  # Numeric number
            "estimated_cost": 0.01,  # Numeric number
        }
        
        is_valid, error = validate_path_evaluation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_path_validation_boolean_is_valid(self):
        """Test validate_path_validation with boolean is_valid field."""
        response = {
            "is_valid": False,  # Boolean False
            "confidence": 0.85,
            "efficiency_score": 0.9,
        }
        
        is_valid, error = validate_path_validation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_path_validation_array_suggested_improvements(self):
        """Test validate_path_validation with array of suggested improvements."""
        response = {
            "is_valid": True,
            "confidence": 0.85,
            "efficiency_score": 0.9,
            "suggested_improvements": [
                "Improve step 1",
                "Optimize step 2",
                "Add validation step",
            ],
        }
        
        is_valid, error = validate_path_validation(response)
        
        assert is_valid is True
        assert error == ""

    def test_validate_comprehensive_evaluation_empty_evaluations(self):
        """Test validate_comprehensive_evaluation with empty path_evaluations."""
        response = {
            "recommended_path": ["agent1"],
            "reasoning": "Test reasoning",
            "confidence": 0.9,
            "path_evaluations": [],  # Empty, but minItems is 1
        }
        
        is_valid, error = validate_comprehensive_evaluation(response)
        
        assert is_valid is False
        assert "too few items" in error.lower()
        assert "path_evaluations" in error
