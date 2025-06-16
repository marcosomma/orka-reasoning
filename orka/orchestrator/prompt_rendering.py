# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Prompt Rendering
===============

Handles Jinja2 template rendering for dynamic prompt construction.
"""

from jinja2 import Template


class PromptRenderer:
    """
    Handles prompt rendering and template processing.
    """

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with the given payload.
        Used for dynamic prompt construction.
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead.",
            )
        return Template(template_str).render(**payload)

    def _add_prompt_to_payload(self, agent, payload_out, payload):
        """
        Add prompt and formatted_prompt to payload_out if agent has a prompt.
        Also capture LLM response details (confidence, internal_reasoning) if available.

        Args:
            agent: The agent instance
            payload_out: The payload dictionary to modify
            payload: The context payload for template rendering
        """
        if hasattr(agent, "prompt") and agent.prompt:
            payload_out["prompt"] = agent.prompt

            # Check if agent has an enhanced formatted_prompt (e.g., from binary/classification agents)
            if hasattr(agent, "_last_formatted_prompt") and agent._last_formatted_prompt:
                payload_out["formatted_prompt"] = agent._last_formatted_prompt
            else:
                # If the agent has a prompt, render it with the current payload context
                try:
                    formatted_prompt = self.render_prompt(agent.prompt, payload)
                    payload_out["formatted_prompt"] = formatted_prompt
                except Exception:
                    # If rendering fails, keep the original prompt
                    payload_out["formatted_prompt"] = agent.prompt

        # Capture LLM response details if available (for binary/classification agents)
        if hasattr(agent, "_last_response") and agent._last_response:
            payload_out["response"] = agent._last_response
        if hasattr(agent, "_last_confidence") and agent._last_confidence:
            payload_out["confidence"] = agent._last_confidence
        if hasattr(agent, "_last_internal_reasoning") and agent._last_internal_reasoning:
            payload_out["internal_reasoning"] = agent._last_internal_reasoning

    def _render_agent_prompt(self, agent, payload):
        """
        Render agent's prompt and add formatted_prompt to payload for agent execution.

        Args:
            agent: The agent instance
            payload: The payload dictionary to modify
        """
        if hasattr(agent, "prompt") and agent.prompt:
            try:
                formatted_prompt = self.render_prompt(agent.prompt, payload)
                payload["formatted_prompt"] = formatted_prompt
            except Exception:
                # If rendering fails, use the original prompt
                payload["formatted_prompt"] = agent.prompt

    @staticmethod
    def normalize_bool(value):
        """
        Normalize a value to boolean.
        Accepts bools, strings like 'true', 'yes', etc., or complex objects with 'result' field.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "yes"]
        if isinstance(value, dict):
            # For complex agent responses, try multiple extraction paths
            # Path 1: Direct result field (for nested agent responses)
            if "result" in value:
                nested_result = value["result"]
                if isinstance(nested_result, dict):
                    # Check for result.result (binary agents) or result.response
                    if "result" in nested_result:
                        return PromptRenderer.normalize_bool(nested_result["result"])
                    elif "response" in nested_result:
                        return PromptRenderer.normalize_bool(nested_result["response"])
                else:
                    # Direct boolean/string result
                    return PromptRenderer.normalize_bool(nested_result)
            # Path 2: Direct response field
            elif "response" in value:
                return PromptRenderer.normalize_bool(value["response"])
        return False
