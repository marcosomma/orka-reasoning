# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for ResponseParserMixin."""

import pytest
import json
from unittest.mock import MagicMock, patch

from orka.orchestrator.dry_run.response_parser import ResponseParserMixin
from orka.orchestrator.dry_run.data_classes import PathEvaluation, ValidationResult


class ConcreteResponseParser(ResponseParserMixin):
    """Concrete implementation for testing."""

    pass


class TestResponseParserMixin:
    """Tests for ResponseParserMixin."""

    @pytest.fixture
    def parser(self):
        """Create a ResponseParserMixin instance."""
        return ConcreteResponseParser()

    def test_parse_evaluation_response_valid(self, parser):
        """Test parsing valid evaluation response."""
        response = json.dumps({
            "relevance_score": 0.85,
            "confidence": 0.9,
            "reasoning": "Good match for query",
            "expected_output": "Search results",
            "estimated_tokens": 500,
            "estimated_cost": 0.005,
            "estimated_latency_ms": 1000,
            "risk_factors": ["network_dependency"],
            "efficiency_rating": "high",
        })

        with patch(
            "orka.orchestrator.dry_run.response_parser.validate_path_evaluation",
            return_value=(True, None),
        ):
            result = parser._parse_evaluation_response(response, "test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"
        assert result.relevance_score == 0.85
        assert result.efficiency_rating == "high"

    def test_parse_evaluation_response_invalid_json(self, parser):
        """Test parsing invalid JSON response."""
        response = "not valid json {"

        result = parser._parse_evaluation_response(response, "test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.confidence == 0.3  # Fallback value
        assert "failed" in result.reasoning.lower()

    def test_parse_evaluation_response_schema_failure(self, parser):
        """Test parsing response that fails schema validation."""
        response = json.dumps({"relevance_score": 0.5})  # Missing required fields

        with patch(
            "orka.orchestrator.dry_run.response_parser.validate_path_evaluation",
            return_value=(False, "Missing required field"),
        ):
            result = parser._parse_evaluation_response(response, "test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.confidence == 0.3  # Fallback

    def test_parse_validation_response_valid(self, parser):
        """Test parsing valid validation response."""
        response = json.dumps({
            "is_valid": True,
            "confidence": 0.9,
            "efficiency_score": 0.85,
            "validation_reasoning": "Path is optimal",
            "suggested_improvements": [],
            "risk_assessment": "low",
        })

        with patch(
            "orka.orchestrator.dry_run.response_parser.validate_path_validation",
            return_value=(True, None),
        ):
            result = parser._parse_validation_response(response)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.efficiency_score == 0.85

    def test_parse_validation_response_invalid_json(self, parser):
        """Test parsing invalid JSON validation response."""
        response = "invalid json"

        result = parser._parse_validation_response(response)

        assert isinstance(result, ValidationResult)
        assert result.confidence == 0.3  # Fallback

    def test_parse_validation_response_approved_validation_score_variant(self, parser):
        """Test parsing validation response using approved/validation_score keys."""
        response = json.dumps({
            "approved": False,
            "validation_score": 0.42,
            "confidence": 0.7,
            "reasoning": "Not efficient",
        })

        with patch(
            "orka.orchestrator.dry_run.response_parser.validate_path_validation",
            return_value=(True, None),
        ):
            result = parser._parse_validation_response(response)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert result.efficiency_score == 0.42

    def test_parse_evaluation_response_coerce_types(self, parser):
        """Test that string numbers are coerced by schema-aware parser."""
        response = json.dumps({
            "relevance_score": "0.75",
            "confidence": "0.6",
            "reasoning": "ok",
        })

        with patch(
            "orka.orchestrator.dry_run.response_parser.validate_path_evaluation",
            return_value=(True, None),
        ):
            result = parser._parse_evaluation_response(response, "node-x")

        assert isinstance(result, PathEvaluation)
        assert result.relevance_score == 0.75
        assert result.confidence == 0.6

    def test_parse_comprehensive_evaluation_response_valid(self, parser):
        """Test parsing valid comprehensive evaluation response."""
        response = json.dumps({
            "recommended_path": ["search_agent", "response_builder"],
            "reasoning": "Optimal for factual query",
            "confidence": 0.9,
            "expected_outcome": "Comprehensive answer",
            "path_evaluations": [
                {
                    "path": ["search_agent"],
                    "score": 0.7,
                    "pros": ["Fast"],
                    "cons": ["No response generation"],
                }
            ],
        })

        result = parser._parse_comprehensive_evaluation_response(response)

        assert result["recommended_path"] == ["search_agent", "response_builder"]
        assert result["confidence"] == 0.9
        assert len(result["path_evaluations"]) == 1

    def test_parse_comprehensive_evaluation_response_missing_field(self, parser):
        """Test parsing response with missing required field."""
        response = json.dumps({
            "recommended_path": ["agent1"],
            # Missing "reasoning" and "confidence"
        })

        result = parser._parse_comprehensive_evaluation_response(response)

        # With schema-aware parsing, we auto-fill defaults instead of failing the whole object
        assert isinstance(result["recommended_path"], list)
        assert result["confidence"] in (0.5, 0.3)
        assert "reasoning" in result

    def test_parse_comprehensive_evaluation_response_not_dict(self, parser):
        """Test parsing response that is not a dict."""
        response = json.dumps(["not", "a", "dict"])

        result = parser._parse_comprehensive_evaluation_response(response)

        assert result["recommended_path"] == []
        assert result["confidence"] == 0.3

    def test_parse_comprehensive_evaluation_response_string_path(self, parser):
        """Support string path split by arrows."""
        response = json.dumps({
            "recommended_path": "search_agent -> analysis_agent -> response_builder",
            "reasoning": "ok",
            "confidence": 0.8,
        })
        result = parser._parse_comprehensive_evaluation_response(response)
        assert result["recommended_path"] == [
            "search_agent",
            "analysis_agent",
            "response_builder",
        ]

    def test_parse_comprehensive_evaluation_response_selected_path_variant(self, parser):
        """Accept selected_path variant mapping to recommended_path."""
        response = json.dumps({
            "selected_path": ["a", "b", "c"],
            "reasoning": "ok",
            "confidence": 0.7,
        })
        result = parser._parse_comprehensive_evaluation_response(response)
        assert result["recommended_path"] == ["a", "b", "c"]

    def test_create_fallback_evaluation(self, parser):
        """Test creating fallback evaluation."""
        result = parser._create_fallback_evaluation("test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"
        assert result.relevance_score == 0.5
        assert result.confidence == 0.3
        assert "fallback" in result.reasoning.lower()
        assert "evaluation_failure" in result.risk_factors

    def test_create_fallback_validation(self, parser):
        """Test creating fallback validation."""
        result = parser._create_fallback_validation()

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.confidence == 0.3
        assert "retry_evaluation" in result.suggested_improvements

