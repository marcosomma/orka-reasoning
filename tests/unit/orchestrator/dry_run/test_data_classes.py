# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for dry_run data classes."""

import pytest

from orka.orchestrator.dry_run.data_classes import PathEvaluation, ValidationResult


class TestPathEvaluation:
    """Tests for PathEvaluation dataclass."""

    def test_path_evaluation_creation(self):
        """Test creating a PathEvaluation instance."""
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test reasoning",
            expected_output="Test output",
            estimated_tokens=500,
            estimated_cost=0.005,
            estimated_latency_ms=1000,
            risk_factors=["risk1", "risk2"],
            efficiency_rating="high",
        )

        assert evaluation.node_id == "test_agent"
        assert evaluation.relevance_score == 0.8
        assert evaluation.confidence == 0.9
        assert evaluation.reasoning == "Test reasoning"
        assert evaluation.expected_output == "Test output"
        assert evaluation.estimated_tokens == 500
        assert evaluation.estimated_cost == 0.005
        assert evaluation.estimated_latency_ms == 1000
        assert evaluation.risk_factors == ["risk1", "risk2"]
        assert evaluation.efficiency_rating == "high"

    def test_path_evaluation_default_values(self):
        """Test PathEvaluation with minimum required fields."""
        evaluation = PathEvaluation(
            node_id="agent",
            relevance_score=0.5,
            confidence=0.5,
            reasoning="",
            expected_output="",
            estimated_tokens=0,
            estimated_cost=0.0,
            estimated_latency_ms=0,
            risk_factors=[],
            efficiency_rating="medium",
        )

        assert evaluation.node_id == "agent"
        assert evaluation.risk_factors == []


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult instance."""
        result = ValidationResult(
            is_valid=True,
            confidence=0.85,
            efficiency_score=0.9,
            validation_reasoning="Valid path",
            suggested_improvements=["improvement1"],
            risk_assessment="low",
        )

        assert result.is_valid is True
        assert result.confidence == 0.85
        assert result.efficiency_score == 0.9
        assert result.validation_reasoning == "Valid path"
        assert result.suggested_improvements == ["improvement1"]
        assert result.risk_assessment == "low"

    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid path."""
        result = ValidationResult(
            is_valid=False,
            confidence=0.3,
            efficiency_score=0.2,
            validation_reasoning="Path is suboptimal",
            suggested_improvements=["use different agent", "add response builder"],
            risk_assessment="high",
        )

        assert result.is_valid is False
        assert len(result.suggested_improvements) == 2

