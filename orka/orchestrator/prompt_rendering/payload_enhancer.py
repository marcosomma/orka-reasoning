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
Payload Enhancer Mixin
======================

Methods for enhancing payloads with template-friendly variables.
"""

from typing import Any, Dict

from .template_safe_object import TemplateSafeObject


class PayloadEnhancerMixin:
    """Mixin providing payload enhancement methods for template rendering."""

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
        if "previous_outputs" in enhanced_payload and isinstance(
            enhanced_payload["previous_outputs"], dict
        ):
            safe_prev = {}
            for k, v in enhanced_payload["previous_outputs"].items():
                safe_prev[k] = TemplateSafeObject(v)
            enhanced_payload["previous_outputs"] = safe_prev

        # Wrap common template fields to make attribute access and startswith safe
        for key in ("web_sources", "past_context", "expires_at", "input"):
            if key in enhanced_payload:
                enhanced_payload[key] = TemplateSafeObject(enhanced_payload[key])

        return enhanced_payload

    def _enhance_previous_outputs(
        self, original_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
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
                    "response": agent_result.get("result"),
                    "memories": agent_result.get("memory_entries"),
                    "_metrics": agent_result.get("metrics", {}),
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

