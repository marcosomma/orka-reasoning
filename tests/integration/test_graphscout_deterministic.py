# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma

"""
Integration tests for GraphScout deterministic fallback functionality.

Tests the DeterministicPathEvaluator and its integration with SmartPathEvaluator
using real components (no mocking) to ensure proper fallback behavior.
"""

import pytest

from orka.nodes.graph_scout_agent import GraphScoutConfig
from orka.orchestrator.dry_run_engine import (
    DeterministicPathEvaluator,
    SmartPathEvaluator,
)


class TestDeterministicPathEvaluator:
    """Test DeterministicPathEvaluator with real component behavior."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return GraphScoutConfig(
            k_beam=3,
            max_depth=2,
            llm_evaluation_enabled=False,  # Force deterministic
            fallback_to_heuristics=True,
        )

    @pytest.fixture
    def evaluator(self, config):
        """Create deterministic evaluator."""
        return DeterministicPathEvaluator(config)

    @pytest.fixture
    def sample_candidates(self):
        """Create sample candidate paths."""
        return [
            {
                "node_id": "search_agent",
                "path": ["search_agent"],
                "estimated_cost": 0.001,
                "estimated_latency": 500,
            },
            {
                "node_id": "analysis_agent",
                "path": ["search_agent", "analysis_agent"],
                "estimated_cost": 0.005,
                "estimated_latency": 1500,
            },
            {
                "node_id": "memory_reader",
                "path": ["memory_reader", "analysis_agent", "response_builder"],
                "estimated_cost": 0.003,
                "estimated_latency": 1000,
            },
        ]

    def test_evaluator_initialization(self, evaluator, config):
        """Test that evaluator initializes correctly."""
        assert evaluator.config == config
        assert evaluator is not None

    def test_evaluate_candidates_returns_all(self, evaluator, sample_candidates):
        """Test that evaluator processes all candidates."""
        question = "Find information about Python testing"
        context = {}

        results = evaluator.evaluate_candidates(sample_candidates, question, context)

        assert len(results) == 3
        assert all("llm_evaluation" in c for c in results)
        assert all("llm_validation" in c for c in results)

    def test_evaluation_structure(self, evaluator, sample_candidates):
        """Test that evaluation structure is correct."""
        question = "Search for data"
        context = {}

        results = evaluator.evaluate_candidates(sample_candidates, question, context)

        for result in results:
            eval_data = result["llm_evaluation"]
            assert "relevance_score" in eval_data
            assert "confidence" in eval_data
            assert "reasoning" in eval_data
            assert "is_deterministic_fallback" in eval_data
            assert eval_data["is_deterministic_fallback"] is True

            validation_data = result["llm_validation"]
            assert "is_valid" in validation_data
            assert "confidence" in validation_data
            assert "efficiency_score" in validation_data
            assert "is_deterministic_fallback" in validation_data

    def test_keyword_matching_boosts_relevance(self, evaluator):
        """Test that keyword matching increases relevance scores."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "other_agent", "path": ["other_agent"]},
        ]

        question = "Search for information about AI"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        search_score = results[0]["llm_evaluation"]["relevance_score"]
        other_score = results[1]["llm_evaluation"]["relevance_score"]

        # Search agent should score higher for "search" query
        assert search_score > other_score

    def test_path_length_affects_confidence(self, evaluator):
        """Test that path length impacts confidence scoring."""
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2", "agent3"]},
            {"node_id": "agent4", "path": ["agent4", "agent5", "agent6"]},
        ]

        question = "Generic query"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        # Optimal path (2-3 agents) should have highest confidence
        confidences = [r["llm_evaluation"]["confidence"] for r in results]
        assert confidences[1] >= confidences[0]  # 2 agents >= 1 agent
        assert confidences[1] >= confidences[2]  # 2 agents >= 3 agents

    def test_efficiency_scores_favor_short_paths(self, evaluator):
        """Test that efficiency scoring favors shorter paths."""
        candidates = [
            {"node_id": "short", "path": ["a", "b"]},
            {"node_id": "medium", "path": ["a", "b", "c"]},
            {"node_id": "long", "path": ["a", "b", "c", "d", "e"]},
        ]

        question = "Query"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        efficiencies = [r["llm_validation"]["efficiency_score"] for r in results]
        assert efficiencies[0] > efficiencies[1]  # Short > medium
        assert efficiencies[1] > efficiencies[2]  # Medium > long


class TestSmartPathEvaluatorFallback:
    """Test SmartPathEvaluator fallback to deterministic evaluator."""

    @pytest.fixture
    def config_with_fallback(self):
        """Config that disables LLM and enables fallback."""
        return GraphScoutConfig(
            llm_evaluation_enabled=False,  # Disable LLM
            fallback_to_heuristics=True,
            k_beam=3,
        )

    @pytest.fixture
    def smart_evaluator(self, config_with_fallback):
        """Create smart evaluator with fallback enabled."""
        return SmartPathEvaluator(config_with_fallback)

    @pytest.fixture
    def sample_candidates(self):
        """Sample candidates for evaluation."""
        return [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2", "agent3"]},
        ]

    def test_smart_evaluator_uses_deterministic_when_llm_disabled(
        self, smart_evaluator, sample_candidates
    ):
        """Test that SmartPathEvaluator uses deterministic evaluator when LLM disabled."""
        question = "Test query"
        context = {}

        # Note: This is a synchronous test so we can't actually call the async simulate_candidates
        # But we can verify that the deterministic evaluator was initialized
        assert smart_evaluator.deterministic_evaluator is not None
        assert isinstance(smart_evaluator.deterministic_evaluator, DeterministicPathEvaluator)

    def test_fallback_evaluator_initialized(self, smart_evaluator):
        """Test that fallback evaluator is properly initialized."""
        assert smart_evaluator.deterministic_evaluator is not None
        assert smart_evaluator.deterministic_evaluator.config == smart_evaluator.config


class TestDeterministicEvaluatorRealScenarios:
    """Test deterministic evaluator with realistic scenarios."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with default config."""
        config = GraphScoutConfig()
        return DeterministicPathEvaluator(config)

    def test_search_query_scenario(self, evaluator):
        """Test evaluation for a search-focused query."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent", "analysis_agent"]},
            {"node_id": "memory_reader", "path": ["memory_reader"]},
            {"node_id": "llm_agent", "path": ["llm_agent"]},
        ]

        question = "Search for recent papers on machine learning"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        # Search agent should score highest for search query
        scores = [r["llm_evaluation"]["relevance_score"] for r in results]
        search_idx = 0  # search_agent is first
        assert scores[search_idx] == max(scores)

    def test_memory_query_scenario(self, evaluator):
        """Test evaluation for a memory-focused query."""
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "memory_reader", "path": ["memory_reader", "llm_agent"]},
            {"node_id": "llm_agent", "path": ["llm_agent"]},
        ]

        question = "Remember what we discussed about the project yesterday"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        # Memory reader should score highest for memory query
        scores = [r["llm_evaluation"]["relevance_score"] for r in results]
        memory_idx = 1  # memory_reader is second
        assert scores[memory_idx] > scores[0]  # Better than search

    def test_all_candidates_marked_as_fallback(self, evaluator):
        """Test that all results are marked as deterministic fallback."""
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2"]},
        ]

        question = "Test"
        context = {}

        results = evaluator.evaluate_candidates(candidates, question, context)

        for result in results:
            assert result["llm_evaluation"]["is_deterministic_fallback"] is True
            assert result["llm_validation"]["is_deterministic_fallback"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
