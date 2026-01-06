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
Scoring Presets
===============

Context-aware scoring configurations for different evaluation scenarios.

Preset Contexts
---------------
- **graphscout**: Path evaluation for GraphScout agent routing
- **quality**: Generic response quality assessment  
- **loop_convergence**: Iterative improvement loops (LoopNode)
- **validation**: Schema and constraint validation

Each context provides strict/moderate/lenient severity levels.

Migration Guide
--------------
**OLD USAGE** (deprecated):
```python
preset = load_preset("strict")  # Ambiguous context
```

**NEW USAGE** (recommended):
```python
preset = load_preset("strict", context="graphscout")
# Or use backward-compatible default
preset = load_preset("strict")  # Defaults to graphscout for compatibility
```

**YAML Configuration**:
```yaml
- id: validator
  type: loop_validator
  scoring_preset: "strict"           # OLD: Defaults to graphscout
  scoring_context: "quality"         # NEW: Explicit context
```
"""

from typing import Dict, Any, Optional

# Context-specific preset configurations
PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    # ============================================================================
    # GRAPHSCOUT CONTEXT - Agent path evaluation
    # ============================================================================
    "graphscout": {
        "strict": {
            "description": "High standards for production-critical agent paths",
            "context": "graphscout",
            "weights": {
                "completeness": {
                    "has_all_required_steps": 0.20,
                    "addresses_all_query_aspects": 0.15,
                    "handles_edge_cases": 0.10,
                    "includes_fallback_path": 0.10,
                },
                "efficiency": {
                    "minimizes_redundant_calls": 0.08,
                    "uses_appropriate_agents": 0.08,
                    "optimizes_cost": 0.04,
                    "optimizes_latency": 0.04,
                },
                "safety": {
                    "validates_inputs": 0.06,
                    "handles_errors_gracefully": 0.05,
                    "has_timeout_protection": 0.03,
                    "avoids_risky_combinations": 0.02,
                },
                "coherence": {
                    "logical_agent_sequence": 0.03,
                    "proper_data_flow": 0.01,
                    "no_conflicting_actions": 0.01,
                },
            },
            "thresholds": {
                "approved": 0.90,
                "needs_improvement": 0.75,
            },
        },
        "moderate": {
            "description": "Balanced approach for general-purpose agent paths",
            "context": "graphscout",
            "weights": {
                "completeness": {
                    "has_all_required_steps": 0.18,
                    "addresses_all_query_aspects": 0.12,
                    "handles_edge_cases": 0.08,
                    "includes_fallback_path": 0.07,
                },
                "efficiency": {
                    "minimizes_redundant_calls": 0.10,
                    "uses_appropriate_agents": 0.10,
                    "optimizes_cost": 0.05,
                    "optimizes_latency": 0.05,
                },
                "safety": {
                    "validates_inputs": 0.08,
                    "handles_errors_gracefully": 0.07,
                    "has_timeout_protection": 0.03,
                    "avoids_risky_combinations": 0.02,
                },
                "coherence": {
                    "logical_agent_sequence": 0.03,
                    "proper_data_flow": 0.01,
                    "no_conflicting_actions": 0.01,
                },
            },
            "thresholds": {
                "approved": 0.85,
                "needs_improvement": 0.70,
            },
        },
        "lenient": {
            "description": "Relaxed standards for exploratory agent paths",
            "context": "graphscout",
            "weights": {
                "completeness": {
                    "has_all_required_steps": 0.15,
                    "addresses_all_query_aspects": 0.10,
                    "handles_edge_cases": 0.05,
                    "includes_fallback_path": 0.05,
                },
                "efficiency": {
                    "minimizes_redundant_calls": 0.12,
                    "uses_appropriate_agents": 0.12,
                    "optimizes_cost": 0.06,
                    "optimizes_latency": 0.06,
                },
                "safety": {
                    "validates_inputs": 0.10,
                    "handles_errors_gracefully": 0.08,
                    "has_timeout_protection": 0.04,
                    "avoids_risky_combinations": 0.02,
                },
                "coherence": {
                    "logical_agent_sequence": 0.03,
                    "proper_data_flow": 0.01,
                    "no_conflicting_actions": 0.01,
                },
            },
            "thresholds": {
                "approved": 0.80,
                "needs_improvement": 0.65,
            },
        },
    },
    
    # ============================================================================
    # QUALITY CONTEXT - Response quality assessment
    # ============================================================================
    "quality": {
        "strict": {
            "description": "High standards for response quality",
            "context": "quality",
            "weights": {
                "accuracy": {
                    "factually_correct": 0.25,
                    "addresses_question": 0.20,
                    "no_hallucinations": 0.15,
                },
                "completeness": {
                    "comprehensive_answer": 0.15,
                    "includes_examples": 0.05,
                },
                "clarity": {
                    "well_structured": 0.08,
                    "easy_to_understand": 0.07,
                },
                "relevance": {
                    "stays_on_topic": 0.05,
                },
            },
            "thresholds": {
                "approved": 0.90,
                "needs_improvement": 0.75,
            },
        },
        "moderate": {
            "description": "Balanced quality standards",
            "context": "quality",
            "weights": {
                "accuracy": {
                    "factually_correct": 0.22,
                    "addresses_question": 0.18,
                    "no_hallucinations": 0.12,
                },
                "completeness": {
                    "comprehensive_answer": 0.18,
                    "includes_examples": 0.08,
                },
                "clarity": {
                    "well_structured": 0.10,
                    "easy_to_understand": 0.07,
                },
                "relevance": {
                    "stays_on_topic": 0.05,
                },
            },
            "thresholds": {
                "approved": 0.85,
                "needs_improvement": 0.70,
            },
        },
        "lenient": {
            "description": "Relaxed quality standards for exploratory responses",
            "context": "quality",
            "weights": {
                "accuracy": {
                    "factually_correct": 0.20,
                    "addresses_question": 0.15,
                    "no_hallucinations": 0.10,
                },
                "completeness": {
                    "comprehensive_answer": 0.20,
                    "includes_examples": 0.10,
                },
                "clarity": {
                    "well_structured": 0.12,
                    "easy_to_understand": 0.08,
                },
                "relevance": {
                    "stays_on_topic": 0.05,
                },
            },
            "thresholds": {
                "approved": 0.75,
                "needs_improvement": 0.60,
            },
        },
    },
    
    # ============================================================================
    # LOOP_CONVERGENCE CONTEXT - Iterative improvement evaluation
    # ============================================================================
    "loop_convergence": {
        "strict": {
            "description": "Strict convergence criteria for iterative loops",
            "context": "loop_convergence",
            "weights": {
                "improvement": {
                    "better_than_previous": 0.30,
                    "significant_delta": 0.15,
                    "approaching_target": 0.10,
                },
                "stability": {
                    "not_degrading": 0.15,
                    "consistent_direction": 0.10,
                },
                "convergence": {
                    "delta_decreasing": 0.10,
                    "within_tolerance": 0.10,
                },
            },
            "thresholds": {
                "approved": 0.90,
                "needs_improvement": 0.75,
                "terminate_loop": 0.50,  # Stop if below this
            },
        },
        "moderate": {
            "description": "Balanced convergence criteria",
            "context": "loop_convergence",
            "weights": {
                "improvement": {
                    "better_than_previous": 0.25,
                    "significant_delta": 0.15,
                    "approaching_target": 0.10,
                },
                "stability": {
                    "not_degrading": 0.18,
                    "consistent_direction": 0.12,
                },
                "convergence": {
                    "delta_decreasing": 0.12,
                    "within_tolerance": 0.08,
                },
            },
            "thresholds": {
                "approved": 0.85,
                "needs_improvement": 0.70,
                "terminate_loop": 0.45,
            },
        },
        "lenient": {
            "description": "Relaxed convergence criteria for exploratory loops",
            "context": "loop_convergence",
            "weights": {
                "improvement": {
                    "better_than_previous": 0.25,
                    "significant_delta": 0.12,
                    "approaching_target": 0.08,
                },
                "stability": {
                    "not_degrading": 0.20,
                    "consistent_direction": 0.15,
                },
                "convergence": {
                    "delta_decreasing": 0.10,
                    "within_tolerance": 0.10,
                },
            },
            "thresholds": {
                "approved": 0.75,
                "needs_improvement": 0.60,
                "terminate_loop": 0.40,
            },
        },
    },
    
    # ============================================================================
    # VALIDATION CONTEXT - Schema and constraint validation
    # ============================================================================
    "validation": {
        "strict": {
            "description": "Strict validation of schema and constraints",
            "context": "validation",
            "weights": {
                "schema_compliance": {
                    "matches_schema": 0.30,
                    "all_required_fields": 0.20,
                    "correct_types": 0.15,
                },
                "constraints": {
                    "within_bounds": 0.15,
                    "valid_relationships": 0.10,
                },
                "format": {
                    "well_formed": 0.10,
                },
            },
            "thresholds": {
                "approved": 0.95,
                "needs_improvement": 0.85,
            },
        },
        "moderate": {
            "description": "Balanced validation criteria",
            "context": "validation",
            "weights": {
                "schema_compliance": {
                    "matches_schema": 0.25,
                    "all_required_fields": 0.20,
                    "correct_types": 0.15,
                },
                "constraints": {
                    "within_bounds": 0.18,
                    "valid_relationships": 0.12,
                },
                "format": {
                    "well_formed": 0.10,
                },
            },
            "thresholds": {
                "approved": 0.90,
                "needs_improvement": 0.75,
            },
        },
        "lenient": {
            "description": "Relaxed validation for drafts",
            "context": "validation",
            "weights": {
                "schema_compliance": {
                    "matches_schema": 0.20,
                    "all_required_fields": 0.18,
                    "correct_types": 0.15,
                },
                "constraints": {
                    "within_bounds": 0.20,
                    "valid_relationships": 0.15,
                },
                "format": {
                    "well_formed": 0.12,
                },
            },
            "thresholds": {
                "approved": 0.80,
                "needs_improvement": 0.65,
            },
        },
    },
}


def load_preset(
    preset_name: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load a scoring preset by name and context.

    Args:
        preset_name: Name of preset ('strict', 'moderate', or 'lenient')
        context: Evaluation context ('graphscout', 'quality', 'loop_convergence', 'validation')
                 If None, defaults to 'graphscout' for backward compatibility

    Returns:
        Preset configuration dict

    Raises:
        ValueError: If preset name or context is invalid

    Examples:
        >>> # New context-aware usage
        >>> preset = load_preset("strict", context="quality")
        >>> 
        >>> # Backward compatible (defaults to graphscout)
        >>> preset = load_preset("moderate")
    """
    # Default to graphscout for backward compatibility
    if context is None:
        context = "graphscout"
    
    if context not in PRESETS:
        available_contexts = ", ".join(PRESETS.keys())
        raise ValueError(
            f"Unknown scoring context '{context}'. Available: {available_contexts}"
        )
    
    if preset_name not in PRESETS[context]:
        available_presets = ", ".join(PRESETS[context].keys())
        raise ValueError(
            f"Unknown scoring preset '{preset_name}' for context '{context}'. "
            f"Available: {available_presets}"
        )

    return PRESETS[context][preset_name]


