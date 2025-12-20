import types
from unittest.mock import MagicMock

import pytest


def make_fake_pool():
    class FakePool:
        def __init__(self):
            self.max_connections = 42
            # emulate internals some redis versions expose
            self._created_connections = 1
            self._available_connections = [object(), object()]
            self._in_use_connections = [object()]

        @classmethod
        def from_url(cls, *args, **kwargs):
            return cls()

    return FakePool


class FakeRedisClient(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def ping(self):
        return True

    def hset(self, *args, **kwargs):
        return 1

    def expire(self, *args, **kwargs):
        return True


@pytest.mark.parametrize("available_attrs", [True, False])
def test_get_connection_stats_and_cleanup(monkeypatch, available_attrs):
    # Patch ConnectionPool class used in module
    FakePool = make_fake_pool()
    monkeypatch.setattr(
        "orka.memory.redisstack_logger.ConnectionPool", FakePool, raising=True
    )

    # Patch redis.Redis to return a fake client
    monkeypatch.setattr(
        "orka.memory.redisstack_logger.redis.Redis",
        lambda connection_pool=None: FakeRedisClient(),
        raising=True,
    )

    # Patch bootstrap helpers to avoid index creation logic
    import orka.utils.bootstrap_memory_index as bmi

    monkeypatch.setattr(bmi, "verify_memory_index", lambda **kw: {"exists": True, "vector_field_exists": True, "content_field_exists": True, "fields": []})
    monkeypatch.setattr(bmi, "ensure_enhanced_memory_index", lambda **kw: True)

    # Now import the class under test and instantiate
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    # Create instance - should not attempt network due to our patches
    logger = RedisStackMemoryLogger(redis_url="redis://fake:6379/0", index_name="test_idx")

    stats = logger.get_connection_stats()
    assert isinstance(stats, dict)
    assert stats.get("max_connections") == getattr(logger._connection_pool, "max_connections")

    # Add a couple of fake tracked connections to simulate activity
    client1 = FakeRedisClient()
    client2 = FakeRedisClient()
    logger._active_connections.add(client1)
    logger._active_connections.add(client2)

    result = logger.cleanup_connections()
    assert result["status"] == "success"
    assert result["cleared_tracked_connections"] >= 2
import json
from unittest.mock import MagicMock


def make_mock_client():
    mock = MagicMock()

    def hgetall(key):
        return {
            b"content": b"hello",
            b"node_id": b"node1",
            b"trace_id": b"trace1",
            b"importance_score": b"0.75",
            b"memory_type": b"short_term",
            b"timestamp": b"1234567890",
            b"metadata": b'{"log_type": "memory"}',
        }

    mock.hgetall.side_effect = hgetall
    mock.hset.return_value = 1
    mock.hget.return_value = b"val"
    mock.keys.return_value = [b"orka_memory:1"]
    mock.delete.return_value = 1

    class Doc:
        def __init__(self, _id):
            self.id = _id

    class FT:
        def __init__(self):
            self.docs = [Doc("orka_memory:1")]

        def search(self, q):
            ns = MagicMock()
            ns.docs = self.docs
            return ns

    ft = FT()
    mock.ft.return_value = ft

    return mock


def test_search_memories_vector_and_fallback(monkeypatch):
    # import inside test to ensure patched globals from conftest are applied
    import orka.utils.bootstrap_memory_index as bm
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    # Patch bootstrap helpers
    monkeypatch.setattr(bm, "verify_memory_index", lambda *a, **k: {"exists": True, "vector_field_exists": True, "content_field_exists": True, "num_docs": 1, "fields": []})
    monkeypatch.setattr(bm, "ensure_enhanced_memory_index", lambda *a, **k: True)

    # Patch hybrid_vector_search to return one result
    monkeypatch.setattr(bm, "hybrid_vector_search", lambda *a, **k: [{"key": "orka_memory:1", "score": 0.8}])

    # Prepare mock client and patch thread-safe client getter
    mock_client = make_mock_client()

    monkeypatch.setattr(RedisStackMemoryLogger, "_get_thread_safe_client", lambda self: mock_client)

    # Provide a fake embedder so vector search path is taken
    embedder = MagicMock(embedding_dim=384)

    logger = RedisStackMemoryLogger(redis_url="redis://test:6379/0", embedder=embedder)

    results = logger.search_memories("find me", num_results=5)
    assert isinstance(results, list)
    # formatted result should contain content and similarity_score
    if results:
        r = results[0]
        assert "content" in r and "similarity_score" in r


def test_escape_and_validate_helpers():
    from orka.memory.redisstack_logger import RedisStackMemoryLogger
    logger = RedisStackMemoryLogger(redis_url="redis://test:6379/0", embedder=None)

    escaped = logger._escape_redis_search_query("hello:world?{x}")
    assert "\\:" in escaped and "\\?" in escaped

    # Phrase escaping should NOT over-escape punctuation (it is used inside quotes).
    phrase = logger._escape_redis_search_phrase('What is this? "quoted" \\ backslash')
    assert "\\?" not in phrase
    assert '\\"quoted\\"' in phrase
    assert "\\\\" in phrase

    assert logger._validate_similarity_score(0.5) == 0.5
    assert logger._validate_similarity_score(-1) == 0.0
    assert logger._validate_similarity_score(float("nan")) == 0.0
    assert logger._validate_similarity_score("not-a-number") == 0.0


def test_log_memory_and_delete(monkeypatch):
    # Patch ConnectionPool and Redis to avoid real network
    import orka.memory.redisstack_logger as rs_mod
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    monkeypatch.setattr(rs_mod.ConnectionPool, "from_url", lambda *a, **k: object())

    mock_client = make_mock_client()
    monkeypatch.setattr(rs_mod.redis, "Redis", lambda *a, **k: mock_client)

    # Patch bootstrap helpers to be no-op
    import orka.utils.bootstrap_memory_index as bm
    monkeypatch.setattr(bm, "ensure_enhanced_memory_index", lambda *a, **k: True)
    monkeypatch.setattr(bm, "verify_memory_index", lambda *a, **k: {"exists": True, "vector_field_exists": True, "content_field_exists": True, "fields": []})

    logger = RedisStackMemoryLogger(redis_url="redis://test:6379/0", embedder=None)

    mid = logger.log_memory("content", "node1", "trace1", metadata={"log_type": "memory"}, importance_score=0.5)
    assert isinstance(mid, str)

    # delete by pattern should call client.delete via wrappers (clear_all_memories uses keys+delete)
    logger.clear_all_memories()
    # since our mock delete returns 1, ensure the underlying client.delete was invoked
    assert mock_client.delete.called
