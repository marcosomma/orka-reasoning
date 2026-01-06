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
Utility Helper Functions
========================

General utility helper functions for templates.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_utility_helpers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create utility helper functions for Jinja2 templates.

    Args:
        payload: The current execution payload

    Returns:
        Dictionary of utility helper functions
    """

    def safe_get(obj, key, default=""):
        """Safely get a value from an object with a default."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    def safe_str(v):
        """Safe string conversion - returns empty string for None."""
        return "" if v is None else str(v)

    def has_context(agent_name: str) -> bool:
        """Return True if there is any context for the given agent name."""
        prev_outputs = payload.get("previous_outputs", {})

        # Direct previous outputs check
        if agent_name in prev_outputs:
            val = prev_outputs[agent_name]
            return bool(val)

        # Input-level context
        if "input" in payload and isinstance(payload["input"], dict):
            input_data = payload["input"]
            if input_data.get("conversation_context"):
                return True

        # Search memories
        memories = payload.get("memories", [])
        if isinstance(memories, list):
            for m in memories:
                if isinstance(m, dict) and m.get("agent_name") == agent_name:
                    return True

        return False

    return {
        "safe_get": safe_get,
        "safe_str": safe_str,
        "has_context": has_context,
    }


def normalize_bool(value) -> bool:
    """
    Normalize a value to boolean with support for complex agent responses.

    Args:
        value: The value to normalize (bool, str, dict, or other)

    Returns:
        bool: The normalized boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["true", "yes"]
    if isinstance(value, dict):
        if "result" in value:
            nested_result = value["result"]
            if isinstance(nested_result, dict):
                if "result" in nested_result:
                    return normalize_bool(nested_result["result"])
                elif "response" in nested_result:
                    return normalize_bool(nested_result["response"])
            else:
                return normalize_bool(nested_result)
        elif "response" in value:
            return normalize_bool(value["response"])
    return False

