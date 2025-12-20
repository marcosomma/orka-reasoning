from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, cast

logger = logging.getLogger(__name__)


def is_valid_boolean_structure(data: Any) -> bool:
    """
    Check if data contains valid boolean evaluation structure.

    Mirrors LoopNode._is_valid_boolean_structure behavior.
    """
    if not isinstance(data, dict):
        return False

    # Accept a wider variety of boolean evaluation structures.
    # Valid if data is a dict with at least one nested dict that contains
    # at least one boolean-like value (bool or string/number that can
    # be interpreted as boolean).
    def _has_boolean_like_values(d: dict) -> bool:
        for v in d.values():
            if isinstance(v, bool):
                return True
            if isinstance(v, str) and v.strip().lower() in (
                "true",
                "yes",
                "1",
                "pass",
                "passed",
                "✓",
            ):
                return True
            if isinstance(v, (int, float)) and v != 0:
                return True
        return False

    nested_dims = 0
    single_dim_count = 0
    for _, value in data.items():
        if isinstance(value, dict) and _has_boolean_like_values(value):
            nested_dims += 1
            single_dim_count = len(value)

    # If canonical dimensions are present, keep the former stricter rule
    canonical_present = any(d in data for d in ["completeness", "efficiency", "safety", "coherence"])
    if canonical_present:
        return nested_dims >= 2

    # For custom contexts: accept if at least 2 nested dimensions,
    # or a single dimension that provides at least 2 boolean criteria.
    if nested_dims >= 2:
        return True
    if nested_dims == 1 and single_dim_count >= 2:
        return True

    return False


def extract_boolean_from_text(text: str) -> Optional[Dict[str, Dict[str, bool]]]:
    """
    Extract boolean evaluations from text.

    Mirrors LoopNode._extract_boolean_from_text behavior:
    - extracts first {...} blob
    - normalizes Python dict literals to JSON
    - lowercases top-level keys
    - validates structure
    """
    try:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None

        json_text = json_match.group(0)

        # Normalize Python syntax to JSON
        json_text = re.sub(r"\bTrue\b", "true", json_text)
        json_text = re.sub(r"\bFalse\b", "false", json_text)
        json_text = re.sub(r"\bNone\b", "null", json_text)
        json_text = json_text.replace("'", '"')

        data = json.loads(json_text)

        # Convert UPPERCASE keys to lowercase
        if isinstance(data, dict):
            normalized_data: Dict[str, Dict[str, bool]] = {}
            for key, value in data.items():
                normalized_key = str(key).lower()
                if isinstance(value, dict):
                    normalized_data[normalized_key] = {k: v for k, v in value.items()}
                else:
                    normalized_data[normalized_key] = cast(Dict[str, bool], value)
            data = normalized_data
            logger.debug("Normalized keys to lowercase: %s", list(data.keys()))

        if is_valid_boolean_structure(data):
            logger.info("✅ Successfully extracted boolean evaluations from text")
            return cast(Dict[str, Dict[str, bool]], data)

        logger.debug("❌ Invalid boolean structure. Keys found: %s", list(data.keys()) if isinstance(data, dict) else [])
        return None

    except json.JSONDecodeError as e:
        logger.debug("JSON parse failed: %s", e)
        return None
    except Exception as e:
        logger.error("Boolean extraction exception: %s", e, exc_info=True)
        return None


