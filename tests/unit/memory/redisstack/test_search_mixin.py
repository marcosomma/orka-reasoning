# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# Tests for MemorySearchMixin - isolated, mocked, GitHub Actions compatible

import json
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class MockSearchHost:
    """Mock host class that provides required methods for MemorySearchMixin."""

    def __init__(self):
        self.embedder = MagicMock()
        self.embedder.embedding_dim = 384
        self.index_name = "test_index"
        self.vector_params = {}
        self._mock_client = MagicMock()
        self._ensure_index_called = False

    def _get_thread_safe_client(self):
        return self._mock_client

    def _safe_get_redis_value(self, memory_data, key, default=None):
        value = memory_data.get(key, memory_data.get(key.encode("utf-8") if isinstance(key, str) else key, default))
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return default
        return value

    def _get_embedding_sync(self, text):
        return np.zeros(384, dtype=np.float32)

    def _is_expired(self, memory_data):
        return False

    def _get_ttl_info(self, key, memory_data, current_time_ms):
        return {
            "ttl_seconds": -1,
            "ttl_formatted": "N/A",
            "expires_at": None,
            "expires_at_formatted": "N/A",
            "has_expiry": False,
        }

    def _ensure_index(self):
        self._ensure_index_called = True


class TestSearchMixinEscaping:
    """Tests for query escaping methods."""

    def test_escape_redis_search_query(self):
        """_escape_redis_search_query should escape special characters."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Test escaping
        result = host._escape_redis_search_query("test:query")
        assert "\\:" in result

        result = host._escape_redis_search_query("test@user")
        assert "\\@" in result

        result = host._escape_redis_search_query("test-value")
        assert "\\-" in result

    def test_escape_redis_search_query_with_underscores(self):
        """_escape_redis_search_query should optionally escape underscores."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        result = host._escape_redis_search_query("test_id", include_underscores=True)
        assert "\\_" in result

        result = host._escape_redis_search_query("test_id", include_underscores=False)
        assert "\\_" not in result

    def test_escape_redis_search_phrase(self):
        """_escape_redis_search_phrase should escape quote-breaking chars."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        result = host._escape_redis_search_phrase('test "quoted" phrase')
        assert '\\"' in result

        result = host._escape_redis_search_phrase("test\\backslash")
        assert "\\\\" in result

    def test_escape_empty_query(self):
        """Escaping should handle empty strings."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        assert host._escape_redis_search_query("") == ""
        assert host._escape_redis_search_phrase("") == ""


class TestSearchMixinValidation:
    """Tests for score validation."""

    def test_validate_similarity_score_normal(self):
        """_validate_similarity_score should return valid scores unchanged."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        assert host._validate_similarity_score(0.5) == 0.5
        assert host._validate_similarity_score(0.0) == 0.0
        assert host._validate_similarity_score(1.0) == 1.0

    def test_validate_similarity_score_clamp(self):
        """_validate_similarity_score should clamp out-of-range values."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        assert host._validate_similarity_score(1.5) == 1.0
        assert host._validate_similarity_score(-0.5) == 0.0

    def test_validate_similarity_score_nan(self):
        """_validate_similarity_score should handle NaN values."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        assert host._validate_similarity_score(float("nan")) == 0.0
        assert host._validate_similarity_score(float("inf")) == 0.0

    def test_validate_similarity_score_invalid(self):
        """_validate_similarity_score should handle invalid values."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        assert host._validate_similarity_score("invalid") == 0.0
        assert host._validate_similarity_score(None) == 0.0


class TestSearchMixinBasicSearch:
    """Tests for basic Redis search."""

    def test_basic_redis_search_with_results(self):
        """_basic_redis_search should return matching memories."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Setup mock data
        memory_data = {
            "content": "test content with search query",
            "node_id": "agent_1",
            "trace_id": "trace_1",
            "importance_score": "0.8",
            "memory_type": "short_term",
            "timestamp": str(int(time.time() * 1000)),
            "metadata": json.dumps({"log_type": "memory", "category": "stored"}),
        }

        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(return_value=memory_data)

        results = host._basic_redis_search("search", num_results=10)

        assert len(results) == 1
        assert results[0]["content"] == "test content with search query"
        assert results[0]["node_id"] == "agent_1"

    def test_basic_redis_search_no_match(self):
        """_basic_redis_search should return empty for non-matching query."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Setup mock data without matching content
        memory_data = {
            "content": "unrelated content",
            "node_id": "agent_1",
            "trace_id": "trace_1",
            "importance_score": "0.8",
            "memory_type": "short_term",
            "timestamp": str(int(time.time() * 1000)),
            "metadata": json.dumps({"log_type": "memory", "category": "stored"}),
        }

        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(return_value=memory_data)

        results = host._basic_redis_search("specific search term", num_results=10)

        assert len(results) == 0

    def test_basic_redis_search_filters_logs(self):
        """_basic_redis_search should filter by log_type."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Setup mock data as a log (not memory)
        memory_data = {
            "content": "log entry",
            "node_id": "agent_1",
            "trace_id": "trace_1",
            "importance_score": "0.5",
            "memory_type": "short_term",
            "timestamp": str(int(time.time() * 1000)),
            "metadata": json.dumps({"log_type": "log", "category": "log"}),
        }

        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(return_value=memory_data)

        # Should not find when looking for memories
        results = host._basic_redis_search("log", num_results=10, log_type="memory")
        assert len(results) == 0

        # Should find when looking for logs
        results = host._basic_redis_search("log", num_results=10, log_type="log")
        assert len(results) == 1


class TestSearchMixinFallbackSearch:
    """Tests for fallback text search."""

    def test_fallback_text_search_builds_query(self):
        """_fallback_text_search should build correct FT.SEARCH query."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Mock FT.SEARCH to fail so we can verify query building
        mock_ft = MagicMock()
        mock_ft.search = MagicMock(side_effect=Exception("Test"))
        host._mock_client.ft = MagicMock(return_value=mock_ft)
        host._mock_client.keys = MagicMock(return_value=[])

        # Should fall back to basic search
        results = host._fallback_text_search("test query", num_results=10)

        # Verify it tried FT.SEARCH
        host._mock_client.ft.assert_called()


class TestSearchMixinSearchMemories:
    """Tests for main search_memories method."""

    def test_search_memories_no_embedder(self):
        """search_memories should use text search when no embedder."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()
        host.embedder = None
        host._mock_client.keys = MagicMock(return_value=[])

        results = host.search_memories("test query")

        assert isinstance(results, list)

    def test_search_memories_empty_query(self):
        """search_memories should handle empty query."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()
        host._mock_client.keys = MagicMock(return_value=[])

        results = host.search_memories("")

        assert isinstance(results, list)

    def test_search_memories_with_filters(self):
        """search_memories should apply filters correctly."""
        from orka.memory.redisstack.search_mixin import MemorySearchMixin

        class TestHost(MockSearchHost, MemorySearchMixin):
            pass

        host = TestHost()

        # Setup mock with memory that doesn't match filter
        memory_data = {
            "content": "test content",
            "node_id": "agent_2",  # Different from filter
            "trace_id": "trace_1",
            "importance_score": "0.8",
            "memory_type": "short_term",
            "timestamp": str(int(time.time() * 1000)),
            "metadata": json.dumps({"log_type": "memory", "category": "stored"}),
        }

        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(return_value=memory_data)

        # Filter by node_id that doesn't match
        results = host._basic_redis_search("test", num_results=10, node_id="agent_1")

        assert len(results) == 0

