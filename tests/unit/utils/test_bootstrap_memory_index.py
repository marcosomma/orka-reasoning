# Tests for orka.utils.bootstrap_memory_index to increase branch coverage

import asyncio
import math
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import redis

import orka.utils.bootstrap_memory_index as bmi


class DummyDoc:
    def __init__(self, doc_id: str, **attrs):
        self.id = doc_id
        for k, v in attrs.items():
            setattr(self, k, v)


class DummySearchResults:
    def __init__(self, docs):
        self.docs = docs


class DummyFT:
    def __init__(self):
        self._info = {}
        self.created = False
        self.dropped = False
        self._search_results = DummySearchResults([])
        self._raise_on_search: Exception | None = None

    def info(self):
        return self._info

    def create_index(self, *args, **kwargs):
        self.created = True

    def dropindex(self):
        if getattr(self, "raise_drop", None):
            raise Exception("drop failed")
        self.dropped = True

    def search(self, *args, **kwargs):
        if self._raise_on_search:
            raise self._raise_on_search
        return self._search_results


class DummyRedisClient:
    def __init__(self):
        self._fts = {}

    def ft(self, name):
        if name not in self._fts:
            self._fts[name] = DummyFT()
        return self._fts[name]


class TestEnsureMemoryIndex:
    def test_existing_index_returns_true(self):
        client = DummyRedisClient()
        client.ft("idx")._info = {"num_docs": 1}
        assert bmi.ensure_memory_index(client, "idx") is True

    def test_unknown_index_creates(self):
        client = DummyRedisClient()

        class RespErr(redis.ResponseError):
            pass

        def info():
            raise RespErr("Unknown index name")

        client.ft("idx").info = info  # type: ignore[assignment]
        assert bmi.ensure_memory_index(client, "idx") is True
        assert client.ft("idx").created is True

    def test_other_error_returns_false_and_warns(self, caplog):
        client = DummyRedisClient()

        def info():
            raise Exception("unknown command ft.create not supported")

        client.ft("idx").info = info  # type: ignore[assignment]
        out = bmi.ensure_memory_index(client, "idx")
        assert out is False


class TestEnsureEnhancedMemoryIndex:
    def test_vector_not_available_falls_back(self, monkeypatch):
        client = DummyRedisClient()
        # Force flag to False to hit fallback branch
        monkeypatch.setattr(bmi, "VECTOR_SEARCH_AVAILABLE", False)
        called = {"ensure_basic": False}
        monkeypatch.setattr(bmi, "ensure_memory_index", lambda *a, **k: called.__setitem__("ensure_basic", True) or True)
        assert bmi.ensure_enhanced_memory_index(client, "eidx") is True
        assert called["ensure_basic"] is True

    def test_index_exists_with_vector_field_returns_true(self, monkeypatch):
        client = DummyRedisClient()
        monkeypatch.setattr(bmi, "VECTOR_SEARCH_AVAILABLE", True)
        # verify returns exists + vector_field_exists
        monkeypatch.setattr(
            bmi,
            "verify_memory_index",
            lambda c, n: {"exists": True, "vector_field_exists": True, "num_docs": 1, "fields": {}},
        )
        assert bmi.ensure_enhanced_memory_index(client, "eidx") is True

    def test_vector_field_missing_no_recreate_returns_false(self, monkeypatch):
        client = DummyRedisClient()
        monkeypatch.setattr(bmi, "VECTOR_SEARCH_AVAILABLE", True)
        monkeypatch.setattr(
            bmi,
            "verify_memory_index",
            lambda c, n: {"exists": True, "vector_field_exists": False, "fields": {}},
        )
        assert bmi.ensure_enhanced_memory_index(client, "eidx", force_recreate=False) is False

    def test_vector_field_missing_with_recreate_drop_fail(self, monkeypatch):
        client = DummyRedisClient()
        monkeypatch.setattr(bmi, "VECTOR_SEARCH_AVAILABLE", True)
        monkeypatch.setattr(
            bmi,
            "verify_memory_index",
            lambda c, n: {"exists": True, "vector_field_exists": False, "fields": {}},
        )
        client.ft("eidx").raise_drop = True
        assert bmi.ensure_enhanced_memory_index(client, "eidx", force_recreate=True) is False

    def test_index_not_exists_create_success(self, monkeypatch):
        client = DummyRedisClient()
        monkeypatch.setattr(bmi, "VECTOR_SEARCH_AVAILABLE", True)
        monkeypatch.setattr(
            bmi,
            "verify_memory_index",
            lambda c, n: {"exists": False, "vector_field_exists": False, "fields": {}},
        )
        ok = bmi.ensure_enhanced_memory_index(client, "eidx")
        assert ok is True
        assert client.ft("eidx").created is True


