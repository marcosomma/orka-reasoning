# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Robust JSON Parsing and Schema Validation for LLM Outputs
=========================================================

This module provides defensive JSON parsing capabilities designed to handle
malformed, ambiguous, or invalid JSON responses from LLMs. It includes:

- Automatic repair of common JSON syntax errors
- Schema validation with detailed error messages
- Type coercion and normalization
- Multiple fallback strategies
- Comprehensive error tracking and reporting

Key Features:
- Uses json_repair library for automatic syntax fixing
- Supports JSONSchema validation for structure enforcement
- Handles common LLM response formats (markdown code blocks, reasoning tags, etc.)
- Provides actionable error messages for debugging
- Tracks parsing failures for monitoring and improvement

Usage:
    >>> from orka.utils.json_parser import parse_llm_json, validate_schema
    >>> 
    >>> # Basic parsing with automatic repair
    >>> result = parse_llm_json(llm_response)
    >>> 
    >>> # Parsing with schema validation
    >>> schema = {"type": "object", "required": ["response", "confidence"]}
    >>> result = parse_llm_json(llm_response, schema=schema, strict=True)
    >>> 
    >>> # With error tracking
    >>> result = parse_llm_json(llm_response, track_errors=True, agent_id="my_agent")

For v1.0.0 Production Readiness:
- Strict schema checking and coercion for LLM result parsing
- Defensive error handling with actionable error messages
- Fallback strategies for robustness
- Comprehensive test coverage for edge cases
"""

import json
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from json_repair import repair_json
    REPAIR_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    repair_json = None
    REPAIR_AVAILABLE = False

from jsonschema import Draft7Validator, ValidationError, validate

logger = logging.getLogger(__name__)


class JSONParseError(Exception):
    """Base exception for JSON parsing errors with detailed context."""

    def __init__(
        self,
        message: str,
        original_text: str = "",
        error_type: str = "unknown",
        attempted_fixes: List[str] = None,
        schema_errors: List[str] = None,
    ):
        """
        Initialize JSON parse error with detailed context.

        Args:
            message: Human-readable error message
            original_text: The original text that failed to parse
            error_type: Category of error (syntax, schema, type, etc.)
            attempted_fixes: List of fix strategies that were attempted
            schema_errors: Schema validation errors if applicable
        """
        super().__init__(message)
        self.original_text = original_text[:500]  # Limit to 500 chars for logging
        self.error_type = error_type
        self.attempted_fixes = attempted_fixes or []
        self.schema_errors = schema_errors or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/tracking."""
        return {
            "error": str(self),
            "error_type": self.error_type,
            "original_text_preview": self.original_text,
            "attempted_fixes": self.attempted_fixes,
            "schema_errors": self.schema_errors,
        }


class ParseStrategy(str, Enum):
    """Strategies for parsing JSON from LLM responses."""

    DIRECT = "direct"  # Try direct JSON parsing
    CODE_BLOCK = "code_block"  # Extract from markdown code blocks
    REASONING_STRIP = "reasoning_strip"  # Remove <think> reasoning tags
    REPAIR = "repair"  # Use json_repair library
    NORMALIZE = "normalize"  # Normalize Python syntax to JSON
    EXTRACT = "extract"  # Extract first JSON object


