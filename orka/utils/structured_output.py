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

"""Structured output configuration utilities.

Provides `StructuredOutputConfig`, default schemas per agent type, and a provider
capability matrix to enable model-level structured outputs (JSON mode, tool calls)
or prompt-based fallbacks. Includes helpers to build JSON Schema and prompt
instructions and to resolve provider/model capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# Agent-type specific default schemas
AGENT_DEFAULT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "openai-answer": {
        "required": ["response"],
        "optional": {"confidence": "number", "internal_reasoning": "string"},
    },
    "openai-classification": {
        "required": ["category", "confidence"],
        "optional": {"reasoning": "string", "alternatives": "array"},
    },
    "openai-binary": {
        "required": ["result"],  # Note: result is boolean type
        "optional": {"confidence": "number", "reasoning": "string"},
        "types": {"result": "boolean"},  # Explicit type override
    },
    "local_llm": {
        "required": ["response"],
        "optional": {"confidence": "number", "internal_reasoning": "string"},
    },
    # GraphScout path evaluation (Stage 1)
    "path-evaluator": {
        "required": ["relevance_score", "confidence", "reasoning"],
        "optional": {
            "expected_output": "string",
            "estimated_tokens": "integer",
            "estimated_cost": "number",
            "estimated_latency_ms": "integer",
            "efficiency_rating": "string",
            "risk_factors": "array",
        },
        "types": {
            "relevance_score": "number",
            "confidence": "number",
            "reasoning": "string",
        },
    },
    # GraphScout path validation (Stage 2)
    "path-validator": {
        "required": ["approved", "validation_score"],
        "optional": {
            "concerns": "array",
            "suggestions": "array",
        },
        "types": {
            "approved": "boolean",
            "validation_score": "number",
        },
    },
    # GraphScout comprehensive evaluation
    "path-comprehensive": {
        "required": ["recommended_path", "reasoning", "confidence"],
        "optional": {
            "expected_outcome": "string",
            "path_evaluations": "array",
        },
        "types": {
            "recommended_path": "array",
            "reasoning": "string",
            "confidence": "number",
        },
    },
    # PlanValidator boolean evaluation
    "plan-validator": {
        "required": ["completeness", "efficiency", "safety", "coherence"],
        "optional": {
            "rationale": "string",
        },
        # Top-level fields are objects with nested booleans; keep type hints generic here
        "types": {
            "completeness": "object",
            "efficiency": "object",
            "safety": "object",
            "coherence": "object",
        },
    },
}


PROVIDER_CAPABILITIES = {
    "openai": {
        "models": {
            "gpt-4o": ["model_json", "tool_call"],
            "gpt-4o-mini": ["model_json", "tool_call"],
            "gpt-4-turbo": ["model_json", "tool_call"],
            "gpt-4": ["tool_call"],  # No json_object mode
            "gpt-3.5-turbo-1106": ["model_json", "tool_call"],
            "gpt-3.5-turbo": ["tool_call"],
            "*": ["tool_call"],  # Default fallback
        },
        "default_mode": "model_json",
    },
    "anthropic": {
        "models": {
            "claude-3-*": ["tool_call"],
            "claude-2*": [],  # No structured output support
            "*": ["tool_call"],
        },
        "default_mode": "tool_call",
    },
    "ollama": {
        "models": {"*": []},  # No native support
        "default_mode": "prompt",
    },
    "lm_studio": {
        "models": {"*": []},
        "default_mode": "prompt",
    },
    "openai_compatible": {
        "models": {"*": []},  # Assume no support unless proven
        "default_mode": "prompt",
    },
}


@dataclass
class StructuredOutputConfig:
    """Per-agent structured output configuration.

    Each agent can have its own schema tailored to its output contract. Config is
    resolved from (highest priority first):
        1. Agent params.structured_output
        2. Orchestrator structured_output_defaults
        3. Built-in defaults for the agent type
    """

    enabled: bool = False
    mode: Literal["auto", "model_json", "tool_call", "prompt"] = "auto"
    schema: Optional[Dict[str, Any]] = None
    require_code_block: bool = False
    coerce_types: bool = True
    strict: bool = False

    # Internal: agent type for default schema lookup
    _agent_type: str = field(default="openai-answer", repr=False)

    @classmethod
    def from_params(
        cls,
        agent_params: Dict[str, Any],
        agent_type: str,
        orchestrator_defaults: Optional[Dict[str, Any]] = None,
    ) -> "StructuredOutputConfig":
        """Build config by merging agent params with orchestrator defaults.

        Args:
            agent_params: The agent's params dict (may contain structured_output)
            agent_type: Agent type string (e.g., 'openai-answer', 'openai-binary')
            orchestrator_defaults: Optional workflow-level defaults

        Returns:
            Fully resolved StructuredOutputConfig for this agent
        """
        # Start with built-in defaults
        config: Dict[str, Any] = {
            "enabled": False,
            "mode": "auto",
            "schema": None,
            "require_code_block": False,
            "coerce_types": True,
            "strict": False,
        }

        # Layer 1: Apply orchestrator defaults (if any)
        if orchestrator_defaults and isinstance(orchestrator_defaults, dict):
            for key in list(config.keys()):
                if key in orchestrator_defaults:
                    config[key] = orchestrator_defaults[key]

        # Layer 2: Apply agent-specific config (overrides orchestrator)
        agent_so = agent_params.get("structured_output", {}) if agent_params else {}
        if isinstance(agent_so, dict):
            for key in list(config.keys()):
                if key in agent_so:
                    config[key] = agent_so[key]

        # Layer 3: If no schema specified, use agent-type default when enabled
        if config["schema"] is None and config.get("enabled"):
            default_schema = AGENT_DEFAULT_SCHEMAS.get(
                agent_type, AGENT_DEFAULT_SCHEMAS["openai-answer"]
            )
            # Use a shallow copy to avoid mutating the module constant
            config["schema"] = {**default_schema}

        return cls(
            enabled=bool(config["enabled"]),
            mode=config["mode"],
            schema=config["schema"],
            require_code_block=bool(config["require_code_block"]),
            coerce_types=bool(config["coerce_types"]),
            strict=bool(config["strict"]),
            _agent_type=agent_type,
        )

    def resolve_mode(self, provider: str, model: str) -> str:
        """Determine actual mode based on provider/model capabilities.

        When mode='auto', selects best available mode for the provider.
        """
        if self.mode != "auto":
            return self.mode

        # Check provider capabilities
        caps = PROVIDER_CAPABILITIES.get(provider, {})
        model_caps = _get_model_capabilities(caps, model)

        # Prefer tool_call for schema enforcement, fall back gracefully
        if "tool_call" in model_caps:
            return "tool_call"
        if "model_json" in model_caps:
            return "model_json"
        return "prompt"

    def build_json_schema(self) -> Dict[str, Any]:
        """Build JSON Schema for tool_call mode based on agent's schema config.

        Returns a valid JSON Schema object with proper types.
        """
        schema = self.schema or AGENT_DEFAULT_SCHEMAS.get(
            self._agent_type, AGENT_DEFAULT_SCHEMAS["openai-answer"]
        )

        required: List[str] = list(schema.get("required", ["response"]))
        optional: Dict[str, Any] = dict(schema.get("optional", {}))
        type_overrides: Dict[str, str] = dict(schema.get("types", {}))

        properties: Dict[str, Any] = {}

        # Build properties from required fields
        for field_name in required:
            field_type = type_overrides.get(field_name, "string")
            properties[field_name] = {"type": _yaml_type_to_json_schema(field_type)}

        # Build properties from optional fields
        for field_name, field_type in optional.items():
            properties[field_name] = {"type": _yaml_type_to_json_schema(field_type)}

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": not self.strict,
        }

    def build_prompt_instructions(self) -> str:
        """Build prompt injection instructions for prompt mode.

        Generates clear JSON format instructions based on the schema.
        """
        if not self.schema:
            # Fallback: no instructions
            return ""

        required = list(self.schema.get("required", ["response"]))
        optional = dict(self.schema.get("optional", {}))

        fields_desc: List[str] = []
        for f in required:
            fields_desc.append(f'  "{f}": <required>')
        for f, t in optional.items():
            fields_desc.append(f'  "{f}": <{t}, optional>')

        fields_str = ",\n".join(fields_desc)

        instruction = f"""
# CRITICAL: Return ONLY valid JSON in this exact format:
```json
{{
{fields_str}
}}
```
Rules:
- Use double quotes for all strings
- No text outside the JSON object
- All required fields must be present
"""
        return instruction.strip()


def _yaml_type_to_json_schema(yaml_type: str) -> str:
    """Convert YAML type hint to JSON Schema type."""
    mapping = {
        "string": "string",
        "str": "string",
        "number": "number",
        "num": "number",
        "float": "number",
        "integer": "integer",
        "int": "integer",
        "boolean": "boolean",
        "bool": "boolean",
        "array": "array",
        "list": "array",
        "object": "object",
        "dict": "object",
    }
    return mapping.get(yaml_type.lower(), "string")


def _get_model_capabilities(provider_caps: Dict[str, Any], model: str) -> List[str]:
    """Get capabilities for a specific model, with wildcard fallback."""
    models = provider_caps.get("models", {}) if provider_caps else {}

    # Exact match
    if model in models:
        return models[model]

    # Wildcard pattern matching (e.g., "gpt-4*" matches "gpt-4o")
    for pattern, caps in models.items():
        if pattern.endswith("*") and model.startswith(pattern[:-1]):
            return caps

    # Default fallback
    return models.get("*", [])