def get_available_contexts() -> list[str]:
    """
    Get list of available scoring contexts.

    Returns:
        List of context names
    """
    return list(PRESETS.keys())


def get_available_presets(context: str) -> list[str]:
    """
    Get list of available presets for a context.

    Args:
        context: Scoring context

    Returns:
        List of preset names

    Raises:
        ValueError: If context is invalid
    """
    if context not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(
            f"Unknown context '{context}'. Available: {available}"
        )
    
    return list(PRESETS[context].keys())


def get_criteria_description(preset_name: str, context: str = "graphscout") -> Dict[str, str]:
    """
    Get human-readable descriptions of criteria for a preset.

    Args:
        preset_name: Name of preset
        context: Evaluation context (default: 'graphscout')

    Returns:
        Dict mapping criterion paths to descriptions
    """
    # Context-specific descriptions
    descriptions = {
        "graphscout": {
            "completeness.has_all_required_steps": "All necessary steps are included in the path",
            "completeness.addresses_all_query_aspects": "The path addresses every aspect of the user query",
            "completeness.handles_edge_cases": "Edge cases and unusual inputs are handled",
            "completeness.includes_fallback_path": "Alternative paths exist for failures",
            "efficiency.minimizes_redundant_calls": "No unnecessary duplicate agent calls",
            "efficiency.uses_appropriate_agents": "Best agents selected for each task",
            "efficiency.optimizes_cost": "Token usage is minimized where possible",
            "efficiency.optimizes_latency": "Response time is minimized",
            "safety.validates_inputs": "Input validation is performed",
            "safety.handles_errors_gracefully": "Error handling is comprehensive",
            "safety.has_timeout_protection": "Timeouts prevent hanging operations",
            "safety.avoids_risky_combinations": "No dangerous agent combinations",
            "coherence.logical_agent_sequence": "Agents are called in logical order",
            "coherence.proper_data_flow": "Data flows correctly between agents",
            "coherence.no_conflicting_actions": "No agents work against each other",
        },
        "quality": {
            "accuracy.factually_correct": "Information is factually accurate",
            "accuracy.addresses_question": "Directly answers the asked question",
            "accuracy.no_hallucinations": "No invented or false information",
            "completeness.comprehensive_answer": "Answer is thorough and complete",
            "completeness.includes_examples": "Includes relevant examples or evidence",
            "clarity.well_structured": "Response is well-organized",
            "clarity.easy_to_understand": "Language is clear and accessible",
            "relevance.stays_on_topic": "Stays focused on the question",
        },
        "loop_convergence": {
            "improvement.better_than_previous": "Current iteration better than previous",
            "improvement.significant_delta": "Meaningful improvement observed",
            "improvement.approaching_target": "Moving towards target/goal",
            "stability.not_degrading": "Quality not decreasing",
            "stability.consistent_direction": "Improvements in consistent direction",
            "convergence.delta_decreasing": "Change rate is decreasing",
            "convergence.within_tolerance": "Within acceptable tolerance of target",
        },
        "validation": {
            "schema_compliance.matches_schema": "Data matches defined schema",
            "schema_compliance.all_required_fields": "All required fields present",
            "schema_compliance.correct_types": "Field types are correct",
            "constraints.within_bounds": "Values within defined constraints",
            "constraints.valid_relationships": "Relationships between fields are valid",
            "format.well_formed": "Data is properly formatted",
        },
    }

    return descriptions.get(context, {})
