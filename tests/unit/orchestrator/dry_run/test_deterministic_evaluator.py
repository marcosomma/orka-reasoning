# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for DeterministicPathEvaluator."""

import pytest
from unittest.mock import MagicMock

from orka.orchestrator.dry_run.deterministic_evaluator import DeterministicPathEvaluator


class TestDeterministicPathEvaluator:
    """Tests for DeterministicPathEvaluator."""

    @pytest.fixture
    def config(self):
        """Create a mock config."""
        return MagicMock()

    @pytest.fixture
    def evaluator(self, config):
        """Create a DeterministicPathEvaluator instance."""
        return DeterministicPathEvaluator(config)

    def test_evaluate_candidates_basic(self, evaluator):
        """Test basic candidate evaluation."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "llm_agent", "path": ["llm_agent"]},
        ]

        result = evaluator.evaluate_candidates(
            candidates, "search for information", {}
        )

        assert len(result) == 2
        assert "llm_evaluation" in result[0]
        assert "llm_validation" in result[0]
        assert result[0]["llm_evaluation"]["is_deterministic_fallback"] is True

    def test_score_relevance_search_match(self, evaluator):
        """Test relevance scoring with keyword match."""
        score = evaluator._score_relevance("search_agent", "search for news")
        assert score > 0.5  # Should get boost for keyword match

    def test_score_relevance_no_match(self, evaluator):
        """Test relevance scoring without keyword match."""
        score = evaluator._score_relevance("random_agent", "hello world")
        assert score == 0.5  # Base score

    def test_score_confidence_optimal_length(self, evaluator):
        """Test confidence scoring for optimal path length."""
        score = evaluator._score_confidence(["agent1", "agent2"], {})
        assert score == 0.8  # Optimal length (2-3)

    def test_score_confidence_single_agent(self, evaluator):
        """Test confidence scoring for single agent."""
        score = evaluator._score_confidence(["agent1"], {})
        assert score == 0.6  # Single agent - might be incomplete

    def test_score_confidence_long_path(self, evaluator):
        """Test confidence scoring for long path."""
        score = evaluator._score_confidence(
            ["a1", "a2", "a3", "a4", "a5", "a6"], {}
        )
        assert score < 0.6  # Long paths get penalized

    def test_score_efficiency_short_path(self, evaluator):
        """Test efficiency scoring for short path."""
        score = evaluator._score_efficiency(["agent1"])
        assert score == 0.9  # Shortest paths are most efficient

    def test_score_efficiency_long_path(self, evaluator):
        """Test efficiency scoring for long path."""
        score = evaluator._score_efficiency(["a1", "a2", "a3", "a4", "a5"])
        assert score < 0.6  # Long paths are less efficient

    def test_evaluate_candidates_memory_query(self, evaluator):
        """Test evaluation with memory-related query."""
        candidates = [
            {"node_id": "memory_reader", "path": ["memory_reader"]},
        ]

        result = evaluator.evaluate_candidates(
            candidates, "remember what we discussed", {}
        )

        assert result[0]["llm_evaluation"]["relevance_score"] > 0.5

    def test_evaluate_candidates_validation_result(self, evaluator):
        """Test that validation results are properly set."""
        candidates = [
            {"node_id": "test_agent", "path": ["test_agent", "response_builder"]},
        ]

        result = evaluator.evaluate_candidates(candidates, "test query", {})

        validation = result[0]["llm_validation"]
        assert "is_valid" in validation
        assert "confidence" in validation
        assert "efficiency_score" in validation
        assert "validation_reasoning" in validation

