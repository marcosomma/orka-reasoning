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
    Stores data in Redis streams with reliability and durability

**Serialization**
    Handles conversion of complex Python objects to JSON-serializable formats
    with intelligent blob deduplication

**Error Resilience**
    Implements fallback mechanisms for handling serialization errors gracefully

**Querying**
    Provides methods to retrieve recent events and specific data points efficiently

**File Export**
    Supports exporting memory logs to files for analysis and backup

**RedisStack Backend**
    High-performance RedisStack backend with HNSW vector indexing for semantic search

Core Use Cases
==============

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

:class:`~orka.memory.redisstack_logger.RedisStackMemoryLogger`
    High-performance RedisStack backend with HNSW vector indexing

:class:`~orka.memory.serialization`
    JSON sanitization and memory processing utilities

:class:`~orka.memory.file_operations`
    Save/load functionality and file I/O operations

:class:`~orka.memory.compressor`
    Data compression utilities for efficient storage

Usage Examples
==============

**Factory Function (Recommended)**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # RedisStack backend (default - recommended)
    redisstack_memory = create_memory_logger("redisstack", redis_url="redis://localhost:6380")

    # Basic Redis backend
    redis_memory = create_memory_logger("redis", redis_url="redis://localhost:6380")

**Direct Instantiation**

.. code-block:: python

    from orka.memory.redis_logger import RedisMemoryLogger
    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    # Redis logger
    redis_logger = RedisMemoryLogger(redis_url="redis://localhost:6380")

    # RedisStack logger with HNSW
    redisstack_logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380")

**Environment-Based Configuration**

.. code-block:: python

    import os
    from orka.memory_logger import create_memory_logger

    # Set backend via environment variable
    os.environ["ORKA_MEMORY_BACKEND"] = "redisstack"

    # Logger will use RedisStack automatically
    memory = create_memory_logger()

Backend Comparison
------------------

**RedisStack Backend (Recommended)**
    * **Best for**: Production AI workloads, high-performance applications
    * **Features**: HNSW vector indexing, 100x faster search, advanced memory management
    * **Performance**: Sub-millisecond search, 50,000+ operations/second

**Redis Backend (Legacy)**
    * **Best for**: Development, single-node deployments, quick prototyping
    * **Features**: Fast in-memory operations, simple setup, full feature support
    * **Limitations**: Basic search capabilities, no vector indexing

Implementation Notes
--------------------

**Backward Compatibility**
    All existing code using ``RedisMemoryLogger`` continues to work unchanged

**Performance Optimizations**
    * Blob deduplication reduces storage overhead
    * In-memory buffers provide fast access to recent events
    * Batch operations improve throughput
    * HNSW indexing for ultra-fast vector search

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


def apply_memory_preset_to_config(
    config: dict[str, Any], memory_preset: str | None = None, operation: str | None = None
) -> dict[str, Any]:
    """
    Apply memory preset operation-specific defaults to a configuration dictionary.

    This function intelligently merges memory preset defaults based on the operation type
    (read/write) with the provided configuration, allowing users to specify just a preset
    and have appropriate defaults applied automatically.

    Args:
        config: Base configuration dictionary
        memory_preset: Name of the memory preset (sensory, working, episodic, semantic, procedural, meta)
        operation: Memory operation type ('read' or 'write')

    Returns:
        Enhanced configuration with preset defaults applied

    Example:
        >>> config = {"operation": "read", "namespace": "test"}
        >>> enhanced = apply_memory_preset_to_config(config, "episodic", "read")
        >>> # Returns config with episodic read defaults like similarity_threshold, vector_weight, etc.
    """
    if not memory_preset or not operation:
        return config

    try:
        from .memory.presets import get_operation_defaults

        # Get operation-specific defaults for the preset
        operation_defaults = get_operation_defaults(memory_preset, operation)

        # Apply defaults for any missing keys in config
        enhanced_config = config.copy()
        for key, default_value in operation_defaults.items():
            if key not in enhanced_config:
                enhanced_config[key] = default_value

        logger.debug(f"Applied {memory_preset}_{operation} preset defaults to config")
        return enhanced_config

    except ImportError:
        logger.warning("Memory presets not available, using config as-is")
        return config
    except Exception as e:
        logger.error(f"Failed to apply preset '{memory_preset}' for operation '{operation}': {e}")
        return config


