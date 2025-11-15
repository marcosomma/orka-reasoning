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
Validation Prompt Builder
=========================

Builds prompts for boolean-based plan validation.
"""

import json
import logging
from typing import Any, Dict, List

from orka.scoring.presets import get_criteria_description

logger = logging.getLogger(__name__)


def build_validation_prompt(
    query: str,
    proposed_path: Dict[str, Any],
    previous_critiques: List[Dict[str, Any]],
    loop_number: int,
    preset_name: str = "moderate",
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
    criteria_instructions = _build_criteria_instructions(preset_name)

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

**OUTPUT FORMAT (JSON only):**
{{
    "completeness": {{
        "has_all_required_steps": true/false,
        "addresses_all_query_aspects": true/false,
        "handles_edge_cases": true/false,
        "includes_fallback_path": true/false
    }},
    "efficiency": {{
        "minimizes_redundant_calls": true/false,
        "uses_appropriate_agents": true/false,
        "optimizes_cost": true/false,
        "optimizes_latency": true/false
    }},
    "safety": {{
        "validates_inputs": true/false,
        "handles_errors_gracefully": true/false,
        "has_timeout_protection": true/false,
        "avoids_risky_combinations": true/false
    }},
    "coherence": {{
        "logical_agent_sequence": true/false,
        "proper_data_flow": true/false,
        "no_conflicting_actions": true/false
    }},
    "rationale": "Brief explanation of your evaluation"
}}

Respond ONLY with the JSON structure above.
"""
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


def _build_criteria_instructions(preset_name: str) -> str:
    """
    Build instructions explaining each criterion.

    Args:
        preset_name: Scoring preset name

    Returns:
        Formatted instructions string
    """
    try:
        descriptions = get_criteria_description(preset_name)
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
    )
