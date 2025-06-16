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
============

The Memory Logger is a critical component of the OrKa framework that provides
persistent storage and retrieval capabilities for orchestration events, agent outputs,
and system state. It serves as both a runtime memory system and an audit trail for
agent workflows.

Key Features:
------------
1. Event Logging: Records all agent activities and system events
2. Data Persistence: Stores data in Redis streams for reliability
3. Serialization: Handles conversion of complex Python objects to JSON-serializable formats
4. Error Resilience: Implements fallback mechanisms for handling serialization errors
5. Querying: Provides methods to retrieve recent events and specific data points
6. File Export: Supports exporting memory logs to files for analysis

The Memory Logger is essential for:
- Enabling agents to access past context and outputs
- Debugging and auditing agent workflows
- Maintaining state across distributed components
- Supporting complex workflow patterns like fork/join

Implementation Notes:
-------------------
- Uses Redis streams as the primary storage backend
- Maintains an in-memory buffer for fast access to recent events
- Implements robust sanitization to handle non-serializable objects
- Provides helper methods for common Redis operations
- Includes a placeholder for future Kafka-based implementation
"""

# Import all components from the new memory package
from .memory.base_logger import BaseMemoryLogger
from .memory.kafka_logger import KafkaMemoryLogger
from .memory.redis_logger import RedisMemoryLogger


def create_memory_logger(backend: str = "redis", **kwargs) -> BaseMemoryLogger:
    """
    Factory function to create a memory logger based on backend type.

    Args:
        backend: Backend type ("redis" or "kafka")
        **kwargs: Backend-specific configuration

    Returns:
        Memory logger instance

    Raises:
        ValueError: If backend type is not supported
    """
    backend = backend.lower()

    if backend == "redis":
        return RedisMemoryLogger(**kwargs)
    elif backend == "kafka":
        return KafkaMemoryLogger(**kwargs)
    else:
        raise ValueError(
            f"Unsupported memory backend: {backend}. Supported backends: redis, kafka",
        )


# Add MemoryLogger alias for backward compatibility with tests
MemoryLogger = RedisMemoryLogger
