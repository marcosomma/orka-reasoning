# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Simplified Prompt Rendering
===========================

This module provides a simplified prompt renderer that leverages the OrkaResponse
structure for template variables. It replaces complex response field guessing with
direct access to standardized OrkaResponse fields.

The SimplifiedPromptRenderer provides:
1. Direct access to OrkaResponse fields in templates
2. Backward compatibility with legacy response formats
3. Simplified template variable resolution
4. Enhanced debugging and error handling

Key improvements over the original prompt renderer:
- Eliminates complex field extraction logic
- Provides consistent variable naming
- Supports both OrkaResponse and legacy formats
- Better error handling for missing variables
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SimplifiedPromptRenderer:
    """
    Simplified prompt renderer that uses OrkaResponse structure for template variables.

    This renderer provides direct access to standardized response fields while
    maintaining backward compatibility with legacy response formats.
    """

    def __init__(self):
        """Initialize the simplified prompt renderer."""
        pass

    def _enhance_payload_for_templates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance payload with template-friendly variables from OrkaResponse fields.

        Args:
            payload: The execution payload containing input and previous outputs

        Returns:
            Enhanced payload with OrkaResponse-aware template variables
        """
        enhanced_payload = payload.copy()

        # Enhance previous_outputs for template access
        if "previous_outputs" in payload:
            enhanced_payload["previous_outputs"] = self._enhance_previous_outputs(
                payload["previous_outputs"]
            )

        # Add essential template helper functions
        enhanced_payload.update(self._get_template_helper_functions(enhanced_payload))

        return enhanced_payload

    def _enhance_previous_outputs(self, original_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance previous outputs with OrkaResponse-aware template variables.

        Args:
            original_outputs: Dictionary of agent outputs

        Returns:
            Enhanced outputs with standardized variable access
        """
        enhanced_outputs: dict[str, object] = {}

        for agent_id, agent_result in original_outputs.items():
            if isinstance(agent_result, dict) and "component_type" in agent_result:
                # This is an OrkaResponse - provide direct field access
                enhanced_outputs[agent_id] = {
                    # Core OrkaResponse fields
                    "result": agent_result.get("result"),
                    "status": agent_result.get("status"),
                    "error": agent_result.get("error"),
                    "confidence": agent_result.get("confidence"),
                    "internal_reasoning": agent_result.get("internal_reasoning"),
                    "formatted_prompt": agent_result.get("formatted_prompt"),
                    "execution_time_ms": agent_result.get("execution_time_ms"),
                    "token_usage": agent_result.get("token_usage"),
                    "cost_usd": agent_result.get("cost_usd"),
                    "memory_entries": agent_result.get("memory_entries"),
                    "sources": agent_result.get("sources"),
                    "trace_id": agent_result.get("trace_id"),
                    # Legacy compatibility fields
                    "response": agent_result.get("result"),  # Legacy field mapping
                    "memories": agent_result.get("memory_entries"),  # Legacy field mapping
                    "_metrics": agent_result.get("metrics", {}),  # Legacy field mapping
                    # Component metadata
                    "component_id": agent_result.get("component_id"),
                    "component_type": agent_result.get("component_type"),
                    "timestamp": agent_result.get("timestamp"),
                }

                # Remove None values for cleaner template access
                current_output = enhanced_outputs[agent_id]
                if isinstance(current_output, dict):
                    enhanced_outputs[agent_id] = {
                        k: v for k, v in current_output.items() if v is not None
                    }
            else:
                # Keep original for legacy compatibility
                enhanced_outputs[agent_id] = agent_result

        return enhanced_outputs

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with comprehensive error handling.

        This method maintains compatibility with the original PromptRenderer interface
        while using the simplified OrkaResponse-aware rendering logic.

        Args:
            template_str (str): The Jinja2 template string to render
            payload (dict): Context data for template variable substitution

        Returns:
            str: The rendered template with variables substituted
        """
        if not isinstance(template_str, str):
            raise ValueError(f"Expected template_str to be str, got {type(template_str)} instead.")

        try:
            # Import Jinja2 only when needed
            import re

            from jinja2 import Template, TemplateError

            # Enhance payload for template rendering
            enhanced_payload = self._enhance_payload_for_templates(payload)

            # Create and render template
            jinja_template = Template(template_str)
            rendered = jinja_template.render(**enhanced_payload)

            # ✅ FIX: Replace unresolved variables with empty strings
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

            logger.debug(f"Successfully rendered template (length: {len(rendered)})")
            return rendered

        except ImportError:
            logger.warning("Jinja2 not available, falling back to simple string replacement")
            return self._simple_string_replacement(template_str, payload)
        except TemplateError as e:
            logger.error(f"Template rendering failed: {e}")
            logger.debug(f"Template: {template_str[:200]}...")
            return self._simple_string_replacement(template_str, payload)
        except Exception as e:
            logger.error(f"Unexpected error during template rendering: {e}")
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

    def render_template(self, template: str, payload: Dict[str, Any]) -> str:
        """
        Render a template with OrkaResponse-enhanced variables.

        This is an alias for render_prompt to maintain compatibility.

        Args:
            template: The template string to render
            payload: The execution payload with context data

        Returns:
            Rendered template string
        """
        result = self.render_prompt(template, payload)
        return str(result) if result is not None else ""

    def _simple_string_replacement(self, template: str, payload: Dict[str, Any]) -> str:
        """
        Simple fallback template rendering using string replacement.

        Args:
            template: The template string
            payload: The execution payload

        Returns:
            Template with simple variable substitutions
        """
        rendered = template

        # Replace basic payload fields
        if "input" in payload:
            rendered = rendered.replace("{{ input }}", str(payload["input"]))

        # Replace previous outputs with simple format
        if "previous_outputs" in payload:
            for agent_id, agent_result in payload["previous_outputs"].items():
                # Handle OrkaResponse format
                if isinstance(agent_result, dict) and "component_type" in agent_result:
                    result_value = str(agent_result.get("result", ""))
                # Handle legacy formats
                elif isinstance(agent_result, dict):
                    result_value = str(agent_result.get("response", agent_result.get("result", "")))
                else:
                    result_value = str(agent_result)

                # Replace template variables
                rendered = rendered.replace(f"{{{{ previous_outputs.{agent_id} }}}}", result_value)
                rendered = rendered.replace(
                    f"{{{{ previous_outputs.{agent_id}.result }}}}", result_value
                )
                rendered = rendered.replace(
                    f"{{{{ previous_outputs.{agent_id}.response }}}}", result_value
                )

        logger.debug("Used simple string replacement for template rendering")
        return rendered

    def _get_template_helper_functions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create essential helper functions for Jinja2 templates.

        Args:
            payload: The current execution payload

        Returns:
            Dictionary of helper functions for template context
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

        def get_agent_response(agent_name):
            """Get an agent's response from previous_outputs."""
            previous_outputs = payload.get("previous_outputs", {})

            # Direct access
            if agent_name in previous_outputs:
                agent_result = previous_outputs[agent_name]
                if isinstance(agent_result, dict):
                    # OrkaResponse format
                    if "result" in agent_result:
                        return str(agent_result["result"])
                    # Legacy format
                    elif "response" in agent_result:
                        return str(agent_result["response"])
                return str(agent_result)

            return f"No response found for {agent_name}"

        def safe_get_response(agent_name, fallback="No response available"):
            """Safely get an agent response with fallback."""
            response = get_agent_response(agent_name)
            if response and not str(response).startswith("No response found"):
                return response
            return fallback

        def get_progressive_response():
            """Get progressive agent response."""
            return safe_get_response("progressive_refinement") or safe_get_response(
                "radical_progressive"
            )

        def get_conservative_response():
            """Get conservative agent response."""
            return safe_get_response("conservative_refinement") or safe_get_response(
                "traditional_conservative"
            )

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

        def has_past_loops():
            """Check if there are past loops available."""
            past_loops = get_past_loops()
            return len(past_loops) > 0

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
                    # Check if this agent has past_loops data
                    if "past_loops" in agent_result:
                        return agent_result["past_loops"]
                    # Check nested result structure
                    if "result" in agent_result and isinstance(agent_result["result"], dict):
                        nested_result = agent_result["result"]
                        if "past_loops" in nested_result:
                            return nested_result["past_loops"]

            return []

        def get_past_insights():
            """Get insights from the last past loop."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                return last_loop.get("synthesis_insights", "No synthesis insights found")
            return "No synthesis insights found"

        def get_past_loop_data(key=None):
            """Get data from the last past loop. If key is provided, return that specific value."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                if key is None:
                    # Return the entire last loop as formatted string
                    return str(last_loop)
                return last_loop.get(key, f"No {key} found")
            return "No past loops found"

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

        def get_fork_responses(fork_group_name):
            """Get all responses from a fork group execution."""
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

                    return responses

            return {}

        def format_memory_query(perspective, topic=None):
            """Format a memory query for a specific perspective."""
            if topic is None:
                topic = get_input()
            return f"{perspective.title()} perspective on: {topic}"

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

        def joined_results():
            """Get joined results from fork operations if available."""
            previous_outputs = payload.get("previous_outputs", {})
            for agent_name, agent_result in previous_outputs.items():
                if isinstance(agent_result, dict) and "joined_results" in agent_result:
                    return agent_result["joined_results"]
            return []

        def safe_get(obj, key, default=""):
            """Safely get a value from an object with a default."""
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        def get_loop_rounds():
            """Get the number of completed loop rounds from any loop node."""
            past_loops = get_past_loops()
            if past_loops:
                return len(past_loops)

            # Generic search through all previous outputs for loop metadata
            prev_outputs = payload.get("previous_outputs", {})
            for agent_name, agent_result in prev_outputs.items():
                if isinstance(agent_result, dict):
                    # Check for loops_completed field
                    if "loops_completed" in agent_result:
                        return agent_result["loops_completed"]
                    # Check nested result structure
                    if "result" in agent_result and isinstance(agent_result["result"], dict):
                        nested_result = agent_result["result"]
                        if "loops_completed" in nested_result:
                            return nested_result["loops_completed"]
            return "Unknown"

        def get_final_score():
            """Get the final score from any loop node using dynamic field discovery."""
            past_loops = get_past_loops()
            if past_loops:
                last_loop = past_loops[-1]
                # Try common score field names
                for score_field in ["agreement_score", "final_score", "score"]:
                    if score_field in last_loop:
                        return last_loop[score_field]

            # Generic search through all previous outputs for score metadata
            prev_outputs = payload.get("previous_outputs", {})

            for agent_name, agent_result in prev_outputs.items():
                if isinstance(agent_result, dict):
                    # Look for any field containing "score" in the name
                    for key, value in agent_result.items():
                        if "score" in key.lower() and isinstance(value, (int, float, str)):
                            try:
                                # Try to convert to float if it's a string number
                                if isinstance(value, str):
                                    return float(value)
                                return value
                            except (ValueError, TypeError):
                                continue

                    # Check nested result structure
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
            # Generic search through all previous outputs for status
            prev_outputs = payload.get("previous_outputs", {})
            for agent_name, agent_result in prev_outputs.items():
                if isinstance(agent_result, dict):
                    # Check for status field
                    if "status" in agent_result:
                        return agent_result["status"]
                    # Check nested result structure
                    if "result" in agent_result and isinstance(agent_result["result"], dict):
                        nested_result = agent_result["result"]
                        if "status" in nested_result:
                            return nested_result["status"]
            return "completed"

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

        return {
            # Input helpers
            "get_input": get_input,
            "get_current_topic": get_current_topic,
            # Loop helpers
            "get_loop_number": get_loop_number,
            "has_past_loops": has_past_loops,
            "get_past_loops": get_past_loops,
            "get_past_loops_metadata": get_past_loops_metadata,
            "get_past_insights": get_past_insights,
            "get_past_loop_data": get_past_loop_data,
            "get_round_info": get_round_info,
            "get_score_threshold": get_score_threshold,
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
            "get_score_threshold": lambda: payload.get("score_threshold", 0.90),
            # Loop metadata helpers (generic for any loop node)
            "get_loop_rounds": get_loop_rounds,
            "get_final_score": get_final_score,
            "get_loop_status": get_loop_status,
        }

    def _add_prompt_to_payload(
        self, agent, payload_out: Dict[str, Any], payload: Dict[str, Any]
    ) -> None:
        """
        Add prompt and formatted_prompt to payload_out if agent has a prompt.

        Args:
            agent: The agent instance being processed
            payload_out: The output payload dictionary to modify
            payload: The current context payload for template rendering
        """
        if hasattr(agent, "prompt") and agent.prompt:
            payload_out["prompt"] = agent.prompt

            # Use already-rendered formatted_prompt from payload if available
            if "formatted_prompt" in payload and payload["formatted_prompt"]:
                payload_out["formatted_prompt"] = payload["formatted_prompt"]
            else:
                # Render the prompt with current payload context
                try:
                    formatted_prompt = self.render_template(agent.prompt, payload)
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
                assert SimplifiedPromptRenderer.normalize_bool(True) == True
                assert SimplifiedPromptRenderer.normalize_bool("yes") == True
                assert SimplifiedPromptRenderer.normalize_bool("false") == False

                # Complex agent response
                response = {"result": {"response": "true"}}
                assert SimplifiedPromptRenderer.normalize_bool(response) == True
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
                        return SimplifiedPromptRenderer.normalize_bool(nested_result["result"])
                    elif "response" in nested_result:
                        return SimplifiedPromptRenderer.normalize_bool(nested_result["response"])
                else:
                    # Direct boolean/string result
                    return SimplifiedPromptRenderer.normalize_bool(nested_result)
            # Path 2: Direct response field
            elif "response" in value:
                return SimplifiedPromptRenderer.normalize_bool(value["response"])
        return False
