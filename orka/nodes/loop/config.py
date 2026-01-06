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

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_HIGH_PRIORITY_AGENTS: List[str] = [
    "agreement_moderator",
    "quality_moderator",
    "score_moderator",
]

DEFAULT_SCORE_EXTRACTION_CONFIG: Dict[str, Any] = {
    "strategies": [
        {
            "type": "pattern",
            "patterns": [
                r"score:\s*(\d+\.?\d*)",
                r"rating:\s*(\d+\.?\d*)",
                r"confidence:\s*(\d+\.?\d*)",
                r"agreement:\s*(\d+\.?\d*)",
                r"consensus:\s*(\d+\.?\d*)",
                r"AGREEMENT:\s*(\d+\.?\d*)",
                r"SCORE:\s*(\d+\.?\d*)",
                r"Score:\s*(\d+\.?\d*)",
                r"Agreement:\s*(\d+\.?\d*)",
                r"(\d+\.?\d*)/10",
                r"(\d+\.?\d*)%",
                r"(\d+\.?\d*)\s*out\s*of\s*10",
                r"(\d+\.?\d*)\s*points?",
                r"0\.[6-9][0-9]?",  # Pattern for high agreement scores
                r"([0-9]+\.[0-9]+)",  # Any decimal number
            ],
        }
    ]
}

DEFAULT_PAST_LOOPS_METADATA: Dict[str, str] = {
    "loop_number": "{{ loop_number }}",
    "score": "{{ score }}",
    "timestamp": "{{ timestamp }}",
    "insights": "{{ insights }}",
    "improvements": "{{ improvements }}",
    "mistakes": "{{ mistakes }}",
}

DEFAULT_COGNITIVE_EXTRACTION: Dict[str, Any] = {
    "enabled": True,
    "max_length_per_category": 300,
    "extract_patterns": {
        "insights": [],
        "improvements": [],
        "mistakes": [],
    },
    "agent_priorities": {},
}


@dataclass(frozen=True)
class LoopNodeConfig:
    max_loops: int
    score_threshold: float

    scoring_preset: Optional[str]
    scoring_context: str
    custom_weights: Optional[Dict[str, float]]
    score_calculator: Any  # Optional[BooleanScoreCalculator], kept as Any to avoid import coupling.

    high_priority_agents: List[str]
    score_extraction_config: Dict[str, Any]

    internal_workflow: Dict[str, Any]
    past_loops_metadata: Dict[str, str]
    cognitive_extraction: Dict[str, Any]
    persist_across_runs: bool


