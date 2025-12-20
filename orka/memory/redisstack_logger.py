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
RedisStack Memory Logger Implementation
=====================================

High-performance memory logger leveraging RedisStack's advanced capabilities.
Uses modular mixins for maintainability - see orka.memory.redisstack package.
"""

import json
import logging
import time
import uuid
from typing import Any

import redis
from redis.connection import ConnectionPool

from orka.memory.base_logger import BaseMemoryLogger
from orka.memory.redisstack.connection_manager import ConnectionManager
from orka.memory.redisstack.crud_mixin import MemoryCRUDMixin
from orka.memory.redisstack.decay_mixin import MemoryDecayMixin
from orka.memory.redisstack.embedding_mixin import EmbeddingMixin
from orka.memory.redisstack.logging_mixin import OrchestrationLoggingMixin
from orka.memory.redisstack.metrics_mixin import MetricsMixin
from orka.memory.redisstack.redis_interface_mixin import RedisInterfaceMixin
from orka.memory.redisstack.search_mixin import MemorySearchMixin
from orka.memory.redisstack.vector_index_manager import VectorIndexManager

# Re-export for backward compatibility with tests
__all__ = ["RedisStackMemoryLogger", "ConnectionPool", "redis"]

logger = logging.getLogger(__name__)


class RedisStackMemoryLogger(
    BaseMemoryLogger,
    EmbeddingMixin,  # Must be before MemorySearchMixin (provides _get_embedding_sync)
    MemorySearchMixin,
    MemoryDecayMixin,
    MemoryCRUDMixin,
    MetricsMixin,
    OrchestrationLoggingMixin,
    RedisInterfaceMixin,
):
    """
    Ultra-high-performance memory engine - RedisStack-powered with HNSW indexing.

    Uses composition and mixins for maintainability:
    - ConnectionManager: Thread-safe connection pooling
    - VectorIndexManager: HNSW index operations
    - MemorySearchMixin: Vector/text search
    - MemoryDecayMixin: Expiry and cleanup
    - MemoryCRUDMixin: CRUD operations
    - MetricsMixin: Statistics and metrics
    - OrchestrationLoggingMixin: Event logging
    - RedisInterfaceMixin: Redis delegations
    - EmbeddingMixin: Content formatting and embeddings
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6380/0",
        index_name: str = "orka_enhanced_memory",
        embedder: Any = None,
        memory_decay_config: dict[str, Any] | None = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: dict[str, Any] | None = None,
        memory_preset: str | None = None,
        enable_hnsw: bool = True,
        vector_params: dict[str, Any] | None = None,
        format_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        """Initialize the RedisStack memory logger with modular components."""
        effective_decay_config = memory_decay_config or decay_config

        super().__init__(
            stream_key,
            debug_keep_previous_outputs,
            effective_decay_config,
            memory_preset,
        )

        self.redis_url = redis_url
        self.index_name = index_name
        self.embedder = embedder
        self.enable_hnsw = enable_hnsw
        self.vector_params = vector_params or {}
        self.format_params = format_params or {}
        self.stream_key = stream_key
        self.debug_keep_previous_outputs = debug_keep_previous_outputs
        self.memory_decay_config: dict[str, Any] | None = effective_decay_config

        # Initialize connection manager (composition)
        self._conn_mgr = ConnectionManager(
            redis_url=redis_url,
            max_connections=self.vector_params.get("max_connections", 100),
        )

        # Initialize vector index manager (composition)
        self._index_mgr = VectorIndexManager(
            conn_mgr=self._conn_mgr,
            index_name=index_name,
            enable_hnsw=enable_hnsw,
            vector_params=vector_params,
            embedder=embedder,
        )

        # Backward compatibility
        self._connection_pool = self._conn_mgr.connection_pool
        self._connection_lock = self._conn_mgr._connection_lock
        self._embedding_lock = self._conn_mgr._connection_lock
        self._active_connections = self._conn_mgr._active_connections

        self.redis_client = None
        self._client_initialized = False

        self._ensure_index()
        logger.info(f"RedisStack memory logger initialized with index: {self.index_name}")

    # ==========================================================================
    # Connection Delegation
    # ==========================================================================

    def _create_connection_pool(self):
        """Delegate to ConnectionManager."""
        return self._conn_mgr._create_connection_pool()

    def _create_redis_connection(self, test_connection: bool = True):
        """Delegate to ConnectionManager."""
        return self._conn_mgr._create_redis_connection(test_connection)

    def _get_redis_client(self):
        """Get the main Redis client with lazy initialization."""
        if not self._client_initialized or self.redis_client is None:
            self.redis_client = self._conn_mgr.get_client()
            self._client_initialized = True
        return self.redis_client

    def _get_thread_safe_client(self):
        """Get a thread-safe Redis client using the connection pool."""
        return self._conn_mgr.get_thread_safe_client()

    @property
    def redis(self):
        """Backward compatibility property for redis client access."""
        return self._get_redis_client()

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection pool statistics for monitoring."""
        return self._conn_mgr.get_connection_stats()

    def cleanup_connections(self) -> dict[str, Any]:
        """Clean up connection resources."""
        return self._conn_mgr.cleanup()

    # ==========================================================================
    # Index Management
    # ==========================================================================

    def _ensure_index(self) -> None:
        """Ensure the enhanced memory index exists."""
        vector_dim = 384
        if self.embedder and hasattr(self.embedder, "embedding_dim"):
            vector_dim = self.embedder.embedding_dim
        self._index_mgr.ensure_index(vector_dim=vector_dim)

    def ensure_index(self) -> bool:
        """Ensure the enhanced memory index exists - for factory compatibility."""
        try:
            self._ensure_index()
            return True
        except Exception as e:
            logger.error(f"Failed to ensure index: {e}")
            return False

    # ==========================================================================
    # Memory Storage
    # ==========================================================================

    def log_memory(
        self,
        content: str,
        node_id: str,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 1.0,
        memory_type: str = "short_term",
        expiry_hours: float | None = None,
    ) -> str:
        """Store memory with vector embedding for enhanced search."""
        try:
            memory_id = str(uuid.uuid4()).replace("-", "")
            memory_key = f"orka_memory:{memory_id}"
            current_time_ms = int(time.time() * 1000)
            metadata = metadata or {}

            orka_expire_time = None
            if expiry_hours is not None:
                orka_expire_time = current_time_ms + int(expiry_hours * 3600 * 1000)

            client = self._get_thread_safe_client()

            try:
                content_str: str = str(content) if not isinstance(content, str) else content
                content = content_str
                json.dumps(metadata)
            except Exception as serialize_error:
                logger.error(f"Serialization error: {serialize_error}")
                metadata = {
                    "error": "serialization_failed",
                    "original_error": str(serialize_error),
                    "node_id": node_id,
                    "trace_id": trace_id,
                    "log_type": "memory",
                }
                content = str(content)

            formatted_content = self._format_content(content)

            memory_data: dict[str, Any] = {
                "content": formatted_content,
                "node_id": node_id,
                "trace_id": trace_id,
                "timestamp": str(current_time_ms),
                "importance_score": str(importance_score),
                "memory_type": memory_type,
                "metadata": json.dumps(metadata),
            }

            if orka_expire_time is not None:
                memory_data["orka_expire_time"] = str(orka_expire_time)

            if self.embedder:
                try:
                    embedding = self._get_embedding_sync(content)
                    if embedding is not None:
                        memory_data["content_vector"] = embedding.tobytes()
                except Exception as e:
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.warning(f"Failed to generate embedding: {error_msg}")

            client.hset(
                memory_key,
                mapping={
                    k: str(v) if not isinstance(v, (bytes, int, float)) else v
                    for k, v in memory_data.items()
                },
            )

            if orka_expire_time:
                ttl_seconds = max(1, int((orka_expire_time - current_time_ms) / 1000))
                client.expire(memory_key, ttl_seconds)

            return memory_key

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    # ==========================================================================
    # Abstract Method Implementations (for ABC compliance)
    # ==========================================================================

    def cleanup_expired_memories(self, dry_run: bool = False) -> dict[str, Any]:
        """Clean up expired memories using connection pool."""
        cleaned = 0
        total_checked = 0
        errors: list[str] = []

        try:
            if not hasattr(self, "_connection_pool") or self._connection_pool is None:
                return {
                    "cleaned": 0,
                    "total_checked": 0,
                    "expired_found": 0,
                    "dry_run": dry_run,
                    "cleanup_type": "redisstack_not_ready",
                    "errors": ["Connection pool not yet initialized"],
                }

            try:
                client = self._get_thread_safe_client()
            except Exception as e:
                return {
                    "cleaned": 0,
                    "total_checked": 0,
                    "expired_found": 0,
                    "dry_run": dry_run,
                    "cleanup_type": "redisstack_connection_failed",
                    "errors": [f"Connection failed: {e}"],
                }

            pattern = "orka_memory:*"
            keys = client.keys(pattern)
            total_checked = len(keys)

            expired_keys = []
            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if self._is_expired(memory_data):
                        expired_keys.append(key)
                except Exception as e:
                    errors.append(f"Error checking {key}: {e}")

            if not dry_run and expired_keys:
                batch_size = 100
                for i in range(0, len(expired_keys), batch_size):
                    batch = expired_keys[i : i + batch_size]
                    try:
                        deleted_count = client.delete(*batch)
                        cleaned += deleted_count
                    except Exception as e:
                        errors.append(f"Batch deletion error: {e}")

            result = {
                "cleaned": cleaned,
                "total_checked": total_checked,
                "expired_found": len(expired_keys),
                "dry_run": dry_run,
                "cleanup_type": "redisstack",
                "errors": errors,
            }

            if cleaned > 0:
                logger.info(f"Cleanup completed: {cleaned} expired memories removed")

            return result

        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return {
                "error": str(e),
                "cleaned": 0,
                "total_checked": total_checked,
                "cleanup_type": "redisstack_failed",
                "errors": errors + [str(e)],
            }

    # ==========================================================================
    # Mixin Method Delegations (for ABC compliance)
    # ==========================================================================

    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: dict[str, Any],
        step: int | None = None,
        run_id: str | None = None,
        fork_group: str | None = None,
        parent: str | None = None,
        previous_outputs: dict[str, Any] | None = None,
        agent_decay_config: dict[str, Any] | None = None,
        log_type: str = "log",
    ) -> None:
        """Log orchestration event - delegates to OrchestrationLoggingMixin."""
        return OrchestrationLoggingMixin.log(
            self, agent_id, event_type, payload, step, run_id,
            fork_group, parent, previous_outputs, agent_decay_config, log_type
        )

    def tail(self, count: int = 10) -> list[dict[str, Any]]:
        """Get recent entries - delegates to MemoryCRUDMixin."""
        return MemoryCRUDMixin.tail(self, count)

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory stats - delegates to MetricsMixin."""
        return MetricsMixin.get_memory_stats(self)

    def hset(self, name: str, key: str, value: str | bytes | int | float) -> int:
        return RedisInterfaceMixin.hset(self, name, key, value)

    def hget(self, name: str, key: str) -> str | None:
        return RedisInterfaceMixin.hget(self, name, key)

    def hkeys(self, name: str) -> list[str]:
        return RedisInterfaceMixin.hkeys(self, name)

    def hdel(self, name: str, *keys: str) -> int:
        return RedisInterfaceMixin.hdel(self, name, *keys)

    def smembers(self, name: str) -> list[str]:
        return RedisInterfaceMixin.smembers(self, name)

    def sadd(self, name: str, *values: str) -> int:
        return RedisInterfaceMixin.sadd(self, name, *values)

    def srem(self, name: str, *values: str) -> int:
        return RedisInterfaceMixin.srem(self, name, *values)

    def get(self, key: str) -> str | None:
        return RedisInterfaceMixin.get(self, key)

    def set(self, key: str, value: str | bytes | int | float) -> bool:
        return RedisInterfaceMixin.set(self, key, value)

    def delete(self, *keys: str) -> int:
        return RedisInterfaceMixin.delete(self, *keys)

    # ==========================================================================
    # Resource Cleanup
    # ==========================================================================

    def close(self) -> None:
        """Clean up resources."""
        try:
            self.stop_decay_scheduler()
            if hasattr(self, "redis_client") and self.redis_client is not None:
                self.redis_client.close()
            if hasattr(self, "_conn_mgr"):
                self._conn_mgr.close()
        except Exception as e:
            logger.error(f"Error closing RedisStack logger: {e}")

    def __del__(self):
        """Cleanup when the logger is destroyed."""
        try:
            self.cleanup_connections()
        except Exception:
            pass
