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
Memory Presets System - Minsky-Inspired Cognitive Architecture
=============================================================

This module implements a simplified memory configuration system based on Marvin Minsky's
cognitive theories from "The Society of Mind" and related work. It provides 6 preset
memory types that cover the spectrum of cognitive memory needs.

Minsky-Inspired Memory Hierarchy
-------------------------------

The 6 memory types are inspired by Minsky's cognitive architecture concepts:

1. **Sensory Memory** - Immediate, high-throughput processing
2. **Working Memory** - Active processing and temporary storage
3. **Episodic Memory** - Experience and interaction history
4. **Semantic Memory** - Knowledge and learned facts
5. **Procedural Memory** - Skills, patterns, and processes
6. **Meta Memory** - System knowledge and self-reflection

Each preset includes:
- Optimized decay rules for the memory type
- Appropriate importance scoring
- Vector search configuration
- TTL and cleanup settings
- Namespace organization

Usage Examples
--------------

**Simple YAML Configuration:**

```yaml
orchestrator:
  id: smart-assistant
  memory_preset: "episodic"  # Just specify the preset!
  agents: [...]
```

**Advanced Configuration with Override:**

```yaml
orchestrator:
  id: smart-assistant
  memory_preset: "semantic"
  memory_config:
    # Preset provides base config, override specific values
    default_long_term_hours: 720  # Override: extend to 30 days
  agents: [...]
```

**Agent-Specific Memory Types:**

```yaml
agents:
  - id: knowledge_agent
    type: memory
    memory_preset: "semantic"  # For storing facts
    config:
      operation: write
    namespace: knowledge_base

  - id: interaction_logger
    type: memory
    memory_preset: "episodic"  # For conversation history
    config:
      operation: write
    namespace: conversations
```

Performance Benefits
-------------------

