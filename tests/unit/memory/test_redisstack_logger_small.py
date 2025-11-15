import weakref
from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack_logger import RedisStackMemoryLogger


def test_get_connection_stats_and_cleanup(monkeypatch):
    # Prevent heavy initialization by stubbing internal methods
    monkeypatch.setattr(RedisStackMemoryLogger, "_create_connection_pool", lambda self: MagicMock())
    monkeypatch.setattr(RedisStackMemoryLogger, "_ensure_index", lambda self: None)

    logger = RedisStackMemoryLogger(redis_url="redis://noop:6379/0")

    # Add some fake active connections (MagicMock is weakrefable)
    client1 = MagicMock()
    client2 = MagicMock()
    logger._active_connections.add(client1)
    logger._active_connections.add(client2)

    stats = logger.get_connection_stats()
    assert "active_tracked_connections" in stats

    # Now call cleanup and ensure it returns dict and clears active connections
    before = len(logger._active_connections)
    res = logger.cleanup_connections()
    assert isinstance(res, dict)
    # WeakSet.clear() called: active connections should be 0
    assert len(logger._active_connections) == 0
