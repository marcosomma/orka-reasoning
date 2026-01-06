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
Deterministic Path Evaluator
============================

Fallback evaluator using heuristics when LLM fails.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DeterministicPathEvaluator:
    """Fallback evaluator using heuristics when LLM fails."""

    def __init__(self, config: Any):
        """Initialize deterministic evaluator with config."""
        self.config = config
        logger.info("DeterministicPathEvaluator initialized for LLM fallback")

    def evaluate_candidates(
        self, candidates: List[Dict], question: str, context: Dict
    ) -> List[Dict]:
        """Evaluate candidates using rule-based heuristics."""
        evaluated = []

        for candidate in candidates:
            node_id = candidate["node_id"]
            path = candidate.get("path", [node_id])

            # Heuristic scoring
            relevance = self._score_relevance(node_id, question)
            confidence = self._score_confidence(path, context)
            efficiency = self._score_efficiency(path)

            candidate["llm_evaluation"] = {
                "relevance_score": relevance,
                "confidence": confidence,
                "reasoning": f"Heuristic evaluation: {node_id} matched question keywords",
                "expected_output": "Agent execution result",
                "estimated_tokens": 500,
                "estimated_cost": 0.001,
                "estimated_latency_ms": 1000,
                "risk_factors": [],
                "efficiency_rating": "medium",
                "is_deterministic_fallback": True,
            }

            candidate["llm_validation"] = {
                "is_valid": relevance > 0.5,
                "confidence": confidence,
                "efficiency_score": efficiency,
                "validation_reasoning": f"Heuristic validation based on path structure (length: {len(path)})",
                "suggested_improvements": [],
                "risk_assessment": "low",
                "is_deterministic_fallback": True,
            }

            evaluated.append(candidate)

        logger.info(f"DeterministicPathEvaluator evaluated {len(evaluated)} candidates")
        return evaluated

    def _score_relevance(self, node_id: str, question: str) -> float:
        """Score relevance based on keyword matching."""
        node_id_lower = node_id.lower()
        question_lower = question.lower()

        # Base score
        score = 0.5

        # Keyword matching
        keywords = {
            "search": ["search", "find", "look", "query"],
            "memory": ["remember", "recall", "history", "past"],
            "analysis": ["analyze", "evaluate", "assess", "examine"],
            "llm": ["generate", "create", "write", "answer"],
        }

        for agent_type, question_keywords in keywords.items():
            if agent_type in node_id_lower:
                if any(kw in question_lower for kw in question_keywords):
                    score += 0.3
                    break

        return min(1.0, score)

    def _score_confidence(self, path: List[str], context: Dict) -> float:
        """Score confidence based on path structure."""
        # Optimal path length gives higher confidence
        length = len(path)

        if 2 <= length <= 3:
            return 0.8  # Optimal length
        elif length == 1:
            return 0.6  # Single agent - might be incomplete
        elif length == 4:
            return 0.7  # Slightly longer, still acceptable
        else:
            return max(0.4, 0.7 - (length - 4) * 0.1)

    def _score_efficiency(self, path: List[str]) -> float:
        """Score efficiency based on path length."""
        length = len(path)

        # Shorter paths are more efficient
        if length <= 2:
            return 0.9
        elif length == 3:
            return 0.8
        elif length == 4:
            return 0.6
        else:
            return max(0.3, 0.6 - (length - 4) * 0.1)

