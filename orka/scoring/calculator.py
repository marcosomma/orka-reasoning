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
Boolean Score Calculator
========================

Calculates deterministic scores from boolean evaluation criteria.
"""

import logging
from typing import Any, Dict, List, Optional
import copy

from .presets import load_preset

logger = logging.getLogger(__name__)


class BooleanScoreCalculator:
    """
    Calculates scores from boolean evaluation criteria.

    Provides deterministic, auditable scoring by:
    1. Accepting boolean evaluations per criterion
    2. Applying configured weights
    3. Returning detailed breakdowns

    Args:
        preset: Name of scoring preset ('strict', 'moderate', 'lenient')
        context: Scoring context ('graphscout', 'quality', 'loop_convergence', 'validation')
                 Defaults to 'graphscout' for backward compatibility
        custom_weights: Optional custom weight overrides
    """

    def __init__(
        self,
        preset: str = "moderate",
        context: str = "graphscout",
        custom_weights: Optional[Dict[str, Any]] = None,
    ):
        self.preset_name = preset
        self.context = context
        preset_config = load_preset(preset, context=context)

        # Deep copy weights to avoid modifying shared preset data
        self.weights = copy.deepcopy(preset_config["weights"])
        self.thresholds = preset_config["thresholds"]

        if custom_weights:
            self._apply_custom_weights(custom_weights)

        self._flatten_weights()

        # Log total weight for debugging
        total_weight = sum(self.flat_weights.values())
        logger.debug(
            f"BooleanScoreCalculator initialized with preset '{preset}' "
            f"in context '{context}' ({len(self.flat_weights)} criteria, "
            f"total_weight={total_weight:.4f})"
        )

    def _apply_custom_weights(self, custom_weights: Dict[str, Any]) -> None:
        """Apply custom weight overrides and renormalize to sum to 1.0."""
        # Collect unknown or invalid keys to surface a useful error
        unknown_dimensions = []
        unknown_criteria = []
        invalid_format = []

        for key, value in custom_weights.items():
            if "." in key:
                dimension, criterion = key.split(".", 1)
                if dimension in self.weights:
                    if criterion in self.weights[dimension]:
                        old_value = self.weights[dimension][criterion]
                        self.weights[dimension][criterion] = float(value)
                        logger.debug(f"Custom weight override: {key} = {value} (was {old_value})")
                    else:
                        unknown_criteria.append(key)
                        logger.warning(f"Custom weight '{key}' references unknown criterion")
                else:
                    unknown_dimensions.append(key)
                    logger.warning(f"Custom weight '{key}' references unknown dimension")
            else:
                invalid_format.append(key)
                logger.warning(
                    f"Custom weight '{key}' has invalid format (use 'dimension.criterion')"
                )

        # Fail fast if any invalid or unknown keys were provided. This prevents
        # silent misconfigurations where typos in custom weight names result in
        # unexpected scoring behavior and many noisy warnings at runtime.
        errors = []
        if invalid_format:
            errors.append(f"invalid_format: {invalid_format}")
        if unknown_dimensions:
            errors.append(f"unknown_dimensions: {unknown_dimensions}")
        if unknown_criteria:
            errors.append(f"unknown_criteria: {unknown_criteria}")

        if errors:
            raise ValueError(
                "Invalid custom_weights provided (see details): " + "; ".join(errors)
            )

        # Renormalize weights to sum to 1.0 after custom overrides
        total_weight = sum(sum(criteria.values()) for criteria in self.weights.values())
        if total_weight > 0 and abs(total_weight - 1.0) > 0.001:
            logger.info(
                f"Renormalizing weights from {total_weight:.4f} to 1.0 after custom overrides"
            )
            normalization_factor = 1.0 / total_weight
            for dimension in self.weights:
                for criterion in self.weights[dimension]:
                    self.weights[dimension][criterion] *= normalization_factor

    def _flatten_weights(self) -> None:
        """Flatten nested weights dict to flat structure."""
        self.flat_weights: Dict[str, float] = {}

        for dimension, criteria in self.weights.items():
            for criterion, weight in criteria.items():
                key = f"{dimension}.{criterion}"
                self.flat_weights[key] = float(weight)

    def calculate(self, boolean_evaluations: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
        """
        Calculate score from boolean evaluations.

        Args:
            boolean_evaluations: Nested dict of boolean values
                Example: {"completeness": {"has_all_required_steps": true, ...}, ...}

        Returns:
            Dict containing:
                - score: Overall score (0.0-1.0)
                - assessment: APPROVED/NEEDS_IMPROVEMENT/REJECTED
                - breakdown: Detailed per-criterion results
                - passed_criteria: List of passed criteria
                - failed_criteria: List of failed criteria
                - dimension_scores: Scores per dimension
        """
        score = 0.0
        breakdown = {}
        passed_criteria = []
        failed_criteria = []
        dimension_scores: Dict[str, Dict[str, Any]] = {}

        for dimension, criteria in self.weights.items():
            dimension_score = 0.0
            dimension_max = 0.0
            dimension_breakdown = []

            for criterion, weight in criteria.items():
                key = f"{dimension}.{criterion}"
                dimension_max += weight

                criterion_value = self._get_nested_value(boolean_evaluations, dimension, criterion)
                if criterion_value is True:
                    score += weight
                    dimension_score += weight
                    passed_criteria.append(key)
                    status = "✓"
                elif criterion_value is False:
                    failed_criteria.append(key)
                    status = "✗"
                else:
                    # Defer per-criterion missing warnings; collect and summarize later
                    failed_criteria.append(key)
                    status = "?"

                breakdown[key] = {
                    "weight": weight,
                    "passed": criterion_value is True,
                    "status": status,
                }

                dimension_breakdown.append(
                    {
                        "criterion": criterion,
                        "weight": weight,
                        "passed": criterion_value is True,
                        "status": status,
                    }
                )

            dimension_scores[dimension] = {
                "score": dimension_score,
                "max_score": dimension_max,
                "percentage": (dimension_score / dimension_max * 100) if dimension_max > 0 else 0.0,
                "breakdown": dimension_breakdown,
            }

        assessment = self._score_to_assessment(score)

        # Log any missing/invalid boolean values once to avoid noisy logs
        missing = [k for k, v in breakdown.items() if v["status"] == "?"]
        if missing:
            logger.warning(
                f"Missing or invalid boolean values for {len(missing)} criteria: {missing[:10]}{'...' if len(missing) > 10 else ''}. Treating as False"
            )

        result = {
            "score": round(score, 4),
            "assessment": assessment,
            "breakdown": breakdown,
            "passed_criteria": passed_criteria,
            "failed_criteria": failed_criteria,
            "dimension_scores": dimension_scores,
            "total_criteria": len(self.flat_weights),
            "passed_count": len(passed_criteria),
            "failed_count": len(failed_criteria),
        }

        logger.info(
            f"Score calculated: {score:.4f} ({assessment}) - \n"
            f"--------------------------------------------------\n"
            f"Passed: {len(passed_criteria)}/{len(self.flat_weights)} \n"
            f"Failed: {len(failed_criteria)}/{len(self.flat_weights)} \n"
            f"Breakdown: {breakdown} \n"
            f"Passed Criteria: {passed_criteria} \n"
            f"Failed Criteria: {failed_criteria} \n"
            f"Dimension Scores: {dimension_scores} \n"
            f"Passed: {passed_criteria} \n"
            f"Failed: {failed_criteria} \n"
            f"Total Criteria: {self.flat_weights} \n"
            f"--------------------------------------------------\n"
        )
        logger.debug(result)

        return result

    def _get_nested_value(
        self, evaluations: Dict[str, Any], dimension: str, criterion: str
    ) -> Optional[bool]:
        """Extract boolean value from nested evaluation structure."""
        if dimension not in evaluations:
            return None

        dimension_data = evaluations[dimension]
        if not isinstance(dimension_data, dict):
            return None

        if criterion not in dimension_data:
            return None

        value = dimension_data[criterion]

        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ("true", "yes", "1", "pass", "passed"):
                return True
            if value_lower in ("false", "no", "0", "fail", "failed"):
                return False

        return None

    def _score_to_assessment(self, score: float) -> str:
        """Convert numeric score to assessment category."""
        if score >= self.thresholds["approved"]:
            return "APPROVED"
        elif score >= self.thresholds["needs_improvement"]:
            return "NEEDS_IMPROVEMENT"
        else:
            return "REJECTED"

    def get_breakdown(self, result: Dict[str, Any]) -> str:
        """
        Format detailed breakdown as readable string.

        Args:
            result: Result dict from calculate()

        Returns:
            Formatted breakdown string
        """
        lines = [
            f"Score: {result['score']:.4f} ({result['assessment']})",
            f"Passed: {result['passed_count']}/{result['total_criteria']} criteria",
            "",
            "Breakdown by Dimension:",
        ]

        for dimension, dim_data in result["dimension_scores"].items():
            lines.append(
                f"\n{dimension.upper()}: {dim_data['score']:.2f}/{dim_data['max_score']:.2f} ({dim_data['percentage']:.1f}%)"
            )

            for item in dim_data["breakdown"]:
                lines.append(
                    f"  {item['status']} {item['criterion']} (weight: {item['weight']:.3f})"
                )

        return "\n".join(lines)

    def get_failed_criteria(self, result: Dict[str, Any]) -> List[str]:
        """
        Extract list of failed criteria from result.

        Args:
            result: Result dict from calculate()

        Returns:
            List of failed criterion keys
        """
        failed = result.get("failed_criteria", [])
        if not isinstance(failed, list):
            return []
        return [str(item) for item in failed]
