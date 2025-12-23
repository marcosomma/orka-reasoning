# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Unit tests for SearchMethodsMixin (memory_reader).

These tests exercise vector, keyword, hybrid and stream search paths
and the legacy wrappers, targeting >=80% coverage for the module.
"""

import asyncio
import json
import time
from typing import Any, List

import numpy as np
import pytest

from orka.nodes.memory_reader.search_methods import SearchMethodsMixin


class DummyEmbedder:
    """Minimal async embedder stub returning deterministic vectors."""

    def __init__(self):
        self.last_text: str | None = None

    async def encode(self, text: str):
        self.last_text = text
        # Produce a simple deterministic vector from the text length
        n = max(1, min(4, len(text) % 5))
        vec = np.zeros(4, dtype=float)
        vec[:n] = 1.0
        return vec


class FakeRedisClient:
    """Async subset of Redis used in tests (xrange only)."""

    def __init__(self, entries: list[tuple[bytes, dict[bytes, bytes]]]):
        self._entries = entries

    async def xrange(self, stream_name: str, count: int):  # noqa: D401 - simple stub
        # stream_name is ignored in the stub; return up to count entries
        return self._entries[:count]


class FakeMemoryLogger:
    """Async memory logger stub used by Search methods."""

    def __init__(self):
        self._memories: List[dict[str, Any]] = []
        self.redis: Any = None
        self.raise_on_search: bool = False

    def set_memories(self, memories: List[dict[str, Any]]):
        self._memories = list(memories)

    def set_stream_entries(self, entries: list[tuple[bytes, dict[bytes, bytes]]]):
        self.redis = FakeRedisClient(entries)

    async def search_memories(self, query: str | None = None, namespace: str | None = None, limit: int = 10):  # noqa: D401 - simple stub
        if self.raise_on_search:
            raise RuntimeError("search error")
        # Ignore query/namespace for unit tests; just return up to limit
        # Ensure we return a shallow copy so tests can modify safely
        return [dict(m) for m in self._memories[:limit]]


class ConcreteSearchHost(SearchMethodsMixin):
    """Concrete class mixing in SearchMethodsMixin for testing."""

    def __init__(self):
        self.memory_logger = FakeMemoryLogger()
        self.embedder = DummyEmbedder()
        self.limit = 3
        self.similarity_threshold = 0.2
        self.context_weight = 0.5
        self.enable_context_search = True
        self.enable_temporal_ranking = False


@pytest.mark.asyncio
class TestGenerateContextVector:
    async def test_generate_context_vector_uses_last_three(self):
        host = ConcreteSearchHost()
        ctx = [
            {"content": "c1"},
            {"content": "c2"},
            {"content": "c3"},
            {"content": "c4"},
        ]
        vec = await host._generate_context_vector(ctx)
        assert isinstance(vec, np.ndarray)
        # The embedder must have received the concatenation of the last 3 items
        assert host.embedder.last_text == "c2 c3 c4"

    async def test_generate_context_vector_empty(self):
        host = ConcreteSearchHost()
        assert await host._generate_context_vector([]) is None


@pytest.mark.asyncio
class TestContextAwareVectorSearch:
    async def test_context_vector_search_filters_and_sorts(self):
        host = ConcreteSearchHost()
        # Query embedding points towards the first axis
        query_vec = np.array([1.0, 0.0, 0.0, 0.0])

        # Memories with different vectors and contents
        host.memory_logger.set_memories(
            [
                {"id": "m1", "content": "hello alpha", "vector": [1.0, 0.0, 0.0, 0.0]},
                {"id": "m2", "content": "hello beta", "vector": [0.7, 0.7, 0.0, 0.0]},
                {"id": "m3", "content": "gamma", "vector": [0.0, 1.0, 0.0, 0.0]},
                {"id": "m4", "content": "no vector here"},
            ]
        )

        # Provide conversation context to enable context-weighted score
        conversation_context = [{"content": "alpha context"}]

        res = await host._context_aware_vector_search(
            query_embedding=query_vec,
            namespace="ns",
            conversation_context=conversation_context,
            threshold=0.0,
        )

        # Should include at most limit items and be sorted by similarity desc
        assert 1 <= len(res) <= host.limit
        assert all(r["match_type"] == "context_aware_vector" for r in res)
        sims = [r["similarity"] for r in res]
        assert sims == sorted(sims, reverse=True)

    async def test_context_vector_search_no_memory_logger(self):
        host = ConcreteSearchHost()
        host.memory_logger = None  # type: ignore[assignment]
        out = await host._context_aware_vector_search(np.ones(4), "ns", [], 0.5)
        assert out == []


@pytest.mark.asyncio
class TestEnhancedKeywordSearch:
    async def test_keyword_search_with_and_without_context(self):
        host = ConcreteSearchHost()
        # Three simple memories, metadata absent on one to test normalization
        host.memory_logger.set_memories(
            [
                {"content": "hello world", "metadata": {"tag": 1}},
                {"content": "world of code"},
                {"content": "completely different"},
            ]
        )

        # Without context: similarity equals query overlap
        res_no_ctx = await host._enhanced_keyword_search(
            namespace="ns",
            query="hello world",
            conversation_context=None,
        )
        assert len(res_no_ctx) >= 1
        assert all("similarity" in r for r in res_no_ctx)
        # The first result should contain both words
        assert res_no_ctx[0]["similarity"] >= 1.0
        assert isinstance(res_no_ctx[1]["metadata"], dict)

        # With context: similarity blends query and context overlap
        res_ctx = await host._enhanced_keyword_search(
            namespace="ns",
            query="hello",
            conversation_context=[{"content": "extra world context"}],
        )
        assert len(res_ctx) >= 1
        assert all("similarity" in r for r in res_ctx)

    async def test_keyword_search_handles_logger_errors(self):
        host = ConcreteSearchHost()
        host.memory_logger.raise_on_search = True
        out = await host._enhanced_keyword_search(namespace="ns", query="q")
        assert out == []


@pytest.mark.asyncio
class TestStreamSearch:
    async def test_context_aware_stream_search(self):
        host = ConcreteSearchHost()
        # Build two valid entries and one malformed JSON, ensure bytes payload
        now = str(int(time.time())).encode("utf-8")
        valid1 = (
            b"1-0",
            {
                b"payload": json.dumps({"content": "hello stream", "metadata": {"a": 1}}).encode(
                    "utf-8"
                ),
                b"ts": now,
            },
        )
        valid2 = (
            b"2-0",
            {
                b"payload": json.dumps({"content": "stream world", "metadata": {"b": 2}}).encode(
                    "utf-8"
                ),
                b"ts": now,
            },
        )
        bad = (b"3-0", {b"payload": b"{not json}", b"ts": now})

        host.memory_logger.set_stream_entries([valid1, valid2, bad])

        out = await host._context_aware_stream_search(
            stream_name="mystream",
            query="hello world",
            query_embedding=np.array([1.0, 0.0, 0.0, 0.0]),
            conversation_context=None,
            threshold=0.0,
        )

        # Malformed entry should be skipped; only 2 results
        assert len(out) == 2
        assert all(r["match_type"] == "context_aware_stream" for r in out)
        assert all("entry_id" in r for r in out)

    async def test_stream_search_handles_missing_logger_or_redis(self):
        host = ConcreteSearchHost()
        # Missing logger
        host.memory_logger = None  # type: ignore[assignment]
        out = await host._context_aware_stream_search(
            stream_name="s",
            query="q",
            query_embedding=np.ones(4),
        )
        assert out == []

        # Logger without redis
        host = ConcreteSearchHost()
        out = await host._context_aware_stream_search(
            stream_name="s",
            query="q",
            query_embedding=np.ones(4),
        )
        assert out == []


@pytest.mark.asyncio
class TestLegacyWrappers:
    async def test_vector_keyword_and_stream_legacy(self):
        host = ConcreteSearchHost()
        # Fill memories and stream to exercise legacy wrappers
        host.memory_logger.set_memories(
            [
                {"content": "hello world", "vector": [1.0, 0.0, 0.0, 0.0]},
                {"content": "other", "vector": [0.0, 1.0, 0.0, 0.0]},
            ]
        )
        host.memory_logger.set_stream_entries(
            [
                (
                    b"1-0",
                    {b"payload": json.dumps({"content": "hello"}).encode("utf-8"), b"ts": b"0"},
                )
            ]
        )

        # Lower threshold so legacy wrapper returns results even if similarities are 0
        host.similarity_threshold = 0.0
        vec_res = await host._vector_search(np.array([1.0, 0.0, 0.0, 0.0]), namespace="ns")
        key_res = await host._keyword_search(query="hello", namespace="ns")
        stream_res = await host._stream_search(
            stream_key="s",
            query="hello",
            query_embedding=np.array([1.0, 0.0, 0.0, 0.0]),
            threshold=0.0,
        )

        assert len(vec_res) >= 1
        assert len(key_res) >= 1
        assert len(stream_res) >= 1
