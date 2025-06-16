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
Memory package for OrKa memory loggers and utilities.
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
