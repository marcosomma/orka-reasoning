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
Loop Helper Functions
=====================

Helper functions for accessing loop data in templates.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_loop_helpers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create loop-related helper functions for Jinja2 templates.

    Args:
        payload: The current execution payload

    Returns:
        Dictionary of loop helper functions
    """

    def get_loop_number():
        """Get the current loop number."""
        if "loop_number" in payload:
            return payload["loop_number"]
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"].get("loop_number", 1)
        return 1

    def get_past_loops():
        """Get the past loops list from any loop node."""
        # Try multiple locations for past_loops data
        if "input" in payload and isinstance(payload["input"], dict):
            prev_outputs = payload["input"].get("previous_outputs", {})
            if "past_loops" in prev_outputs:
                return prev_outputs["past_loops"]

        # Also check direct previous_outputs
        prev_outputs = payload.get("previous_outputs", {})
        if "past_loops" in prev_outputs:
            return prev_outputs["past_loops"]

        # Generic search through all previous outputs for loop results
        for agent_name, agent_result in prev_outputs.items():
            if isinstance(agent_result, dict):
                if "past_loops" in agent_result:
                    return agent_result["past_loops"]
                if "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    if "past_loops" in nested_result:
                        return nested_result["past_loops"]

        return []

    def has_past_loops():
        """Check if there are past loops available."""
        return len(get_past_loops()) > 0

    def get_past_insights():
        """Get insights from the last past loop."""
        past_loops = get_past_loops()
        if past_loops:
            last_loop = past_loops[-1]
            return last_loop.get("synthesis_insights", "No synthesis insights found")
        return "No synthesis insights found"

    def get_past_loop_data(key=None):
        """Get data from the last past loop."""
        past_loops = get_past_loops()
        if past_loops:
            last_loop = past_loops[-1]
            if key is None:
                return str(last_loop)
            return last_loop.get(key, f"No {key} found")
        return "No past loops found"

    def get_round_info():
        """Get formatted round information for display."""
        loop_num = get_loop_number()
        if has_past_loops():
            last_loop = get_past_loops()[-1]
            return last_loop.get("round", str(loop_num))
        return str(loop_num)

    def get_past_loops_metadata():
        """Get past loops metadata for template rendering."""
        if "past_loops_metadata" in payload:
            return payload["past_loops_metadata"]
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"].get("past_loops_metadata", {})
        return {}

    def get_score_threshold():
        """Get the score threshold for loop validation."""
        if "score_threshold" in payload:
            return payload["score_threshold"]
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"].get("score_threshold", 0.8)
        return 0.8

    def get_loop_rounds():
        """Get the number of completed loop rounds."""
        past_loops = get_past_loops()
        if past_loops:
            return len(past_loops)

        prev_outputs = payload.get("previous_outputs", {})
        for agent_name, agent_result in prev_outputs.items():
            if isinstance(agent_result, dict):
                if "loops_completed" in agent_result:
                    return agent_result["loops_completed"]
                if "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    if "loops_completed" in nested_result:
                        return nested_result["loops_completed"]
        return "Unknown"

    def get_final_score():
        """Get the final score from any loop node."""
        past_loops = get_past_loops()
        if past_loops:
            last_loop = past_loops[-1]
            for score_field in ["agreement_score", "final_score", "score"]:
                if score_field in last_loop:
                    return last_loop[score_field]

        prev_outputs = payload.get("previous_outputs", {})
        for agent_name, agent_result in prev_outputs.items():
            if isinstance(agent_result, dict):
                for key, value in agent_result.items():
                    if "score" in key.lower() and isinstance(value, (int, float, str)):
                        try:
                            if isinstance(value, str):
                                return float(value)
                            return value
                        except (ValueError, TypeError):
                            continue

                if "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    for key, value in nested_result.items():
                        if "score" in key.lower() and isinstance(value, (int, float, str)):
                            try:
                                if isinstance(value, str):
                                    return float(value)
                                return value
                            except (ValueError, TypeError):
                                continue
        return "Unknown"

    def get_loop_status():
        """Get the status of any loop execution."""
        prev_outputs = payload.get("previous_outputs", {})
        for agent_name, agent_result in prev_outputs.items():
            if isinstance(agent_result, dict):
                if "status" in agent_result:
                    return agent_result["status"]
                if "result" in agent_result and isinstance(agent_result["result"], dict):
                    nested_result = agent_result["result"]
                    if "status" in nested_result:
                        return nested_result["status"]
        return "completed"

    def get_loop_output(agent_id: str, prev_outputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get the complete output dict from a LoopNode agent."""
        previous_outputs = prev_outputs if prev_outputs is not None else payload.get("previous_outputs", {})

        if not previous_outputs:
            logger.warning(f"get_loop_output: previous_outputs is empty for agent '{agent_id}'")
            return {}

        if agent_id not in previous_outputs:
            logger.debug(f"get_loop_output: agent '{agent_id}' not found")
            return {}

        output = previous_outputs[agent_id]
        if hasattr(output, "raw"):
            output = output.raw()

        if isinstance(output, dict) and "response" in output:
            response_value = output["response"]
            if isinstance(response_value, dict):
                return response_value

        if isinstance(output, dict):
            return output

        logger.warning(f"get_loop_output: output for '{agent_id}' is not a dict")
        return {}

    return {
        "get_loop_number": get_loop_number,
        "has_past_loops": has_past_loops,
        "get_past_loops": get_past_loops,
        "get_past_loops_metadata": get_past_loops_metadata,
        "get_past_insights": get_past_insights,
        "get_past_loop_data": get_past_loop_data,
        "get_round_info": get_round_info,
        "get_score_threshold": get_score_threshold,
        "get_loop_rounds": get_loop_rounds,
        "get_final_score": get_final_score,
        "get_loop_status": get_loop_status,
        "get_loop_output": get_loop_output,
    }

