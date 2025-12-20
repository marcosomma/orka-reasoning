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
structure for template variables.

This class has been refactored into smaller modules in the prompt_rendering/ package:
- TemplateSafeObject: Safe wrapper for template attribute access
- PayloadEnhancerMixin: Payload enhancement for templates
- input_helpers: Input-related template helper functions
- loop_helpers: Loop-related template helper functions
- agent_helpers: Agent response template helper functions
- memory_helpers: Memory-related template helper functions
- utility_helpers: General utility template helper functions
"""

import json
import logging
import re
from typing import Any, Dict

from .prompt_rendering.template_safe_object import TemplateSafeObject, unwrap_template_safe
from .prompt_rendering.payload_enhancer import PayloadEnhancerMixin
from .prompt_rendering.input_helpers import create_input_helpers
from .prompt_rendering.loop_helpers import create_loop_helpers
from .prompt_rendering.agent_helpers import create_agent_helpers
from .prompt_rendering.memory_helpers import create_memory_helpers
from .prompt_rendering.utility_helpers import create_utility_helpers, normalize_bool

try:
    from .template_helpers import register_template_helpers

    TEMPLATE_HELPERS_AVAILABLE = True
except ImportError:
    TEMPLATE_HELPERS_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "template_helpers not available, custom filters disabled"
    )

logger = logging.getLogger(__name__)


class SimplifiedPromptRenderer(PayloadEnhancerMixin):
    """
    Simplified prompt renderer that uses OrkaResponse structure for template variables.

    This renderer provides direct access to standardized response fields while
    maintaining backward compatibility with legacy response formats.
    """

    # Keep backward compatibility alias
    _TemplateSafeObject = TemplateSafeObject

    def __init__(self):
        """Initialize the simplified prompt renderer."""
        pass

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
        """Backward compatibility wrapper for unwrap_template_safe."""
        return unwrap_template_safe(value)

    @staticmethod
    def normalize_bool(value) -> bool:
        """Normalize a value to boolean with support for complex agent responses."""
        return normalize_bool(value)

    def render_prompt(self, template_str, payload):
        """
        Render a Jinja2 template string with comprehensive error handling.

        Args:
            template_str (str): The Jinja2 template string to render
            payload (dict): Context data for template variable substitution

        Returns:
            str: The rendered template with variables substituted
        """
        if not isinstance(template_str, str):
            raise ValueError(
                f"Expected template_str to be str, got {type(template_str)} instead."
            )

        try:
            from jinja2 import Environment, TemplateError

            # Enhance payload for template rendering
            enhanced_payload = self._enhance_payload_for_templates(payload)

            # Create Jinja2 environment with custom filters
            env = Environment()
            env.filters["tojson"] = lambda v: json.dumps(
                unwrap_template_safe(v),
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

            # Register helper functions
            helper_functions = self._get_template_helper_functions(enhanced_payload)
            env.globals.update(helper_functions)
            env.globals["get_input_field"] = SimplifiedPromptRenderer.get_input_field
            env.globals["safe_str"] = lambda v: "" if v is None else str(v)

            logger.debug(
                f"Registered {len(helper_functions)+1} internal helper functions"
            )

            # Create and render template
            jinja_template = env.from_string(template_str)
            rendered = jinja_template.render(**enhanced_payload)

            # Replace unresolved variables with empty strings
            unresolved_pattern = r"\{\{\s*[^}]+\s*\}\}"
            unresolved_vars = re.findall(unresolved_pattern, rendered)

            if unresolved_vars:
                logger.debug(
                    f"Replacing {len(unresolved_vars)} unresolved variables"
                )
                rendered = re.sub(unresolved_pattern, "", rendered)
                rendered = re.sub(r"\s+", " ", rendered).strip()

            logger.debug(f"Successfully rendered template (length: {len(rendered)})")
            return rendered

        except ImportError:
            logger.warning("Jinja2 not available, falling back to simple replacement")
            return self._simple_string_replacement(template_str, payload)
        except Exception as e:
            if "TemplateError" in str(type(e)):
                logger.error(f"Template rendering failed: {e}")
                logger.debug(f"Template: {template_str[:200]}...")
                return self._simple_string_replacement(template_str, payload)

            logger.error(f"Unexpected error during template rendering: {e}")
            fallback_rendered = re.sub(r"\{\{\s*[^}]+\s*\}\}", "", template_str)
            fallback_rendered = re.sub(r"\s+", " ", fallback_rendered).strip()
            logger.warning(f"Using fallback rendering: '{fallback_rendered}'")
            return fallback_rendered

    def render_template(self, template: str, payload: Dict[str, Any]) -> str:
        """
        Render a template with OrkaResponse-enhanced variables.

        This is an alias for render_prompt to maintain compatibility.
        """
        result = self.render_prompt(template, payload)
        return str(result) if result is not None else ""

    def _simple_string_replacement(
        self, template: str, payload: Dict[str, Any]
    ) -> str:
        """Simple fallback template rendering using string replacement."""
        rendered = template

        if "input" in payload:
            rendered = rendered.replace("{{ input }}", str(payload["input"]))

        if "previous_outputs" in payload:
            for agent_id, agent_result in payload["previous_outputs"].items():
                if isinstance(agent_result, dict) and "component_type" in agent_result:
                    result_value = str(agent_result.get("result", ""))
                elif isinstance(agent_result, dict):
                    result_value = str(
                        agent_result.get("response", agent_result.get("result", ""))
                    )
                else:
                    result_value = str(agent_result)

                rendered = rendered.replace(
                    f"{{{{ previous_outputs.{agent_id} }}}}", result_value
                )
                rendered = rendered.replace(
                    f"{{{{ previous_outputs.{agent_id}.result }}}}", result_value
                )
                rendered = rendered.replace(
                    f"{{{{ previous_outputs.{agent_id}.response }}}}", result_value
                )

        logger.debug("Used simple string replacement for template rendering")
        return rendered

    def _get_template_helper_functions(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create essential helper functions for Jinja2 templates.

        Args:
            payload: The current execution payload

        Returns:
            Dictionary of helper functions for template context
        """
        # Create helpers from each module
        input_helpers = create_input_helpers(payload)
        loop_helpers = create_loop_helpers(payload)
        agent_helpers = create_agent_helpers(payload)
        memory_helpers = create_memory_helpers(payload, loop_helpers)
        utility_helpers = create_utility_helpers(payload)

        # Combine all helpers
        helpers = {}
        helpers.update(input_helpers)
        helpers.update(loop_helpers)
        helpers.update(agent_helpers)
        helpers.update(memory_helpers)
        helpers.update(utility_helpers)

        # Add score threshold lambda (overrides the one from loop_helpers if needed)
        helpers["get_score_threshold"] = lambda: payload.get("score_threshold", 0.90)

        return helpers

    def _add_prompt_to_payload(
        self, agent, payload_out: Dict[str, Any], payload: Dict[str, Any]
    ) -> None:
        """Add prompt and formatted_prompt to payload_out if agent has a prompt."""
        if hasattr(agent, "prompt") and agent.prompt:
            payload_out["prompt"] = agent.prompt

            if "formatted_prompt" in payload and payload["formatted_prompt"]:
                payload_out["formatted_prompt"] = payload["formatted_prompt"]
            else:
                try:
                    formatted_prompt = self.render_template(agent.prompt, payload)
                    payload_out["formatted_prompt"] = formatted_prompt
                except Exception:
                    payload_out["formatted_prompt"] = agent.prompt

        if hasattr(agent, "_last_response") and agent._last_response:
            payload_out["response"] = agent._last_response
        if hasattr(agent, "_last_confidence") and agent._last_confidence:
            payload_out["confidence"] = agent._last_confidence
        if hasattr(agent, "_last_internal_reasoning") and agent._last_internal_reasoning:
            payload_out["internal_reasoning"] = agent._last_internal_reasoning

    def _render_agent_prompt(self, agent, payload):
        """Render agent's prompt and add formatted_prompt to payload."""
        if hasattr(agent, "prompt") and agent.prompt:
            try:
                formatted_prompt = self.render_prompt(agent.prompt, payload)
                payload["formatted_prompt"] = formatted_prompt
            except Exception as e:
                logger.warning(
                    f"Prompt rendering failed for agent "
                    f"{getattr(agent, 'agent_id', 'unknown')}: {e}"
                )
                payload["formatted_prompt"] = agent.prompt or ""
        else:
            payload["formatted_prompt"] = ""