def _extract_json_candidate(text: str) -> Optional[str]:
    """
    Extract a *candidate* JSON string from text, even if it is not yet valid JSON.

    This is intentionally more permissive than `extract_json_from_text()` so that
    normalization/repair strategies can run on malformed-but-recoverable JSON.
    """
    if not text or not isinstance(text, str):
        return None

    raw = text.strip()
    if not raw:
        return None

    # Prefer fenced code blocks.
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", raw, re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1).strip()

    code_match = re.search(r"```\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()

    # Remove reasoning tags if present.
    reasoning_pattern = r"<(?:think|reasoning|thoughts?)>.*?</(?:think|reasoning|thoughts?)>"
    cleaned = re.sub(reasoning_pattern, "", raw, flags=re.DOTALL | re.IGNORECASE).strip()
    if cleaned and cleaned != raw:
        raw = cleaned

    # Extract first balanced JSON object/array (without validating).
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = raw.find(start_char)
        if start_idx == -1:
            continue

        depth = 0
        for i in range(start_idx, len(raw)):
            if raw[i] == start_char:
                depth += 1
            elif raw[i] == end_char:
                depth -= 1
                if depth == 0:
                    return raw[start_idx : i + 1].strip()

    return raw


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON content from various text formats.

    Handles:
    - Markdown code blocks (```json ... ```, ``` ... ```)
    - Reasoning tags (<think>...</think>)
    - XML-style tags (<response>...</response>)
    - Embedded JSON in plain text

    Args:
        text: Text potentially containing JSON

    Returns:
        Extracted JSON string or None if no JSON found
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Strategy 1: Try direct JSON (already valid)
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    # Try ```json ... ``` first (most specific)
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if json_match:
        content = json_match.group(1).strip()
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

    # Try generic ``` ... ``` blocks
    code_match = re.search(r"```\s*\n?(.*?)\n?```", text, re.DOTALL)
    if code_match:
        content = code_match.group(1).strip()
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

    # Strategy 3: Remove reasoning/thinking tags
    # <think>...</think>, <reasoning>...</reasoning>, etc.
    reasoning_pattern = r"<(?:think|reasoning|thoughts?)>.*?</(?:think|reasoning|thoughts?)>"
    cleaned = re.sub(reasoning_pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()
    if cleaned != text:
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass

    # Strategy 4: Extract first JSON object/array
    # Look for balanced braces or brackets
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue

        # Find matching closing bracket/brace
        depth = 0
        for i in range(start_idx, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start_idx : i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break

    return None


def normalize_python_to_json(text: str) -> str:
    """
    Normalize Python-style syntax to valid JSON.

    Converts:
    - Single quotes to double quotes
    - True/False/None to true/false/null
    - Trailing commas

    Args:
        text: Python-style JSON string

    Returns:
        JSON-compliant string
    """
    # Replace Python boolean/null with JSON equivalents
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)

    # Replace single quotes with double quotes (carefully)
    # This is a simplified approach - json_repair will handle complex cases
    text = re.sub(r"'([^']*)':", r'"\1":', text)  # Keys
    text = re.sub(r":\s*'([^']*)'", r': "\1"', text)  # String values

    # Remove trailing commas
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)

    return text


def repair_malformed_json(text: str) -> Optional[str]:
    """
    Attempt to repair malformed JSON using json_repair library.

    Args:
        text: Potentially malformed JSON string

    Returns:
        Repaired JSON string or None if repair failed
    """
    if not text or not isinstance(text, str):
        return None

    # Prefer the optional dependency if present, but always keep a built-in fallback
    # so Orka remains functional in constrained CI environments.
    if REPAIR_AVAILABLE and repair_json is not None:
        try:
            repaired = repair_json(text, return_objects=False)
            json.loads(repaired)
            return repaired
        except Exception as e:
            logger.debug(f"json_repair failed; falling back to built-in repair: {e}")

    # Built-in best-effort repair (covers common LLM malformations).
    candidate = text.strip()
    try:
        # Fast-path: already valid.
        json.loads(candidate)
        return candidate
    except Exception as e:
        logger.debug(f"Initial JSON validation failed, attempting repair: {e}")

    def _strip_js_style_comments(s: str) -> str:
        # NOTE: This is heuristic and may remove '//' inside strings, but it's
        # acceptable for LLM-output recovery. We validate via json.loads after.
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
        s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
        return s

    def _quote_unquoted_object_keys(s: str) -> str:
        # {key: 1} or , key: 1  -> {"key": 1}
        return re.sub(r'([{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)', r'\1"\2"\3', s)

    def _remove_trailing_commas(s: str) -> str:
        return re.sub(r",\s*([}\]])", r"\1", s)

    def _normalize_python_literals(s: str) -> str:
        s = re.sub(r"\bTrue\b", "true", s)
        s = re.sub(r"\bFalse\b", "false", s)
        s = re.sub(r"\bNone\b", "null", s)
        return s

    def _normalize_single_quotes(s: str) -> str:
        # Reuse the existing normalizer for common key/value quoting patterns.
        return normalize_python_to_json(s)

    repaired_attempt = candidate
    repaired_attempt = _strip_js_style_comments(repaired_attempt)
    repaired_attempt = _normalize_python_literals(repaired_attempt)
    repaired_attempt = _quote_unquoted_object_keys(repaired_attempt)
    repaired_attempt = _normalize_single_quotes(repaired_attempt)
    repaired_attempt = _remove_trailing_commas(repaired_attempt)

    # A second pass helps for inputs like "{key: 'value',}" after first quoting.
    repaired_attempt = _quote_unquoted_object_keys(repaired_attempt)
    repaired_attempt = _remove_trailing_commas(repaired_attempt)

    try:
        json.loads(repaired_attempt)
        return repaired_attempt
    except Exception as e:
        logger.debug(f"Built-in JSON repair failed: {e}")
        return None


def parse_llm_json(
    text: str,
    schema: Optional[Dict[str, Any]] = None,
    strict: bool = False,
    coerce_types: bool = True,
    default: Optional[Dict[str, Any]] = None,
    track_errors: bool = False,
    agent_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Robustly parse JSON from LLM output with multiple fallback strategies.

    This is the main entry point for parsing LLM responses. It attempts multiple
    strategies in sequence and provides detailed error information when all fail.

    Args:
        text: Raw text from LLM (may contain JSON, markdown, reasoning tags, etc.)
        schema: Optional JSONSchema to validate against
        strict: If True, raise exception on parse/validation failure
        coerce_types: If True, attempt to coerce types to match schema
        default: Default value to return if parsing fails (only used if strict=False)
        track_errors: If True, log detailed error information
        agent_id: Agent ID for error tracking

    Returns:
        Parsed JSON as dictionary

    Raises:
        JSONParseError: If strict=True and parsing/validation fails

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "required": ["response", "confidence"],
        ...     "properties": {
        ...         "response": {"type": "string"},
        ...         "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        ...     }
        ... }
        >>> result = parse_llm_json(llm_output, schema=schema, strict=True)
    """
    attempted_strategies = []

    # Strategy 1: Extract JSON from text
    json_text = extract_json_from_text(text)
    if json_text:
        attempted_strategies.append(ParseStrategy.EXTRACT)
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                # Validate schema if provided
                if schema:
                    parsed = validate_and_coerce(
                        parsed, schema, coerce_types=coerce_types, strict=strict
                    )
                return parsed
        except json.JSONDecodeError as e:
            if track_errors:
                logger.debug(f"[{agent_id}] Direct parse failed after extraction: {e}")

    # Strategy 2: Normalize Python syntax and try again (even if extraction failed)
    candidate_text = json_text or _extract_json_candidate(text)
    if candidate_text:
        normalized = normalize_python_to_json(candidate_text)
        attempted_strategies.append(ParseStrategy.NORMALIZE)
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, dict):
                if schema:
                    parsed = validate_and_coerce(
                        parsed, schema, coerce_types=coerce_types, strict=strict
                    )
                return parsed
        except json.JSONDecodeError as e:
            if track_errors:
                logger.debug(f"[{agent_id}] Normalized parse failed: {e}")

    # Strategy 3: Use json_repair library
    repaired = repair_malformed_json(candidate_text or text)
    if repaired:
        attempted_strategies.append(ParseStrategy.REPAIR)
        try:
            parsed = json.loads(repaired)
            if isinstance(parsed, dict):
                if schema:
                    parsed = validate_and_coerce(
                        parsed, schema, coerce_types=coerce_types, strict=strict
                    )
                return parsed
        except json.JSONDecodeError as e:
            if track_errors:
                logger.debug(f"[{agent_id}] Repaired JSON parse failed: {e}")

    # All strategies failed
    error_msg = (
        f"Failed to parse JSON from LLM response using strategies: "
        f"{[s.value for s in attempted_strategies]}"
    )

    if track_errors:
        logger.error(
            f"[{agent_id}] {error_msg}",
            extra={
                "agent_id": agent_id,
                "text_preview": text[:200],
                "strategies_attempted": [s.value for s in attempted_strategies],
            },
        )

    if strict:
        raise JSONParseError(
            message=error_msg,
            original_text=text,
            error_type="parse_failure",
            attempted_fixes=[s.value for s in attempted_strategies],
        )

    # Return default if provided
    if default is not None:
        return default

    # Last resort: return error structure
    return {
        "error": "json_parse_failed",
        "message": error_msg,
        "original_text": text[:200],
        "strategies_attempted": [s.value for s in attempted_strategies],
    }


def validate_and_coerce(
    data: Dict[str, Any],
    schema: Dict[str, Any],
    coerce_types: bool = True,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Validate JSON data against schema and optionally coerce types.

    Args:
        data: Parsed JSON data
        schema: JSONSchema specification
        coerce_types: If True, attempt to coerce types to match schema
        strict: If True, raise exception on validation failure

    Returns:
        Validated (and potentially coerced) data

    Raises:
        JSONParseError: If strict=True and validation fails
    """
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(data))

    if not errors:
        return data

    # If coercion is enabled, try to fix type mismatches
    if coerce_types:
        data = _coerce_types(data, schema, errors)
        # Re-validate after coercion
        errors = list(validator.iter_errors(data))

    if errors:
        error_messages = [_format_validation_error(e) for e in errors[:5]]  # Limit to 5 errors
        if len(errors) > 5:
            error_messages.append(f"... and {len(errors) - 5} more validation errors")

        if strict:
            raise JSONParseError(
                message=f"Schema validation failed with {len(errors)} error(s)",
                error_type="schema_validation",
                schema_errors=error_messages,
            )
        else:
            logger.warning(
                f"Schema validation failed with {len(errors)} error(s): {error_messages[:3]}"
            )

    return data


def _coerce_types(
    data: Dict[str, Any], schema: Dict[str, Any], errors: List[ValidationError]
) -> Dict[str, Any]:
    """
    Attempt to coerce types in data to match schema requirements.

    Handles common type mismatches:
    - String to number/boolean
    - Number to string
    - Missing required fields with defaults

    Args:
        data: Data to coerce
        schema: Schema specification
        errors: Validation errors from initial validation

    Returns:
        Data with coerced types
    """
    coerced = data.copy()

    # Extract properties schema
    properties = schema.get("properties", {})

    for key, prop_schema in properties.items():
        if key not in coerced:
            # Only add missing fields if they have explicit defaults
            # Don't auto-fill required fields - let validation catch them
            if "default" in prop_schema:
                coerced[key] = prop_schema["default"]
            continue

        value = coerced[key]
        expected_type = prop_schema.get("type")

        # Skip if type is already correct
        if expected_type is None:
            continue

        # Coerce string to number
        if expected_type in ("number", "integer") and isinstance(value, str):
            try:
                coerced[key] = int(value) if expected_type == "integer" else float(value)
            except (ValueError, TypeError):
                logger.debug(f"Failed to coerce '{key}' value '{value}' to {expected_type}")

        # Coerce string to boolean
        elif expected_type == "boolean" and isinstance(value, str):
            coerced[key] = value.lower() in ("true", "yes", "1")

        # Coerce number to string
        elif expected_type == "string" and isinstance(value, (int, float)):
            coerced[key] = str(value)

        # Coerce boolean to string
        elif expected_type == "string" and isinstance(value, bool):
            coerced[key] = str(value).lower()

    return coerced


def _format_validation_error(error: ValidationError) -> str:
    """
    Format a JSONSchema validation error into an actionable message.

    Args:
        error: Validation error from jsonschema

    Returns:
        Human-readable error message
    """
    path = ".".join(str(p) for p in error.path) if error.path else "root"
    return f"At '{path}': {error.message}"


def create_standard_schema(
    required_fields: Optional[List[str]] = None,
    optional_fields: Optional[Dict[str, Union[str, List[str]]]] = None,
    required_field_types: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> Dict[str, Any]:
    """
    Create a standard JSONSchema for common LLM response patterns.

    Args:
        required_fields: List of required field names (default: ["response"])
        optional_fields: Dict of optional field names to types
                        (default: {"confidence": "number", "reasoning": "string"})
        required_field_types: Optional mapping of required field names to JSONSchema
                             type(s). If not provided, required fields default to
                             "string" except for "response" which defaults to
                             ["string", "object", "array"].

    Returns:
        JSONSchema dictionary

    Example:
        >>> schema = create_standard_schema(
        ...     required_fields=["response", "answer"],
        ...     optional_fields={"confidence": "number", "source": "string"}
        ... )
    """
    required_fields = required_fields or ["response"]
    optional_fields = optional_fields or {
        "confidence": "number",
        "internal_reasoning": "string",
    }

    required_field_types = required_field_types or {}

    # Default: response can be structured (dict/list) or plain text.
    if "response" not in required_field_types:
        required_field_types["response"] = ["string", "object", "array"]

    properties = {}

    # Add required fields (default to string type)
    for field in required_fields:
        field_type = required_field_types.get(field, "string")
        properties[field] = {"type": field_type}

    # Add optional fields with specified types
    for field, field_type in optional_fields.items():
        properties[field] = {"type": field_type}

    return {"type": "object", "required": required_fields, "properties": properties}


# Convenience function for backward compatibility with existing codebase
def parse_json_safely(
    json_content: str, fallback_value: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Legacy function for backward compatibility.

    Use parse_llm_json() for new code.

    Args:
        json_content: JSON string to parse
        fallback_value: Value to return on failure

    Returns:
        Parsed JSON or fallback_value
    """
    return parse_llm_json(
        json_content, strict=False, default=fallback_value, track_errors=False
    )
