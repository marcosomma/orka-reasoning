# OrKa: Orchestrator Kit Agents
# Additional coverage for MemorySearchMixin

import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class MockSearchHost:
    """Mock host class that provides required methods for MemorySearchMixin."""

    def __init__(self):
        self.embedder = object()  # truthy; _get_embedding_sync provides the vector
        self.index_name = "test_index"
        self.vector_params = {}
        self._mock_client = MagicMock()
        self._ensure_index_called = False

    def _get_thread_safe_client(self):
        return self._mock_client

    def _safe_get_redis_value(self, memory_data, key, default=None):
        # Allow both str and bytes keys in memory_data
        value = memory_data.get(key, memory_data.get(key.encode("utf-8") if isinstance(key, str) else key, default))
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except Exception:
                return default
        return value

    def _get_embedding_sync(self, text):
        # Deterministic embedding vector
        return np.ones(4, dtype=np.float32)

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


@pytest.fixture
def host_cls():
    from orka.memory.redisstack.search_mixin import MemorySearchMixin

    class TestHost(MockSearchHost, MemorySearchMixin):
        pass

    return TestHost


class DummyDoc:
    def __init__(self, doc_id: str):
        self.id = doc_id


@pytest.mark.unit
class TestVectorSearchFlow:
    def test_vector_search_happy_path(self, host_cls):
        host = host_cls()

        # Prepare redis client hgetall data
        memory_data = {
            "content": "hello world",
            "node_id": "n1",
            "trace_id": "t1",
            "importance_score": "0.7",
            "memory_type": "short",
            "timestamp": str(int(time.time() * 1000)),
            "metadata": json.dumps({"log_type": "memory", "category": "stored", "namespace": "ns"}),
        }
        host._mock_client.hgetall = MagicMock(side_effect=lambda k: memory_data if (k == "orka_memory:1" or k == b"orka_memory:1") else None)

        with patch("orka.utils.bootstrap_memory_index.verify_memory_index", return_value={"exists": True, "vector_field_exists": True, "num_docs": 1}), \
             patch("orka.utils.bootstrap_memory_index.hybrid_vector_search", return_value=[{"key": "orka_memory:1", "score": 0.8}, {"key": "orka_memory:missing", "score": float('nan')}]):
            results = host.search_memories(
                query="hello",
                num_results=5,
                node_id="n1",
                memory_type="short",
                min_importance=0.1,
                log_type="memory",
                namespace="ns",
            )

        assert len(results) == 1
        r = results[0]
        assert r["content"] == "hello world"
        assert 0.0 <= r["similarity_score"] <= 1.0
        assert host._ensure_index_called is False

    def test_vector_search_index_missing_then_fallback(self, host_cls, monkeypatch):
        host = host_cls()

        # Force verify to report missing index twice
        verify_calls = iter([
            {"exists": False, "vector_field_exists": False, "num_docs": 0},
        ])

        monkeypatch.setattr(
            "orka.utils.bootstrap_memory_index.verify_memory_index",
            lambda client, index_name: next(verify_calls, {"exists": False, "vector_field_exists": False, "num_docs": 0}),
        )
        monkeypatch.setattr(
            host,
            "_fallback_text_search",
            lambda query, num_results, trace_id, node_id, memory_type, min_importance, log_type, namespace: [{"content": "fallback"}],
        )

        results = host.search_memories("hello")
        assert results and results[0]["content"] == "fallback"
        assert host._ensure_index_called is True

    def test_vector_field_missing_recreate_still_missing(self, host_cls, monkeypatch):
        host = host_cls()

        # First says exists but missing vector field; after ensure_index still missing
        calls = iter([
            {"exists": True, "vector_field_exists": False, "num_docs": 1},
            {"exists": True, "vector_field_exists": False, "num_docs": 1},
        ])

        monkeypatch.setattr(
            "orka.utils.bootstrap_memory_index.verify_memory_index",
            lambda client, index_name: next(calls),
        )
        monkeypatch.setattr(
            host,
            "_fallback_text_search",
            lambda *args, **kwargs: [{"content": "fallback2"}],
        )

        results = host.search_memories("hello")
        assert results and results[0]["content"] == "fallback2"
        assert host._ensure_index_called is True

    def test_vector_search_exception_goes_to_fallback(self, host_cls, monkeypatch):
        host = host_cls()

        def raise_err(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr("orka.utils.bootstrap_memory_index.verify_memory_index", raise_err)
        monkeypatch.setattr(host, "_fallback_text_search", lambda *args, **kwargs: [{"content": "fb"}])

        out = host.search_memories("hello")
        assert out and out[0]["content"] == "fb"


@pytest.mark.unit
class TestProcessResultsAndFallback:
    def test_process_search_results_filters(self, host_cls):
        host = host_cls()
        # Mock client to return memory that should be filtered out by namespace
        memory_data = {
            "content": "c",
            "node_id": "n",
            "trace_id": "t",
            "importance_score": "1.0",
            "memory_type": "short",
            "timestamp": "0",
            "metadata": json.dumps({"log_type": "memory", "category": "stored", "namespace": "wrong"}),
        }
        host._mock_client.hgetall = MagicMock(return_value=memory_data)

        results = host._process_search_results(
            results=[{"key": "orka_memory:1", "score": 2.0}],
            node_id=None,
            memory_type=None,
            min_importance=None,
            log_type="memory",
            namespace="ns",
        )
        assert results == []

        # Now allow namespace and forbid memory under log type
        memory_data["metadata"] = json.dumps({"log_type": "memory", "category": "stored", "namespace": "ns"})
        results = host._process_search_results(
            results=[{"key": "orka_memory:1", "score": 2.0}],
            node_id=None,
            memory_type=None,
            min_importance=None,
            log_type="log",
            namespace="ns",
        )
        assert results == []

        # Allow as memory and ensure score is clamped within [0,1]
        results = host._process_search_results(
            results=[{"key": "orka_memory:1", "score": 10}],
            node_id=None,
            memory_type=None,
            min_importance=None,
            log_type="memory",
            namespace="ns",
        )
        assert len(results) == 1
        assert 0.0 <= results[0]["similarity_score"] <= 1.0

    def test_fallback_text_search_success_and_parse_metadata_error(self, host_cls):
        host = host_cls()

        # Prepare docs
        docs = [DummyDoc("orka_memory:1"), DummyDoc("orka_memory:2")]
        search_results = SimpleNamespace(docs=docs)

        # ft(index).search should return our search_results
        mock_ft = MagicMock()
        mock_ft.search = MagicMock(return_value=search_results)
        host._mock_client.ft = MagicMock(return_value=mock_ft)

        # First memory has valid metadata; second has malformed to hit exception path
        good_md = json.dumps({"log_type": "memory", "category": "stored", "namespace": "ns"})
        bad_md = "{not-json}"

        mem_by_id = {
            "orka_memory:1": {
                "content": "A",
                "node_id": "n",
                "trace_id": "t",
                "importance_score": "0.3",
                "memory_type": "short",
                "timestamp": "0",
                "metadata": good_md,
            },
            "orka_memory:2": {
                "content": "B",
                "node_id": "n",
                "trace_id": "t",
                "importance_score": "0.4",
                "memory_type": "short",
                "timestamp": "0",
                "metadata": bad_md,
            },
        }
        host._mock_client.hgetall = MagicMock(side_effect=lambda k: mem_by_id[k])

        results = host._fallback_text_search(
            query="hello",
            num_results=10,
            log_type="memory",
            namespace="ns",
        )

        # Second doc has malformed metadata and should be filtered when log_type=="memory"
        assert len(results) == 1
        assert results[0]["content"] == "A"
        assert results[0].get("similarity_score") == 0.5

    def test_basic_search_more_filters(self, host_cls):
        host = host_cls()

        now_ms = str(int(time.time() * 1000))
        # Two keys, bytes and str to cover decoding
        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1", "orka_memory:2"])

        all_data = {
            b"orka_memory:1": {
                "content": "contains term",
                "node_id": "n",
                "trace_id": "t",
                "importance_score": "0.9",
                "memory_type": "short",
                "timestamp": now_ms,
                "metadata": json.dumps({"log_type": "memory", "category": "stored", "namespace": "ns"}),
            },
            "orka_memory:2": {
                "content": "no match",
                "node_id": "n2",
                "trace_id": "t2",
                "importance_score": "0.1",
                "memory_type": "short",
                "timestamp": now_ms,
                "metadata": json.dumps({"log_type": "memory", "category": "stored", "namespace": "other"}),
            },
        }
        host._mock_client.hgetall = MagicMock(side_effect=lambda k: all_data.get(k))

        # Apply multiple filters to include only first
        out = host._basic_redis_search(
            query="term",
            num_results=10,
            trace_id="t",
            node_id="n",
            memory_type="short",
            min_importance=0.5,
            log_type="memory",
            namespace="ns",
        )
        assert len(out) == 1
        assert out[0]["content"] == "contains term"

    def test_vector_zero_results_triggers_fallback(self, host_cls, monkeypatch):
        host = host_cls()

        monkeypatch.setattr(
            "orka.utils.bootstrap_memory_index.verify_memory_index",
            lambda *args, **kwargs: {"exists": True, "vector_field_exists": True, "num_docs": 0},
        )
        monkeypatch.setattr(
            "orka.utils.bootstrap_memory_index.hybrid_vector_search",
            lambda **kwargs: [],
        )
        monkeypatch.setattr(host, "_fallback_text_search", lambda *args, **kwargs: [{"content": "fb3"}])

        out = host.search_memories("hello")
        assert out and out[0]["content"] == "fb3"
