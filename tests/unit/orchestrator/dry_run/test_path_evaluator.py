# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for PathEvaluatorMixin."""

import pytest
from unittest.mock import MagicMock

from orka.orchestrator.dry_run.path_evaluator import PathEvaluatorMixin
from orka.orchestrator.dry_run.data_classes import PathEvaluation, ValidationResult


class ConcretePathEvaluator(PathEvaluatorMixin):
    """Concrete implementation for testing."""

    pass


class TestPathEvaluatorMixin:
    """Tests for PathEvaluatorMixin."""

    @pytest.fixture
    def evaluator(self):
        """Create a PathEvaluatorMixin instance."""
        return ConcretePathEvaluator()

    @pytest.fixture
    def available_agents(self):
        """Create sample available agents."""
        return {
            "search_agent": {
                "id": "search_agent",
                "type": "DuckDuckGoTool",
                "description": "Web search",
                "cost_estimate": 0.0002,
                "latency_estimate": 800,
            },
            "response_builder": {
                "id": "response_builder",
                "type": "LocalLLMAgent",
                "description": "Response generation",
                "cost_estimate": 0.0005,
                "latency_estimate": 4000,
            },
            "memory_reader": {
                "id": "memory_reader",
                "type": "MemoryReaderNode",
                "description": "Memory retrieval",
                "cost_estimate": 0.0001,
                "latency_estimate": 200,
            },
        }

    def test_generate_possible_paths(self, evaluator, available_agents):
        """Test generating possible paths from candidates."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "response_builder", "path": ["search_agent", "response_builder"]},
        ]

        paths = evaluator._generate_possible_paths(available_agents, candidates)

        assert len(paths) == 2
        assert paths[0]["path"] == ["search_agent"]
        assert paths[1]["path"] == ["search_agent", "response_builder"]
        assert paths[1]["total_cost"] > paths[0]["total_cost"]

    def test_generate_path_specific_outcome_single_search(self, evaluator, available_agents):
        """Test outcome generation for single search agent."""
        outcome = evaluator._generate_path_specific_outcome(
            ["search_agent"], available_agents
        )

        assert "web" in outcome.lower() or "information" in outcome.lower()

    def test_generate_path_specific_outcome_single_memory(self, evaluator, available_agents):
        """Test outcome generation for single memory agent."""
        outcome = evaluator._generate_path_specific_outcome(
            ["memory_reader"], available_agents
        )

        assert "knowledge base" in outcome.lower() or "stored" in outcome.lower()

    def test_generate_path_specific_outcome_multi_step(self, evaluator, available_agents):
        """Test outcome generation for multi-step path."""
        outcome = evaluator._generate_path_specific_outcome(
            ["search_agent", "response_builder"], available_agents
        )

        assert "Multi-step" in outcome or "workflow" in outcome.lower()

    def test_generate_path_specific_outcome_empty(self, evaluator, available_agents):
        """Test outcome generation for empty path."""
        outcome = evaluator._generate_path_specific_outcome([], available_agents)

        assert outcome == "Unknown outcome"

    def test_generate_fallback_path_evaluation_search(self, evaluator, available_agents):
        """Test fallback evaluation for search path."""
        evaluation = evaluator._generate_fallback_path_evaluation(
            ["search_agent"], available_agents
        )

        assert evaluation["score"] > 0.5  # Search gets boost
        assert "web" in evaluation["reasoning"].lower()
        assert len(evaluation["pros"]) > 0

    def test_generate_fallback_path_evaluation_multi_hop(self, evaluator, available_agents):
        """Test fallback evaluation for multi-hop path."""
        # Add response builder attributes
        available_agents["response_builder"]["type"] = "LocalLLMAgent"

        evaluation = evaluator._generate_fallback_path_evaluation(
            ["search_agent", "response_builder"], available_agents
        )

        assert evaluation["score"] > 0.6  # Multi-hop with search gets boost
        assert "pros" in evaluation
        assert "cons" in evaluation

    def test_generate_fallback_path_evaluation_empty(self, evaluator, available_agents):
        """Test fallback evaluation for empty path."""
        evaluation = evaluator._generate_fallback_path_evaluation([], available_agents)

        assert evaluation["score"] == 0.3
        assert "Empty path" in evaluation["reasoning"]

    def test_map_evaluation_to_candidates(self, evaluator, available_agents):
        """Test mapping evaluation results to candidates."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
        ]
        evaluation_results = {
            "recommended_path": ["search_agent"],
            "reasoning": "Best path",
            "confidence": 0.9,
            "path_evaluations": [
                {
                    "path": ["search_agent"],
                    "score": 0.85,
                    "pros": ["Fast", "Current info"],
                    "cons": ["No response generation"],
                }
            ],
        }

        result = evaluator._map_evaluation_to_candidates(
            candidates, evaluation_results, available_agents
        )

        assert len(result) == 1
        assert result[0]["llm_evaluation"]["score"] == 0.85
        assert result[0]["llm_evaluation"]["is_recommended"] is True

    def test_combine_evaluation_results(self, evaluator):
        """Test combining evaluation and validation results."""
        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Good match",
            expected_output="Test output",
            estimated_tokens=500,
            estimated_cost=0.005,
            estimated_latency_ms=1000,
            risk_factors=[],
            efficiency_rating="high",
        )
        validation = ValidationResult(
            is_valid=True,
            confidence=0.85,
            efficiency_score=0.9,
            validation_reasoning="Valid",
            suggested_improvements=[],
            risk_assessment="low",
        )

        result = evaluator._combine_evaluation_results(candidate, evaluation, validation)

        assert "llm_evaluation" in result
        assert result["llm_evaluation"]["stage1"]["relevance_score"] == 0.8
        assert result["llm_evaluation"]["stage2"]["is_valid"] is True
        assert result["estimated_cost"] == 0.005

    def test_combine_evaluation_results_invalid(self, evaluator):
        """Test combining results when validation fails."""
        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Good match",
            expected_output="Test output",
            estimated_tokens=500,
            estimated_cost=0.005,
            estimated_latency_ms=1000,
            risk_factors=[],
            efficiency_rating="high",
        )
        validation = ValidationResult(
            is_valid=False,  # Invalid
            confidence=0.5,
            efficiency_score=0.3,
            validation_reasoning="Suboptimal",
            suggested_improvements=["Use different agent"],
            risk_assessment="high",
        )

        result = evaluator._combine_evaluation_results(candidate, evaluation, validation)

        # Relevance should be penalized for invalid validation
        assert result["llm_evaluation"]["final_scores"]["relevance"] == 0.4  # 0.8 * 0.5