class TestHybridVectorSearch:
    def test_non_numpy_vector_early_exit(self):
        client = DummyRedisClient()
        out = bmi.hybrid_vector_search(client, "q", [1, 2, 3])
        assert out == []

    def test_vector_search_success_and_score_handling_and_trace_filter(self):
        client = DummyRedisClient()
        ft = client.ft("orka_enhanced_memory")
        ft._search_results = DummySearchResults([
            DummyDoc("1", content="A", node_id="n1", trace_id="t1", vector_score=0.1),  # distance -> similarity clamped to <=1
            DummyDoc("2", content="B", node_id="n2", trace_id="t1", score=3.0),  # >2 -> 0.0
            DummyDoc("3", content="C", node_id="n3", trace_id="t2", similarity=-0.5),  # negative -> 1.0 then clamped
            DummyDoc("4", content="D", node_id="n4", trace_id="t1"),  # missing score -> 0.0
        ])
        vec = np.ones(4, dtype=np.float32)
        out = bmi.hybrid_vector_search(client, "what", vec, num_results=4, trace_id="t1")
        assert all(r["trace_id"] == "t1" for r in out)
        assert len(out) == 3
        assert all(0.0 <= r["score"] <= 1.0 for r in out)

    def test_vector_search_fallback_to_text(self):
        client = DummyRedisClient()
        ft = client.ft("orka_enhanced_memory")
        ft._search_results = DummySearchResults([
            DummyDoc("5", content="E", node_id="n", trace_id="t")
        ])
        calls = {"i": 0}
        def search_side_effect(*args, **kwargs):
            calls["i"] += 1
            if calls["i"] == 1:
                raise Exception("boom")
            return ft._search_results
        ft.search = search_side_effect  # type: ignore[assignment]
        vec = np.ones(4, dtype=np.float32)

        out = bmi.hybrid_vector_search(client, "hello", vec, num_results=1)
        assert len(out) == 1
        assert out[0]["content"] == "E"


class TestVerifyMemoryIndex:
    def test_verify_parses_attributes_and_handles_errors(self):
        client = DummyRedisClient()
        # Build a fake info attrs list: [name, b"content", type, b"TEXT"] and vector with DIM
        client.ft("idx")._info = {
            "num_docs": 2,
            "attributes": [
                [b"attribute", b"content", b"type", b"TEXT"],
                [b"attribute", b"content_vector", b"type", b"VECTOR", b"ignored", b"DIM", 384],
            ],
        }
        info = bmi.verify_memory_index(client, "idx")
        assert info["exists"] is True
        assert info["vector_field_exists"] is True
        assert info["content_field_exists"] is True
        assert info["vector_field_dim"] == 384

        # Error path
        client.ft("idx").info = lambda: (_ for _ in ()).throw(Exception("fail"))  # type: ignore[assignment]
        info2 = bmi.verify_memory_index(client, "idx")
        assert info2["exists"] is False
        assert "error" in info2


class TestLegacyVectorSearch:
    def test_legacy_search_success_and_filtering(self, monkeypatch):
        client = DummyRedisClient()
        docs = [
            DummyDoc("k1", content="x", session="s1", agent="a1", ts=1, similarity=0.9),
            DummyDoc("k2", content="y", session="s2", agent="a2", ts=2, similarity=0.4),
        ]
        client.ft("memory_idx")._search_results = DummySearchResults(docs)
        out = bmi.legacy_vector_search(client, [0.1, 0.2, 0.3], session="s1", agent="a1", similarity_threshold=0.5, num_results=5)
        assert len(out) == 1
        assert out[0]["key"] == "k1"

    def test_legacy_search_error_returns_empty(self):
        client = DummyRedisClient()
        client.ft("memory_idx")._raise_on_search = Exception("no index")
        out = bmi.legacy_vector_search(client, np.array([1,2,3], dtype=np.float32))
        assert out == []


@pytest.mark.asyncio
class TestRetry:
    async def test_retry_success_first_attempt(self):
        async def op():
            return "ok"
        res = await bmi.retry(op(), attempts=3, backoff=0.01)
        assert res == "ok"

    async def test_retry_invalid_attempts(self):
        with pytest.raises(RuntimeError):
            await bmi.retry(asyncio.sleep(0), attempts=0)

    async def test_retry_raises_when_attempts_one(self):
        class Boom(redis.ConnectionError):
            pass

        async def op():
            raise Boom("conn")

        with pytest.raises(redis.ConnectionError):
            await bmi.retry(op(), attempts=1, backoff=0.01)
