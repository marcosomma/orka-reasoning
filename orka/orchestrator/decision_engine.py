# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Decision Engine
==============

Final decision-making logic for path selection.
Implements commit margin analysis, confidence thresholds, and decision types.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Final decision-making engine for path selection.

    Analyzes scored candidates and makes final routing decisions based on:
    - Score margins between top candidates
    - Confidence thresholds
    - Budget constraints
    - Safety requirements
    """

    def __init__(self, config: Any):
        """Initialize decision engine with configuration."""
        self.config = config
        self.commit_margin = config.commit_margin
        self.k_beam = config.k_beam
        self.require_terminal = getattr(config, "require_terminal", True)

        logger.debug(
            f"DecisionEngine initialized with commit_margin={self.commit_margin}, require_terminal={self.require_terminal}"
        )

    async def make_decision(
        self, scored_candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make final routing decision based on scored candidates.

        Args:
            scored_candidates: List of candidates with scores
            context: Execution context

        Returns:
            Decision object with type, target, confidence, and reasoning
        """
        try:
            if not scored_candidates:
                return self._create_decision("fallback", None, 0.0, "No candidates available")

            # Sort by score (should already be sorted)
            scored_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)

            # Check for terminal paths (2-hop chains ending with response builders)
            if self.require_terminal:
                terminal_paths = self._find_terminal_paths(scored_candidates, context)
                if terminal_paths:
                    best_terminal = terminal_paths[0]
                    terminal_path = best_terminal["path"]
                    logger.info(f"🎯 Creating commit_path decision with target: {terminal_path}")
                    return self._create_decision(
                        "commit_path",
                        terminal_path,
                        best_terminal.get("confidence", 0.8),
                        f"🎯 Terminal path to response builder (score={best_terminal.get('score', 0.0):.3f})",
                    )

            top_candidate = scored_candidates[0]
            top_score = top_candidate.get("score", 0.0)

            # Dynamic commit margin based on query type
            dynamic_margin = self._get_dynamic_margin(context)
            logger.debug(f"Using dynamic margin: {dynamic_margin} (base: {self.commit_margin})")

            # Single candidate case
            if len(scored_candidates) == 1:
                return await self._handle_single_candidate(top_candidate, context)

            # Multiple candidates case
            second_score = scored_candidates[1].get("score", 0.0)
            score_margin = top_score - second_score

            logger.debug(
                f"Decision analysis: top_score={top_score:.3f}, "
                f"second_score={second_score:.3f}, margin={score_margin:.3f}"
            )

            # High confidence - commit to single path
            if score_margin >= dynamic_margin:
                return await self._handle_high_confidence_decision(
                    top_candidate, score_margin, context
                )

            # Low confidence - return shortlist
            return await self._handle_low_confidence_decision(
                scored_candidates[: self.k_beam], score_margin, context
            )

        except Exception as e:
            logger.error(f"Decision making failed: {e}")
            return self._create_decision("fallback", None, 0.0, f"Decision engine error: {e}")

    def _find_terminal_paths(
        self, scored_candidates: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find terminal paths that end with response builders."""
        terminal_paths = []

        try:
            logger.info(f"🔍 Searching for terminal paths in {len(scored_candidates)} candidates")

            # First priority: 2-hop paths ending with response builders
            for candidate in scored_candidates:
                path = candidate.get("path", [candidate["node_id"]])
                logger.debug(f"🔍 Checking path: {' → '.join(path)} (length: {len(path)})")

                # Prioritize 2-hop chains
                if len(path) == 2:
                    last_node = path[-1]
                    is_terminal = self._is_response_builder(last_node, context)
                    logger.info(
                        f"🔍 2-hop path {' → '.join(path)}: last_node='{last_node}' is_terminal={is_terminal}"
                    )
                    if is_terminal:
                        terminal_paths.append(candidate)
                        logger.info(f"✅ Found 2-hop terminal path: {' → '.join(path)}")

            # If no 2-hop terminals, consider longer paths
            if not terminal_paths:
                logger.info("🔍 No 2-hop terminals found, checking longer paths...")
                for candidate in scored_candidates:
                    path = candidate.get("path", [candidate["node_id"]])

                    if len(path) > 2:
                        last_node = path[-1]
                        is_terminal = self._is_response_builder(last_node, context)
                        logger.info(
                            f"🔍 {len(path)}-hop path {' → '.join(path)}: last_node='{last_node}' is_terminal={is_terminal}"
                        )
                        if is_terminal:
                            terminal_paths.append(candidate)
                            logger.info(
                                f"✅ Found {len(path)}-hop terminal path: {' → '.join(path)}"
                            )

            logger.info(
                f"🔍 Terminal path search complete: found {len(terminal_paths)} terminal paths"
            )

            # Sort terminal paths by score
            terminal_paths.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            return terminal_paths

        except Exception as e:
            logger.error(f"Terminal path detection failed: {e}")
            return []

    def _get_dynamic_margin(self, context: Dict[str, Any]) -> float:
        """Get dynamic commit margin based on query type and context."""
        try:
            # Check if we have classification information
            previous_outputs = context.get("previous_outputs", {})

            # Look for input classifier output
            classifier_output = previous_outputs.get("input_classifier", {})
            if isinstance(classifier_output, dict):
                classification = classifier_output.get("response", "").lower()
            else:
                classification = str(classifier_output).lower()

            # Dynamic margins based on query type
            if "factual" in classification:
                return 0.08  # Lower margin for factual queries
            elif "analytical" in classification:
                return 0.15  # Medium margin for analytical queries
            elif "technical" in classification:
                return 0.12  # Medium-low margin for technical queries
            elif "creative" in classification:
                return 0.2  # Higher margin for creative queries (more subjective)

            # Fallback: use base margin
            return float(self.commit_margin)

        except Exception as e:
            logger.debug(f"Dynamic margin calculation failed: {e}")
            return float(self.commit_margin)

    def _is_response_builder(self, node_id: str, context: Dict[str, Any]) -> bool:
        """Check if a node is a response builder."""
        try:
            logger.debug(f"🔍 Checking if '{node_id}' is a response builder...")

            # Check capabilities first (most reliable)
            graph_state = context.get("graph_state")
            if graph_state and node_id in graph_state.nodes:
                node_obj = graph_state.nodes[node_id]
                if hasattr(node_obj, "capabilities"):
                    capabilities = getattr(node_obj, "capabilities", [])
                    logger.debug(f"🔍 Node '{node_id}' capabilities: {capabilities}")
                    if "answer_emit" in capabilities or "response_generation" in capabilities:
                        logger.debug(f"✅ Node '{node_id}' is response builder (capabilities)")
                        return True

            # Fallback to heuristics based on node name and type patterns
            response_builder_patterns = [
                "response_builder",
                "answer_builder",
                "final_response",
                "llm_response",
                "openai_response",
            ]

            node_id_lower = node_id.lower()
            logger.debug(
                f"🔍 Checking node name '{node_id_lower}' against patterns: {response_builder_patterns}"
            )
            for pattern in response_builder_patterns:
                if pattern in node_id_lower:
                    logger.debug(
                        f"✅ Node '{node_id}' is response builder (name pattern: '{pattern}')"
                    )
                    return True

            # Additional check: if the node type contains "localllm" or "openai"
            # and doesn't contain "classification", it's likely a response builder
            # This would require access to the orchestrator's node configuration
            # For now, we'll use the name-based heuristic

            logger.debug(f"❌ Node '{node_id}' is NOT a response builder")
            return False

        except Exception as e:
            logger.error(f"Response builder check failed: {e}")
            return False

    async def _handle_single_candidate(
        self, candidate: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle case with single candidate."""
        try:
            score = candidate.get("score", 0.0)
            confidence = candidate.get("confidence", 0.0)

            # Check if single candidate is good enough
            if score >= 0.7 and confidence >= 0.6:
                path = candidate.get("path", [candidate["node_id"]])

                if len(path) == 1:
                    return self._create_decision(
                        "commit_next",
                        candidate["node_id"],
                        confidence,
                        f"Single high-quality candidate (score={score:.3f})",
                    )
                else:
                    return self._create_decision(
                        "commit_path",
                        path,
                        confidence,
                        f"Single high-quality path (score={score:.3f})",
                    )
            else:
                return self._create_decision(
                    "shortlist",
                    [candidate],
                    confidence,
                    f"Single candidate with moderate quality (score={score:.3f})",
                )

        except Exception as e:
            logger.error(f"Single candidate handling failed: {e}")
            return self._create_decision("fallback", None, 0.0, f"Single candidate error: {e}")

    async def _handle_high_confidence_decision(
        self, top_candidate: Dict[str, Any], margin: float, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle high confidence decision with clear winner."""
        try:
            path = top_candidate.get("path", [top_candidate["node_id"]])
            confidence = top_candidate.get("confidence", 0.0)
            score = top_candidate.get("score", 0.0)

            # Boost confidence based on margin
            adjusted_confidence = min(1.0, confidence + (margin * 0.5))

            if len(path) == 1:
                return self._create_decision(
                    "commit_next",
                    top_candidate["node_id"],
                    adjusted_confidence,
                    f"Clear winner with margin {margin:.3f} (score={score:.3f})",
                )
            else:
                return self._create_decision(
                    "commit_path",
                    path,
                    adjusted_confidence,
                    f"Clear path winner with margin {margin:.3f} (score={score:.3f})",
                )

        except Exception as e:
            logger.error(f"High confidence decision failed: {e}")
            return self._create_decision("fallback", None, 0.0, f"High confidence error: {e}")

    async def _handle_low_confidence_decision(
        self, top_candidates: List[Dict[str, Any]], margin: float, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle low confidence decision with multiple viable options."""
        try:
            # Calculate average confidence
            confidences = [c.get("confidence", 0.0) for c in top_candidates]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Penalize confidence due to uncertainty
            adjusted_confidence = max(0.0, avg_confidence - 0.2)

            return self._create_decision(
                "shortlist",
                top_candidates,
                adjusted_confidence,
                f"Close competition with margin {margin:.3f} - returning top {len(top_candidates)} options",
            )

        except Exception as e:
            logger.error(f"Low confidence decision failed: {e}")
            return self._create_decision("fallback", None, 0.0, f"Low confidence error: {e}")

    def _create_decision(
        self, decision_type: str, target: Any, confidence: float, reasoning: str
    ) -> Dict[str, Any]:
        """Create a standardized decision object."""
        return {
            "decision_type": decision_type,
            "target": target,
            "confidence": confidence,
            "reasoning": reasoning,
            "trace": {
                "engine": "DecisionEngine",
                "commit_margin": self.commit_margin,
                "k_beam": self.k_beam,
            },
        }
