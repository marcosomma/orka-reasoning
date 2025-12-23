# Additional branch coverage tests for RedisStackMemoryLogger

import json
from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack_logger import RedisStackMemoryLogger


@pytest.fixture(autouse=True)
def patch_index(monkeypatch):
    # Avoid heavy index setup during init in these tests
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", lambda self: None)


def make_logger(monkeypatch):
    # Keep ConnectionPool.from_url from touching network
    import orka.memory.redisstack_logger as rs_mod

    monkeypatch.setattr(rs_mod.ConnectionPool, "from_url", lambda *a, **k: MagicMock())
    # Stub connection manager get_thread_safe_client by default when needed in tests
    return RedisStackMemoryLogger(redis_url="redis://fake:6379/0")


def test_get_redis_client_lazy_init(monkeypatch):
    logger = make_logger(monkeypatch)

    calls = {"n": 0}
    mock_client = object()

    # Replace underlying conn mgr to observe get_client usage
    class DummyMgr:
        def get_client(self):
            calls["n"] += 1
            return mock_client
    logger._conn_mgr = DummyMgr()  # type: ignore[assignment]
    logger.redis_client = None
    logger._client_initialized = False

    c1 = logger._get_redis_client()
    c2 = logger._get_redis_client()

    assert c1 is mock_client and c2 is mock_client
    assert calls["n"] == 1  # only first call should initialize


def test_ensure_index_error_branch(monkeypatch):
    logger = make_logger(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("fail")

    monkeypatch.setattr(logger, "_ensure_index", boom)
    ok = logger.ensure_index()
    assert ok is False


def test_log_memory_serialization_error_and_embedding_warning(monkeypatch, caplog):
    logger = make_logger(monkeypatch)

    # Thread-safe client mock capturing hset/expire
    class Client:
        def __init__(self):
            self.hset_calls = []
            self.expire_calls = []
        def hset(self, key, mapping):
            self.hset_calls.append((key, mapping))
            return 1
        def expire(self, key, ttl):
            self.expire_calls.append((key, ttl))
            return True
    client = Client()
    monkeypatch.setattr(logger, "_get_thread_safe_client", lambda: client)

    # Force embedder path with error inside embedding
    logger.embedder = object()
    monkeypatch.setattr(logger, "_get_embedding_sync", lambda c: (_ for _ in ()).throw(RuntimeError("emb_fail")))

    # metadata not JSON-serializable triggers serialization error branch
    key = logger.log_memory(content={"x": 1}, node_id="n", trace_id="t", metadata={"s": set([1])}, expiry_hours=0.001)

    assert isinstance(key, str)
    assert client.hset_calls
    _, mapping = client.hset_calls[0]
    # metadata rewritten to error structure
    md = json.loads(mapping["metadata"]) if isinstance(mapping["metadata"], (bytes, str)) else {}
    assert md.get("error") == "serialization_failed"
    # expire should be scheduled
    assert client.expire_calls


def test_log_memory_no_embedder_and_no_expiry(monkeypatch):
    logger = make_logger(monkeypatch)

    class Client:
        def __init__(self):
            self.hset_called = False
            self.expire_called = False
        def hset(self, *a, **k):
            self.hset_called = True
            return 1
        def expire(self, *a, **k):
            self.expire_called = True
            return True
    client = Client()
    monkeypatch.setattr(logger, "_get_thread_safe_client", lambda: client)

    logger.embedder = None  # skip embedding
    k = logger.log_memory("text", "node", "trace", metadata={})
    assert isinstance(k, str)
    assert client.hset_called is True
    # no expiry
    assert client.expire_called is False


def test_cleanup_expired_memories_branches(monkeypatch):
    logger = make_logger(monkeypatch)

    # Branch: not ready (no pool)
    logger._connection_pool = None  # type: ignore[assignment]
    res = logger.cleanup_expired_memories()
    assert res["cleanup_type"] == "redisstack_not_ready"

    # Branch: connection failed
    logger._connection_pool = object()  # type: ignore[assignment]
    monkeypatch.setattr(logger, "_get_thread_safe_client", lambda: (_ for _ in ()).throw(RuntimeError("conn")))
    res = logger.cleanup_expired_memories()
    assert res["cleanup_type"] == "redisstack_connection_failed"

    # Branch: dry run with expired items
    class Client:
        def __init__(self):
            self._keys = [b"k1", b"k2"]
            self.deleted = []
        def keys(self, pattern):
            return self._keys
        def hgetall(self, key):
            return {b"ts": b"0"}
        def delete(self, *keys):
            self.deleted.extend(keys)
            return len(keys)
    client = Client()
    monkeypatch.setattr(logger, "_get_thread_safe_client", lambda: client)
    monkeypatch.setattr(logger, "_is_expired", lambda data: True)
    res = logger.cleanup_expired_memories(dry_run=True)
    assert res["expired_found"] == 2 and res["cleaned"] == 0

    # Branch: deletion with batch and error in hgetall for one key
    class Client2(Client):
        def hgetall(self, key):
            if key == b"k2":
                raise RuntimeError("bad")
            return {b"ts": b"0"}
    client2 = Client2()
    monkeypatch.setattr(logger, "_get_thread_safe_client", lambda: client2)
    monkeypatch.setattr(logger, "_is_expired", lambda data: True)
    res = logger.cleanup_expired_memories(dry_run=False)
    assert res["cleaned"] == 1
    assert res["errors"]  # contains an error from k2


def test_close_and_del(monkeypatch):
    logger = make_logger(monkeypatch)

    closed = {"client": False, "mgr": False, "cleanup": False}

    class DummyClient:
        def close(self):
            closed["client"] = True

    class DummyMgr:
        def close(self):
            closed["mgr"] = True

    logger.redis_client = DummyClient()
    logger._conn_mgr = DummyMgr()  # type: ignore[assignment]

    logger.close()
    assert closed["client"] and closed["mgr"]

    # __del__ calls cleanup_connections but should not raise
    monkeypatch.setattr(logger, "cleanup_connections", lambda: closed.__setitem__("cleanup", True))
    logger.__del__()
    assert closed["cleanup"] is True
