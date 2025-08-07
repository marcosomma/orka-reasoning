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
Memory Logger
=============

The Memory Logger is a critical component of the OrKa framework that provides
persistent storage and retrieval capabilities for orchestration events, agent outputs,
and system state. It serves as both a runtime memory system and an audit trail for
agent workflows.

**Modular Architecture**
    The memory logger features a modular architecture with focused components
    while maintaining 100% backward compatibility through factory functions.

Key Features
------------

**Event Logging**
    Records all agent activities and system events with detailed metadata

**Data Persistence**
    Stores data in Redis streams or Kafka topics for reliability and durability

**Serialization**
    Handles conversion of complex Python objects to JSON-serializable formats
    with intelligent blob deduplication

**Error Resilience**
    Implements fallback mechanisms for handling serialization errors gracefully

**Querying**
    Provides methods to retrieve recent events and specific data points efficiently

**File Export**
    Supports exporting memory logs to files for analysis and backup

**Multiple Backends**
    Supports both Redis and Kafka backends with seamless switching

Core Use Cases
--------------

The Memory Logger is essential for:

* Enabling agents to access past context and outputs
* Debugging and auditing agent workflows
* Maintaining state across distributed components
* Supporting complex workflow patterns like fork/join
* Providing audit trails for compliance and analysis

Modular Components
------------------

The memory system is composed of specialized modules:

:class:`~orka.memory.base_logger.BaseMemoryLogger`
    Abstract base class defining the memory logger interface

:class:`~orka.memory.redis_logger.RedisMemoryLogger`
    Complete Redis backend implementation with streams and data structures

:class:`~orka.memory.kafka_logger.KafkaMemoryLogger`
    Kafka-based event streaming implementation

:class:`~orka.memory.serialization`
    JSON sanitization and memory processing utilities

:class:`~orka.memory.file_operations`
    Save/load functionality and file I/O operations

:class:`~orka.memory.compressor`
    Data compression utilities for efficient storage

Usage Examples
--------------

**Factory Function (Recommended)**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # Redis backend (default)
    redis_memory = create_memory_logger("redis", redis_url="redis://localhost:6379")

    # Kafka backend
    kafka_memory = create_memory_logger("kafka", bootstrap_servers="localhost:9092")

**Direct Instantiation**

.. code-block:: python

    from orka.memory.redis_logger import RedisMemoryLogger
    from orka.memory.kafka_logger import KafkaMemoryLogger

    # Redis logger
    redis_logger = RedisMemoryLogger(redis_url="redis://localhost:6379")

    # Kafka logger
    kafka_logger = KafkaMemoryLogger(bootstrap_servers="localhost:9092")

**Environment-Based Configuration**

.. code-block:: python

    import os
    from orka.memory_logger import create_memory_logger

    # Set backend via environment variable
    os.environ["ORKA_MEMORY_BACKEND"] = "kafka"

    # Logger will use Kafka automatically
    memory = create_memory_logger()

Backend Comparison
------------------

**Redis Backend**
    * **Best for**: Development, single-node deployments, quick prototyping
    * **Features**: Fast in-memory operations, simple setup, full feature support
    * **Limitations**: Single point of failure, memory-bound storage

**Kafka Backend**
    * **Best for**: Production, distributed systems, high-throughput scenarios
    * **Features**: Persistent event log, horizontal scaling, fault tolerance
    * **Limitations**: More complex setup, higher resource usage

Implementation Notes
--------------------

**Backward Compatibility**
    All existing code using ``RedisMemoryLogger`` continues to work unchanged

**Performance Optimizations**
    * Blob deduplication reduces storage overhead
    * In-memory buffers provide fast access to recent events
    * Batch operations improve throughput

**Error Handling**
    * Robust sanitization handles non-serializable objects
    * Graceful degradation prevents workflow failures
    * Detailed error logging aids debugging

**Thread Safety**
    All memory logger implementations are thread-safe for concurrent access
