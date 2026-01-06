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
Validation Prompt Builder
=========================

Builds prompts for boolean-based plan validation.
"""

import json
import logging
from typing import Any, Dict, List

from orka.scoring.presets import get_criteria_description, load_preset

logger = logging.getLogger(__name__)


def build_validation_prompt(
    query: str,
    proposed_path: Dict[str, Any],
    previous_critiques: List[Dict[str, Any]],
    loop_number: int,
    preset_name: str = "moderate",
    scoring_context: str | None = None,
    skip_json_instructions: bool = False,
) -> str:
    """
    Build validation prompt requesting boolean evaluations.

    Args:
        query: Original user query
        proposed_path: Path proposed by GraphScout
        previous_critiques: Past validation feedback
        loop_number: Current iteration number
        preset_name: Scoring preset name for criteria descriptions

    Returns:
        Formatted prompt string
    """
    critique_history = _format_critique_history(previous_critiques)
    criteria_instructions = _build_criteria_instructions(preset_name, scoring_context)

    prompt = f"""You are a Plan Validator agent. Your job is to evaluate proposed agent execution paths using boolean criteria.

**VALIDATION ROUND:** {loop_number}

**ORIGINAL QUERY:**
{query}

**PROPOSED PATH (from GraphScout):**
{json.dumps(proposed_path, indent=2)}
{critique_history}

**YOUR TASK:**
Evaluate the proposed path by answering TRUE or FALSE for each criterion below.

{criteria_instructions}

"""

    if not skip_json_instructions:
        prompt += """
**OUTPUT FORMAT (JSON only):**
{
    "completeness": {
        "has_all_required_steps": true/false,
        "addresses_all_query_aspects": true/false,
        "handles_edge_cases": true/false,
        "includes_fallback_path": true/false
    },
    "efficiency": {
        "minimizes_redundant_calls": true/false,
        "uses_appropriate_agents": true/false,
        "optimizes_cost": true/false,
        "optimizes_latency": true/false
    },
    "safety": {
        "validates_inputs": true/false,
        "handles_errors_gracefully": true/false,
        "has_timeout_protection": true/false,
        "avoids_risky_combinations": true/false
    },
    "coherence": {
        "logical_agent_sequence": true/false,
        "proper_data_flow": true/false,
        "no_conflicting_actions": true/false
    },
    "rationale": "Brief explanation of your evaluation"
}

Respond ONLY with the JSON structure above.

"""

    # If a specific scoring context is requested, dynamically build an
    # ADDITIONAL OUTPUT FORMAT block from the preset weights so the prompt is
    # generic and driven by configuration rather than hardcoded fields.
    if scoring_context and not skip_json_instructions:
        try:
            preset = load_preset(preset_name, context=scoring_context)
            weights = preset.get("weights", {})

            schema_lines = [f"\n\nADDITIONAL OUTPUT FORMAT FOR {scoring_context} CONTEXT (JSON only):", "{"]

            for dim, crits in weights.items():
                schema_lines.append(f'  "{dim}": {{')
                crit_lines = []
                for crit in crits.keys():
                    crit_lines.append(f'    "{crit}": true/false')
                # join with commas and add
                schema_lines.append(
                    ",\n".join(crit_lines)
                )
                schema_lines.append("  },")

            # Add a rationale field and close the object
            schema_lines.append('  "rationale": "Brief explanation of your evaluation"')
            schema_lines.append("}")
            schema_lines.append(f"\nRespond ONLY with the JSON structure above for the {scoring_context} output.")

            prompt += "\n" + "\n".join(schema_lines)

        except Exception as e:
            # If the context/preset cannot be loaded, log and continue without
            # raising — we want the prompt builder to be robust in all cases.
            logger.warning(f"Could not build context-specific schema for '{scoring_context}': {e}")

    return prompt


def _format_critique_history(previous_critiques: List[Dict[str, Any]]) -> str:
    """
    Format previous critiques into readable string.

    Args:
        previous_critiques: List of past critique dicts

    Returns:
        Formatted history string
    """
    if not previous_critiques:
        return ""

    history = "\n\n**PREVIOUS CRITIQUES:**\n"
    for i, critique in enumerate(previous_critiques, 1):
        score = critique.get("score", critique.get("validation_score", "N/A"))
        assessment = critique.get("assessment", critique.get("overall_assessment", "N/A"))
        history += f"Round {i}: Score={score}, Assessment={assessment}\n"

        if "failed_criteria" in critique:
            failed = critique["failed_criteria"]
            if failed:
                history += f"  Failed: {', '.join(failed[:5])}\n"

    return history


def _build_criteria_instructions(preset_name: str, context: str | None = None) -> str:
    """
    Build instructions explaining each criterion.

    Args:
        preset_name: Scoring preset name

    Returns:
        Formatted instructions string
    """
    try:
        descriptions = get_criteria_description(preset_name, context=context or "graphscout")
    except Exception as e:
        logger.warning(f"Failed to load criteria descriptions: {e}")
        descriptions = {}

    dimensions = {
        "COMPLETENESS": [
            "has_all_required_steps",
            "addresses_all_query_aspects",
            "handles_edge_cases",
            "includes_fallback_path",
        ],
        "EFFICIENCY": [
            "minimizes_redundant_calls",
            "uses_appropriate_agents",
            "optimizes_cost",
            "optimizes_latency",
        ],
        "SAFETY": [
            "validates_inputs",
            "handles_errors_gracefully",
            "has_timeout_protection",
            "avoids_risky_combinations",
        ],
        "COHERENCE": [
            "logical_agent_sequence",
            "proper_data_flow",
            "no_conflicting_actions",
        ],
    }

    lines = ["**EVALUATION CRITERIA:**\n"]

    for dimension_name, criteria in dimensions.items():
        lines.append(f"\n{dimension_name}:")

        for criterion in criteria:
            key = f"{dimension_name.lower()}.{criterion}"
            description = descriptions.get(key, "Evaluate this criterion")
            lines.append(f"  - {criterion}: {description}")

    return "\n".join(lines)


def build_simple_validation_prompt(
    query: str,
    proposed_path: Dict[str, Any],
) -> str:
    """
    Build simplified validation prompt (for quick validation).

    Args:
        query: Original user query
        proposed_path: Path proposed by GraphScout

    Returns:
        Formatted prompt string
    """
    return build_validation_prompt(
        query=query,
        proposed_path=proposed_path,
        previous_critiques=[],
        loop_number=1,
        preset_name="moderate",
        scoring_context=None,
    )
