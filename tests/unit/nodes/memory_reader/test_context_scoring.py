# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for ContextScoringMixin."""

import pytest
import time

from orka.nodes.memory_reader.context_scoring import ContextScoringMixin


class ConcreteContextScoring(ContextScoringMixin):
    """Concrete implementation for testing."""

    def __init__(self):
        self.context_weight = 0.2
        self.temporal_decay_hours = 24.0
        self.temporal_weight = 0.1
        self.context_window_size = 10
        self.use_hnsw = True
        self.hybrid_search_enabled = True
        self.ef_runtime = 10
        self.similarity_threshold = 0.7
        self._search_metrics = {
            "hnsw_searches": 0,
            "legacy_searches": 0,
            "total_results_found": 0,
            "average_search_time": 0.0,
        }


class TestContextScoringMixin:
    """Tests for ContextScoringMixin."""

    @pytest.fixture
    def scorer(self):
        return ConcreteContextScoring()

    def test_enhance_with_context_scoring_empty_context(self, scorer):
        """Test enhancement with empty context."""
        results = [{"content": "test content", "similarity_score": 0.5}]
        enhanced = scorer._enhance_with_context_scoring(results, [])
        assert enhanced == results

    def test_enhance_with_context_scoring(self, scorer):
        """Test enhancement with context."""
        results = [{"content": "hello world test", "similarity_score": 0.5}]
        context = [{"content": "hello there friend"}]

        enhanced = scorer._enhance_with_context_scoring(results, context)

        assert enhanced[0]["context_score"] >= 0
        assert "original_similarity" in enhanced[0]

    def test_apply_temporal_ranking(self, scorer):
        """Test temporal ranking application."""
        current_time = time.time()
        results = [
            {"content": "recent", "similarity_score": 0.5, "timestamp": current_time - 3600},
            {"content": "old", "similarity_score": 0.5, "timestamp": current_time - 86400},
        ]

        ranked = scorer._apply_temporal_ranking(results)

        # Recent item should have higher score
        assert ranked[0]["similarity_score"] >= ranked[1]["similarity_score"]

    def test_apply_temporal_ranking_no_timestamp(self, scorer):
        """Test temporal ranking with no timestamp."""
        results = [{"content": "test", "similarity_score": 0.5}]
        ranked = scorer._apply_temporal_ranking(results)
        assert ranked[0]["similarity_score"] == 0.5

    def test_update_search_metrics(self, scorer):
        """Test search metrics update."""
        scorer._search_metrics["hnsw_searches"] = 1
        scorer._update_search_metrics(0.1, 5)

        assert scorer._search_metrics["average_search_time"] == 0.1
        assert scorer._search_metrics["total_results_found"] == 5

    def test_update_search_metrics_exponential_average(self, scorer):
        """Test exponential moving average."""
        scorer._search_metrics["hnsw_searches"] = 5
        scorer._search_metrics["legacy_searches"] = 5
        scorer._search_metrics["average_search_time"] = 0.2
        scorer._update_search_metrics(0.1, 5)

        # Should be between 0.1 and 0.2
        assert 0.1 < scorer._search_metrics["average_search_time"] < 0.2

    def test_get_search_metrics(self, scorer):
        """Test getting search metrics."""
        metrics = scorer.get_search_metrics()

        assert "hnsw_enabled" in metrics
        assert "hybrid_search_enabled" in metrics
        assert "ef_runtime" in metrics
        assert "similarity_threshold" in metrics

    def test_extract_conversation_context(self, scorer):
        """Test extracting conversation context."""
        context = {
            "previous_outputs": {
                "agent1": {"response": "Hello there"},
                "agent2": "Direct output",
            }
        }

        extracted = scorer._extract_conversation_context(context)

        assert len(extracted) == 2

    def test_extract_conversation_context_limit(self, scorer):
        """Test context window size limit."""
        scorer.context_window_size = 2
        context = {
            "previous_outputs": {
                "agent1": {"response": "One"},
                "agent2": {"response": "Two"},
                "agent3": {"response": "Three"},
            }
        }

        extracted = scorer._extract_conversation_context(context)

        assert len(extracted) <= 2

