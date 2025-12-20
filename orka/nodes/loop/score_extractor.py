from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional, TypeGuard, Union

import numpy as np

from ...scoring import BooleanScoreCalculator
from ...utils.embedder import get_embedder
from .boolean_extraction import extract_boolean_from_text, is_valid_boolean_structure
from .score_utils import normalize_score

logger = logging.getLogger(__name__)


class LoopScoreExtractor:
    """Extract LoopNode scores from agent results.

    This is a direct extraction of the legacy LoopNode score logic:
    - _try_boolean_scoring
    - _extract_score
    - _compute_agreement_score
    and their helper methods.
    """

    def __init__(
        self,
        *,
        node_id: str,
        score_calculator: Optional[BooleanScoreCalculator],
        scoring_preset: Optional[str],
        score_extraction_config: Dict[str, Any],
        high_priority_agents: List[str],
    ) -> None:
        self.node_id = node_id
        self.score_calculator = score_calculator
        self.scoring_preset = scoring_preset
        self.score_extraction_config = score_extraction_config
        self.high_priority_agents = high_priority_agents

    def _is_valid_value(self, value: Any) -> TypeGuard[Union[str, int, float]]:
        try:
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str) and value.strip():
                float(value)
                return True
            return False
        except (ValueError, TypeError):
            return False

    def _try_boolean_scoring(self, result: Dict[str, Any]) -> Optional[float]:
        if not self.score_calculator:
            logger.debug(
                "LoopNode '%s': No score_calculator configured (scoring preset not set)",
                self.node_id,
            )
            return None

        logger.info(
            "LoopNode '%s': Attempting boolean score extraction from %s agents",
            self.node_id,
            len(result),
        )

        any_boolean_present = any(
            isinstance(v, dict) and "boolean_evaluations" in v for v in result.values()
        )
        any_boolean_has_entries = any(
            isinstance(v, dict)
            and isinstance(v.get("boolean_evaluations"), dict)
            and any(
                isinstance(c, dict) and bool(c) for c in v.get("boolean_evaluations", {}).values()
            )
            for v in result.values()
        )
        routing_indicators = (
            "join_results",
            "routing_decision",
            "routing",
            "proposed_path",
            "path",
            "join",
        )
        has_routing_or_join = False
        for v in result.values():
            if isinstance(v, dict):
                if any(k in v for k in routing_indicators):
                    has_routing_or_join = True
                    break
                if "response" in v and isinstance(v["response"], str):
                    txt = v["response"]
                    if any(
                        tok in txt
                        for tok in (
                            "Join Results",
                            "Routing Decision",
                            "proposed_path",
                            "proposed path",
                        )
                    ):
                        has_routing_or_join = True
                        break
        if any_boolean_present and not any_boolean_has_entries and not has_routing_or_join:
            logger.warning(
                "LoopNode '%s': boolean_evaluations present but empty and no routing/join data observed; skipping boolean scoring and falling back to numeric extraction",
                self.node_id,
            )
            return None

        for agent_id, agent_result in result.items():
            if not isinstance(agent_result, dict):
                logger.debug("  - Agent '%s': Not a dict, skipping", agent_id)
                continue

            logger.debug("  - Agent '%s': Checking for boolean evaluations...", agent_id)

            if "boolean_evaluations" in agent_result:
                boolean_evals = agent_result["boolean_evaluations"]
                logger.info("  - Agent '%s': Found boolean_evaluations field", agent_id)
                if isinstance(boolean_evals, dict) and is_valid_boolean_structure(boolean_evals):
                    try:
                        if not hasattr(self.score_calculator, "flat_weights") or not isinstance(
                            getattr(self.score_calculator, "flat_weights", None), dict
                        ):
                            score_result = self.score_calculator.calculate(boolean_evals)
                            logger.info(
                                "✅ Boolean evaluations from '%s': %s/%s passed, score=%0.4f",
                                agent_id,
                                score_result["passed_count"],
                                score_result["total_criteria"],
                                score_result["score"],
                            )
                            return float(score_result["score"])

                        total_expected = len(self.score_calculator.flat_weights)
                        provided_keys = set()
                        for dim, criteria in boolean_evals.items():
                            if isinstance(criteria, dict):
                                for crit in criteria.keys():
                                    provided_keys.add(f"{dim}.{crit}")

                        provided_count = len(
                            [k for k in provided_keys if k in self.score_calculator.flat_weights]
                        )
                        provided_fraction = (
                            provided_count / total_expected if total_expected else 0.0
                        )

                        MIN_PROVIDED_FRACTION = 0.5
                        if provided_fraction < MIN_PROVIDED_FRACTION:
                            logger.warning(
                                "  - Agent '%s': boolean_evaluations too sparse (%s/%s criteria). Skipping.",
                                agent_id,
                                provided_count,
                                total_expected,
                            )
                            continue

                        score_result = self.score_calculator.calculate(boolean_evals)
                        logger.info(
                            "✅ Boolean evaluations from '%s': %s/%s passed, score=%0.4f",
                            agent_id,
                            score_result["passed_count"],
                            score_result["total_criteria"],
                            score_result["score"],
                        )
                        return float(score_result["score"])
                    except Exception as e:
                        logger.error(
                            "Failed to calculate boolean score from '%s': %s",
                            agent_id,
                            e,
                            exc_info=True,
                        )
                        continue
                else:
                    logger.warning(
                        "  - Agent '%s': boolean_evaluations invalid structure", agent_id
                    )

            if "validation_score" in agent_result and "boolean_evaluations" in agent_result:
                logger.info("  - Agent '%s': Found validation_score field", agent_id)
                try:
                    score = float(agent_result["validation_score"])
                    logger.info("✅ Using validation_score from '%s': %0.4f", agent_id, score)
                    return score
                except (ValueError, TypeError) as e:
                    logger.warning("  - Agent '%s': Invalid validation_score: %s", agent_id, e)
                    continue

            if "response" in agent_result:
                response_text = str(agent_result["response"])
                logger.debug(
                    "  - Agent '%s': Checking response text (%s chars)...",
                    agent_id,
                    len(response_text),
                )

                boolean_evals = extract_boolean_from_text(response_text)
                if boolean_evals and is_valid_boolean_structure(boolean_evals):
                    try:
                        score_result = self.score_calculator.calculate(boolean_evals)
                        logger.info(
                            "✅ Boolean evaluations from '%s' response text: %s/%s passed, score=%0.4f",
                            agent_id,
                            score_result["passed_count"],
                            score_result["total_criteria"],
                            score_result["score"],
                        )
                        return float(score_result["score"])
                    except Exception as e:
                        logger.debug(
                            "  - Failed to parse boolean from '%s' response: %s", agent_id, e
                        )
                        continue
                else:
                    logger.debug(
                        "  - Agent '%s': No valid boolean structure in response", agent_id
                    )

        logger.warning("LoopNode '%s': ❌ No valid boolean evaluations found in any agent", self.node_id)
        return None

    async def extract_score(self, result: Dict[str, Any]) -> float:
        if not result:
            return 0.0

        logger.debug("Score extraction called with %s agents", len(result))
        for agent_id, agent_result in result.items():
            if isinstance(agent_result, dict) and "response" in agent_result:
                response_text = str(agent_result["response"])
                response_preview = (
                    response_text[:100] + "..." if len(response_text) > 100 else response_text
                )
                logger.debug("Agent '%s' response preview: %s", agent_id, response_preview)

        if self.score_calculator:
            boolean_score = self._try_boolean_scoring(result)
            if boolean_score is not None:
                logger.info(
                    "✅ Using boolean scoring: %0.4f (preset: %s)", boolean_score, self.scoring_preset
                )
                return float(boolean_score)
            logger.debug(
                "Boolean scoring attempted but no valid evaluations found, falling back to legacy"
            )

        strategies = self.score_extraction_config.get("strategies", [])

        for priority_agent in self.high_priority_agents:
            if priority_agent in result:
                agent_result = result[priority_agent]
                if isinstance(agent_result, dict) and "response" in agent_result:
                    response_text = str(agent_result["response"])
                    logger.info(
                        "🔍 Checking high-priority agent '%s': %s...",
                        priority_agent,
                        response_text[:100],
                    )

                    all_patterns: list[str] = []
                    for strategy in strategies:
                        if strategy.get("type") == "pattern" and "patterns" in strategy:
                            patterns = strategy["patterns"]
                            if isinstance(patterns, list):
                                all_patterns.extend(patterns)

                    if not all_patterns:
                        all_patterns = [
                            r"AGREEMENT_SCORE:\s*([0-9.]+)",
                            r"Agreement Score:\s*([0-9.]+)",
                            r"AGREEMENT_SCORE\s*([0-9.]+)",
                            r"Score:\s*([0-9.]+)",
                            r"SCORE:\s*([0-9.]+)",
                        ]

                    for score_pattern in all_patterns:
                        match = re.search(score_pattern, response_text)
                        if match:
                            try:
                                raw_str = match.group(1) if match.groups() else match.group(0)
                                raw = float(raw_str)
                                score = normalize_score(
                                    raw, pattern=score_pattern, matched_text=response_text
                                )
                                logger.info(
                                    "✅ Found score %s from high-priority agent '%s' using pattern: %s",
                                    score,
                                    priority_agent,
                                    score_pattern,
                                )
                                return float(score)
                            except (ValueError, TypeError):
                                continue

                    logger.warning(
                        "❌ High-priority agent '%s' found but no score extracted from: %s",
                        priority_agent,
                        response_text,
                    )

        for strategy in strategies:
            if not isinstance(strategy, dict):
                continue

            strategy_type = strategy.get("type")

            if strategy_type == "direct_key":
                key = str(strategy.get("key", ""))
                if key in result:
                    value = result[key]
                    if self._is_valid_value(value):
                        raw = float(value)
                        score = normalize_score(raw, matched_text=str(value))
                        logger.info("✅ Found score %s via direct_key strategy", score)
                        return float(score)

            elif strategy_type == "pattern":
                patterns = strategy.get("patterns", [])
                if not isinstance(patterns, list):
                    continue

                for pattern in patterns:
                    if not isinstance(pattern, str):
                        continue

                    logger.debug("🔍 Trying pattern: %s", pattern)

                    for agent_id, agent_result in result.items():
                        if isinstance(agent_result, str):
                            match = re.search(pattern, agent_result)
                            if match:
                                try:
                                    raw_str = match.group(1) if match.groups() else match.group(0)
                                    raw = float(raw_str)
                                    score = normalize_score(
                                        raw, pattern=pattern, matched_text=agent_result
                                    )
                                    logger.info(
                                        "✅ Found score %s in %s (direct string) using pattern: %s",
                                        score,
                                        agent_id,
                                        pattern,
                                    )
                                    return float(score)
                                except (ValueError, TypeError):
                                    continue

                        elif isinstance(agent_result, dict):
                            for key in ["response", "result", "output", "data"]:
                                if key in agent_result and isinstance(agent_result[key], str):
                                    text_content = agent_result[key]
                                    logger.debug(
                                        "🔍 Searching in %s.%s: %r",
                                        agent_id,
                                        key,
                                        text_content[:200],
                                    )
                                    match = re.search(pattern, text_content)
                                    if match:
                                        try:
                                            raw_str = match.group(1) if match.groups() else match.group(0)
                                            score = float(raw_str)
                                            logger.debug(
                                                "✅ Matched text: '%s'", text_content[:200]
                                            )
                                            logger.info(
                                                "✅ Found score %s in %s.%s using pattern: %s",
                                                score,
                                                agent_id,
                                                key,
                                                pattern,
                                            )
                                            return float(score)
                                        except (ValueError, TypeError, IndexError):
                                            continue
                                    else:
                                        if (
                                            "agreement" in agent_id.lower()
                                            or "AGREEMENT_SCORE" in text_content
                                        ):
                                            logger.debug(
                                                "❌ No match for pattern '%s' in %s.%s: '%s'",
                                                pattern,
                                                agent_id,
                                                key,
                                                text_content[:100],
                                            )

            elif strategy_type == "agent_key":
                agents = strategy.get("agents", [])
                key = str(strategy.get("key", "response"))
                logger.debug(
                    "🔍 Trying agent_key strategy for agents: %s, key: %s", agents, key
                )

                for agent_name in agents:
                    if agent_name in result:
                        logger.debug("🔍 Found agent '%s' in results", agent_name)
                        agent_result = result[agent_name]
                        if isinstance(agent_result, dict) and key in agent_result:
                            response_text = str(agent_result[key])
                            logger.debug(
                                "🔍 Agent '%s' %s: '%s'", agent_name, key, response_text[:100]
                            )
                            agent_score_patterns: list[str] = []
                            for s in strategies:
                                if s.get("type") == "pattern" and "patterns" in s:
                                    patterns = s["patterns"]
                                    if isinstance(patterns, list):
                                        agent_score_patterns.extend(patterns)

                            if not agent_score_patterns:
                                agent_score_patterns = [
                                    r"AGREEMENT_SCORE:\s*([0-9.]+)",
                                    r"Agreement Score:\s*([0-9.]+)",
                                    r"SCORE:\s*([0-9.]+)",
                                    r"Score:\s*([0-9.]+)",
                                ]

                            for score_pattern in agent_score_patterns:
                                score_match = re.search(score_pattern, response_text)
                                if score_match:
                                    try:
                                        raw = float(score_match.group(1))
                                        score = normalize_score(
                                            raw,
                                            pattern=score_pattern,
                                            matched_text=response_text,
                                        )
                                        logger.info(
                                            "✅ Found score %s in agent_key strategy from %s using pattern: %s",
                                            score,
                                            agent_name,
                                            score_pattern,
                                        )
                                        return float(score)
                                    except (ValueError, TypeError):
                                        continue
                    else:
                        logger.debug(
                            "🔍 Agent '%s' not found in results. Available agents: %s",
                            agent_name,
                            list(result.keys()),
                        )

        agent_ids = list(result.keys())
        has_score_agents = any(agent_id in result for agent_id in self.high_priority_agents)
        if has_score_agents:
            logger.warning(
                "❌ Score agents present but no scores extracted. NOT using embedding fallback to avoid overriding explicit scores."
            )
            return 0.0

        cognitive_agents = [
            aid
            for aid in agent_ids
            if any(word in aid.lower() for word in ["progressive", "conservative", "realist", "purist"])
        ]
        if len(cognitive_agents) >= 2:
            logger.info(
                "Detected cognitive debate with agents: %s (no score moderators found)",
                cognitive_agents,
            )
            logger.info("Using embedding-based agreement computation as final fallback")
            try:
                agreement_score = await self._compute_agreement_score(result)
                logger.info("✅ Computed fallback agreement score: %s", agreement_score)
                return float(agreement_score)
            except Exception as e:
                logger.error("Failed to compute agreement score: %s", e)
                return 0.0

        logger.warning("❌ No valid score extraction method succeeded")
        return 0.0

    async def _compute_agreement_score(self, result: Dict[str, Any]) -> float:
        try:
            agent_responses: List[Dict[str, Any]] = []
            for agent_id, agent_result in result.items():
                if isinstance(agent_result, dict):
                    response_text = None
                    for field in ["response", "result", "output", "content", "answer"]:
                        if field in agent_result and agent_result[field]:
                            response_text = str(agent_result[field])
                            break
                    if response_text:
                        agent_responses.append(
                            {"agent_id": agent_id, "response": response_text, "embedding": None}
                        )
                elif isinstance(agent_result, str) and agent_result.strip():
                    agent_responses.append(
                        {"agent_id": agent_id, "response": agent_result, "embedding": None}
                    )

            if len(agent_responses) < 2:
                logger.warning(
                    "Only %s agent responses found, need at least 2 for agreement",
                    len(agent_responses),
                )
                return 0.0

            embedder = get_embedder()

            for agent_data in agent_responses:
                try:
                    response_text = agent_data["response"]
                    if response_text and isinstance(response_text, str):
                        embedding = await embedder.encode(response_text)
                        agent_data["embedding"] = np.array(embedding) if embedding is not None else None
                    else:
                        agent_data["embedding"] = None
                except Exception as e:
                    logger.warning(
                        "Failed to generate embedding for %s: %s", agent_data["agent_id"], e
                    )
                    agent_data["embedding"] = None

            valid_embeddings = []
            valid_agents = []
            for agent_data in agent_responses:
                if agent_data["embedding"] is not None and len(agent_data["embedding"]) > 0:
                    valid_embeddings.append(agent_data["embedding"])
                    valid_agents.append(agent_data["agent_id"])

            if len(valid_embeddings) < 2:
                logger.warning("Only %s valid embeddings, returning 0.0", len(valid_embeddings))
                return 0.0

            from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

            embeddings_matrix = np.array(valid_embeddings)
            similarity_matrix = cosine_similarity(embeddings_matrix)

            n = len(similarity_matrix)
            if n < 2:
                return 0.0

            total_similarity = np.sum(similarity_matrix) - np.trace(similarity_matrix)
            max_pairs = n * (n - 1)
            if max_pairs == 0:
                return 0.0

            mean_agreement = total_similarity / max_pairs
            agreement_score = max(0.0, min(1.0, float(mean_agreement)))

            logger.info(
                "Computed agreement score: %0.3f from %s agents: %s",
                agreement_score,
                len(valid_agents),
                valid_agents,
            )
            return agreement_score
        except Exception as e:
            logger.error("Error computing agreement score: %s", e)
            return 0.0


