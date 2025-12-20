# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Response Parser
===============

Methods for parsing LLM responses into structured evaluation results.
"""

import json
import logging
from typing import Any, Dict

from ..llm_response_schemas import validate_path_evaluation, validate_path_validation
from .data_classes import PathEvaluation, ValidationResult

logger = logging.getLogger(__name__)


class ResponseParserMixin:
    """Mixin providing response parsing methods for path evaluation."""

    def _parse_evaluation_response(self, response: str, node_id: str) -> PathEvaluation:
        """Parse and validate LLM evaluation response into structured format."""
        try:
            data = json.loads(response)

            # Validate against schema
            is_valid, error_msg = validate_path_evaluation(data)
            if not is_valid:
                logger.warning(f"Evaluation response failed schema validation: {error_msg}")
                logger.debug(f"Invalid response: {data}")
                raise ValueError(f"Schema validation failed: {error_msg}")

            return PathEvaluation(
                node_id=node_id,
                relevance_score=float(data.get("relevance_score", 0.5)),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=str(data.get("reasoning", "No reasoning provided")),
                expected_output=str(data.get("expected_output", "Unknown output")),
                estimated_tokens=int(data.get("estimated_tokens") or 100),
                estimated_cost=float(data.get("estimated_cost") or 0.001),
                estimated_latency_ms=int(data.get("estimated_latency_ms") or 1000),
                risk_factors=data.get("risk_factors") or [],
                efficiency_rating=str(data.get("efficiency_rating", "medium")),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON in evaluation response: {e}")
            return self._create_fallback_evaluation(node_id)
        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return self._create_fallback_evaluation(node_id)

    def _parse_validation_response(self, response: str) -> ValidationResult:
        """Parse and validate LLM validation response into structured format."""
        try:
            data = json.loads(response)

            # Validate against schema
            is_valid, error_msg = validate_path_validation(data)
            if not is_valid:
                logger.warning(f"Validation response failed schema validation: {error_msg}")
                logger.debug(f"Invalid response: {data}")
                raise ValueError(f"Schema validation failed: {error_msg}")

            return ValidationResult(
                is_valid=bool(data.get("is_valid", True)),
                confidence=float(data.get("confidence", 0.5)),
                efficiency_score=float(data.get("efficiency_score", 0.5)),
                validation_reasoning=str(
                    data.get("validation_reasoning", "No validation reasoning")
                ),
                suggested_improvements=data.get("suggested_improvements", []),
                risk_assessment=str(data.get("risk_assessment", "medium")),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON in validation response: {e}")
            return self._create_fallback_validation()
        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            return self._create_fallback_validation()

    def _parse_comprehensive_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse the comprehensive LLM evaluation response."""
        try:
            data = json.loads(response)

            # Ensure data is a dictionary
            if not isinstance(data, dict):
                raise ValueError("Response is not a valid JSON object")

            # Validate required fields
            required_fields = ["recommended_path", "reasoning", "confidence"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            return data

        except Exception as e:
            logger.error(f"Failed to parse comprehensive evaluation response: {e}")
            return {
                "recommended_path": [],
                "reasoning": "Failed to parse LLM response",
                "confidence": 0.3,
                "expected_outcome": "Unknown",
                "path_evaluations": [],
            }

    def _create_fallback_evaluation(self, node_id: str) -> PathEvaluation:
        """Create fallback evaluation when LLM fails."""
        return PathEvaluation(
            node_id=node_id,
            relevance_score=0.5,
            confidence=0.3,
            reasoning="LLM evaluation failed, using fallback",
            expected_output="Unable to predict output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=1000,
            risk_factors=["evaluation_failure"],
            efficiency_rating="medium",
        )

    def _create_fallback_validation(self) -> ValidationResult:
        """Create fallback validation when LLM fails."""
        return ValidationResult(
            is_valid=True,
            confidence=0.3,
            efficiency_score=0.5,
            validation_reasoning="LLM validation failed, using fallback",
            suggested_improvements=["retry_evaluation"],
            risk_assessment="medium",
        )

