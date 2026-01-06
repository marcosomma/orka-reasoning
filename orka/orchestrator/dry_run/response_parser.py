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
Response Parser
===============

Methods for parsing LLM responses into structured evaluation results.
"""

import json
import logging
from typing import Any, Dict

from ...utils.json_parser import parse_llm_json
from ...utils.structured_output import StructuredOutputConfig
from ..llm_response_schemas import validate_path_evaluation, validate_path_validation
from .data_classes import PathEvaluation, ValidationResult

logger = logging.getLogger(__name__)


class ResponseParserMixin:
    """Mixin providing response parsing methods for path evaluation."""

    def _parse_evaluation_response(self, response: str, node_id: str) -> PathEvaluation:
        """Parse and validate LLM evaluation response using schema-aware parsing."""
        try:
            # Build schema from StructuredOutputConfig (path-evaluator)
            try:
                cfg = getattr(self, "eval_structured_config", None)
                if not cfg:
                    cfg = StructuredOutputConfig.from_params(
                        agent_params={"structured_output": {"enabled": True, "mode": "prompt"}},
                        agent_type="path-evaluator",
                    )
                schema = cfg.build_json_schema()
            except Exception:
                schema = None

            if schema:
                data = parse_llm_json(
                    response,
                    schema=schema,
                    strict=False,
                    coerce_types=True,
                    track_errors=True,
                    agent_id=f"path_evaluator_{node_id}",
                )
            else:
                data = json.loads(response)

            # Fallback immediately on parse failure
            if not isinstance(data, dict) or data.get("error") == "json_parse_failed":
                return self._create_fallback_evaluation(node_id)

            # Validate against existing schema function for additional safety
            if isinstance(data, dict):
                ok, err = validate_path_evaluation(data)
                if not ok:
                    logger.warning(f"Evaluation response failed schema validation: {err}")
                    return self._create_fallback_evaluation(node_id)
            else:
                raise ValueError("Parsed evaluation response is not a dict")

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

        except Exception as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return self._create_fallback_evaluation(node_id)

    def _parse_validation_response(self, response: str) -> ValidationResult:
        """Parse and validate LLM validation response using schema-aware parsing."""
        try:
            # Primary schema (tests expect approved/validation_score in defaults)
            data: Dict[str, Any]
            cfg_primary = StructuredOutputConfig.from_params(
                agent_params={"structured_output": {"enabled": True, "mode": "prompt"}},
                agent_type="path-validator",
            )
            parsed = parse_llm_json(
                response,
                schema=cfg_primary.build_json_schema(),
                strict=False,
                coerce_types=True,
                track_errors=True,
                agent_id="path_validator",
            )

            if isinstance(parsed, dict) and (
                "approved" in parsed or "validation_score" in parsed
            ) and parsed.get("error") != "json_parse_failed":
                data = parsed
            else:
                # Fallback schema aligned with prompt_builder keys
                cfg_alt = StructuredOutputConfig.from_params(
                    agent_params={
                        "structured_output": {
                            "enabled": True,
                            "mode": "prompt",
                            "schema": {
                                "required": ["is_valid", "efficiency_score"],
                                "optional": {
                                    "confidence": "number",
                                    "validation_reasoning": "string",
                                    "suggested_improvements": "array",
                                    "risk_assessment": "string",
                                },
                                "types": {
                                    "is_valid": "boolean",
                                    "efficiency_score": "number",
                                },
                            },
                        }
                    },
                    agent_type="path-validator",
                )
                data = parse_llm_json(
                    response,
                    schema=cfg_alt.build_json_schema(),
                    strict=False,
                    coerce_types=True,
                    track_errors=True,
                    agent_id="path_validator",
                )

            if not isinstance(data, dict) or data.get("error") == "json_parse_failed":
                return self._create_fallback_validation()

            # Validate with existing schema function (best-effort)
            ok, err = validate_path_validation(data)
            if not ok:
                logger.warning(f"Validation response failed schema validation: {err}")
                return self._create_fallback_validation()

            # Support both key variants
            is_valid_val = data.get("is_valid")
            if is_valid_val is None:
                is_valid_val = data.get("approved", True)

            eff_score = data.get("efficiency_score")
            if eff_score is None:
                eff_score = data.get("validation_score", 0.5)

            return ValidationResult(
                is_valid=bool(is_valid_val),
                confidence=float(data.get("confidence", 0.5)),
                efficiency_score=float(eff_score),
                validation_reasoning=str(
                    data.get("validation_reasoning", data.get("reasoning", "No validation reasoning"))
                ),
                suggested_improvements=data.get("suggested_improvements", []),
                risk_assessment=str(data.get("risk_assessment", "medium")),
            )

        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            return self._create_fallback_validation()

    def _parse_comprehensive_evaluation_response(self, response: str) -> Dict[str, Any]:
        """Parse the comprehensive LLM evaluation response using schema-aware parsing.

        Accepts variants such as a string path ("a -> b -> c") or alternate keys like
        selected_path / decision.selected_path and maps them to recommended_path.
        """
        try:
            # Prefer schema-aware parsing
            try:
                cfg = StructuredOutputConfig.from_params(
                    agent_params={"structured_output": {"enabled": True, "mode": "prompt"}},
                    agent_type="path-comprehensive",
                )
                parsed = parse_llm_json(
                    response,
                    schema=cfg.build_json_schema(),
                    strict=False,
                    coerce_types=True,
                    track_errors=True,
                    agent_id="path_comprehensive",
                )
            except Exception:
                parsed = json.loads(response)

            if not isinstance(parsed, dict) or parsed.get("error") == "json_parse_failed":
                raise ValueError("Comprehensive evaluation parse failed")

            data: Dict[str, Any] = dict(parsed)

            # Normalize recommended_path from variants
            if "recommended_path" not in data or not data.get("recommended_path"):
                if isinstance(data.get("selected_path"), list):
                    data["recommended_path"] = data["selected_path"]
                elif isinstance(data.get("decision", {}), dict) and isinstance(
                    data["decision"].get("selected_path"), list
                ):
                    data["recommended_path"] = data["decision"]["selected_path"]

            # Support a string path like "a -> b -> c"
            rp = data.get("recommended_path")
            if isinstance(rp, str):
                # Split on arrows or arrows with spaces
                parts = [p.strip() for p in rp.replace("->", "->").split("->") if p.strip()]
                data["recommended_path"] = parts

            # Ensure fields exist
            if not isinstance(data.get("recommended_path"), list):
                raise ValueError("Missing required field: recommended_path")
            if "reasoning" not in data:
                data["reasoning"] = "No reasoning provided"
            if "confidence" not in data:
                data["confidence"] = 0.5

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

