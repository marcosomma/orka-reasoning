# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Boolean Evaluation Parser
=========================

Parses LLM responses to extract boolean evaluation criteria.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_boolean_evaluation(response: str) -> Dict[str, Dict[str, bool]]:
    """
    Parse LLM response to extract boolean evaluations.

    Attempts to extract JSON structure with boolean values per criterion.
    Falls back to text-based extraction if JSON parsing fails.

    Args:
        response: Raw LLM response text

    Returns:
        Nested dict of boolean evaluations:
        {"dimension": {"criterion": bool, ...}, ...}
    """
    logger.debug("Parsing boolean evaluation response")

    json_data = _extract_json_from_text(response)

    if json_data and _is_valid_boolean_structure(json_data):
        logger.debug("Successfully extracted JSON boolean evaluation")
        return _normalize_boolean_structure(json_data)

    logger.debug("Using fallback text-based boolean extraction")
    return _extract_booleans_from_text(response)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text using regex.

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON dict or None if extraction fails
    """
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)

    if json_match:
        try:
            parsed = json.loads(
                json_match.group(1) if json_match.lastindex else json_match.group(0)
            )
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode failed: {e}")

    return None


def _is_valid_boolean_structure(data: Dict[str, Any]) -> bool:
    """
    Check if data contains valid boolean evaluation structure.

    Args:
        data: Parsed JSON dict

    Returns:
        True if structure appears valid
    """
    expected_dimensions = ["completeness", "efficiency", "safety", "coherence"]
    found_dimensions = 0

    for dimension in expected_dimensions:
        if dimension in data:
            dimension_data = data[dimension]
            if isinstance(dimension_data, dict) and len(dimension_data) > 0:
                found_dimensions += 1

    return found_dimensions >= 2


def _normalize_boolean_structure(data: Dict[str, Any]) -> Dict[str, Dict[str, bool]]:
    """
    Normalize JSON data to consistent boolean structure.

    Args:
        data: Parsed JSON with boolean evaluations

    Returns:
        Normalized nested dict of booleans
    """
    result: Dict[str, Dict[str, bool]] = {}

    for dimension, criteria in data.items():
        if not isinstance(criteria, dict):
            continue

        result[dimension] = {}

        for criterion, value in criteria.items():
            result[dimension][criterion] = _normalize_boolean_value(value)

    return result


def _normalize_boolean_value(value: Any) -> bool:
    """
    Normalize various value types to boolean.

    Args:
        value: Value to convert to boolean

    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value_lower = value.lower().strip()
        return value_lower in ("true", "yes", "1", "pass", "passed", "✓")

    if isinstance(value, (int, float)):
        return value > 0

    return False


def _extract_booleans_from_text(text: str) -> Dict[str, Dict[str, bool]]:
    """
    Extract boolean values from plain text (fallback).

    Uses pattern matching to find criterion: true/false pairs.

    Args:
        text: Raw text response

    Returns:
        Nested dict of boolean evaluations with defaults
    """
    result: Dict[str, Dict[str, bool]] = {
        "completeness": {},
        "efficiency": {},
        "safety": {},
        "coherence": {},
    }

    patterns = [
        r"([a-z_]+):\s*(true|false|yes|no|pass|fail|✓|✗)",
        r'"([a-z_]+)":\s*(true|false|yes|no)',
        r"([a-z_]+)\s*=\s*(true|false|yes|no)",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            criterion = match.group(1)
            value_str = match.group(2).lower()

            bool_value = value_str in ("true", "yes", "pass", "✓")

            for dimension in result.keys():
                if criterion in _get_dimension_criteria(dimension):
                    result[dimension][criterion] = bool_value
                    logger.debug(f"Extracted {dimension}.{criterion} = {bool_value}")

    _fill_missing_defaults(result)

    return result


def _get_dimension_criteria(dimension: str) -> list[str]:
    """
    Get expected criteria names for a dimension.

    Args:
        dimension: Dimension name

    Returns:
        List of criterion names
    """
    criteria_map = {
        "completeness": [
            "has_all_required_steps",
            "addresses_all_query_aspects",
            "handles_edge_cases",
            "includes_fallback_path",
        ],
        "efficiency": [
            "minimizes_redundant_calls",
            "uses_appropriate_agents",
            "optimizes_cost",
            "optimizes_latency",
        ],
        "safety": [
            "validates_inputs",
            "handles_errors_gracefully",
            "has_timeout_protection",
            "avoids_risky_combinations",
        ],
        "coherence": [
            "logical_agent_sequence",
            "proper_data_flow",
            "no_conflicting_actions",
        ],
    }

    return criteria_map.get(dimension, [])


def _fill_missing_defaults(result: Dict[str, Dict[str, bool]]) -> None:
    """
    Fill in missing criteria with default False values.

    Modifies result dict in place.

    Args:
        result: Nested dict to fill with defaults
    """
    for dimension, expected_criteria in [
        ("completeness", _get_dimension_criteria("completeness")),
        ("efficiency", _get_dimension_criteria("efficiency")),
        ("safety", _get_dimension_criteria("safety")),
        ("coherence", _get_dimension_criteria("coherence")),
    ]:
        if dimension not in result:
            result[dimension] = {}

        for criterion in expected_criteria:
            if criterion not in result[dimension]:
                result[dimension][criterion] = False
                logger.debug(f"Using default False for {dimension}.{criterion}")
