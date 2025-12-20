# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Configuration Mixin
===================

Methods for memory logger configuration and preset resolution.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfigMixin:
    """Mixin providing configuration methods for memory loggers."""

    def _resolve_memory_preset(
        self,
        memory_preset: str | None,
        decay_config: dict[str, Any],
        operation: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve memory preset configuration and merge with custom config.

        Args:
            memory_preset: Name of the memory preset to use
            decay_config: Custom decay configuration to override preset values
            operation: Memory operation type ('read' or 'write')

        Returns:
            Merged configuration dictionary
        """
        if not memory_preset:
            return decay_config

        try:
            from ..presets import merge_preset_with_config

            return merge_preset_with_config(memory_preset, decay_config, operation)
        except ImportError:
            logger.warning("Memory presets not available, using custom config only")
            return decay_config
        except Exception as e:
            logger.error(f"Failed to load memory preset '{memory_preset}': {e}")
            logger.warning("Falling back to custom decay config")
            return decay_config

    def _init_decay_config(self, decay_config: dict[str, Any]) -> dict[str, Any]:
        """
        Initialize decay configuration with defaults.

        Args:
            decay_config: Raw decay configuration

        Returns:
            Processed decay configuration with defaults applied
        """
        default_config = {
            "enabled": False,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
            "memory_type_rules": {
                "long_term_events": ["success", "completion", "write", "result"],
                "short_term_events": ["debug", "processing", "start", "progress"],
            },
            "importance_rules": {
                "base_score": 0.5,
                "event_type_boosts": {
                    "write": 0.3,
                    "success": 0.2,
                    "completion": 0.2,
                    "result": 0.1,
                },
                "agent_type_boosts": {
                    "memory": 0.2,
                    "openai-answer": 0.1,
                },
            },
        }

        # Deep merge with defaults
        merged_config = default_config.copy()
        for key, value in decay_config.items():
            if isinstance(value, dict) and key in merged_config:
                target_dict = merged_config.get(key)
                if isinstance(target_dict, dict):
                    target_dict.update(value)
                else:
                    merged_config[key] = value
            else:
                merged_config[key] = value

        return merged_config

