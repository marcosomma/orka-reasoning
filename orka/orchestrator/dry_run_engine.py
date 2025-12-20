# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Smart Path Evaluator
===================

Intelligent LLM-powered path evaluation system that replaces static mocks
with dynamic reasoning about optimal workflow paths.

Uses a two-stage LLM approach:
1. Path Selection LLM: Analyzes agent capabilities and suggests best paths
2. Validation LLM: Validates selections and assesses efficiency

This module has been refactored into smaller components in the dry_run/ package.
"""

import json
import logging
from typing import Any, Dict, List

from .dry_run.data_classes import PathEvaluation, ValidationResult
from .dry_run.deterministic_evaluator import DeterministicPathEvaluator
from .dry_run.llm_providers import LLMProviderMixin
from .dry_run.prompt_builder import PromptBuilderMixin
from .dry_run.response_parser import ResponseParserMixin
from .dry_run.agent_analyzer import AgentAnalyzerMixin
from .dry_run.path_evaluator import PathEvaluatorMixin

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "PathEvaluation",
    "ValidationResult",
    "DeterministicPathEvaluator",
    "SmartPathEvaluator",
    "DryRunEngine",
]


class SmartPathEvaluator(
    LLMProviderMixin,
    PromptBuilderMixin,
    ResponseParserMixin,
    AgentAnalyzerMixin,
    PathEvaluatorMixin,
):
    """
    LLM-powered intelligent path evaluation system.

    Replaces static mocks with dynamic reasoning about:
    - Agent capability matching
    - Expected output quality
    - Resource efficiency
    - Risk assessment
    """

    def __init__(self, config: Any):
        """Initialize smart evaluator with LLM configuration and deterministic fallback."""
        self.config = config
        self.max_preview_tokens = config.max_preview_tokens

        # Initialize deterministic fallback evaluator
        self.deterministic_evaluator = DeterministicPathEvaluator(config)

        # LLM configuration for two-stage evaluation
        self.evaluation_llm_config = {
            "model": getattr(config, "evaluation_model", "MISSING_EVALUATION_MODEL"),
            "model_name": getattr(
                config, "evaluation_model_name", "MISSING_EVALUATION_MODEL_NAME"
            ),
            "max_tokens": 500,
            "temperature": 0.1,
        }

        self.validation_llm_config = {
            "model": getattr(config, "validation_model", "MISSING_VALIDATION_MODEL"),
            "model_name": getattr(
                config, "validation_model_name", "MISSING_VALIDATION_MODEL_NAME"
            ),
            "max_tokens": 300,
            "temperature": 0.0,
        }

        logger.debug(
            "SmartPathEvaluator initialized with LLM-powered evaluation and deterministic fallback"
        )

    async def simulate_candidates(
        self,
        candidates: List[Dict[str, Any]],
        question: str,
        context: Dict[str, Any],
        orchestrator: Any,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate candidates using LLM reasoning with deterministic fallback.

        Args:
            candidates: List of candidate paths
            question: The question being routed
            context: Execution context
            orchestrator: Orchestrator instance

        Returns:
            Candidates with evaluation results (LLM or deterministic)
        """
        # Check if LLM evaluation is disabled
        if not getattr(self.config, "llm_evaluation_enabled", True):
            logger.info("LLM evaluation disabled, using deterministic evaluator")
            return self.deterministic_evaluator.evaluate_candidates(candidates, question, context)

        try:
            # Extract all available agent information
            available_agents = await self._extract_all_agent_info(orchestrator)

            # Generate all possible path combinations
            possible_paths = self._generate_possible_paths(available_agents, candidates)

            # Let LLM evaluate all paths at once for optimal decision making
            evaluation_results = await self._llm_path_evaluation(
                question, available_agents, possible_paths, context
            )

            # Map evaluation results back to candidates
            evaluated_candidates = self._map_evaluation_to_candidates(
                candidates, evaluation_results, available_agents
            )

            logger.info(
                f"LLM-evaluated {len(evaluated_candidates)} candidates based on real agent data"
            )
            return evaluated_candidates

        except (ValueError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"LLM evaluation failed: {e}")

            # Check if fallback to heuristics is enabled
            if getattr(self.config, "fallback_to_heuristics", True):
                logger.warning("Falling back to deterministic evaluator")
                return self.deterministic_evaluator.evaluate_candidates(
                    candidates, question, context
                )
            else:
                logger.critical("LLM evaluation failed and fallback disabled")
                raise
        except Exception as e:
            logger.error(f"Smart evaluation failed with unexpected error: {e}")
            return await self._fallback_heuristic_evaluation(candidates, question, context)

    async def _stage1_path_evaluation(
        self, candidate: Dict[str, Any], question: str, context: Dict[str, Any], orchestrator: Any
    ) -> PathEvaluation:
        """Stage 1: LLM analyzes agent capabilities and suggests path suitability."""
        try:
            node_id = candidate["node_id"]

            # Get agent information
            agent_info = await self._extract_agent_info(node_id, orchestrator)

            # Construct evaluation prompt
            evaluation_prompt = self._build_evaluation_prompt(
                question, agent_info, candidate, context
            )

            # Call LLM for path evaluation
            llm_response = await self._call_evaluation_llm(evaluation_prompt)

            # Parse LLM response into structured evaluation
            evaluation = self._parse_evaluation_response(llm_response, node_id)

            # CRITICAL: Prevent self-routing
            current_agent = context.get("current_agent_id", "unknown")
            if node_id == current_agent:
                logger.warning(
                    f"LLM tried to route to current agent {node_id}, overriding to prevent loop"
                )
                evaluation.relevance_score = 0.0
                evaluation.confidence = 0.0
                evaluation.reasoning = f"Prevented self-routing to {node_id} to avoid infinite loop"
                evaluation.efficiency_rating = "low"
                evaluation.risk_factors = ["infinite_loop_prevention"]

            return evaluation

        except Exception as e:
            logger.error(f"Stage 1 evaluation failed for {candidate.get('node_id')}: {e}")
            return self._create_fallback_evaluation(candidate["node_id"])

    async def _stage2_path_validation(
        self,
        candidate: Dict[str, Any],
        evaluation: PathEvaluation,
        question: str,
        context: Dict[str, Any],
    ) -> ValidationResult:
        """Stage 2: LLM validates the path selection and assesses efficiency."""
        try:
            validation_prompt = self._build_validation_prompt(
                question, candidate, evaluation, context
            )
            llm_response = await self._call_validation_llm(validation_prompt)
            return self._parse_validation_response(llm_response)

        except Exception as e:
            logger.error(f"Stage 2 validation failed for {candidate.get('node_id')}: {e}")
            return self._create_fallback_validation()

    async def _call_evaluation_llm(self, prompt: str) -> str:
        """Call LLM for Stage 1 evaluation."""
        try:
            if not getattr(self.config, "llm_evaluation_enabled", True):
                logger.warning("LLM evaluation disabled, cannot proceed without LLM")
                raise ValueError("LLM evaluation is required but disabled")

            model_name = getattr(self.config, "evaluation_model_name", "MISSING_EVALUATION_MODEL_NAME")
            model_url = getattr(self.config, "model_url", "MISSING_MODEL_URL")
            provider = getattr(self.config, "provider", "MISSING_PROVIDER")
            temperature = 0.1

            missing_fields = []
            if not isinstance(provider, str) or not provider.strip() or str(provider).startswith("MISSING_"):
                missing_fields.append("provider")
            if not isinstance(model_url, str) or not model_url.strip() or str(model_url).startswith("MISSING_"):
                missing_fields.append("model_url")
            if not isinstance(model_name, str) or not model_name.strip() or str(model_name).startswith("MISSING_"):
                missing_fields.append("evaluation_model_name")
            if missing_fields:
                raise ValueError(
                    "Missing LLM configuration for SmartPathEvaluator evaluation stage: "
                    + ", ".join(missing_fields)
                )

            provider_norm = str(provider).lower().strip()
            if provider_norm == "ollama":
                raw_response = await self._call_ollama_async(
                    model_url, model_name, prompt, temperature
                )
            elif provider_norm in ["lm_studio", "lmstudio"]:
                raw_response = await self._call_lm_studio_async(
                    model_url, model_name, prompt, temperature
                )
            else:
                logger.error(f"Unsupported LLM provider: {provider}")
                raise ValueError(f"Unsupported LLM provider: {provider}")

            json_response = self._extract_json_from_response(raw_response)
            if json_response:
                return json_response

            logger.error("Failed to extract JSON from LLM response")
            raise ValueError("LLM response does not contain valid JSON")

        except Exception as e:
            logger.error(f"Evaluation LLM call failed: {e.__class__.__name__}: {e}")
            logger.warning("LLM evaluation unavailable - will use heuristic fallback scoring")
            raise

    async def _call_validation_llm(self, prompt: str) -> str:
        """Call LLM for Stage 2 validation."""
        try:
            if not getattr(self.config, "llm_evaluation_enabled", True):
                logger.warning("LLM validation disabled, cannot proceed without LLM")
                raise ValueError("LLM validation is required but disabled")

            model_name = getattr(self.config, "validation_model_name", "MISSING_VALIDATION_MODEL_NAME")
            model_url = getattr(self.config, "model_url", "MISSING_MODEL_URL")
            provider = getattr(self.config, "provider", "MISSING_PROVIDER")
            temperature = 0.0

            missing_fields = []
            if not isinstance(provider, str) or not provider.strip() or str(provider).startswith("MISSING_"):
                missing_fields.append("provider")
            if not isinstance(model_url, str) or not model_url.strip() or str(model_url).startswith("MISSING_"):
                missing_fields.append("model_url")
            if not isinstance(model_name, str) or not model_name.strip() or str(model_name).startswith("MISSING_"):
                missing_fields.append("validation_model_name")
            if missing_fields:
                raise ValueError(
                    "Missing LLM configuration for SmartPathEvaluator validation stage: "
                    + ", ".join(missing_fields)
                )

            provider_norm = str(provider).lower().strip()
            if provider_norm == "ollama":
                raw_response = await self._call_ollama_async(
                    model_url, model_name, prompt, temperature
                )
            elif provider_norm in ["lm_studio", "lmstudio"]:
                raw_response = await self._call_lm_studio_async(
                    model_url, model_name, prompt, temperature
                )
            else:
                logger.error(f"Unsupported LLM provider: {provider}")
                raise ValueError(f"Unsupported LLM provider: {provider}")

            json_response = self._extract_json_from_response(raw_response)
            if json_response:
                return json_response

            logger.error("Failed to extract JSON from LLM validation response")
            raise ValueError("LLM validation response does not contain valid JSON")

        except Exception as e:
            logger.error(f"Validation LLM call failed: {e}")
            raise

    async def _llm_path_evaluation(
        self,
        question: str,
        available_agents: Dict[str, Dict[str, Any]],
        possible_paths: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Let LLM evaluate all possible paths and choose the best one."""
        try:
            evaluation_prompt = self._build_comprehensive_evaluation_prompt(
                question, available_agents, possible_paths, context
            )
            llm_response = await self._call_evaluation_llm(evaluation_prompt)
            return self._parse_comprehensive_evaluation_response(llm_response)

        except Exception as e:
            logger.error(f"LLM path evaluation failed: {e.__class__.__name__}: {e}")
            logger.info("Switching to deterministic heuristic evaluation mode")
            return {"error": f"{e.__class__.__name__}: {str(e)}", "fallback": True}

    async def _fallback_heuristic_evaluation(
        self, candidates: List[Dict[str, Any]], question: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fallback to simple heuristic evaluation when LLM fails."""
        try:
            for candidate in candidates:
                node_id = candidate["node_id"]

                relevance_score = 0.5
                if "search" in question.lower() and "search" in node_id.lower():
                    relevance_score = 0.7
                elif "memory" in question.lower() and "memory" in node_id.lower():
                    relevance_score = 0.7
                elif "analyze" in question.lower() and "llm" in node_id.lower():
                    relevance_score = 0.7

                candidate.update(
                    {
                        "preview": f"Heuristic evaluation for {node_id}",
                        "estimated_cost": 0.001,
                        "estimated_latency": 1000,
                        "estimated_tokens": 100,
                        "llm_evaluation": {
                            "final_scores": {
                                "relevance": relevance_score,
                                "confidence": 0.5,
                                "efficiency": 0.5,
                            }
                        },
                    }
                )

            return candidates

        except Exception as e:
            logger.error(f"Fallback heuristic evaluation failed: {e}")
            return candidates


# Keep backward compatibility by aliasing the new class
DryRunEngine = SmartPathEvaluator
