# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# Tests for ConnectionManager - isolated, mocked, GitHub Actions compatible

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_pool():
    """Create a mock connection pool with common attributes."""
    pool = MagicMock()
    pool.max_connections = 100
    pool._created_connections = 5
    pool._available_connections = [1, 2, 3]
    pool._in_use_connections = [4, 5]
    pool.disconnect = MagicMock()
    return pool


class TestConnectionManagerInit:
    """Tests for ConnectionManager initialization."""

    def test_init_creates_connection_pool(self, monkeypatch):
        """ConnectionManager should create a connection pool on init."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")

        assert mgr._connection_pool == mock_pool
        assert mgr.redis_url == "redis://test:6379/0"
        assert mgr.max_connections == 100

    def test_init_with_custom_params(self, monkeypatch):
        """ConnectionManager should accept custom parameters."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(
            redis_url="redis://custom:6380/1",
            max_connections=50,
            socket_connect_timeout=10,
            socket_timeout=20,
        )

        assert mgr.max_connections == 50
        assert mgr.socket_connect_timeout == 10
        assert mgr.socket_timeout == 20


class TestConnectionManagerClient:
    """Tests for client access methods."""

    def test_get_client_lazy_initialization(self, monkeypatch):
        """get_client should lazily initialize the Redis client."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            ConnectionManager,
            "_create_redis_connection",
            lambda self, test_connection=True: mock_client,
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")

        # Client should not be initialized yet
        assert mgr._redis_client is None
        assert mgr._client_initialized is False

        # First call should initialize
        client = mgr.get_client()
        assert client == mock_client
        assert mgr._client_initialized is True

        # Second call should return same client
        client2 = mgr.get_client()
        assert client2 == mock_client

    def test_get_thread_safe_client(self, monkeypatch):
        """get_thread_safe_client should return a client from the pool."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mock_client = MagicMock()

        with patch("redis.Redis", return_value=mock_client):
            mgr = ConnectionManager(redis_url="redis://test:6379/0")
            client = mgr.get_thread_safe_client()

            assert client == mock_client
            # Should track the connection
            assert mock_client in mgr._active_connections


class TestConnectionManagerStats:
    """Tests for connection statistics."""

    def test_get_connection_stats(self, monkeypatch):
        """get_connection_stats should return pool statistics."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")
        stats = mgr.get_connection_stats()

        assert stats["active_tracked_connections"] == 0
        assert stats["max_connections"] == 100
        assert stats["pool_created_connections"] == 5
        assert stats["pool_available_connections"] == 3
        assert stats["pool_in_use_connections"] == 2

    def test_get_connection_stats_without_pool_attrs(self, monkeypatch):
        """get_connection_stats should handle pools without internal attrs."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        # Pool without internal attributes
        mock_pool = MagicMock(spec=["max_connections"])
        mock_pool.max_connections = 50
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")
        stats = mgr.get_connection_stats()

        assert stats["max_connections"] == 50
        assert "pool_stats" in stats or "active_tracked_connections" in stats


class TestConnectionManagerCleanup:
    """Tests for cleanup operations."""

    def test_cleanup_clears_connections(self, monkeypatch):
        """cleanup should clear tracked connections and disconnect pool."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")

        # Add some dummy connections (using objects that can be weakly referenced)
        class DummyClient:
            pass

        c1, c2 = DummyClient(), DummyClient()
        mgr._active_connections.add(c1)
        mgr._active_connections.add(c2)

        result = mgr.cleanup()

        assert result["status"] == "success"
        assert result["cleared_tracked_connections"] == 2
        assert mock_pool.disconnect.called

    def test_close_disconnects_pool(self, monkeypatch):
        """close should close client and disconnect pool."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mock_client = MagicMock()
        monkeypatch.setattr(
            ConnectionManager,
            "_create_redis_connection",
            lambda self, test_connection=True: mock_client,
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")
        mgr.get_client()  # Initialize client

        mgr.close()

        assert mock_client.close.called
        assert mock_pool.disconnect.called


class TestConnectionManagerPoolCreation:
    """Tests for connection pool creation."""

    def test_create_connection_pool_success(self, monkeypatch):
        """_create_connection_pool should create pool with correct params."""
        from redis.connection import ConnectionPool

        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()

        with patch.object(
            ConnectionPool, "from_url", return_value=mock_pool
        ) as mock_from_url:
            mgr = ConnectionManager(
                redis_url="redis://test:6379/0",
                max_connections=50,
                socket_timeout=15,
            )

            # Verify from_url was called with correct params
            mock_from_url.assert_called_once()
            call_kwargs = mock_from_url.call_args[1]
            assert call_kwargs["max_connections"] == 50
            assert call_kwargs["socket_timeout"] == 15

    def test_connection_pool_property(self, monkeypatch):
        """connection_pool property should return the underlying pool."""
        from orka.memory.redisstack.connection_manager import ConnectionManager

        mock_pool = _make_mock_pool()
        monkeypatch.setattr(
            ConnectionManager, "_create_connection_pool", lambda self: mock_pool
        )

        mgr = ConnectionManager(redis_url="redis://test:6379/0")

        assert mgr.connection_pool == mock_pool

