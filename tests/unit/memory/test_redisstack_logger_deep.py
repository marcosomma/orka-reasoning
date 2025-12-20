from unittest.mock import MagicMock

import pytest


def _make_pool_with_attrs():
    class Pool:
        pass

    p = Pool()
    p.max_connections = 10
    p._created_connections = 5
    p._available_connections = [1, 2]
    p._in_use_connections = [3]
    p.disconnect = MagicMock()
    return p


def test_get_connection_stats_with_pool_attrs(monkeypatch):
    # Patch ConnectionManager's pool creation to return our custom pool
    from orka.memory.redisstack.connection_manager import ConnectionManager
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    mock_pool = _make_pool_with_attrs()

    monkeypatch.setattr(
        ConnectionManager,
        "_create_connection_pool",
        lambda self: mock_pool,
    )
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", lambda self: None)

    logger = RedisStackMemoryLogger(redis_url="redis://fake", index_name="test_idx")

    stats = logger.get_connection_stats()
    assert stats["active_tracked_connections"] == 0
    assert stats["max_connections"] == 10
    # pool-specific attributes should be present
    assert stats["pool_created_connections"] == 5
    assert stats["pool_available_connections"] == 2
    assert stats["pool_in_use_connections"] == 1


def test_cleanup_connections_clears_and_disconnects(monkeypatch):
    from orka.memory.redisstack.connection_manager import ConnectionManager
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    mock_pool = _make_pool_with_attrs()

    monkeypatch.setattr(
        ConnectionManager,
        "_create_connection_pool",
        lambda self: mock_pool,
    )
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", lambda self: None)

    logger = RedisStackMemoryLogger(redis_url="redis://fake", index_name="test_idx")

    # Add dummy weakrefable client objects to active connections
    class DummyClient:
        pass

    c1 = DummyClient()
    c2 = DummyClient()
    logger._active_connections.add(c1)
    logger._active_connections.add(c2)

    res = logger.cleanup_connections()
    assert res["status"] == "success"
    assert res["cleared_tracked_connections"] == 2
    # Ensure disconnect was invoked on the pool
    assert mock_pool.disconnect.called


def test_ensure_index_calls_bootstrap_helpers(monkeypatch):
    from orka.memory.redisstack.connection_manager import ConnectionManager
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    # Avoid network in pool creation during __init__ but call the real _ensure_index later
    mock_pool = _make_pool_with_attrs()
    monkeypatch.setattr(
        ConnectionManager,
        "_create_connection_pool",
        lambda self: mock_pool,
    )

    # Temporarily stub _ensure_index during __init__, then restore the original
    original_ensure = RedisStackMemoryLogger._ensure_index
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", lambda self: None)

    logger = RedisStackMemoryLogger(redis_url="redis://fake", index_name="test_idx")

    # Restore the real implementation so we can invoke it under controlled conditions
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", original_ensure)

    # Patch _get_redis_client to return a fake client (so connection attempt succeeds)
    fake_client = MagicMock()
    monkeypatch.setattr(logger, "_get_redis_client", lambda: fake_client)
    monkeypatch.setattr(logger._conn_mgr, "get_client", lambda: fake_client)

    # Patch bootstrap helpers
    import threading

    import orka.utils.bootstrap_memory_index as bmi

    called = {"ensure": 0, "verify": 0}

    def fake_ensure(**kwargs):
        called["ensure"] += 1
        return True

    def fake_verify(redis_client, index_name):
        called["verify"] += 1
        return {
            "exists": True,
            "vector_field_exists": True,
            "content_field_exists": True,
            "fields": ["content", "content_vector"],
        }

    monkeypatch.setattr(bmi, "ensure_enhanced_memory_index", fake_ensure)
    monkeypatch.setattr(bmi, "verify_memory_index", fake_verify)

    # Replace threading.Thread with a fake that runs the target synchronously
    class FakeThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=False):
            self._target = target
            self._args = args or ()
            self._kwargs = kwargs or {}

        def start(self):
            # Execute target immediately in the current thread so result_queue is populated
            if callable(self._target):
                self._target(*self._args, **(self._kwargs or {}))

    monkeypatch.setattr(threading, "Thread", FakeThread)

    # Call the real _ensure_index (it will use our patched helpers and FakeThread)
    logger._ensure_index()

    # Ensure bootstrap helpers were invoked at least once
    assert called["verify"] + called["ensure"] >= 1
