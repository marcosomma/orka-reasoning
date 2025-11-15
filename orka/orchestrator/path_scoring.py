# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Path Scoring System
==================

Multi-criteria scoring system for evaluating candidate paths.

Supports two modes:
1. **Numeric Mode (default)**: Continuous scores (0.0-1.0) with weighted aggregation
2. **Boolean Mode**: Deterministic pass/fail criteria with audit trails

Combines LLM evaluation, heuristics, historical priors, and budget considerations.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PathScorer:
    """
    Multi-criteria path scoring system with dual-mode support.

    **Numeric Mode (default)**:
    - Continuous scores (0.0-1.0)
    - Weighted aggregation
    - Probabilistic ranking

    **Boolean Mode**:
    - Deterministic pass/fail criteria
    - Audit trails for compliance
    - Explicit failure reasons

    Evaluates candidate paths using:
    - LLM relevance assessment
    - Heuristic matching (capabilities, constraints)
    - Historical success priors
    - Cost and latency penalties
    - Safety risk assessment
    """

    def __init__(self, config: Any):
        """
        Initialize path scorer with configuration.

        Args:
            config: Configuration object with scoring_mode parameter:
                   - 'numeric' (default): Continuous scoring
                   - 'boolean': Deterministic criteria evaluation
        """
        self.config = config
        self.score_weights = config.score_weights

        # Scoring mode selection
        self.scoring_mode = getattr(config, "scoring_mode", "numeric")
        if self.scoring_mode not in ("numeric", "boolean"):
            logger.warning(
                f"Invalid scoring_mode '{self.scoring_mode}', defaulting to 'numeric'"
            )
            self.scoring_mode = "numeric"

        # Initialize boolean scoring engine if needed
        self.boolean_engine = None
        if self.scoring_mode == "boolean":
            from .boolean_scoring import BooleanScoringEngine

            self.boolean_engine = BooleanScoringEngine(config)
            logger.info("PathScorer initialized in BOOLEAN mode with deterministic criteria")
        else:
            logger.info("PathScorer initialized in NUMERIC mode with continuous scoring")
        
        # Extract scoring thresholds from config
        self.max_reasonable_cost = getattr(config, "max_reasonable_cost", 0.10)
        self.path_length_penalty = getattr(config, "path_length_penalty", 0.10)
        self.keyword_match_boost = getattr(config, "keyword_match_boost", 0.30)
        self.default_neutral_score = getattr(config, "default_neutral_score", 0.50)
        self.optimal_path_length = getattr(config, "optimal_path_length", (2, 3))
        
        # Input readiness thresholds
        self.min_readiness_score = getattr(config, "min_readiness_score", 0.30)
        self.no_requirements_score = getattr(config, "no_requirements_score", 0.90)
        
        # Safety thresholds
        self.risky_capabilities = getattr(config, "risky_capabilities", {"file_write", "code_execution", "external_api"})
        self.safety_markers = getattr(config, "safety_markers", {"sandboxed", "read_only", "validated"})
        self.safe_default_score = getattr(config, "safe_default_score", 0.70)

        # Initialize LLM evaluator (placeholder for now)
        self.llm_evaluator = None

        logger.debug(f"PathScorer initialized with weights: {self.score_weights}")

    async def score_candidates(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Score all candidates using multi-criteria evaluation.

        **Behavior depends on scoring_mode**:
        - **numeric**: Returns continuous scores (0.0-1.0)
        - **boolean**: Returns pass/fail criteria with audit trails

        Args:
            candidates: List of candidate paths to score
            question: The question/query being routed
            context: Execution context

        Returns:
            List of candidates with scores and components (sorted by score/pass-rate)
        """
        # Route to appropriate scoring method
        if self.scoring_mode == "boolean":
            return await self._score_candidates_boolean(candidates, question, context)
        else:
            return await self._score_candidates_numeric(candidates, question, context)

    async def _score_candidates_numeric(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score candidates using continuous numeric scores (original implementation)."""
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
                f"[NUMERIC] Scored {len(scored_candidates)} candidates, "
                f"top score: {scored_candidates[0]['score']:.3f}, "
                f"keeping top {len(final_candidates)} (k_beam={k_beam})"
            )

            return final_candidates

        except Exception as e:
            logger.error(f"Numeric candidate scoring failed: {e}")
            return candidates

    async def _score_candidates_boolean(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score candidates using deterministic boolean criteria."""
        try:
            assert self.boolean_engine is not None, "Boolean engine not initialized"

            scored_candidates = []

            # Evaluate each candidate using boolean criteria
            for candidate in candidates:
                result = await self.boolean_engine.evaluate_candidate(
                    candidate, question, context
                )

                # Add boolean scoring results to candidate
                candidate["boolean_result"] = {
                    "overall_pass": result.overall_pass,
                    "criteria_results": result.criteria_results,
                    "passed_criteria": result.passed_criteria,
                    "total_criteria": result.total_criteria,
                    "pass_percentage": result.pass_percentage,
                    "critical_failures": result.critical_failures,
                    "reasoning": result.reasoning,
                    "audit_trail": result.audit_trail,
                }

                # Set numeric score based on pass percentage for sorting
                candidate["score"] = result.pass_percentage if result.overall_pass else 0.0
                candidate["confidence"] = 1.0 if result.overall_pass else 0.0

                scored_candidates.append(candidate)

            # Sort by pass status first, then by pass percentage
            scored_candidates.sort(
                key=lambda x: (
                    x["boolean_result"]["overall_pass"],
                    x["boolean_result"]["pass_percentage"],
                ),
                reverse=True,
            )

            # Apply beam width limiting
            k_beam = getattr(self.config, "k_beam", 3)
            final_candidates = scored_candidates[:k_beam]

            passing = sum(1 for c in scored_candidates if c["boolean_result"]["overall_pass"])
            logger.info(
                f"[BOOLEAN] Evaluated {len(scored_candidates)} candidates: "
                f"{passing} passed, {len(scored_candidates) - passing} failed, "
                f"keeping top {len(final_candidates)} (k_beam={k_beam})"
            )

            return final_candidates

        except Exception as e:
            logger.error(f"Boolean candidate scoring failed: {e}")
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
            relevance_score = self.default_neutral_score  # Default neutral score

            # Boost score for certain node types based on question content
            if "search" in question_lower and "search" in node_id.lower():
                relevance_score += self.keyword_match_boost
            elif "memory" in question_lower and "memory" in node_id.lower():
                relevance_score += self.keyword_match_boost
            elif "analyze" in question_lower and "llm" in node_id.lower():
                relevance_score += self.keyword_match_boost

            # Penalize very long paths (configurable)
            if len(path) > 3:
                relevance_score -= self.path_length_penalty

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
        """Score based on historical performance and path structure."""
        try:
            node_id = candidate["node_id"]
            path = candidate.get("path", [node_id])
            
            # Base score from path structure
            path_score = self._score_path_structure(path)
            
            # Try to get historical success from memory
            orchestrator = context.get("orchestrator")
            if orchestrator and hasattr(orchestrator, "memory_manager"):
                try:
                    history_score = self._get_historical_score(node_id, orchestrator.memory_manager)
                    # Blend structure and history (70% history, 30% structure)
                    return 0.7 * history_score + 0.3 * path_score
                except Exception as e:
                    logger.debug(f"Memory lookup failed for {node_id}: {e}")
            
            # Fallback to structure-based scoring
            return path_score
            
        except Exception as e:
            logger.warning(f"Error scoring priors for {candidate.get('node_id')}: {e}")
            return 0.5
    
    def _score_path_structure(self, path: List[str]) -> float:
        """Score based on path length and composition."""
        length = len(path)
        min_optimal, max_optimal = self.optimal_path_length
        
        # Score based on proximity to optimal path length
        if length == 1:
            return 0.5  # Too short, might be incomplete
        elif min_optimal <= length <= max_optimal:
            return 0.9  # Optimal range
        elif length == max_optimal + 1:
            return 0.7  # Acceptable
        else:
            # Penalize long paths using configurable penalty
            penalty = (length - max_optimal - 1) * self.path_length_penalty
            return max(0.3, 0.7 - penalty)
    
    def _get_historical_score(self, node_id: str, memory_manager: Any) -> float:
        """Query memory for historical agent performance."""
        # Simple query: success rate of agent in past runs
        # This is a basic implementation - can be extended
        query_key = f"agent_success_rate:{node_id}"
        
        # Memory manager should have get_metric or similar
        if hasattr(memory_manager, "get_metric"):
            success_rate = memory_manager.get_metric(query_key)
            if success_rate is not None:
                return float(success_rate)
        
        return 0.6  # No history - neutral-positive default

    async def _score_cost(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Score candidate based on cost efficiency."""
        try:
            estimated_cost = candidate.get("estimated_cost", 0.001)

            # Normalize cost to 0-1 scale (inverted - lower cost is better)
            normalized_cost = min(1.0, estimated_cost / self.max_reasonable_cost)

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
        """Check if required inputs are available for this candidate."""
        try:
            node_id = candidate["node_id"]
            
            # Get agent definition from orchestrator
            orchestrator = context.get("orchestrator")
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return 0.5  # Unknown - neutral score
            
            agent = orchestrator.agents.get(node_id)
            if not agent:
                return 0.5
            
            # Check if agent has required_inputs config
            required_inputs = getattr(agent, "required_inputs", [])
            if not required_inputs:
                return self.no_requirements_score  # No requirements - likely ready
            
            # Check if inputs are in previous_outputs
            previous_outputs = context.get("previous_outputs", {})
            available_inputs = set(previous_outputs.keys())
            required_set = set(required_inputs)
            
            if required_set.issubset(available_inputs):
                return 1.0  # All required inputs available
            
            missing = required_set - available_inputs
            readiness = 1.0 - (len(missing) / len(required_inputs))
            return max(self.min_readiness_score, readiness)  # Minimum for partial readiness
            
        except Exception as e:
            logger.warning(f"Error checking input readiness for {candidate.get('node_id')}: {e}")
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

        except KeyError as e:
            logger.warning(f"Missing node_id in candidate: {e}")
            return 0.5
        except Exception as e:
            logger.warning(f"Error checking modality fit for {candidate.get('node_id', 'unknown')}: {e}")
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

        except KeyError as e:
            logger.warning(f"Missing node_id in candidate: {e}")
            return 0.5
        except Exception as e:
            logger.warning(f"Error checking domain overlap for {candidate.get('node_id', 'unknown')}: {e}")
            return 0.5

    def _check_safety_fit(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Check if candidate meets safety requirements."""
        try:
            node_id = candidate["node_id"]
            orchestrator = context.get("orchestrator")
            
            if not orchestrator or not hasattr(orchestrator, "agents"):
                return self.safe_default_score  # Unknown - somewhat safe default
            
            agent = orchestrator.agents.get(node_id)
            if not agent:
                return 0.5
            
            # Check safety tags/capabilities
            safety_tags = getattr(agent, "safety_tags", [])
            capabilities = getattr(agent, "capabilities", [])
            
            # Red flags that reduce safety score (configurable)
            risky_found = self.risky_capabilities.intersection(set(capabilities))
            
            if risky_found:
                # Has risky capabilities - check for safety tags
                if any(tag in safety_tags for tag in self.safety_markers):
                    return 0.8  # Risky but has safety measures
                return 0.6  # Risky without explicit safety
            
            return 0.9  # No risky capabilities found
            
        except Exception as e:
            logger.warning(f"Error checking safety for {candidate.get('node_id')}: {e}")
            return 0.5