def create_memory_logger(
    backend: str = "redisstack",
    redis_url: str | None = None,
    stream_key: str = "orka:memory",
    debug_keep_previous_outputs: bool = False,
    decay_config: dict[str, Any] | None = None,
    memory_preset: str | None = None,
    operation: str | None = None,  # NEW: Support for operation-aware presets
    enable_hnsw: bool = True,
    vector_params: dict[str, Any] | None = None,
    format_params: dict[str, Any] | None = None,
    index_name: str = "orka_enhanced_memory",
    vector_dim: int = 384,
    force_recreate_index: bool = False,
    **kwargs,
) -> BaseMemoryLogger:
    """
    Enhanced factory with RedisStack as primary backend.

    Creates a memory logger instance based on the specified backend.
    Defaults to RedisStack for optimal performance with automatic fallback.

    Args:
        backend: Memory backend type ("redisstack", "redis")
        redis_url: Redis connection URL
        stream_key: Redis stream key for logging
        debug_keep_previous_outputs: Whether to keep previous outputs in logs
        decay_config: Memory decay configuration
        memory_preset: Memory preset name (sensory, working, episodic, semantic, procedural, meta)
        enable_hnsw: Enable HNSW vector indexing (RedisStack only)
        vector_params: HNSW configuration parameters
        format_params: Content formatting parameters (e.g., newline handling, custom filters)
        index_name: Name of the RedisStack index for vector search
        vector_dim: Dimension of vector embeddings
        force_recreate_index: Whether to force recreate index if it exists but is misconfigured
        **kwargs: Additional parameters for backward compatibility

    Returns:
        Configured memory logger instance

    Raises:
        ImportError: If required dependencies are not available
        ConnectionError: If backend connection fails

    Notes:
        All parameters can be configured through YAML configuration.
        Vector parameters can be specified in detail through the vector_params dictionary.
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

    # Handle force basic Redis flag
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
                memory_preset=memory_preset,
            )
        except ImportError as e:
            raise ImportError(f"Basic Redis backend not available: {e}") from e

    # PRIORITY: Try RedisStack first for redis/redisstack backends
    if backend in ["redisstack", "redis"]:
        try:
            from .memory.redisstack_logger import RedisStackMemoryLogger

            # Initialize embedder for vector search
            embedder = None
            try:
                from .utils.embedder import get_embedder

                embedder = get_embedder()
                logger.info("✅ Embedder initialized for vector search")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize embedder: {e}")
                logger.warning("Vector search will not be available")

            # Prepare vector params with additional configuration
            effective_vector_params = vector_params or {}

            # Add force_recreate to vector params if specified
            if force_recreate_index:
                effective_vector_params["force_recreate"] = True

            logger.info("✅ RedisStack with HNSW and vector search enabled")

            return RedisStackMemoryLogger(
                redis_url=redis_url or "redis://localhost:6380/0",
                index_name=index_name,
                embedder=embedder,
                memory_decay_config=decay_config,
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
                memory_preset=memory_preset,
                enable_hnsw=enable_hnsw,
                vector_params=effective_vector_params,
                format_params=format_params,
                vector_dim=vector_dim,
                force_recreate_index=force_recreate_index,
                **kwargs,
            )

        except ImportError as e:
            # Fall back to basic Redis if RedisStack is not available
            logger.warning(f"RedisStack not available, falling back to basic Redis: {e}")
            try:
                from .memory.redis_logger import RedisMemoryLogger

                return RedisMemoryLogger(
                    redis_url=redis_url,
                    stream_key=stream_key,
                    debug_keep_previous_outputs=debug_keep_previous_outputs,
                    decay_config=decay_config,
                    memory_preset=memory_preset,
                )
            except ImportError as e:
                raise ImportError(f"No Redis backends available: {e}") from e

    raise ValueError(f"Unsupported backend: {backend}. Supported: redisstack, redis")


# Add MemoryLogger alias for backward compatibility with tests
MemoryLogger = RedisMemoryLogger
