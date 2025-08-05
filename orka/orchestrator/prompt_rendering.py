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
        Render a Jinja2 template string with comprehensive error handling.

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

        try:
            # Enhance payload for better template rendering
            enhanced_payload = self._enhance_payload_for_templates(payload)

            # Render template with fault tolerance
            template = Template(template_str)
            rendered = template.render(**enhanced_payload)

            # ✅ FIX: Replace unresolved variables with empty strings
            import logging
            import re

            logger = logging.getLogger(__name__)
            unresolved_pattern = r"\{\{\s*[^}]+\s*\}\}"
            unresolved_vars = re.findall(unresolved_pattern, rendered)

            if unresolved_vars:
                logger.debug(
                    f"Replacing {len(unresolved_vars)} unresolved variables with empty strings: {unresolved_vars}"
                )
                # Replace all unresolved variables with empty strings
                rendered = re.sub(unresolved_pattern, "", rendered)
                # Clean up any resulting double spaces or newlines
                rendered = re.sub(r"\s+", " ", rendered).strip()

            return rendered

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Template rendering failed, attempting fallback: {e}")
            logger.debug(f"- Template: {template_str}")
            logger.debug(
                f"Context keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}"
            )

            # ✅ Fallback: Replace all template variables with empty strings and return
            import re

            fallback_rendered = re.sub(r"\{\{\s*[^}]+\s*\}\}", "", template_str)
            fallback_rendered = re.sub(r"\s+", " ", fallback_rendered).strip()
            logger.warning(f"Using fallback rendering: '{fallback_rendered}'")
            return fallback_rendered

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

        # Add helper functions for template use
        enhanced_payload.update(self._get_template_helper_functions(enhanced_payload))

        return enhanced_payload

    def _get_template_helper_functions(self, payload):
        """
        Create helper functions available in Jinja2 templates for easier variable access.

        These functions provide a cleaner, more maintainable way to access complex
        nested data structures in YAML workflow templates.

        Returns:
            dict: Dictionary of helper functions for template context
        """

        def get_input():
            """Get the main input string, handling nested input structures."""
            if "input" in payload:
                input_data = payload["input"]
                if isinstance(input_data, dict):
                    return input_data.get("input", str(input_data))
                return str(input_data)
            return ""

        def get_loop_number():
            """Get the current loop number."""
            if "loop_number" in payload:
                return payload["loop_number"]
            if "input" in payload and isinstance(payload["input"], dict):
                return payload["input"].get("loop_number", 1)
            return 1

        def has_past_loops():
            """Check if there are past loops available."""
            past_loops = get_past_loops()
            return len(past_loops) > 0

        def get_past_loops():
            """Get the past loops list."""
            # Try multiple locations for past_loops data
            if "input" in payload and isinstance(payload["input"], dict):
                prev_outputs = payload["input"].get("previous_outputs", {})
                if "past_loops" in prev_outputs:
                    return prev_outputs["past_loops"]

            # Also check direct previous_outputs
            prev_outputs = payload.get("previous_outputs", {})
            if "past_loops" in prev_outputs:
                return prev_outputs["past_loops"]

            return []

        def get_past_insights():
            """Get insights from the last past loop."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                return last_loop.get("synthesis_insights", "No synthesis insights found")
            return "No synthesis insights found"

        def get_past_loop_data(key):
            """Get specific data from the last past loop."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                return last_loop.get(key, f"No {key} found")
            return f"No {key} found"

        def get_agent_response(agent_name):
            """
            Get an agent's response from previous_outputs, handling fork executions and complex workflows.

            This function searches through:
            1. Direct previous_outputs[agent_name]
            2. Fork results in previous_outputs
            3. Nested workflow results
            4. Join node results
            """
            previous_outputs = payload.get("previous_outputs", {})

            # First, try direct access
            if agent_name in previous_outputs:
                agent_result = previous_outputs[agent_name]
                if isinstance(agent_result, dict):
                    return agent_result.get("response", "")
                return str(agent_result)

            # Search through all previous outputs for nested results (fork executions, etc.)
            for key, value in previous_outputs.items():
                if isinstance(value, dict):
                    # Check if this is a nested result containing our agent
                    if agent_name in value:
                        nested_result = value[agent_name]
                        if isinstance(nested_result, dict):
                            return nested_result.get("response", "")
                        return str(nested_result)

                    # Check if this has a "result" field containing our agent
                    if "result" in value and isinstance(value["result"], dict):
                        if agent_name in value["result"]:
                            nested_result = value["result"][agent_name]
                            if isinstance(nested_result, dict):
                                return nested_result.get("response", "")
                            return str(nested_result)

                    # Check for fork group results
                    if "results" in value and isinstance(value["results"], dict):
                        if agent_name in value["results"]:
                            nested_result = value["results"][agent_name]
                            if isinstance(nested_result, dict):
                                return nested_result.get("response", "")
                            return str(nested_result)

            return f"No response found for {agent_name}"

        def get_fork_responses(fork_group_name):
            """
            Get all responses from a fork group execution.
            Returns a dictionary of {agent_name: response} for all agents in the fork.
            """
            previous_outputs = payload.get("previous_outputs", {})

            # Look for fork group results
            if fork_group_name in previous_outputs:
                fork_result = previous_outputs[fork_group_name]
                if isinstance(fork_result, dict):
                    responses = {}

                    # Check direct agent results
                    for key, value in fork_result.items():
                        if isinstance(value, dict) and "response" in value:
                            responses[key] = value["response"]

                    # Check nested results structure
                    if "result" in fork_result and isinstance(fork_result["result"], dict):
                        for key, value in fork_result["result"].items():
                            if isinstance(value, dict) and "response" in value:
                                responses[key] = value["response"]

                    # Check results field
                    if "results" in fork_result and isinstance(fork_result["results"], dict):
                        for key, value in fork_result["results"].items():
                            if isinstance(value, dict) and "response" in value:
                                responses[key] = value["response"]

                    return responses

            return {}

        def get_progressive_response():
            """Get progressive agent response using robust search."""
            return get_agent_response("progressive_refinement") or get_agent_response(
                "radical_progressive"
            )

        def get_conservative_response():
            """Get conservative agent response using robust search."""
            return get_agent_response("conservative_refinement") or get_agent_response(
                "traditional_conservative"
            )

        def get_realist_response():
            """Get realist agent response using robust search."""
            return get_agent_response("realist_refinement") or get_agent_response(
                "pragmatic_realist"
            )

        def get_purist_response():
            """Get purist agent response using robust search."""
            return get_agent_response("purist_refinement") or get_agent_response("ethical_purist")

        def get_collaborative_responses():
            """Get all collaborative refinement responses as a formatted string."""
            responses = []

            progressive = get_progressive_response()
            if progressive and progressive != "No response found for progressive_refinement":
                responses.append(f"Progressive: {progressive}")

            conservative = get_conservative_response()
            if conservative and conservative != "No response found for conservative_refinement":
                responses.append(f"Conservative: {conservative}")

            realist = get_realist_response()
            if realist and realist != "No response found for realist_refinement":
                responses.append(f"Realist: {realist}")

            purist = get_purist_response()
            if purist and purist != "No response found for purist_refinement":
                responses.append(f"Purist: {purist}")

            return "\n\n".join(responses) if responses else "No collaborative responses available"

        def safe_get_response(agent_name, fallback="No response available"):
            """Safely get an agent response with fallback."""
            response = get_agent_response(agent_name)
            if response and not response.startswith("No response found"):
                return response
            return fallback

        def format_memory_query(perspective, topic=None):
            """Format a memory query for a specific perspective."""
            if topic is None:
                topic = get_input()
            return f"{perspective.title()} perspective on: {topic}"

        def get_current_topic():
            """Get the current topic being discussed."""
            return get_input()

        def get_round_info():
            """Get formatted round information for display."""
            loop_num = get_loop_number()
            if has_past_loops():
                last_loop = get_past_loops()[-1]
                return last_loop.get("round", str(loop_num))
            return str(loop_num)

        def safe_get(obj, key, default=""):
            """Safely get a value from an object with a default."""
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        def joined_results():
            """Get joined results from fork operations if available."""
            previous_outputs = payload.get("previous_outputs", {})
            for agent_name, agent_result in previous_outputs.items():
                if isinstance(agent_result, dict) and "joined_results" in agent_result:
                    return agent_result["joined_results"]
            return []

        def get_my_past_memory(agent_type):
            """Get past memory entries for a specific agent type."""
            memories = payload.get("memories", [])
            if not memories:
                return "No past memory available"

            # Filter memories by agent type
            my_memories = []
            for memory in memories:
                if isinstance(memory, dict):
                    metadata = memory.get("metadata", {})
                    if metadata.get("agent_type") == agent_type:
                        my_memories.append(memory.get("content", ""))

            if my_memories:
                return "\n".join(my_memories[-3:])  # Last 3 memories
            return "No past memory for this agent type"

        def get_my_past_decisions(agent_name):
            """Get past loop decisions for a specific agent."""
            past_loops = get_past_loops()
            if not past_loops:
                return "No past decisions available"

            my_decisions = []
            for loop in past_loops:
                if agent_name in loop:
                    my_decisions.append(f"Loop {loop.get('round', '?')}: {loop[agent_name]}")

            if my_decisions:
                return "\n".join(my_decisions[-2:])  # Last 2 decisions
            return f"No past decisions for {agent_name}"

        def get_agent_memory_context(agent_type, agent_name):
            """Get comprehensive context for an agent including memory and decisions."""
            memory = get_my_past_memory(agent_type)
            decisions = get_my_past_decisions(agent_name)

            context = []
            if memory != "No past memory available":
                context.append(f"PAST MEMORY:\n{memory}")
            if decisions != f"No past decisions for {agent_name}":
                context.append(f"PAST DECISIONS:\n{decisions}")

            return "\n\n".join(context) if context else "No past context available"

        def get_debate_evolution():
            """Get how the debate has evolved across loops."""
            past_loops = get_past_loops()
            if not past_loops:
                return "First round of debate"

            evolution = []
            for i, loop in enumerate(past_loops):
                score = loop.get("agreement_score", "Unknown")
                evolution.append(f"Round {i+1}: Agreement {score}")

            return " → ".join(evolution)

        return {
            # Input helpers
            "get_input": get_input,
            "get_current_topic": get_current_topic,
            # Loop helpers
            "get_loop_number": get_loop_number,
            "has_past_loops": has_past_loops,
            "get_past_loops": get_past_loops,
            "get_past_insights": get_past_insights,
            "get_past_loop_data": get_past_loop_data,
            "get_round_info": get_round_info,
            # Agent helpers
            "get_agent_response": get_agent_response,
            "get_fork_responses": get_fork_responses,
            "get_progressive_response": get_progressive_response,
            "get_conservative_response": get_conservative_response,
            "get_realist_response": get_realist_response,
            "get_purist_response": get_purist_response,
            "get_collaborative_responses": get_collaborative_responses,
            "safe_get_response": safe_get_response,
            "joined_results": joined_results,
            # Memory helpers
            "format_memory_query": format_memory_query,
            "get_my_past_memory": get_my_past_memory,
            "get_my_past_decisions": get_my_past_decisions,
            "get_agent_memory_context": get_agent_memory_context,
            "get_debate_evolution": get_debate_evolution,
            # Utility helpers
            "safe_get": safe_get,
        }

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
            # ✅ FIX: Use already-rendered formatted_prompt from payload if available
            elif "formatted_prompt" in payload and payload["formatted_prompt"]:
                payload_out["formatted_prompt"] = payload["formatted_prompt"]
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