def build_loop_node_config(
    node_id: str,
    kwargs: Dict[str, Any],
    *,
    calculator_cls: Any,
    logger: Any,
) -> LoopNodeConfig:
    max_loops: int = kwargs.get("max_loops", 5)
    score_threshold: float = kwargs.get("score_threshold", 0.8)

    # Boolean scoring configuration (optional)
    scoring_config = kwargs.get("scoring", {})
    scoring_preset: Optional[str] = (
        scoring_config.get("preset") if isinstance(scoring_config, dict) else None
    )
    custom_weights: Optional[Dict[str, float]] = (
        scoring_config.get("custom_weights") if isinstance(scoring_config, dict) else None
    )
    # Scoring context (e.g., 'loop_convergence', 'quality', 'graphscout')
    scoring_context: str = (
        scoring_config.get("context") if isinstance(scoring_config, dict) else "loop_convergence"
    )

    score_calculator: Any = None
    if scoring_preset:
        try:
            score_calculator = calculator_cls(
                preset=scoring_preset,
                context=scoring_context,
                custom_weights=custom_weights,
            )
            logger.info(
                f"LoopNode '{node_id}': Initialized with boolean scoring preset '{scoring_preset}'"
            )
        except Exception as e:
            logger.warning(
                f"LoopNode '{node_id}': Failed to initialize boolean scoring: {e}. "
                "Falling back to legacy score extraction."
            )
            score_calculator = None

    high_priority_agents: List[str] = kwargs.get(
        "high_priority_agents", copy.deepcopy(DEFAULT_HIGH_PRIORITY_AGENTS)
    )

    # Debug: Log the received configuration
    if "score_extraction_config" in kwargs:
        logger.debug(f"LoopNode {node_id}: Received custom score_extraction_config from YAML")
        custom_config = kwargs["score_extraction_config"]
        if isinstance(custom_config, dict) and "strategies" in custom_config:
            logger.debug(f"LoopNode {node_id}: Found {len(custom_config['strategies'])} strategies")
            for i, strategy in enumerate(custom_config["strategies"]):
                if strategy.get("type") == "pattern" and "patterns" in strategy:
                    logger.debug(
                        f"LoopNode {node_id}: Strategy {i+1} has {len(strategy['patterns'])} patterns"
                    )
                    logger.debug(
                        f"LoopNode {node_id}: First pattern: {strategy['patterns'][0] if strategy['patterns'] else 'None'}"
                    )
    else:
        logger.debug(f"LoopNode {node_id}: No custom score_extraction_config, using defaults")

    score_extraction_config: Dict[str, Any] = kwargs.get(
        "score_extraction_config", copy.deepcopy(DEFAULT_SCORE_EXTRACTION_CONFIG)
    )

    # Debug: Log which configuration is actually being used
    if isinstance(score_extraction_config, dict) and "strategies" in score_extraction_config:
        strategy_count = len(score_extraction_config["strategies"])
        logger.debug(f"LoopNode {node_id}: Using {strategy_count} extraction strategies")
        for i, strategy in enumerate(score_extraction_config["strategies"]):
            if strategy.get("type") == "pattern" and "patterns" in strategy:
                pattern_count = len(strategy["patterns"])
                first_pattern = strategy["patterns"][0] if strategy["patterns"] else "None"
                logger.debug(
                    f"LoopNode {node_id}: Strategy {i+1} (pattern): {pattern_count} patterns, first: {first_pattern}"
                )

    # Backward compatibility - convert old format to new format
    if "score_extraction_pattern" in kwargs or "score_extraction_key" in kwargs:
        logger.warning(
            "score_extraction_pattern and score_extraction_key are deprecated. Use score_extraction_config instead.",
        )

        old_strategies: List[Dict[str, Any]] = []
        if "score_extraction_key" in kwargs:
            old_strategies.append({"type": "direct_key", "key": kwargs["score_extraction_key"]})
        if "score_extraction_pattern" in kwargs:
            old_strategies.append(
                {"type": "pattern", "patterns": [kwargs["score_extraction_pattern"]]}
            )
        if old_strategies:
            score_extraction_config = {"strategies": old_strategies}

    internal_workflow: Dict[str, Any] = kwargs.get("internal_workflow", {})

    user_metadata = kwargs.get("past_loops_metadata", {})
    if user_metadata:
        past_loops_metadata: Dict[str, str] = user_metadata
    else:
        logger.debug("Using default past_loops_metadata structure")
        past_loops_metadata = copy.deepcopy(DEFAULT_PAST_LOOPS_METADATA)

    cognitive_extraction: Dict[str, Any] = kwargs.get(
        "cognitive_extraction", copy.deepcopy(DEFAULT_COGNITIVE_EXTRACTION)
    )

    # Default should be isolated per run. Persistence across runs is opt-in.
    persist_across_runs: bool = kwargs.get("persist_across_runs", False)

    return LoopNodeConfig(
        max_loops=max_loops,
        score_threshold=score_threshold,
        scoring_preset=scoring_preset,
        scoring_context=scoring_context,
        custom_weights=custom_weights,
        score_calculator=score_calculator,
        high_priority_agents=high_priority_agents,
        score_extraction_config=score_extraction_config,
        internal_workflow=internal_workflow,
        past_loops_metadata=past_loops_metadata,
        cognitive_extraction=cognitive_extraction,
        persist_across_runs=persist_across_runs,
    )


