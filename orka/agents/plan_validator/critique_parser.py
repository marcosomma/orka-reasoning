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
Critique Parser for Plan Validator
===================================

Parses and structures LLM-generated critique responses into a standardized format.
Handles both well-formed JSON responses and fallback text parsing.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Hardcoded validation dimensions
VALIDATION_DIMENSIONS = ["completeness", "efficiency", "safety", "coherence", "fallback"]


def parse_critique(response: str) -> Dict[str, Any]:
    """
    Parse LLM critique response into structured format.

    Attempts to extract JSON from the response. If that fails, uses
    text-based extraction with fallback values.

    Args:
        response: Raw LLM response text

    Returns:
        Dict containing:
            - validation_score: float (0.0-1.0)
            - overall_assessment: str (APPROVED/NEEDS_IMPROVEMENT/REJECTED)
            - critiques: dict of dimension critiques
            - recommended_changes: list of strings
            - approval_confidence: float
            - rationale: str
    """
    logger.debug("Parsing critique response")

    # Try to extract JSON first
    json_data = _extract_json_from_text(response)

    if json_data and "validation_score" in json_data:
        logger.debug("Successfully extracted JSON critique")
        return _structure_json_critique(json_data)

    # Fallback to text extraction
    logger.debug("Using fallback text extraction")
    return _structure_fallback_critique(response)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text using regex.

    Handles JSON in markdown code blocks and plain JSON.

    Args:
        text: Text potentially containing JSON

    Returns:
        Parsed JSON dict or None if extraction fails
    """
    # Try markdown code block first
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not json_match:
        # Try plain JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)

    if json_match:
        try:
            parsed = json.loads(
                json_match.group(1) if json_match.lastindex else json_match.group(0)
            )
            if isinstance(parsed, dict):
                return parsed
            return None
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode failed: {e}")
            return None

    return None


def _extract_score_from_text(text: str) -> float:
    """
    Extract validation score from text using regex patterns.

    Args:
        text: Text containing score information

    Returns:
        float: Extracted score (0.0-1.0), defaults to 0.5 if not found
    """
    patterns = [
        r"validation_score[\"']?\s*:\s*([0-9.]+)",
        r"VALIDATION_SCORE:\s*([0-9.]+)",
        r"score:\s*([0-9.]+)",
        r"Score:\s*([0-9.]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
            except ValueError:
                continue

    logger.warning("Could not extract validation score, using default 0.5")
    return 0.5


def _structure_json_critique(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structure a well-formed JSON critique response.

    Args:
        json_data: Parsed JSON from LLM

    Returns:
        Standardized critique dict
    """
    validation_score = float(json_data.get("validation_score", 0.5))

    return {
        "validation_score": validation_score,
        "overall_assessment": json_data.get(
            "overall_assessment",
            _score_to_assessment(validation_score),
        ),
        "critiques": _structure_dimension_critiques(json_data.get("critiques", {})),
        "recommended_changes": json_data.get("recommended_changes", []),
        "approval_confidence": float(json_data.get("approval_confidence", validation_score)),
        "rationale": json_data.get("rationale", "No detailed rationale provided"),
    }


def _structure_fallback_critique(response: str) -> Dict[str, Any]:
    """
    Structure critique from plain text response (fallback).

    Args:
        response: Raw text response

    Returns:
        Standardized critique dict with default values
    """
    validation_score = _extract_score_from_text(response)

    return {
        "validation_score": validation_score,
        "overall_assessment": _score_to_assessment(validation_score),
        "critiques": _create_default_dimension_critiques(validation_score),
        "recommended_changes": [],
        "approval_confidence": validation_score,
        "rationale": response[:500] if len(response) > 500 else response,
    }


def _structure_dimension_critiques(critiques_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Structure dimension-specific critiques.

    Args:
        critiques_data: Raw critiques dict from JSON

    Returns:
        Structured critiques with all dimensions
    """
    structured = {}

    for dimension in VALIDATION_DIMENSIONS:
        if dimension in critiques_data:
            dim_data = critiques_data[dimension]
            structured[dimension] = {
                "score": float(dim_data.get("score", 0.5)),
                "issues": dim_data.get("issues", []),
                "suggestions": dim_data.get("suggestions", []),
            }
        else:
            structured[dimension] = {
                "score": 0.5,
                "issues": [],
                "suggestions": [],
            }

    return structured


def _create_default_dimension_critiques(score: float) -> Dict[str, Dict[str, Any]]:
    """
    Create default dimension critiques when parsing fails.

    Args:
        score: Overall validation score to use for all dimensions

    Returns:
        Default critiques dict
    """
    return {
        dimension: {
            "score": score,
            "issues": [],
            "suggestions": [],
        }
        for dimension in VALIDATION_DIMENSIONS
    }


def _score_to_assessment(score: float) -> str:
    """
    Convert numeric score to assessment category.

    Args:
        score: Validation score (0.0-1.0)

    Returns:
        Assessment string: APPROVED, NEEDS_IMPROVEMENT, or REJECTED
    """
    if score >= 0.85:
        return "APPROVED"
    elif score >= 0.7:
        return "NEEDS_IMPROVEMENT"
    else:
        return "REJECTED"
