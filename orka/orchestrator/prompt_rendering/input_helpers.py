# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Input Helper Functions
======================

Helper functions for accessing input data in templates.
"""

from typing import Any, Dict


def create_input_helpers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create input-related helper functions for Jinja2 templates.

    Args:
        payload: The current execution payload

    Returns:
        Dictionary of input helper functions
    """

    def get_input():
        """Get the main input string, handling nested input structures."""
        if "input" in payload:
            input_data = payload["input"]
            if isinstance(input_data, dict):
                return input_data.get("input", str(input_data))
            return str(input_data)
        return ""

    def get_current_topic():
        """Get the current topic being discussed."""
        return get_input()

    @staticmethod
    def get_input_field(input_obj, field, default=None):
        """
        Helper to extract a field from input (dict or JSON) in Jinja2 templates.
        Usage: {{ get_input_field(input, 'fieldname') }}
        """
        if isinstance(input_obj, dict):
            return input_obj.get(field, default)
        return default

    return {
        "get_input": get_input,
        "get_current_topic": get_current_topic,
        "get_input_field": get_input_field,
    }

