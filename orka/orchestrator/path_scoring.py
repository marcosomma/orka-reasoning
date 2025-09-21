# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Path Scoring System
==================

Multi-criteria scoring system for evaluating candidate paths.
Combines LLM evaluation, heuristics, historical priors, and budget considerations.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PathScorer:
    """
    Multi-criteria path scoring system.

    Evaluates candidate paths using:
    - LLM relevance assessment
    - Heuristic matching (capabilities, constraints)
    - Historical success priors
    - Cost and latency penalties
    - Safety risk assessment
    """

    def __init__(self, config: Any):
        """Initialize path scorer with configuration."""
        self.config = config
        self.score_weights = config.score_weights

        # Initialize LLM evaluator (placeholder for now)
        self.llm_evaluator = None

        logger.debug(f"PathScorer initialized with weights: {self.score_weights}")

    async def score_candidates(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Score all candidates using multi-criteria evaluation.

        Args:
            candidates: List of candidate paths to score
            question: The question/query being routed
            context: Execution context

        Returns:
            List of candidates with scores and components
        """
        try:
            scored_candidates = []

            # Score each candidate
            for candidate in candidates:
                score_components = await self._score_candidate(candidate, question, context)

                # Calculate final weighted score
                final_score = self._calculate_final_score(score_components)

                # Add scoring information to candidate
                candidate["score"] = final_score
                candidate["score_components"] = score_components
                candidate["confidence"] = self._calculate_confidence(score_components)

                scored_candidates.append(candidate)

            # Sort by score (descending)
            scored_candidates.sort(key=lambda x: x["score"], reverse=True)

            # Apply beam width limiting after scoring to keep only top candidates
            k_beam = getattr(self.config, "k_beam", 3)
            final_candidates = scored_candidates[:k_beam]

            logger.info(
                f"Scored {len(scored_candidates)} candidates, "
                f"top score: {scored_candidates[0]['score']:.3f}, "
                f"keeping top {len(final_candidates)} (k_beam={k_beam})"
            )

            return final_candidates

        except Exception as e:
            logger.error(f"Candidate scoring failed: {e}")
            return candidates

    async def _score_candidate(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Score a single candidate across all criteria."""
        try:
            components = {}

            # DEBUG: Log path information for debugging
            path = candidate.get("path", [candidate.get("node_id", "")])
            is_multi_hop = len(path) > 1

            if is_multi_hop:
                logger.info(f"🔍 SCORING multi-hop path: {' → '.join(path)} (depth: {len(path)})")
            else:
                logger.info(f"🔍 SCORING single-hop path: {path[0] if path else 'unknown'}")

            # Normal scoring for all paths
            components["llm"] = await self._score_llm_relevance(candidate, question, context)
            components["heuristics"] = await self._score_heuristics(candidate, question, context)
            components["prior"] = await self._score_priors(candidate, question, context)
            components["cost"] = await self._score_cost(candidate, context)
            components["latency"] = await self._score_latency(candidate, context)

            return components

        except Exception as e:
            logger.error(f"Individual candidate scoring failed: {e}")
            return {"llm": 0.0, "heuristics": 0.0, "prior": 0.0, "cost": 0.0, "latency": 0.0}

    async def _score_llm_relevance(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> float:
        """Score candidate relevance using LLM evaluation results."""
        try:
            # Use LLM evaluation results from SmartPathEvaluator
            llm_eval = candidate.get("llm_evaluation", {})

            if llm_eval:
                # Use the final relevance score from two-stage LLM evaluation
                final_scores = llm_eval.get("final_scores", {})
                relevance_score = final_scores.get("relevance", 0.5)

                logger.debug(
                    f"Using LLM relevance score: {relevance_score} for {candidate['node_id']}"
                )
                return float(relevance_score)

            # Fallback to heuristic if no LLM evaluation available
            node_id = candidate["node_id"]
            path = candidate["path"]

            # Simple keyword matching as fallback
            question_lower = question.lower()
            relevance_score = 0.5  # Default neutral score

            # Boost score for certain node types based on question content
            if "search" in question_lower and "search" in node_id.lower():
                relevance_score += 0.3
            elif "memory" in question_lower and "memory" in node_id.lower():
                relevance_score += 0.3
            elif "analyze" in question_lower and "llm" in node_id.lower():
                relevance_score += 0.3

            # Penalize very long paths
            if len(path) > 3:
                relevance_score -= 0.1

            return min(1.0, max(0.0, relevance_score))

        except Exception as e:
            logger.error(f"LLM relevance scoring failed: {e}")
            return 0.5

    async def _score_heuristics(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> float:
        """Score candidate using rule-based heuristics."""
        try:
            score = 0.0

            # Input readiness check
            score += self._check_input_readiness(candidate, context) * 0.3

            # Modality fit check
            score += self._check_modality_fit(candidate, question) * 0.3

            # Domain overlap check
            score += self._check_domain_overlap(candidate, question) * 0.2

            # Safety fit check
            score += self._check_safety_fit(candidate, context) * 0.2

            return min(1.0, max(0.0, score))

        except Exception as e:
            logger.error(f"Heuristic scoring failed: {e}")
            return 0.5

    async def _score_priors(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any]
    ) -> float:
        """Score candidate based on historical success."""
        try:
            # TODO: Implement actual prior lookup from memory
            # For now, return neutral score

            node_id = candidate["node_id"]

            # Simple heuristic: prefer shorter paths initially
            path_length = len(candidate["path"])
            if path_length == 1:
                return 0.7  # Prefer direct paths
            elif path_length == 2:
                return 0.5  # Neutral for 2-step paths
            else:
                return 0.3  # Penalize longer paths

        except Exception as e:
            logger.error(f"Prior scoring failed: {e}")
            return 0.5

    async def _score_cost(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Score candidate based on cost efficiency."""
        try:
            estimated_cost = candidate.get("estimated_cost", 0.001)

            # Normalize cost to 0-1 scale (inverted - lower cost is better)
            max_reasonable_cost = 0.1  # $0.10 as reasonable maximum
            normalized_cost = min(1.0, estimated_cost / max_reasonable_cost)

            # Return inverted score (1.0 for low cost, 0.0 for high cost)
            return float(1.0 - normalized_cost)

        except Exception as e:
            logger.error(f"Cost scoring failed: {e}")
            return 0.5

    async def _score_latency(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Score candidate based on latency efficiency."""
        try:
            estimated_latency = candidate.get("estimated_latency", 1000)

            # Normalize latency to 0-1 scale (inverted - lower latency is better)
            max_reasonable_latency = 10000  # 10 seconds as reasonable maximum
            normalized_latency = min(1.0, estimated_latency / max_reasonable_latency)

            # Return inverted score (1.0 for low latency, 0.0 for high latency)
            return float(1.0 - normalized_latency)

        except Exception as e:
            logger.error(f"Latency scoring failed: {e}")
            return 0.5

    def _calculate_final_score(self, components: Dict[str, float]) -> float:
        """Calculate weighted final score from components."""
        try:
            final_score = 0.0

            for component, score in components.items():
                weight = self.score_weights.get(component, 0.0)
                final_score += weight * score

            return min(1.0, max(0.0, final_score))

        except Exception as e:
            logger.error(f"Final score calculation failed: {e}")
            return 0.0

    def _calculate_confidence(self, components: Dict[str, float]) -> float:
        """Calculate confidence based on score consistency."""
        try:
            scores = list(components.values())
            if not scores:
                return 0.0

            # High confidence when scores are consistently high
            avg_score = sum(scores) / len(scores)

            # Calculate variance to penalize inconsistent scores
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            consistency_penalty = min(0.3, variance)

            confidence = avg_score - consistency_penalty
            return min(1.0, max(0.0, confidence))

        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.0

    def _check_input_readiness(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Check if required inputs are available."""
        try:
            # TODO: Implement actual input requirement checking
            # For now, assume inputs are generally available
            return 0.8

        except Exception:
            return 0.5

    def _check_modality_fit(self, candidate: Dict[str, Any], question: str) -> float:
        """Check if candidate matches question modality."""
        try:
            node_id = candidate["node_id"].lower()
            question_lower = question.lower()

            # Simple modality matching
            if any(word in question_lower for word in ["image", "picture", "visual"]):
                if "vision" in node_id or "image" in node_id:
                    return 1.0
                else:
                    return 0.3

            # Text processing is default
            return 0.7

        except Exception:
            return 0.5

    def _check_domain_overlap(self, candidate: Dict[str, Any], question: str) -> float:
        """Check domain overlap between candidate and question."""
        try:
            # TODO: Implement semantic similarity checking
            # For now, use simple keyword overlap

            node_id = candidate["node_id"].lower()
            question_words = set(question.lower().split())
            node_words = set(node_id.split("_"))

            overlap = len(question_words & node_words)
            max_possible = min(len(question_words), len(node_words))

            if max_possible == 0:
                return 0.5

            return overlap / max_possible

        except Exception:
            return 0.5

    def _check_safety_fit(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Check if candidate meets safety requirements."""
        try:
            # TODO: Implement actual safety checking
            # For now, assume most paths are safe
            return 0.9

        except Exception:
            return 0.5
