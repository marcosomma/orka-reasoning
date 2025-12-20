# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for CostAnalysisMixin."""

import pytest

from orka.memory.base_logger_mixins.cost_analysis_mixin import CostAnalysisMixin


class ConcreteCostAnalysis(CostAnalysisMixin):
    """Concrete implementation for testing."""

    def __init__(self):
        self._blob_store = {}
        self._blob_threshold = 200

    def _deduplicate_dict_content(self, data):
        return data

    def save_to_file(self, file_path):
        pass


class TestCostAnalysisMixin:
    """Tests for CostAnalysisMixin."""

    @pytest.fixture
    def analyzer(self):
        return ConcreteCostAnalysis()

    def test_extract_cost_analysis_empty(self, analyzer):
        """Test cost analysis with no events."""
        result = analyzer._extract_cost_analysis({}, [])

        assert "summary" in result
        assert result["summary"]["total_agents"] == 0

    def test_extract_cost_analysis_with_metrics(self, analyzer):
        """Test cost analysis with agent metrics."""
        events = [
            {
                "agent_id": "agent1",
                "event_type": "LLMAgent",
                "payload": {
                    "_metrics": {
                        "tokens": 100,
                        "prompt_tokens": 60,
                        "completion_tokens": 40,
                        "cost_usd": 0.01,
                        "latency_ms": 500,
                        "model": "gpt-4",
                        "provider": "openai",
                    }
                },
            }
        ]
        result = analyzer._extract_cost_analysis({}, events)

        assert result["summary"]["total_agents"] == 1
        assert result["summary"]["total_tokens"] == 100
        assert "agent1" in result["agents"]
        assert "gpt-4" in result["by_model"]
        assert "openai" in result["by_provider"]

    def test_extract_cost_analysis_aggregation(self, analyzer):
        """Test cost aggregation across multiple agents."""
        events = [
            {
                "agent_id": "agent1",
                "event_type": "LLMAgent",
                "payload": {"_metrics": {"tokens": 50, "cost_usd": 0.01}},
            },
            {
                "agent_id": "agent2",
                "event_type": "LLMAgent",
                "payload": {"_metrics": {"tokens": 100, "cost_usd": 0.02}},
            },
        ]
        result = analyzer._extract_cost_analysis({}, events)

        assert result["summary"]["total_tokens"] == 150
        assert result["summary"]["total_cost_usd"] == 0.03

    def test_extract_agent_metrics_direct(self, analyzer):
        """Test direct metrics extraction."""
        event = {"payload": {"_metrics": {"tokens": 100}}}
        result = analyzer._extract_agent_metrics(event, {})

        assert result["tokens"] == 100

    def test_extract_agent_metrics_blob_reference(self, analyzer):
        """Test metrics extraction from blob reference."""
        analyzer._blob_store["hash123"] = {"_metrics": {"tokens": 200}}
        event = {"payload": {"_type": "blob_reference", "ref": "hash123"}}
        result = analyzer._extract_agent_metrics(event, {})

        assert result["tokens"] == 200

    def test_extract_metrics_recursive(self, analyzer):
        """Test recursive metrics extraction."""
        data = {"nested": {"_metrics": {"tokens": 50, "latency_ms": 100}}}
        metrics = {}
        analyzer._extract_metrics_recursive(data, metrics)

        assert metrics["tokens"] == 50
        assert metrics["latency_ms"] == 100

    def test_extract_metrics_recursive_depth_limit(self, analyzer):
        """Test depth limit in recursive extraction."""
        # Create deeply nested structure
        data = {"level": {}}
        current = data["level"]
        for i in range(15):
            current["nested"] = {}
            current = current["nested"]
        current["_metrics"] = {"tokens": 100}

        metrics = {}
        analyzer._extract_metrics_recursive(data, metrics, max_depth=5)

        # Should not find deeply nested metrics
        assert "tokens" not in metrics

    def test_extract_metrics_recursive_list(self, analyzer):
        """Test metrics extraction from lists."""
        data = {"items": [{"_metrics": {"tokens": 10}}, {"_metrics": {"tokens": 20}}]}
        metrics = {}
        analyzer._extract_metrics_recursive(data, metrics)

        assert metrics["tokens"] == 30

