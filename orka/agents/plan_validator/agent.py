# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Plan Validator Agent
====================

Meta-cognitive agent that validates and critiques proposed agent execution paths.
Works in feedback loops with GraphScout to iteratively improve path selection.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, cast

from orka.scoring import BooleanScoreCalculator

from ..base_agent import BaseAgent, Context
from . import boolean_parser, llm_client
from . import prompt_builder

logger = logging.getLogger(__name__)


class PlanValidatorAgent(BaseAgent):
    """
    Agent that validates and critiques proposed agent execution paths.

    Evaluates paths across multiple dimensions (completeness, efficiency,
    safety, coherence, fallback) and provides structured feedback for
    iterative improvement.

    Args:
        agent_id: Unique identifier for the agent
        model:  LLM model name (default: "gpt-oss:20b")
        llm_provider: Provider type ("ollama" or "openai_compatible")
        llm_url: LLM API endpoint URL
        temperature: Temperature for LLM generation
        scoring_preset: Scoring preset name ('strict', 'moderate', 'lenient')
        custom_weights: Optional custom weight overrides
        **kwargs: Additional arguments for BaseAgent
    """

    def __init__(
        self,
        agent_id: str,
        llm_model: str = "MISSING_LLM_MODEL",
        llm_provider: str = "MISSING_LLM_PROVIDER",
        llm_url: str = "MISSING_LLM_URL",
        temperature: float = 0.2,
        scoring_preset: str = "moderate",
        custom_weights: Optional[Dict[str, float]] = None,
        **kwargs: Any,
    ):
        super().__init__(agent_id, **kwargs)

        missing: List[str] = []
        if not isinstance(llm_model, str) or not llm_model.strip() or llm_model.startswith("MISSING_"):
            missing.append("llm_model (or model)")
        if (
            not isinstance(llm_provider, str)
            or not llm_provider.strip()
            or llm_provider.startswith("MISSING_")
        ):
            missing.append("llm_provider (or provider)")
        if not isinstance(llm_url, str) or not llm_url.strip() or llm_url.startswith("MISSING_"):
            missing.append("llm_url (or model_url/url)")
        if missing:
            raise ValueError(
                "PlanValidatorAgent requires explicit LLM configuration; missing: "
                + ", ".join(missing)
            )

        self.llm_model = llm_model
        self.llm_provider = llm_provider
        self.llm_url = llm_url
        self.temperature = temperature
        self.scoring_preset = scoring_preset
        self.custom_weights = custom_weights

        self.score_calculator = BooleanScoreCalculator(
            preset=scoring_preset,
            custom_weights=custom_weights,
        )

        logger.info(
            f"Initialized PlanValidatorAgent '{agent_id}' with model '{llm_model}' "
            f"and scoring preset '{scoring_preset}'"
        )

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """
        Validate a proposed agent path.

        Args:
            ctx: Context containing:
                - input: Original user query
                - previous_outputs: Including GraphScout proposed path
                - loop_number: Current iteration number
                - past_loops: Previous validation rounds (optional)

        Returns:
            Structured critique dict with validation_score
        """
        # Extract information from context
        original_query = self._extract_query(ctx)
        proposed_path = self._extract_proposed_path(ctx)
        previous_critiques = self._extract_previous_critiques(ctx)
        loop_num_val = ctx.get("loop_number", 1)
        if isinstance(loop_num_val, int):
            loop_number = loop_num_val
        else:
            loop_number = 1

        logger.info(f"PlanValidator (Round {loop_number}): Evaluating proposed path")
        logger.debug(f"Query: {original_query[:100]}...")

        # Build validation prompt requesting boolean evaluations
        validation_prompt = prompt_builder.build_validation_prompt(
            query=original_query,
            proposed_path=proposed_path,
            previous_critiques=previous_critiques,
            loop_number=loop_number,
            preset_name=self.scoring_preset,
            scoring_context=ctx.get("scoring_context") if isinstance(ctx, dict) else None,
        )

        # Call LLM for boolean evaluation
        try:
            llm_response = await llm_client.call_llm(
                prompt=validation_prompt,
                model=self.llm_model,
                url=self.llm_url,
                provider=self.llm_provider,
                temperature=self.temperature,
            )
        except RuntimeError as e:
            logger.error(f"LLM call failed: {e}")
            return self._create_error_result(str(e))

        # Parse boolean evaluations from LLM response
        boolean_evaluations = boolean_parser.parse_boolean_evaluation(llm_response)

        # Determine scoring context (can be provided by runtime ctx for loop-specific scoring)
        scoring_context = ctx.get("scoring_context") if isinstance(ctx, dict) else None

        # If we are in the 'loop_convergence' context and the LLM failed to provide
        # sufficiently many boolean criteria, synthesize a minimal set of booleans
        # heuristically from the LLM textual response so downstream scoring can run.
        if scoring_context == "loop_convergence":
            try:
                # Count provided criteria
                provided = 0
                if isinstance(boolean_evaluations, dict):
                    for v in boolean_evaluations.values():
                        if isinstance(v, dict):
                            provided += len(v)

                MIN_CRITERIA = 2
                if provided < MIN_CRITERIA:
                    synthesized = self._synthesize_loop_convergence_booleans(llm_response, boolean_evaluations)
                    if synthesized:
                        logger.info("PlanValidator: Synthesized loop_convergence boolean_evaluations from LLM response")
                        # Merge synthesized booleans, prefer explicit parsed values when available
                        merged = dict(boolean_evaluations or {})
                        for dim, criteria in synthesized.items():
                            if dim not in merged or not isinstance(merged.get(dim), dict):
                                merged[dim] = {}
                            merged[dim].update({k: v for k, v in criteria.items() if k not in merged[dim]})
                        boolean_evaluations = merged
            except Exception as e:
                logger.debug(f"Synthesis of loop_convergence booleans failed: {e}")

        # Use a context-aware score calculator instance for this run
        if scoring_context and getattr(self.score_calculator, "context", None) != scoring_context:
            score_calc = BooleanScoreCalculator(preset=self.scoring_preset, context=scoring_context, custom_weights=self.custom_weights)
        else:
            score_calc = self.score_calculator

        # Calculate score using boolean calculator
        score_result = score_calc.calculate(boolean_evaluations)

        # Build validation result with additional metadata
        validation_result = self._build_validation_result(
            score_result=score_result,
            boolean_evaluations=boolean_evaluations,
            llm_response=llm_response,
        )

        logger.info(
            f"Validation Score: {validation_result['validation_score']:.4f} "
            f"- {validation_result['overall_assessment']}"
        )
        logger.debug(
            f"Passed: {score_result['passed_count']}/{score_result['total_criteria']} criteria"
        )

        return validation_result

    def _synthesize_loop_convergence_booleans(self, llm_response: str, existing: dict | None = None) -> Dict[str, Dict[str, bool]]:
        """Heuristically synthesize loop_convergence boolean evaluations from text.

        This is intentionally conservative and only creates a few high-value criteria
        when the LLM response does not already contain a robust set.
        """
        text = (llm_response or "").lower()
        synth: Dict[str, Dict[str, bool]] = {
            "improvement": {
                "better_than_previous": False,
                "significant_delta": False,
                "approaching_target": False,
            },
            "stability": {"not_degrading": False, "consistent_direction": False},
            "convergence": {"delta_decreasing": False, "within_tolerance": False},
        }

        # Simple keyword heuristics
        if any(tok in text for tok in ("improve", "improved", "better", "gain", "reduc", "decrease", "decreased")):
            synth["improvement"]["better_than_previous"] = True
        if any(tok in text for tok in ("significant", "substantial", "major", "large")):
            synth["improvement"]["significant_delta"] = True
        if any(tok in text for tok in ("within tolerance", "within range", "close to", "near goal", "approach")):
            synth["improvement"]["approaching_target"] = True

        if any(tok in text for tok in ("stable", "no regression", "no regress", "not degrade", "no degradation")):
            synth["stability"]["not_degrading"] = True
        if any(tok in text for tok in ("consistent", "direction", "trend")):
            synth["stability"]["consistent_direction"] = True

        if any(tok in text for tok in ("decreasing", "decrease", "reduced", "reduction")):
            synth["convergence"]["delta_decreasing"] = True
        if any(tok in text for tok in ("within tolerance", "within range", "within target", "close to")):
            synth["convergence"]["within_tolerance"] = True

        # Try to detect numeric improvements like 'improves by 5%'
        try:
            pct_matches = re.findall(r"(\d+\.?\d*)%", text)
            for m in pct_matches:
                try:
                    val = float(m)
                    if val >= 5.0:
                        synth["improvement"]["significant_delta"] = True
                except Exception:
                    continue
        except Exception:
            pass

        # If synthesis produced no True flags, then return empty so caller knows not to use it.
        any_true = any(any(c for c in d.values()) for d in synth.values())
        return synth if any_true else {}

    def _extract_query(self, ctx: Context) -> str:
        """
        Extract original query from context.

        Args:
            ctx: Context dict

        Returns:
            Query string
        """
        input_val: Any = ctx.get("input")
        # Handle nested input dict
        if isinstance(input_val, dict) and "input" in input_val:
            return str(input_val["input"])
        # Handle direct input or None
        return str(input_val) if input_val is not None else ""

    def _extract_proposed_path(self, ctx: Context) -> Dict[str, Any]:
        """
        Extract proposed path from GraphScout output in previous_outputs.

        Args:
            ctx: Context dict

        Returns:
            Proposed path dict or error dict if not found
        """
        previous_outputs = ctx.get("previous_outputs", {})

        # Look for GraphScout output by common agent IDs
        graphscout_keys = [
            "graph_scout",
            "graphscout_planner",
            "graphscout_router",
            "path_proposer",
            "plan_proposer",
            "dynamic_router",
        ]

        for key in graphscout_keys:
            if key in previous_outputs:
                output = previous_outputs[key]
                logger.debug(f"Found GraphScout output in '{key}'")
                
                # GraphScout returns structure with nested data in 'result' or 'response'
                # LoopNode wraps agent outputs in 'response', while direct calls use 'result'
                for nested_key in ["response", "result"]:
                    if isinstance(output, dict) and nested_key in output:
                        nested_data = output[nested_key]
                        if isinstance(nested_data, dict) and any(k in nested_data for k in ["decision", "decision_type", "target", "path"]):
                            logger.debug(f"Using nested {nested_key} from '{key}'")
                            return cast(Dict[str, Any], nested_data)
                
                # Otherwise use top-level output
                if isinstance(output, dict):
                    return cast(Dict[str, Any], output)

        # Fallback: look for any agent with path/decision info
        # Check both top-level and nested 'result' or 'response' fields
        for agent_id, output in previous_outputs.items():
            if isinstance(output, dict):
                # Check nested response or result first
                for nested_key in ["response", "result"]:
                    if nested_key in output:
                        nested_data = output[nested_key]
                        if isinstance(nested_data, dict) and any(k in nested_data for k in ["decision", "decision_type", "target", "path"]):
                            logger.debug(f"Found proposed path in '{agent_id}' (fallback, nested {nested_key})")
                            return cast(Dict[str, Any], nested_data)
                
                # Check top-level fields
                if any(k in output for k in ["decision", "decision_type", "target", "path"]):
                    logger.debug(f"Found proposed path in '{agent_id}' (fallback, top-level)")
                    return cast(Dict[str, Any], output)

        logger.warning(
            f"No proposed path found in previous_outputs. "
            f"Available keys: {list(previous_outputs.keys())}. "
            f"Expected GraphScout output with 'decision', 'target', or 'path' fields."
        )
        return {"error": "No proposed path found", "available_keys": list(previous_outputs.keys())}

    def _extract_previous_critiques(self, ctx: Context) -> List[Dict[str, Any]]:
        """
        Extract previous validation critiques from past loop iterations.

        Args:
            ctx: Context dict

        Returns:
            List of previous critique dicts
        """
        past_loops = ctx.get("previous_outputs", {}).get("past_loops", [])
        critiques = []

        for loop in past_loops:
            loop_str = str(loop)
            if "validation_score" in loop_str or "critiques" in loop_str:
                critiques.append(loop)

        return critiques

    def _build_validation_result(
        self,
        score_result: Dict[str, Any],
        boolean_evaluations: Dict[str, Dict[str, bool]],
        llm_response: str,
    ) -> Dict[str, Any]:
        """
        Build final validation result from score calculation.

        Args:
            score_result: Result from BooleanScoreCalculator
            boolean_evaluations: Boolean evaluations from LLM
            llm_response: Raw LLM response

        Returns:
            Validation result dict
        """
        return {
            "validation_score": score_result["score"],
            "overall_assessment": score_result["assessment"],
            "boolean_evaluations": boolean_evaluations,
            "breakdown": score_result["breakdown"],
            "passed_criteria": score_result["passed_criteria"],
            "failed_criteria": score_result["failed_criteria"],
            "dimension_scores": score_result["dimension_scores"],
            "rationale": self._extract_rationale(llm_response),
            "scoring_preset": self.scoring_preset,
        }

    def _extract_rationale(self, llm_response: str) -> str:
        """
        Extract rationale from LLM response.

        Args:
            llm_response: Raw LLM response

        Returns:
            Rationale string
        """
        try:
            json_data = json.loads(llm_response)
            if isinstance(json_data, dict) and "rationale" in json_data:
                return str(json_data["rationale"])
        except json.JSONDecodeError:
            pass

        rationale_match = re.search(r'"rationale":\s*"([^"]+)"', llm_response, re.IGNORECASE)
        if rationale_match:
            return str(rationale_match.group(1))

        if len(llm_response) < 500:
            return llm_response[:200]
        return llm_response[:200] + "..."

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        Create error result when validation fails.

        Args:
            error_message: Error description

        Returns:
            Error validation result dict
        """
        return {
            "validation_score": 0.0,
            "overall_assessment": "REJECTED",
            "boolean_evaluations": {},
            "breakdown": {},
            "passed_criteria": [],
            "failed_criteria": [],
            "dimension_scores": {},
            "rationale": f"Validation failed: {error_message}",
            "scoring_preset": self.scoring_preset,
            "error": error_message,
        }
