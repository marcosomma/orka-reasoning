# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
"""Tests for MetricsMixin - statistics and performance metrics."""

import json
from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack.metrics_mixin import MetricsMixin


class MockMetricsLogger(MetricsMixin):
    """Mock class to test MetricsMixin."""

    def __init__(self):
        self.mock_client = MagicMock()
        self.index_name = "test_index"
        self.embedder = None
        self.memory_decay_config = {"enabled": True}

    def _get_thread_safe_client(self):
        return self.mock_client

    def _is_expired(self, memory_data):
        return False

    def _safe_get_redis_value(self, memory_data, key, default=None):
        value = memory_data.get(key, memory_data.get(key.encode("utf-8"), default))
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    def get_recent_stored_memories(self, count=5):
        return []


class TestMetricsMixinStats:
    """Tests for get_memory_stats method."""

    def test_get_memory_stats_empty(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.return_value = []

        result = logger.get_memory_stats()

        assert result["total_entries"] == 0
        assert result["active_entries"] == 0
        assert result["backend"] == "redisstack"
        assert result["index_name"] == "test_index"

    def test_get_memory_stats_with_entries(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:a", b"orka_memory:b"]
        logger.mock_client.hgetall.return_value = {
            b"memory_type": b"short_term",
            b"metadata": b'{"log_type": "memory", "category": "stored"}',
        }

        result = logger.get_memory_stats()

        assert result["total_entries"] == 2
        assert result["vector_search_enabled"] is False
        assert result["decay_enabled"] is True

    def test_get_memory_stats_error_handling(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.side_effect = Exception("Redis error")

        result = logger.get_memory_stats()

        assert "error" in result


class TestMetricsMixinPerformance:
    """Tests for get_performance_metrics method."""

    def test_get_performance_metrics_basic(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.return_value = []
        logger.mock_client.ft.return_value.info.return_value = {
            "num_docs": 0,
            "indexing": False,
            "percent_indexed": 100,
        }

        result = logger.get_performance_metrics()

        assert result["vector_search_enabled"] is False
        assert result["index_status"]["status"] == "available"

    def test_get_performance_metrics_with_embedder(self):
        logger = MockMetricsLogger()
        logger.embedder = MagicMock()
        logger.embedder.model_name = "test-model"
        logger.embedder.embedding_dim = 384
        logger.mock_client.keys.return_value = []
        logger.mock_client.ft.return_value.info.return_value = {}

        result = logger.get_performance_metrics()

        assert result["vector_search_enabled"] is True
        assert result["embedder_model"] == "test-model"
        assert result["embedding_dimension"] == 384

    def test_get_performance_metrics_index_unavailable(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.return_value = []
        logger.mock_client.ft.return_value.info.side_effect = Exception("No index")

        result = logger.get_performance_metrics()

        assert result["index_status"]["status"] == "unavailable"

    def test_get_performance_metrics_namespace_distribution(self):
        logger = MockMetricsLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:a"]
        logger.mock_client.hgetall.return_value = {b"trace_id": b"trace_123"}
        logger.mock_client.ft.return_value.info.side_effect = Exception("No index")

        result = logger.get_performance_metrics()

        assert "namespace_distribution" in result
        assert result["namespace_distribution"].get("trace_123", 0) >= 0

    def test_get_performance_metrics_error(self):
        logger = MockMetricsLogger()
        # Make the initial metrics dictionary creation fail
        logger.embedder = MagicMock()
        type(logger.embedder).model_name = property(
            lambda self: (_ for _ in ()).throw(Exception("Fatal error"))
        )

        result = logger.get_performance_metrics()

        assert "error" in result