"""

# Import all components from the new memory package
import logging
import os
from typing import Any

from .memory.base_logger import BaseMemoryLogger
from .memory.redis_logger import RedisMemoryLogger

logger = logging.getLogger(__name__)


def create_memory_logger(
    backend: str = "redisstack",
    redis_url: str | None = None,
    bootstrap_servers: str | None = None,
    topic_prefix: str = "orka-memory",
    stream_key: str = "orka:memory",
    debug_keep_previous_outputs: bool = False,
    decay_config: dict[str, Any] | None = None,
    enable_hnsw: bool = True,
    vector_params: dict[str, Any] | None = None,
    **kwargs,
) -> BaseMemoryLogger:
    """
    Enhanced factory with RedisStack as primary backend.

    Creates a memory logger instance based on the specified backend.
    Defaults to RedisStack for optimal performance with automatic fallback.

    Args:
        backend: Memory backend type ("redisstack", "redis", "kafka")
        redis_url: Redis connection URL
        bootstrap_servers: Kafka bootstrap servers (for Kafka backend)
        topic_prefix: Kafka topic prefix (for Kafka backend)
        stream_key: Redis stream key for logging
        debug_keep_previous_outputs: Whether to keep previous outputs in logs
        decay_config: Memory decay configuration
        enable_hnsw: Enable HNSW vector indexing (RedisStack only)
        vector_params: HNSW configuration parameters
        **kwargs: Additional parameters for backward compatibility

    Returns:
        Configured memory logger instance

    Raises:
        ImportError: If required dependencies are not available
        ConnectionError: If backend connection fails
    """
    # Normalize backend name
    backend = backend.lower()

    # Set default decay configuration if not provided
    if decay_config is None:
        decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }

    # ✅ Handle force basic Redis flag
    force_basic_redis = os.getenv("ORKA_FORCE_BASIC_REDIS", "false").lower() == "true"

    if force_basic_redis and backend in ["redis", "redisstack"]:
        # Force basic Redis when explicitly requested
        logging.getLogger(__name__).info("🔧 Force basic Redis mode enabled")
        try:
            from .memory.redis_logger import RedisMemoryLogger

            return RedisMemoryLogger(
                redis_url=redis_url,
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
            )
        except ImportError as e:
            raise ImportError(f"Basic Redis backend not available: {e}") from e

    # PRIORITY: Try RedisStack first for redis/redisstack backends
    if backend in ["redisstack", "redis"]:
        try:
            from .memory.redisstack_logger import RedisStackMemoryLogger

            # 🎯 CRITICAL: Initialize embedder for vector search
            embedder = None
            try:
                from .utils.embedder import get_embedder

                embedder = get_embedder()
                logger.info("✅ Embedder initialized for vector search")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize embedder: {e}")
                logger.warning("Vector search will not be available")

            logger_instance = RedisStackMemoryLogger(
                redis_url=redis_url or "redis://localhost:6379/0",
                embedder=embedder,  # 🎯 NEW: Pass embedder for vector search
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
                enable_hnsw=enable_hnsw,
                vector_params=vector_params,
            )

            # Test RedisStack capabilities
            try:
                index_ready = logger_instance.ensure_index()
                if index_ready:
                    if embedder:
                        logging.getLogger(__name__).info(
                            "✅ RedisStack with HNSW and vector search enabled",
                        )
                    else:
                        logging.getLogger(__name__).info(
                            "✅ RedisStack with HNSW enabled (no vector search)",
                        )
                    return logger_instance
                else:
                    logging.getLogger(__name__).warning(
                        "⚠️ RedisStack index failed, falling back to basic Redis",
                    )
            except Exception as e:
                logging.getLogger(__name__).warning(f"RedisStack index test failed: {e}")

        except ImportError as e:
            logging.getLogger(__name__).warning(f"RedisStack not available: {e}")

    # Fallback to basic Redis only if RedisStack fails
    if backend == "redis" or (backend == "redisstack" and not force_basic_redis):
        try:
            from .memory.redis_logger import RedisMemoryLogger

            logging.getLogger(__name__).info("🔄 Using basic Redis backend")
            return RedisMemoryLogger(
                redis_url=redis_url,
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
            )
        except ImportError as e:
            if backend == "redisstack":
                raise ImportError(f"No Redis backends available: {e}") from e

    # Handle Kafka backend with RedisStack integration
    if backend == "kafka":
        try:
            from .memory.kafka_logger import KafkaMemoryLogger

            # ✅ CRITICAL: Use provided parameters or defaults
            kafka_bootstrap_servers = bootstrap_servers or os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092",
            )

            # Get Schema Registry configuration
            schema_registry_url = kwargs.get("schema_registry_url") or os.getenv(
                "KAFKA_SCHEMA_REGISTRY_URL",
                "http://localhost:8081",
            )
            use_schema_registry = kwargs.get("use_schema_registry", True)

            logger.info(
                f"🔄 Creating Kafka memory logger with Schema Registry: {schema_registry_url}"
            )

            return KafkaMemoryLogger(
                bootstrap_servers=str(kafka_bootstrap_servers),
                schema_registry_url=schema_registry_url,
                use_schema_registry=use_schema_registry,
                topic_prefix=topic_prefix,
                redis_url=redis_url or "redis://localhost:6380/0",
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
                enable_hnsw=enable_hnsw,
                vector_params=vector_params,
            )
        except ImportError as e:
            logging.getLogger(__name__).warning(
                f"Kafka not available, falling back to RedisStack: {e}",
            )
            # Recursive call with RedisStack
            return create_memory_logger(
                "redisstack",
                redis_url=redis_url,
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
                enable_hnsw=enable_hnsw,
                vector_params=vector_params,
            )

    raise ValueError(f"Unsupported backend: {backend}. Supported: redisstack, redis, kafka")


# Add MemoryLogger alias for backward compatibility with tests
MemoryLogger = RedisMemoryLogger
