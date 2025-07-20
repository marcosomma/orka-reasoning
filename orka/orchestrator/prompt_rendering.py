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

        # Enhance payload for better template rendering
        enhanced_payload = self._enhance_payload_for_templates(payload)

        return Template(template_str).render(**enhanced_payload)

    def _enhance_payload_for_templates(self, payload):
        """
        Enhance the payload to make template rendering more robust and generic.

        This method ensures that previous_outputs can be accessed in multiple ways
        to support different template patterns used across workflows.
        """
        enhanced_payload = payload.copy()

        # Expose key properties from input object at root level
        # Templates expect {{ loop_number }} but it's nested at {{ input.loop_number }}
        if "input" in enhanced_payload and isinstance(enhanced_payload["input"], dict):
            input_data = enhanced_payload["input"]

            # Expose commonly used template variables at root level
            template_vars = ["loop_number", "past_loops_metadata"]
            for var in template_vars:
                if var in input_data:
                    enhanced_payload[var] = input_data[var]

        # If previous_outputs exists, enhance it for template compatibility
        if "previous_outputs" in enhanced_payload:
            original_outputs = enhanced_payload["previous_outputs"]
            enhanced_outputs = {}

            # Process each agent's output to make it more template-friendly
            for agent_id, agent_result in original_outputs.items():
                # Keep the original structure
                enhanced_outputs[agent_id] = agent_result

                # If the result has a nested structure, also provide direct access
                if isinstance(agent_result, dict):
                    # Handle nested result structures
                    if "result" in agent_result:
                        result_data = agent_result["result"]
                        if isinstance(result_data, dict):
                            # For LLM agents, expose response directly
                            if "response" in result_data:
                                enhanced_outputs[agent_id] = {
                                    "response": result_data["response"],
                                    "confidence": result_data.get("confidence", "0.0"),
                                    "internal_reasoning": result_data.get("internal_reasoning", ""),
                                    "_metrics": result_data.get("_metrics", {}),
                                    "formatted_prompt": result_data.get("formatted_prompt", ""),
                                }
                            # For memory agents, expose memories directly
                            elif "memories" in result_data:
                                enhanced_outputs[agent_id] = {
                                    "memories": result_data["memories"],
                                    "query": result_data.get("query", ""),
                                    "backend": result_data.get("backend", ""),
                                    "search_type": result_data.get("search_type", ""),
                                    "num_results": result_data.get("num_results", 0),
                                }
                            else:
                                # For other result types, use as is
                                enhanced_outputs[agent_id] = result_data
                    else:
                        # If no nested result, check for direct response fields
                        if "response" in agent_result:
                            enhanced_outputs[agent_id] = {
                                "response": agent_result["response"],
                                "confidence": agent_result.get("confidence", "0.0"),
                                "internal_reasoning": agent_result.get("internal_reasoning", ""),
                                "_metrics": agent_result.get("_metrics", {}),
                                "formatted_prompt": agent_result.get("formatted_prompt", ""),
                            }
                        elif "memories" in agent_result:
                            enhanced_outputs[agent_id] = {
                                "memories": agent_result["memories"],
                                "query": agent_result.get("query", ""),
                                "backend": agent_result.get("backend", ""),
                                "search_type": agent_result.get("search_type", ""),
                                "num_results": agent_result.get("num_results", 0),
                            }
                        elif "merged" in agent_result:
                            # Handle merged results from join nodes
                            merged_results = agent_result["merged"]
                            if isinstance(merged_results, dict):
                                for merged_agent_id, merged_result in merged_results.items():
                                    if isinstance(merged_result, dict):
                                        # For LLM agents, expose response directly
                                        if "response" in merged_result:
                                            enhanced_outputs[merged_agent_id] = {
                                                "response": merged_result["response"],
                                                "confidence": merged_result.get(
                                                    "confidence", "0.0"
                                                ),
                                                "internal_reasoning": merged_result.get(
                                                    "internal_reasoning", ""
                                                ),
                                                "_metrics": merged_result.get("_metrics", {}),
                                                "formatted_prompt": merged_result.get(
                                                    "formatted_prompt", ""
                                                ),
                                            }
                                        # For memory agents, expose memories directly
                                        elif "memories" in merged_result:
                                            enhanced_outputs[merged_agent_id] = {
                                                "memories": merged_result["memories"],
                                                "query": merged_result.get("query", ""),
                                                "backend": merged_result.get("backend", ""),
                                                "search_type": merged_result.get("search_type", ""),
                                                "num_results": merged_result.get("num_results", 0),
                                            }
                                        else:
                                            # For other result types, use as is
                                            enhanced_outputs[merged_agent_id] = merged_result
                                    else:
                                        # If not a dict, use as is
                                        enhanced_outputs[merged_agent_id] = merged_result
                        else:
                            # Keep other fields as is
                            enhanced_outputs[agent_id] = agent_result
                else:
                    # If not a dict, keep as is
                    enhanced_outputs[agent_id] = agent_result

            enhanced_payload["previous_outputs"] = enhanced_outputs

        return enhanced_payload

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
