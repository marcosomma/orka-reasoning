# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
LLM Response Schema Validation
================================

JSON schema validation for LLM responses to ensure consistency and
catch malformed responses early.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Stage 1: Path Evaluation Schema
PATH_EVALUATION_SCHEMA = {
    "type": "object",
    "required": ["relevance_score", "confidence", "reasoning"],
    "properties": {
        "relevance_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Relevance score between 0 and 1",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score between 0 and 1",
        },
        "reasoning": {
            "type": "string",
            "minLength": 1,
            "description": "Explanation of the evaluation",
        },
        "expected_output": {"type": "string", "description": "Expected output from this agent"},
        "estimated_tokens": {"type": ["string", "number"], "description": "Estimated token usage"},
        "estimated_cost": {
            "type": ["string", "number"],
            "description": "Estimated cost in dollars",
        },
    },
}

# Stage 2: Path Validation Schema
PATH_VALIDATION_SCHEMA = {
    "type": "object",
    "required": ["is_valid", "confidence", "efficiency_score"],
    "properties": {
        "is_valid": {"type": "boolean", "description": "Whether the path is valid"},
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in the validation",
        },
        "efficiency_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Efficiency score of the path",
        },
        "validation_reasoning": {
            "type": "string",
            "description": "Reasoning for validation decision",
        },
        "suggested_improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Suggested improvements for the path",
        },
        "risk_assessment": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Risk level assessment",
        },
    },
}

# Comprehensive Evaluation Schema
COMPREHENSIVE_EVALUATION_SCHEMA = {
    "type": "object",
    "required": ["recommended_path", "reasoning", "confidence", "path_evaluations"],
    "properties": {
        "recommended_path": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "Recommended agent path as array of agent IDs",
        },
        "reasoning": {
            "type": "string",
            "minLength": 1,
            "description": "Reasoning for path recommendation",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in recommendation",
        },
        "expected_outcome": {
            "type": "string",
            "description": "Expected outcome of following this path",
        },
        "path_evaluations": {
            "type": "array",
            "minItems": 1,
            "description": "Evaluations for each candidate path",
        },
    },
}


def validate_llm_response(response_dict: Dict[str, Any], schema: Dict) -> tuple[bool, str]:
    """
    Validate LLM response against schema.

    Args:
        response_dict: Parsed JSON response from LLM
        schema: JSON schema to validate against

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in response_dict:
                return False, f"Missing required field: {field}"

            if response_dict[field] is None:
                return False, f"Required field is null: {field}"

        # Validate field types and constraints
        properties = schema.get("properties", {})
        for field, value in response_dict.items():
            if field not in properties:
                continue  # Allow extra fields

            field_schema = properties[field]

            # Type validation
            expected_types = field_schema.get("type")
            if expected_types:
                if isinstance(expected_types, str):
                    expected_types = [expected_types]

                value_type = type(value).__name__
                python_to_json = {
                    "str": "string",
                    "int": "number",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object",
                    "NoneType": "null",
                }

                json_type = python_to_json.get(value_type, value_type)
                if json_type not in expected_types:
                    return (
                        False,
                        f"Field '{field}' has wrong type: expected {expected_types}, got {json_type}",
                    )

            # Number constraints
            if isinstance(value, (int, float)):
                if "minimum" in field_schema and value < field_schema["minimum"]:
                    return (
                        False,
                        f"Field '{field}' below minimum: {value} < {field_schema['minimum']}",
                    )
                if "maximum" in field_schema and value > field_schema["maximum"]:
                    return (
                        False,
                        f"Field '{field}' above maximum: {value} > {field_schema['maximum']}",
                    )

            # String constraints
            if isinstance(value, str):
                if "minLength" in field_schema and len(value) < field_schema["minLength"]:
                    return (
                        False,
                        f"Field '{field}' too short: {len(value)} < {field_schema['minLength']}",
                    )
                if "enum" in field_schema and value not in field_schema["enum"]:
                    return (
                        False,
                        f"Field '{field}' not in enum: {value} not in {field_schema['enum']}",
                    )

            # Array constraints
            if isinstance(value, list):
                if "minItems" in field_schema and len(value) < field_schema["minItems"]:
                    return (
                        False,
                        f"Field '{field}' has too few items: {len(value)} < {field_schema['minItems']}",
                    )

        return True, ""

    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return False, f"Validation exception: {str(e)}"


def validate_path_evaluation(response_dict: Dict[str, Any]) -> tuple[bool, str]:
    """Validate path evaluation response."""
    return validate_llm_response(response_dict, PATH_EVALUATION_SCHEMA)


def validate_path_validation(response_dict: Dict[str, Any]) -> tuple[bool, str]:
    """Validate path validation response."""
    return validate_llm_response(response_dict, PATH_VALIDATION_SCHEMA)


def validate_comprehensive_evaluation(response_dict: Dict[str, Any]) -> tuple[bool, str]:
    """Validate comprehensive evaluation response."""
    return validate_llm_response(response_dict, COMPREHENSIVE_EVALUATION_SCHEMA)
