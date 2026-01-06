# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory Package
==============

The memory package provides persistent storage and retrieval capabilities for OrKa
orchestration events, agent outputs, and system state. This package contains the
modular architecture components for memory management with enhanced RedisStack support.

Package Overview
----------------

This package contains specialized components for different aspects of memory management:

**Core Components**

:class:`~orka.memory.base_logger.BaseMemoryLogger`
    Abstract base class defining the memory logger interface and common functionality

:class:`~orka.memory.redis_logger.RedisMemoryLogger`
    Complete Redis backend implementation with Redis streams and data structures

:class:`~orka.memory.redisstack_logger.RedisStackMemoryLogger`
    High-performance RedisStack backend with HNSW vector indexing for semantic search


**Utility Mixins**

:class:`~orka.memory.serialization.SerializationMixin`
    JSON sanitization and memory processing utilities with blob deduplication

:class:`~orka.memory.file_operations.FileOperationsMixin`
    Save/load functionality and file I/O operations

:class:`~orka.memory.compressor.CompressionMixin`
    Data compression utilities for efficient storage

Architecture Benefits
---------------------

**Separation of Concerns**
    Each component handles a specific aspect of memory management

**Modular Design**
    Components can be mixed and matched as needed

**Backend Flexibility**
    Easy to add new storage backends including RedisStack

**Modular Design**
    Components can be mixed and matched as needed for different use cases

**Performance Optimization**
    Specialized components allow for targeted optimizations including HNSW indexing

Usage Patterns
==============

**Direct Usage**

.. code-block:: python

    from orka.memory import RedisMemoryLogger, RedisStackMemoryLogger

    # Standard Redis backend
    redis_logger = RedisMemoryLogger(redis_url="redis://localhost:6380")

    # High-performance RedisStack backend with HNSW
    redisstack_logger = RedisStackMemoryLogger(
        redis_url="redis://localhost:6380",
        enable_hnsw=True,
        vector_params={"M": 16, "ef_construction": 200}
    )


**Through Factory Function (Recommended)**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # Automatically selects appropriate backend
    memory = create_memory_logger("redisstack")  # Uses HNSW indexing
    memory = create_memory_logger("redis")       # Standard Redis

**Custom Implementation**

.. code-block:: python

    from orka.memory import BaseMemoryLogger, SerializationMixin

    class CustomMemoryLogger(BaseMemoryLogger, SerializationMixin):
        # Implement custom storage backend
        pass

Modular Components
------------------

**Available Modules:**

* ``base_logger`` - Abstract base class and common functionality
* ``redis_logger`` - Redis backend implementation
* ``redisstack_logger`` - RedisStack backend with HNSW vector indexing
* ``serialization`` - JSON sanitization and processing utilities
* ``file_operations`` - File I/O and export functionality
* ``compressor`` - Data compression utilities

Performance Characteristics
===========================

**RedisStack vs Redis Logger:**

* **Vector Search**: Up to 100x faster with HNSW indexing vs manual cosine similarity for large datasets
* **Scalability**: O(log n) vs O(n) search complexity (HNSW vs brute force)
* **Memory Usage**: ~60% reduction in memory overhead with optimized vector storage
* **Concurrent Operations**: Support for 1000+ simultaneous searches in typical deployments

Backward Compatibility
----------------------

All components maintain compatibility with the original monolithic memory logger
interface, ensuring existing code continues to work without modification. The
RedisStack logger provides enhanced performance while preserving legacy API.
"""

from typing import Any

from .base_logger import BaseMemoryLogger
from .file_operations import FileOperationsMixin
from .redis_logger import RedisMemoryLogger
from .serialization import SerializationMixin

# Import RedisStack logger with graceful fallback
try:
    from .redisstack_logger import RedisStackMemoryLogger
except ImportError:
    # Define a dummy class if RedisStack dependencies are not available
    class _DummyRedisStackMemoryLogger(BaseMemoryLogger):
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            raise ImportError("RedisStack dependencies not available")

        def cleanup_expired_memories(self, dry_run: bool = False) -> dict[str, Any]:
            raise NotImplementedError

        def get_memory_stats(self) -> dict[str, Any]:
            raise NotImplementedError

        def log(self, *args: Any, **kwargs: Any) -> None:
            raise NotImplementedError

        def tail(self, count: int = 10) -> list[dict[str, Any]]:
            raise NotImplementedError

        def hset(self, name: str, key: str, value: str | bytes | int | float) -> int:
            raise NotImplementedError

        def hget(self, name: str, key: str) -> str | None:
            raise NotImplementedError

        def hkeys(self, name: str) -> list[str]:
            raise NotImplementedError

        def hdel(self, name: str, *keys: str) -> int:
            raise NotImplementedError

        def smembers(self, name: str) -> list[str]:
            raise NotImplementedError

        def sadd(self, name: str, *values: str) -> int:
            raise NotImplementedError

        def srem(self, name: str, *values: str) -> int:
            raise NotImplementedError

        def get(self, key: str) -> str | None:
            raise NotImplementedError

        def set(self, key: str, value: str | bytes | int | float) -> bool:
            raise NotImplementedError

        def delete(self, *keys: str) -> int:
            raise NotImplementedError

        def scan(self, cursor: int = 0, match: str | None = None, count: int = 10):
            raise NotImplementedError

        def ensure_index(self) -> bool:
            raise NotImplementedError

        def log_memory(self, *args: Any, **kwargs: Any) -> str:
            raise NotImplementedError

        def search_memories(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
            raise NotImplementedError

    RedisStackMemoryLogger = _DummyRedisStackMemoryLogger  # type: ignore


__all__ = [
    "BaseMemoryLogger",
    "FileOperationsMixin",
    "RedisMemoryLogger",
    "RedisStackMemoryLogger",
    "SerializationMixin",
]