- **Simplified Configuration**: 90% reduction in memory config complexity
- **Cognitive Alignment**: Memory types match human cognitive patterns
- **Optimized Performance**: Each preset is tuned for its use case
- **Backward Compatible**: Existing configurations continue to work
"""

from typing import Any, Dict

# Minsky-Inspired Memory Presets with Operation-Specific Configurations
# Based on cognitive science principles from "The Society of Mind"
# Now supports both READ and WRITE operation-specific defaults

MEMORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "sensory": {
        "description": "Immediate sensory input processing - very short-term, high-throughput",
        "inspired_by": "Minsky's sensory buffers and immediate perception processing",
        "use_cases": ["Real-time data streams", "Sensor input", "Immediate responses"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 0.25,  # 15 minutes
                "default_long_term_hours": 1.0,  # 1 hour max
                "check_interval_minutes": 5,  # Frequent cleanup
                "memory_type_rules": {
                    "long_term_events": [],  # Almost nothing becomes long-term
                    "short_term_events": [
                        "debug",
                        "processing",
                        "start",
                        "progress",
                        "input",
                        "output",
                    ],
                },
                "importance_rules": {
                    "base_score": 0.1,  # Low importance by default
                    "event_type_boosts": {"critical": 0.4, "error": 0.3},
                    "agent_type_boosts": {"sensor": 0.2},
                },
            },
            "vector_search": {
                "enabled": False,  # No semantic search for sensory data
                "threshold": 0.9,  # Very high threshold if enabled
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 3,
                "similarity_threshold": 0.95,  # Very precise for sensory
                "enable_vector_search": False,
                "enable_temporal_ranking": True,
                "temporal_weight": 0.8,  # Heavy temporal bias
                "text_weight": 1.0,
                "vector_weight": 0.0,
                "enable_hybrid_search": False,
                "ef_runtime": 5,  # Fast retrieval
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": False,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
            },
            "namespace_prefix": "sensory",
        },
    },
    "working": {
        "description": "Active working memory - temporary processing and immediate context",
        "inspired_by": "Minsky's K-lines and active cognitive processes",
        "use_cases": ["Session context", "Temporary calculations", "Active workflows"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 2.0,  # 2 hours
                "default_long_term_hours": 8.0,  # 8 hours max
                "check_interval_minutes": 15,
                "memory_type_rules": {
                    "long_term_events": ["success", "completion", "important"],
                    "short_term_events": ["debug", "processing", "start", "progress", "temporary"],
                },
                "importance_rules": {
                    "base_score": 0.3,
                    "event_type_boosts": {"completion": 0.3, "success": 0.2, "decision": 0.2},
                    "agent_type_boosts": {"router": 0.2, "classifier": 0.1},
                },
            },
            "vector_search": {
                "enabled": True,
                "threshold": 0.75,
                "context_weight": 0.5,  # Heavy context weighting
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 5,
                "similarity_threshold": 0.7,
                "enable_vector_search": True,
                "enable_temporal_ranking": True,
                "temporal_weight": 0.4,
                "text_weight": 0.4,
                "vector_weight": 0.6,
                "enable_hybrid_search": True,
                "ef_runtime": 8,
                "enable_context_search": True,
                "context_weight": 0.5,
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": True,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
                "vector_params": {
                    "type": "FLOAT32",
                    "distance_metric": "COSINE",
                },
            },
            "namespace_prefix": "working",
        },
    },
    "episodic": {
        "description": "Experience and interaction history - personal narrative memory",
        "inspired_by": "Minsky's autobiographical agents and experience recording",
        "use_cases": ["User conversations", "Interaction history", "Session memories"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 24.0,  # 1 day
                "default_long_term_hours": 168.0,  # 1 week
                "check_interval_minutes": 60,  # Hourly cleanup
                "memory_type_rules": {
                    "long_term_events": [
                        "success",
                        "completion",
                        "write",
                        "conversation",
                        "interaction",
                    ],
                    "short_term_events": ["debug", "processing", "start", "temporary"],
                },
                "importance_rules": {
                    "base_score": 0.5,
                    "event_type_boosts": {
                        "user_interaction": 0.4,
                        "conversation": 0.3,
                        "feedback": 0.3,
                        "correction": 0.4,
                    },
                    "agent_type_boosts": {"memory-writer": 0.3, "conversation": 0.2},
                },
            },
            "vector_search": {
                "enabled": True,
                "threshold": 0.7,
                "context_weight": 0.4,
                "temporal_weight": 0.3,  # Recent experiences matter
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 8,
                "similarity_threshold": 0.6,  # More relaxed for conversations
                "enable_vector_search": True,
                "enable_temporal_ranking": True,
                "temporal_weight": 0.3,  # Recent experiences matter
                "text_weight": 0.3,
                "vector_weight": 0.7,
                "enable_hybrid_search": True,
                "ef_runtime": 10,
                "enable_context_search": True,
                "context_weight": 0.4,
                "temporal_decay_hours": 24,  # Day-based relevance
                "context_window_size": 5,
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": True,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
                "vector_params": {
                    "type": "FLOAT32",
                    "distance_metric": "COSINE",
                    "ef_construction": 200,
                    "m": 16,
                },
            },
            "namespace_prefix": "episodic",
        },
    },
    "semantic": {
        "description": "Knowledge and learned facts - long-term knowledge base",
        "inspired_by": "Minsky's knowledge representation and semantic networks",
        "use_cases": ["Facts", "Knowledge base", "Learned information", "Documentation"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 72.0,  # 3 days
                "default_long_term_hours": 2160.0,  # 90 days
                "check_interval_minutes": 240,  # 4-hour cleanup intervals
                "memory_type_rules": {
                    "long_term_events": [
                        "write",
                        "knowledge",
                        "fact",
                        "definition",
                        "completion",
                        "success",
                    ],
                    "short_term_events": ["debug", "processing", "temporary", "draft"],
                },
                "importance_rules": {
                    "base_score": 0.7,  # High base importance for knowledge
                    "event_type_boosts": {
                        "knowledge": 0.3,
                        "definition": 0.3,
                        "fact": 0.3,
                        "write": 0.2,
                        "validation": 0.2,
                    },
                    "agent_type_boosts": {"knowledge": 0.3, "semantic": 0.2, "validator": 0.2},
                },
            },
            "vector_search": {
                "enabled": True,
                "threshold": 0.65,  # Lower threshold for broader knowledge matching
                "context_weight": 0.2,  # Less context-dependent
                "similarity_boost": 0.8,  # Emphasize semantic similarity
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 10,
                "similarity_threshold": 0.65,  # Broader knowledge matching
                "enable_vector_search": True,
                "enable_temporal_ranking": False,  # Knowledge is timeless
                "temporal_weight": 0.1,
                "text_weight": 0.3,
                "vector_weight": 0.7,
                "enable_hybrid_search": True,
                "ef_runtime": 15,  # More thorough search
                "enable_context_search": False,  # Less context-dependent
                "memory_category_filter": "stored",
                "memory_type_filter": "all",
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": True,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
                "vector_params": {
                    "type": "FLOAT32",
                    "distance_metric": "COSINE",
                    "ef_construction": 200,
                    "m": 16,
                },
            },
            "namespace_prefix": "semantic",
        },
    },
    "procedural": {
        "description": "Skills, patterns, and process knowledge - how-to memory",
        "inspired_by": "Minsky's skill learning and procedural knowledge",
        "use_cases": ["Workflows", "Patterns", "Skills", "Process optimization"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 168.0,  # 1 week
                "default_long_term_hours": 4320.0,  # 6 months
                "check_interval_minutes": 480,  # 8-hour cleanup intervals
                "memory_type_rules": {
                    "long_term_events": [
                        "pattern",
                        "workflow",
                        "skill",
                        "process",
                        "optimization",
                        "success",
                    ],
                    "short_term_events": ["debug", "trial", "attempt", "temporary"],
                },
                "importance_rules": {
                    "base_score": 0.6,
                    "event_type_boosts": {
                        "pattern": 0.4,
                        "workflow": 0.3,
                        "optimization": 0.3,
                        "skill": 0.3,
                        "efficiency": 0.2,
                    },
                    "agent_type_boosts": {"orchestrator": 0.3, "optimizer": 0.2, "loop": 0.2},
                },
            },
            "vector_search": {
                "enabled": True,
                "threshold": 0.7,
                "pattern_weight": 0.5,  # Emphasize pattern matching
                "temporal_weight": 0.1,  # Process knowledge is less time-dependent
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 6,
                "similarity_threshold": 0.7,
                "enable_vector_search": True,
                "enable_temporal_ranking": True,
                "temporal_weight": 0.1,  # Process knowledge is less time-dependent
                "text_weight": 0.4,
                "vector_weight": 0.6,
                "enable_hybrid_search": True,
                "ef_runtime": 12,
                "enable_context_search": True,
                "context_weight": 0.3,
                "memory_category_filter": "store",
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": True,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
                "vector_params": {
                    "type": "FLOAT32",
                    "distance_metric": "COSINE",
                    "ef_construction": 200,
                    "m": 16,
                },
            },
            "namespace_prefix": "procedural",
        },
    },
    "meta": {
        "description": "System knowledge and self-reflection - meta-cognitive awareness",
        "inspired_by": "Minsky's self-reflective agents and meta-cognitive processes",
        "use_cases": ["System behavior", "Performance metrics", "Self-awareness", "Meta-learning"],
        "config": {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 48.0,  # 2 days
                "default_long_term_hours": 8760.0,  # 1 year
                "check_interval_minutes": 720,  # 12-hour cleanup intervals
                "memory_type_rules": {
                    "long_term_events": [
                        "meta",
                        "reflection",
                        "performance",
                        "system",
                        "insight",
                        "learning",
                    ],
                    "short_term_events": ["debug", "trace", "monitoring", "temporary"],
                },
                "importance_rules": {
                    "base_score": 0.8,  # Very high importance for meta-knowledge
                    "event_type_boosts": {
                        "insight": 0.2,
                        "reflection": 0.2,
                        "performance": 0.1,
                        "meta": 0.2,
                        "system": 0.1,
                    },
                    "agent_type_boosts": {"meta": 0.3, "monitor": 0.2, "analyzer": 0.2},
                },
            },
            "vector_search": {
                "enabled": True,
                "threshold": 0.8,  # High precision for meta-knowledge
                "meta_weight": 0.6,  # Emphasize meta-cognitive matching
                "system_weight": 0.4,
            },
            # Operation-specific configurations
            "read_defaults": {
                "limit": 4,
                "similarity_threshold": 0.8,  # High precision for meta-knowledge
                "enable_vector_search": True,
                "enable_temporal_ranking": True,
                "temporal_weight": 0.2,
                "text_weight": 0.2,
                "vector_weight": 0.8,
                "enable_hybrid_search": True,
                "ef_runtime": 20,  # Most thorough search
                "enable_context_search": True,
                "context_weight": 0.2,
                "memory_category_filter": "store",
                "fallback_to_text": True,
            },
            "write_defaults": {
                "vector": True,
                "force_recreate_index": False,
                "store_metadata": True,
                "vector_field_name": "content_vector",
                "vector_params": {
                    "type": "FLOAT32",
                    "distance_metric": "COSINE",
                    "ef_construction": 400,  # Higher quality for meta
                    "m": 32,
                },
            },
            "namespace_prefix": "meta",
        },
    },
}


def get_memory_preset(preset_name: str, operation: str | None = None) -> Dict[str, Any]:
    """
    Get a memory preset configuration by name, with optional operation-specific defaults.

    Args:
        preset_name: Name of the preset (sensory, working, episodic, semantic, procedural, meta)
        operation: Memory operation type ('read' or 'write') for operation-specific defaults

    Returns:
        Dictionary containing the preset configuration, merged with operation-specific defaults

    Raises:
        ValueError: If preset_name is not found
    """
    if preset_name not in MEMORY_PRESETS:
        available = ", ".join(MEMORY_PRESETS.keys())
        raise ValueError(f"Unknown memory preset '{preset_name}'. Available presets: {available}")

    preset_config: Dict[str, Any] = MEMORY_PRESETS[preset_name]["config"]
    base_config: Dict[str, Any] = preset_config.copy()

    # Apply operation-specific defaults if operation is specified
    if operation and operation in ["read", "write"]:
        operation_key = f"{operation}_defaults"
        if operation_key in preset_config:
            operation_defaults: Dict[str, Any] = preset_config[operation_key]
            # Merge operation-specific defaults into base config
            base_config.update(operation_defaults)

    return base_config


def list_memory_presets() -> Dict[str, str]:
    """
    List all available memory presets with their descriptions.

    Returns:
        Dictionary mapping preset names to descriptions
    """
    return {name: config["description"] for name, config in MEMORY_PRESETS.items()}


def merge_preset_with_config(
    preset_name: str, custom_config: Dict[str, Any] | None = None, operation: str | None = None
) -> Dict[str, Any]:
    """
    Merge a memory preset with custom configuration overrides, including operation-specific defaults.

    Args:
        preset_name: Name of the preset to use as base
        custom_config: Custom configuration to override preset values
        operation: Memory operation type ('read' or 'write') for operation-specific defaults

    Returns:
        Merged configuration dictionary with operation-specific defaults applied
    """
    base_config = get_memory_preset(preset_name, operation)

    if not custom_config:
        return base_config

    # Deep merge the configurations
    merged = base_config.copy()

    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    return deep_merge(merged, custom_config)


def get_operation_defaults(preset_name: str, operation: str) -> Dict[str, Any]:
    """
    Get operation-specific defaults for a memory preset.

    Args:
        preset_name: Name of the preset
        operation: Memory operation type ('read' or 'write')

    Returns:
        Dictionary containing operation-specific defaults

    Raises:
        ValueError: If preset_name is not found or operation is invalid
    """
    if preset_name not in MEMORY_PRESETS:
        available = ", ".join(MEMORY_PRESETS.keys())
        raise ValueError(f"Unknown memory preset '{preset_name}'. Available presets: {available}")

    if operation not in ["read", "write"]:
        raise ValueError(f"Invalid operation '{operation}'. Must be 'read' or 'write'")

    preset_config: Dict[str, Any] = MEMORY_PRESETS[preset_name]["config"]
    operation_key = f"{operation}_defaults"

    if operation_key not in preset_config:
        return {}

    operation_defaults: Dict[str, Any] = preset_config[operation_key]
    return operation_defaults.copy()


def validate_preset_config(config: Dict[str, Any]) -> bool:
    """
    Validate that a memory configuration follows the expected structure.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_sections = ["decay"]

    # Check if any required section is missing
    if any(section not in config for section in required_sections):
        return False

    # Validate decay section
    decay = config["decay"]
    required_decay_fields = ["enabled", "default_short_term_hours", "default_long_term_hours"]

    # Check if all required decay fields are present
    return all(field in decay for field in required_decay_fields)


# Export the main functions and constants
__all__ = [
    "MEMORY_PRESETS",
    "get_memory_preset",
    "list_memory_presets",
    "merge_preset_with_config",
    "get_operation_defaults",
    "validate_preset_config",
]
