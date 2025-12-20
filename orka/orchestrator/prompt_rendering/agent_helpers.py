# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Agent Helper Functions
======================

Helper functions for accessing agent responses in templates.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def create_agent_helpers(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create agent-related helper functions for Jinja2 templates.

    Args:
        payload: The current execution payload

    Returns:
        Dictionary of agent helper functions
    """

    def get_agent_response(agent_name):
        """Get an agent's response from previous_outputs safely."""
        try:
            previous_outputs = payload.get("previous_outputs", {})

            if agent_name in previous_outputs:
                agent_result = previous_outputs[agent_name]
                if hasattr(agent_result, "raw"):
                    agent_result = agent_result.raw()

                if isinstance(agent_result, dict):
                    p = agent_result.get("payload")
                    if isinstance(p, dict):
                        if "response" in p:
                            pr = p["response"]
                            if isinstance(pr, dict) and "response" in pr:
                                return str(pr["response"])
                            return str(pr)
                        if "result" in p:
                            pr = p["result"]
                            if isinstance(pr, dict) and "response" in pr:
                                return str(pr["response"])
                            return str(pr)

                    if "result" in agent_result:
                        return str(agent_result["result"])
                    elif "response" in agent_result:
                        return str(agent_result["response"])
                return str(agent_result)

            return f"No response found for {agent_name}"
        except Exception as e:
            logger.debug(f"get_agent_response error for {agent_name}: {e}")
            return f"No response found for {agent_name}"

    def safe_get_response(agent_name, fallback="No response available", prev_outputs=None):
        """Safely get an agent response with fallback."""
        try:
            if prev_outputs is not None:
                previous_outputs = prev_outputs
            else:
                previous_outputs = payload.get("previous_outputs", {})

            if agent_name in previous_outputs:
                agent_result = previous_outputs[agent_name]
                if hasattr(agent_result, "raw"):
                    agent_result = agent_result.raw()

                if isinstance(agent_result, dict):
                    p = agent_result.get("payload")
                    if isinstance(p, dict):
                        if "response" in p:
                            pr = p["response"]
                            pr = pr.get("response") if isinstance(pr, dict) and "response" in pr else pr
                            result_str = str(pr)
                            if result_str and not result_str.startswith("No response found"):
                                return result_str
                        if "result" in p:
                            pr = p["result"]
                            pr = pr.get("response") if isinstance(pr, dict) and "response" in pr else pr
                            result_str = str(pr)
                            if result_str and not result_str.startswith("No response found"):
                                return result_str

                    if "result" in agent_result:
                        result_str = str(agent_result["result"])
                        if result_str and not result_str.startswith("No response found"):
                            return result_str
                    elif "response" in agent_result:
                        result_str = str(agent_result["response"])
                        if result_str and not result_str.startswith("No response found"):
                            return result_str
                else:
                    result_str = str(agent_result)
                    if result_str and not result_str.startswith("No response found"):
                        return result_str

            return fallback
        except Exception as e:
            logger.debug(f"safe_get_response error for {agent_name}: {e}")
            return fallback

    def get_progressive_response():
        """Get progressive agent response safely."""
        return safe_get_response("progressive_refinement") or safe_get_response("radical_progressive")

    def get_conservative_response():
        """Get conservative agent response."""
        return safe_get_response("conservative_refinement") or safe_get_response("traditional_conservative")

    def get_realist_response():
        """Get realist agent response."""
        return safe_get_response("realist_refinement") or safe_get_response("pragmatic_realist")

    def get_purist_response():
        """Get purist agent response."""
        return safe_get_response("purist_refinement") or safe_get_response("ethical_purist")

    def get_collaborative_responses():
        """Get all collaborative refinement responses as a formatted string."""
        responses = []

        progressive = get_progressive_response()
        if progressive != "No response available":
            responses.append(f"Progressive: {progressive}")

        conservative = get_conservative_response()
        if conservative != "No response available":
            responses.append(f"Conservative: {conservative}")

        realist = get_realist_response()
        if realist != "No response available":
            responses.append(f"Realist: {realist}")

        purist = get_purist_response()
        if purist != "No response available":
            responses.append(f"Purist: {purist}")

        return "\n\n".join(responses) if responses else "No collaborative responses available"

    def get_fork_responses(fork_group_name=None):
        """Get all responses from a fork group execution."""
        previous_outputs = payload.get("previous_outputs", {})

        def extract_responses(fork_result):
            responses = {}
            if isinstance(fork_result, dict):
                for key, value in fork_result.items():
                    if isinstance(value, dict) and "response" in value:
                        responses[key] = value["response"]

                if "result" in fork_result and isinstance(fork_result["result"], dict):
                    for key, value in fork_result["result"].items():
                        if isinstance(value, dict) and "response" in value:
                            responses[key] = value["response"]
            return responses

        if fork_group_name:
            fork_result = previous_outputs.get(fork_group_name, {})
            return extract_responses(fork_result)

        found = {}
        for key, val in previous_outputs.items():
            candidate = extract_responses(val)
            if candidate:
                found[key] = candidate

        return found

    def joined_results():
        """Get joined results from fork operations if available."""
        previous_outputs = payload.get("previous_outputs", {})
        for agent_name, agent_result in previous_outputs.items():
            if isinstance(agent_result, dict) and "joined_results" in agent_result:
                return agent_result["joined_results"]
        return []

    return {
        "get_agent_response": get_agent_response,
        "safe_get_response": safe_get_response,
        "get_progressive_response": get_progressive_response,
        "get_conservative_response": get_conservative_response,
        "get_realist_response": get_realist_response,
        "get_purist_response": get_purist_response,
        "get_collaborative_responses": get_collaborative_responses,
        "get_fork_responses": get_fork_responses,
        "joined_results": joined_results,
    }

