# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

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
from typing import Any, Dict, Optional

from .memory.base_logger import BaseMemoryLogger
from .memory.kafka_logger import KafkaMemoryLogger
from .memory.redis_logger import RedisMemoryLogger


def create_memory_logger(
    backend: str = "redis",
    redis_url: Optional[str] = None,
    bootstrap_servers: Optional[str] = None,
    topic_prefix: str = "orka-memory",
    stream_key: str = "orka:memory",
    synchronous_send: bool = False,
    debug_keep_previous_outputs: bool = False,
    decay_config: Optional[Dict[str, Any]] = None,
) -> BaseMemoryLogger:
    """
    Factory function to create memory logger instances.

    This function provides a unified interface for creating memory loggers
    across different backends (Redis, Kafka) with automatic fallback handling
    and environment variable integration.

    Args:
        backend: Backend type ("redis" or "kafka")
        redis_url: Redis connection URL (for Redis backend)
        bootstrap_servers: Kafka bootstrap servers (for Kafka backend)
        topic_prefix: Kafka topic prefix (for Kafka backend)
        stream_key: Stream key for memory logging
        synchronous_send: Whether to wait for message delivery confirmation
        debug_keep_previous_outputs: Keep previous outputs for debugging
        decay_config: Configuration for memory decay functionality

    Returns:
        Configured memory logger instance

    Raises:
        ValueError: If backend type is unsupported
        ImportError: If required dependencies are missing

    Examples:
        Basic Redis logger:

        .. code-block:: python

            memory = create_memory_logger("redis")

        Redis with decay enabled:

        .. code-block:: python

            decay_config = {
                "enabled": True,
                "default_short_term_hours": 2.0,
                "default_long_term_hours": 48.0
            }
            memory = create_memory_logger("redis", decay_config=decay_config)

        Kafka logger:

        .. code-block:: python

            memory = create_memory_logger(
                "kafka",
                bootstrap_servers="localhost:9092"
            )
    """
    if backend.lower() == "redis":
        return RedisMemoryLogger(
            redis_url=redis_url,
            stream_key=stream_key,
            debug_keep_previous_outputs=debug_keep_previous_outputs,
            decay_config=decay_config,
        )
    elif backend.lower() == "kafka":
        return KafkaMemoryLogger(
            bootstrap_servers=bootstrap_servers,
            topic_prefix=topic_prefix,
            stream_key=stream_key,
            synchronous_send=synchronous_send,
            debug_keep_previous_outputs=debug_keep_previous_outputs,
            decay_config=decay_config,
        )
    else:
        raise ValueError(f"Unsupported backend: {backend}")


# Add MemoryLogger alias for backward compatibility with tests
MemoryLogger = RedisMemoryLogger
