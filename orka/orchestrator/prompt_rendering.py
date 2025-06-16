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
Prompt Rendering Module
=======================

This module provides Jinja2-based template rendering capabilities for dynamic prompt
construction in the OrKa orchestration framework. It handles the rendering of agent
prompts with dynamic context data and provides utilities for processing agent responses.

The :class:`PromptRenderer` class is integrated into the main orchestrator through
multiple inheritance composition, providing seamless template processing capabilities
throughout the workflow execution.

Key Features
------------

**Dynamic Template Rendering**
    Uses Jinja2 templating engine for flexible prompt construction

**Context Integration**
    Automatically injects previous agent outputs and workflow state into templates

**Response Processing**
    Handles complex agent response structures and extracts relevant data

**Error Resilience**
    Gracefully handles template rendering failures to prevent workflow interruption

Usage Example
-------------

.. code-block:: python

    from orka.orchestrator.prompt_rendering import PromptRenderer

    renderer = PromptRenderer()

    # Render a template with context
    result = renderer.render_prompt(
        "Answer this question: {{ input }} using {{ previous_outputs.retriever }}",
        {
            "input": "What is Python?",
            "previous_outputs": {"retriever": "Python is a programming language"}
        }
    )
"""

from jinja2 import Template


class PromptRenderer:
    """
    Handles prompt rendering and template processing using Jinja2.

    This class provides methods for rendering dynamic prompts with context data,
    processing agent responses, and managing template-related operations within
    the orchestrator workflow.

    The renderer supports complex template structures and provides robust error
    handling to ensure that template failures don't interrupt workflow execution.
    """

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with the given payload.

        This method is the core template rendering functionality, taking a template
        string and context payload to produce a rendered prompt for agent execution.

        Args:
            template_str (str): The Jinja2 template string to render
            payload (dict): Context data for template variable substitution

        Returns:
            str: The rendered template with variables substituted

        Raises:
            ValueError: If template_str is not a string
            jinja2.TemplateError: If template syntax is invalid

        Example:
            .. code-block:: python

                template = "Hello {{ name }}, you have {{ count }} messages"
                context = {"name": "Alice", "count": 5}
                result = renderer.render_prompt(template, context)
                # Returns: "Hello Alice, you have 5 messages"
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead.",
            )
        return Template(template_str).render(**payload)

    def _add_prompt_to_payload(self, agent, payload_out, payload):
        """
        Add prompt and formatted_prompt to payload_out if agent has a prompt.

        This internal method enriches the output payload with prompt information
        and captures additional LLM response details when available. It's used
        during workflow execution to preserve prompt and response metadata.

        Args:
            agent: The agent instance being processed
            payload_out (dict): The output payload dictionary to modify
            payload (dict): The current context payload for template rendering

        Note:
            This method also captures enhanced response data including confidence
            scores and internal reasoning when available from specialized agents.
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

        This method prepares the agent's prompt for execution by rendering any
        template variables and adding the result to the payload under the
        'formatted_prompt' key.

        Args:
            agent: The agent instance whose prompt should be rendered
            payload (dict): The payload dictionary to modify with the rendered prompt

        Note:
            If template rendering fails, the original prompt is used as a fallback
            to ensure workflow continuity.
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
        Normalize a value to boolean with support for complex agent responses.

        This utility method handles the conversion of various data types to boolean
        values, with special support for complex agent response structures that may
        contain nested results.

        Args:
            value: The value to normalize (bool, str, dict, or other)

        Returns:
            bool: The normalized boolean value

        Supported Input Types:
            * **bool**: Returned as-is
            * **str**: 'true', 'yes' (case-insensitive) → True, others → False
            * **dict**: Extracts from 'result' or 'response' keys with recursive processing
            * **other**: Defaults to False

        Example:
            .. code-block:: python

                # Simple cases
                assert PromptRenderer.normalize_bool(True) == True
                assert PromptRenderer.normalize_bool("yes") == True
                assert PromptRenderer.normalize_bool("false") == False

                # Complex agent response
                response = {"result": {"response": "true"}}
                assert PromptRenderer.normalize_bool(response) == True
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
