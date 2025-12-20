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
import json
import re
from typing import Any, Dict

try:
    from .template_helpers import register_template_helpers
    TEMPLATE_HELPERS_AVAILABLE = True
except ImportError:
    TEMPLATE_HELPERS_AVAILABLE = False
    import logging as _logging
    _logging.getLogger(__name__).warning("template_helpers not available, custom filters disabled")

logger = logging.getLogger(__name__)


class SimplifiedPromptRenderer:

    class _TemplateSafeObject:
        """Wrapper that makes template attribute access and common string ops safe.

        It wraps arbitrary values (dict, list, string, number) and exposes
        attribute access (dot notation) by delegating to dict keys when
        possible or falling back to sensible defaults.
        """

        def __init__(self, value: Any):
            self._value = value

        def __getattr__(self, name: str) -> Any:
            # Support common pattern: previous_outputs.agent.result
            val = self._value
            if isinstance(val, dict):
                if name in val:
                    return SimplifiedPromptRenderer._TemplateSafeObject(val[name])
                # allow nested 'result' lookup in nested result dicts
                if "result" in val and isinstance(val["result"], dict) and name in val["result"]:
                    return SimplifiedPromptRenderer._TemplateSafeObject(val["result"][name])
            # fallback: raise AttributeError so Jinja treats as missing
            raise AttributeError(name)

        def __str__(self) -> str:
            val = self._value
            if isinstance(val, (dict, list)):
                # for dict/list return simple string representation
                return str(val)
            return str(val)

        def __repr__(self) -> str:
            return f"TemplateSafeObject({repr(self._value)})"

        def get(self, key, default=None):
            if isinstance(self._value, dict):
                return self._value.get(key, default)
            return default

        def raw(self):
            """Return the underlying raw value wrapped by this object."""
            return self._value

        def __getitem__(self, key):
            if isinstance(self._value, dict):
                val = self._value[key]
                # unwrap nested dicts/values into TemplateSafeObject for consistency
                if isinstance(val, dict) or isinstance(val, list):
                    return SimplifiedPromptRenderer._TemplateSafeObject(val)
                return val
            raise TypeError("TemplateSafeObject is not subscriptable for non-dict values")

        def startswith(self, prefix):
            # Safe startswith: only works for string-like values
            if isinstance(self._value, str):
                return self._value.startswith(prefix)
            return False

        def items(self):
            if isinstance(self._value, dict):
                return self._value.items()
            return []


    @staticmethod
    def get_input_field(input_obj, field, default=None):
        """
        Helper to extract a field from input (dict or JSON) in Jinja2 templates.
        Usage: {{ get_input_field(input, 'fieldname') }}
        """
        if isinstance(input_obj, dict):
            return input_obj.get(field, default)
        return default

    @staticmethod
    def _unwrap_template_safe(value: Any) -> Any:
        """
        Recursively unwrap TemplateSafeObject (or any object exposing .raw()) into plain
        Python types for safe JSON serialization inside templates (e.g. via `|tojson`).
        """
        if hasattr(value, "raw") and callable(getattr(value, "raw")):
            try:
                value = value.raw()
            except Exception:
                return str(value)

        if isinstance(value, dict):
            return {k: SimplifiedPromptRenderer._unwrap_template_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [SimplifiedPromptRenderer._unwrap_template_safe(v) for v in value]
        if isinstance(value, tuple):
            return tuple(SimplifiedPromptRenderer._unwrap_template_safe(v) for v in value)

        return value

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

        # Wrap previous_outputs entries with TemplateSafeObject for safe dot access
        if "previous_outputs" in enhanced_payload and isinstance(enhanced_payload["previous_outputs"], dict):
            safe_prev = {}
            for k, v in enhanced_payload["previous_outputs"].items():
                safe_prev[k] = SimplifiedPromptRenderer._TemplateSafeObject(v)
            enhanced_payload["previous_outputs"] = safe_prev

        # Wrap common template fields to make attribute access and startswith safe
        for key in ("web_sources", "past_context", "expires_at", "input"):
            if key in enhanced_payload:
                enhanced_payload[key] = SimplifiedPromptRenderer._TemplateSafeObject(enhanced_payload[key])
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
            from jinja2 import Environment, TemplateError

            # Enhance payload for template rendering
            enhanced_payload = self._enhance_payload_for_templates(payload)

            # Create Jinja2 environment with custom filters
            env = Environment()
            # Ensure JSON serialization in templates works with TemplateSafeObject
            # (Jinja's default `tojson` uses json.dumps and will crash on our wrapper).
            env.filters["tojson"] = lambda v: json.dumps(
                SimplifiedPromptRenderer._unwrap_template_safe(v),
                ensure_ascii=False,
                default=str,
            )
            # Register custom template helpers if available
            if TEMPLATE_HELPERS_AVAILABLE:
                try:
                    register_template_helpers(env)
                    logger.debug("Custom template helpers registered successfully")
                except Exception as e:
                    logger.warning(f"Failed to register custom template helpers: {e}")
            # Register internal helper functions and get_input_field
            helper_functions = self._get_template_helper_functions(enhanced_payload)
            env.globals.update(helper_functions)
            env.globals['get_input_field'] = SimplifiedPromptRenderer.get_input_field
            # Expose safe string helper to templates
            env.globals['safe_str'] = lambda v: "" if v is None else str(v)
            logger.debug(f"Registered {len(helper_functions)+1} internal helper functions to Jinja2 environment (including get_input_field)")
            # Create and render template
            jinja_template = env.from_string(template_str)
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
            """Get an agent's response from previous_outputs safely."""
            try:
                previous_outputs = payload.get("previous_outputs", {})

                # Direct access
                if agent_name in previous_outputs:
                    agent_result = previous_outputs[agent_name]
                    # Unwrap TemplateSafeObject
                    if hasattr(agent_result, "raw"):
                        agent_result = agent_result.raw()

                    if isinstance(agent_result, dict):
                        # Orchestrator event/log shape: payload.response / payload.result
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

                        # OrkaResponse format
                        if "result" in agent_result:
                            return str(agent_result["result"])
                        # Legacy format
                        elif "response" in agent_result:
                            return str(agent_result["response"])
                    return str(agent_result)

                return f"No response found for {agent_name}"
            except Exception as e:
                logger.debug(f"get_agent_response error for {agent_name}: {e}")
                return f"No response found for {agent_name}"
        def safe_get_response(agent_name, fallback="No response available", prev_outputs=None):
            """
            Safely get an agent response with fallback.
            """
            try:
                # Use provided prev_outputs if given, otherwise use payload's previous_outputs
                if prev_outputs is not None:
                    previous_outputs = prev_outputs
                else:
                    previous_outputs = payload.get("previous_outputs", {})

                # Direct access to previous_outputs
                if agent_name in previous_outputs:
                    agent_result = previous_outputs[agent_name]
                    # Unwrap TemplateSafeObject
                    if hasattr(agent_result, "raw"):
                        agent_result = agent_result.raw()

                    if isinstance(agent_result, dict):
                        # Orchestrator event/log shape: payload.response / payload.result
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

                        # OrkaResponse format
                        if "result" in agent_result:
                            result_str = str(agent_result["result"])
                            if result_str and not result_str.startswith("No response found"):
                                return result_str
                        # Legacy format
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
            try:
                return safe_get_response("progressive_refinement") or safe_get_response(
                    "radical_progressive"
                )
            except Exception as e:
                logger.debug(f"get_progressive_response error: {e}")
                return "No response available"

        def get_conservative_response():
            """Get conservative agent response safely."""
            try:
                return safe_get_response("conservative_refinement") or safe_get_response(
                    "traditional_conservative"
                )
            except Exception as e:
                logger.debug(f"get_conservative_response error: {e}")
                return "No response available"

        def get_realist_response():
            """Get realist agent response safely."""
            try:
                return safe_get_response("realist_refinement") or safe_get_response("pragmatic_realist")
            except Exception as e:
                logger.debug(f"get_realist_response error: {e}")
                return "No response available"

        def get_purist_response():
            """Get purist agent response safely."""
            try:
                return safe_get_response("purist_refinement") or safe_get_response("ethical_purist")
            except Exception as e:
                logger.debug(f"get_purist_response error: {e}")
                return "No response available"

        def get_collaborative_responses():
            """Get all collaborative refinement responses as a formatted string."""
            try:
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
            except Exception as e:
                logger.debug(f"get_collaborative_responses error: {e}")
                return "No collaborative responses available"
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

        def get_fork_responses(fork_group_name=None):
                """Get all responses from a fork group execution.

                If no `fork_group_name` is provided, attempt to find any fork-like
                groups in `previous_outputs` and return a mapping of their
                responses. This avoids TemplateErrors when templates call
                `get_fork_responses()` without args.
                """
                previous_outputs = payload.get("previous_outputs", {})

                def extract_responses(fork_result):
                    responses = {}
                    if isinstance(fork_result, dict):
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

                if fork_group_name:
                    fork_result = previous_outputs.get(fork_group_name, {})
                    return extract_responses(fork_result)

                # No fork_group_name: find candidate fork groups heuristically
                found = {}
                for key, val in previous_outputs.items():
                    candidate = extract_responses(val)
                    if candidate:
                        found[key] = candidate

                return found

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

        def get_loop_output(agent_id: str, prev_outputs: Dict[str, Any] = None) -> Dict[str, Any]:
            """
            Get the complete output dict from a LoopNode agent.
            
            Unlike safe_get_response which returns a string, this returns the full dict
            so you can access fields like loops_completed, final_score, past_loops, etc.
            
            Args:
                agent_id: ID of the loop agent
                prev_outputs: Optional dict of previous outputs (for compatibility with template_helpers)
            
            Returns:
                Complete output dict from the loop, or empty dict if not found
            
            Example:
                {% set loop_data = get_loop_output('cognitive_debate_loop', previous_outputs) %}
                Rounds: {{ loop_data.loops_completed }}
                Score: {{ loop_data.final_score }}
            """
            # Use provided previous_outputs or get from payload
            previous_outputs = prev_outputs if prev_outputs is not None else payload.get("previous_outputs", {})
            
            if not previous_outputs:
                logger.warning(f"get_loop_output: previous_outputs is empty for agent '{agent_id}'")
                return {}
            
            if agent_id not in previous_outputs:
                logger.debug(f"get_loop_output: agent '{agent_id}' not found in previous_outputs")
                return {}
            
            output = previous_outputs[agent_id]
            # Unwrap TemplateSafeObject if present
            if hasattr(output, "raw"):
                output = output.raw()
            
            # LoopNode wraps output in 'response' field
            if isinstance(output, dict) and 'response' in output:
                response_value = output['response']
                if isinstance(response_value, dict):
                    return response_value
            
            # Fallback: return the output dict itself
            if isinstance(output, dict):
                return output
            
            logger.warning(f"get_loop_output: output for '{agent_id}' is not a dict: {type(output)}")
            return {}

        def has_context(agent_name: str) -> bool:
            """Return True if there is any context for the given agent name.

            This covers common cases used in templates: presence in
            `previous_outputs`, simple conversation context in `input`, or
            an associated memory entry.
            """
            prev_outputs = payload.get("previous_outputs", {})
            # Direct previous outputs check
            if agent_name in prev_outputs:
                val = prev_outputs[agent_name]
                # Consider non-empty values as having context
                return bool(val)

            # Input-level context (e.g., conversation_context)
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
            "get_loop_output": get_loop_output,
            # Context helper
            "has_context": has_context,
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
            except Exception as e:
                # 🐛 Bug #7 Fix: Log warning when rendering fails
                logger = logging.getLogger(__name__)
                logger.warning(f"Prompt rendering failed for agent {getattr(agent, 'agent_id', 'unknown')}: {e}")
                # If rendering fails, use the original prompt
                payload["formatted_prompt"] = agent.prompt or ""
        else:
            # 🐛 Bug #7 Fix: Always set formatted_prompt, even if empty
            # This ensures consistent trace output and prevents KeyErrors
            payload["formatted_prompt"] = ""

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
