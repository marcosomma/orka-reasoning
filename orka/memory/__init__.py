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
Memory Package
==============

The memory package provides persistent storage and retrieval capabilities for OrKa
orchestration events, agent outputs, and system state. This package contains the
modular architecture components for memory management.

Package Overview
----------------

This package contains specialized components for different aspects of memory management:

**Core Components**

:class:`~orka.memory.base_logger.BaseMemoryLogger`
    Abstract base class defining the memory logger interface and common functionality

:class:`~orka.memory.redis_logger.RedisMemoryLogger`
    Complete Redis backend implementation with Redis streams and data structures

:class:`~orka.memory.kafka_logger.KafkaMemoryLogger`
    Kafka-based event streaming implementation (optional dependency)

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
    Easy to add new storage backends

**Optional Dependencies**
    Kafka support is optional and gracefully handled if unavailable

**Performance Optimization**
    Specialized components allow for targeted optimizations

Usage Patterns
--------------

**Direct Usage**

.. code-block:: python

    from orka.memory import RedisMemoryLogger, KafkaMemoryLogger

    # Redis backend
    redis_logger = RedisMemoryLogger(redis_url="redis://localhost:6379")

    # Kafka backend (if available)
    if KafkaMemoryLogger:
        kafka_logger = KafkaMemoryLogger(bootstrap_servers="localhost:9092")

**Through Factory Function (Recommended)**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # Automatically selects appropriate backend
    memory = create_memory_logger("redis")

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
* ``kafka_logger`` - Kafka backend implementation (optional)
* ``serialization`` - JSON sanitization and processing utilities
* ``file_operations`` - File I/O and export functionality
* ``compressor`` - Data compression utilities
* ``schema_manager`` - Schema validation and management

Backward Compatibility
----------------------

All components maintain compatibility with the original monolithic memory logger
interface, ensuring existing code continues to work without modification.
"""

from .base_logger import BaseMemoryLogger
from .file_operations import FileOperationsMixin
from .redis_logger import RedisMemoryLogger
from .serialization import SerializationMixin

# Import KafkaMemoryLogger if available (optional dependency)
try:
    from .kafka_logger import KafkaMemoryLogger
except ImportError:
    # Kafka dependencies not available, that's fine
    KafkaMemoryLogger = None

__all__ = [
    "BaseMemoryLogger",
    "FileOperationsMixin",
    "KafkaMemoryLogger",
    "RedisMemoryLogger",
    "SerializationMixin",
]
