# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Connection Manager for RedisStack
=================================

Thread-safe Redis connection pool management with efficient resource handling.

Features
--------
- Connection pooling for efficient Redis operations
- Thread-safe client access
- Connection statistics and monitoring
- Graceful cleanup and resource management

Usage
-----
```python
from orka.memory.redisstack.connection_manager import ConnectionManager

conn_mgr = ConnectionManager(redis_url="redis://localhost:6380/0")
client = conn_mgr.get_thread_safe_client()
stats = conn_mgr.get_connection_stats()
conn_mgr.close()
```
"""

import logging
import weakref
from threading import Lock
from typing import Any

import redis
from redis import Redis
from redis.connection import ConnectionPool

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Thread-safe Redis connection pool manager.

    Manages Redis connections using a connection pool for efficient
    resource utilization and thread-safe access.

    Attributes:
        redis_url: Redis connection URL
        max_connections: Maximum connections in the pool
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6380/0",
        max_connections: int = 100,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 10,
        health_check_interval: int = 300,
    ):
        """
        Initialize the connection manager.

        Args:
            redis_url: Redis connection URL.
            max_connections: Maximum connections in the pool.
            socket_connect_timeout: Connection timeout in seconds.
            socket_timeout: Operation timeout in seconds.
            health_check_interval: Health check interval in seconds.
        """
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_timeout = socket_timeout
        self.health_check_interval = health_check_interval

        # Thread safety for parallel operations
        self._connection_lock = Lock()

        # Track active connections for cleanup (using weak references)
        self._active_connections: weakref.WeakSet[Redis] = weakref.WeakSet()

        # Connection pool for efficient connection management
        self._connection_pool = self._create_connection_pool()

        # Lazy initialization - don't test connection during init
        self._redis_client: redis.Redis | None = None
        self._client_initialized = False

        logger.debug(
            f"ConnectionManager initialized with redis_url={redis_url}, "
            f"max_connections={max_connections}"
        )

    def _create_connection_pool(self) -> ConnectionPool:
        """Create a Redis connection pool for efficient connection management."""
        try:
            pool = ConnectionPool.from_url(
                self.redis_url,
                decode_responses=False,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                health_check_interval=self.health_check_interval,
                max_connections=self.max_connections,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_timeout=self.socket_timeout,
            )
            logger.debug(
                f"Created Redis connection pool with max_connections={self.max_connections}, "
                f"socket_timeout={self.socket_timeout}s"
            )
            return pool
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {e}")
            raise

    def _create_redis_connection(self, test_connection: bool = True) -> redis.Redis:
        """Create a new Redis connection using the connection pool."""
        try:
            client = redis.Redis(connection_pool=self._connection_pool)

            # Only test connection if requested
            if test_connection:
                try:
                    client.ping()
                except (redis.TimeoutError, redis.ConnectionError) as e:
                    logger.warning(
                        f"Redis connection test failed (but client created): {e}"
                    )

            # Track the connection for potential cleanup
            self._active_connections.add(client)
            return client
        except Exception as e:
            logger.error(f"Failed to create Redis connection: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """Get the main Redis client with lazy initialization."""
        if not self._client_initialized or self._redis_client is None:
            with self._connection_lock:
                if not self._client_initialized or self._redis_client is None:
                    try:
                        self._redis_client = self._create_redis_connection(
                            test_connection=False
                        )
                        self._client_initialized = True
                        logger.debug("Lazy initialized main Redis client")
                    except Exception as e:
                        logger.error(f"Failed to initialize Redis client: {e}")
                        raise
        return self._redis_client

    def get_thread_safe_client(self) -> redis.Redis:
        """Get a thread-safe Redis client using the connection pool."""
        try:
            client = redis.Redis(connection_pool=self._connection_pool)
            self._active_connections.add(client)
            return client
        except Exception as e:
            logger.error(f"Failed to get thread-safe Redis client: {e}")
            return self.get_client()

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection pool statistics for monitoring."""
        try:
            pool = self._connection_pool
            stats: dict[str, Any] = {
                "active_tracked_connections": len(self._active_connections),
                "max_connections": getattr(pool, "max_connections", "unknown"),
            }

            # Try to get pool-specific stats if available
            try:
                if hasattr(pool, "_created_connections"):
                    stats["pool_created_connections"] = pool._created_connections
                if hasattr(pool, "_available_connections"):
                    stats["pool_available_connections"] = len(
                        pool._available_connections
                    )
                if hasattr(pool, "_in_use_connections"):
                    stats["pool_in_use_connections"] = len(pool._in_use_connections)
            except AttributeError:
                stats["pool_stats"] = "not_available"

            return stats
        except Exception as e:
            logger.warning(f"Failed to get connection stats: {e}")
            return {"error": str(e)}

    def cleanup(self) -> dict[str, Any]:
        """Clean up connection resources."""
        try:
            stats_before = self.get_connection_stats()

            # Clear tracked connections
            initial_count = len(self._active_connections)
            self._active_connections.clear()

            # Disconnect the connection pool
            if hasattr(self._connection_pool, "disconnect"):
                self._connection_pool.disconnect()

            stats_after = self.get_connection_stats()

            logger.debug(
                f"Connection cleanup completed: cleared {initial_count} tracked connections"
            )

            return {
                "status": "success",
                "cleared_tracked_connections": initial_count,
                "stats_before": stats_before,
                "stats_after": stats_after,
            }
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
            return {"status": "error", "error": str(e)}

    def close(self) -> None:
        """Close all connections and clean up resources."""
        try:
            # Close the main Redis client
            if self._redis_client is not None:
                self._redis_client.close()

            # Disconnect the connection pool
            if self._connection_pool is not None:
                try:
                    self._connection_pool.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting connection pool: {e}")
        except Exception as e:
            logger.error(f"Error closing ConnectionManager: {e}")

    @property
    def connection_pool(self) -> ConnectionPool:
        """Access to the underlying connection pool."""
        return self._connection_pool

    def __del__(self):
        """Cleanup when the manager is destroyed."""
        try:
            self.cleanup()
        except Exception:
            pass

