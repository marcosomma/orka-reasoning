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
Base Memory Logger
==================

Abstract base class for memory loggers that defines the interface that must be
implemented by all memory backends.

This class has been refactored into smaller mixins in the base_logger/ package:
- ConfigMixin: Configuration and preset resolution
- ClassificationMixin: Memory classification (importance, type, category)
- DecaySchedulerMixin: Automatic memory decay scheduling
- BlobDeduplicationMixin: Blob deduplication for storage optimization
- MemoryProcessingMixin: Memory entry processing before saving
- CostAnalysisMixin: Cost and token analysis extraction
"""

import logging
import threading
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from .file_operations import FileOperationsMixin
from .serialization import SerializationMixin
from .base_logger_mixins.config_mixin import ConfigMixin
from .base_logger_mixins.classification_mixin import ClassificationMixin
from .base_logger_mixins.decay_scheduler_mixin import DecaySchedulerMixin
from .base_logger_mixins.blob_dedup_mixin import BlobDeduplicationMixin, json_serializer
from .base_logger_mixins.memory_processing_mixin import MemoryProcessingMixin
from .base_logger_mixins.cost_analysis_mixin import CostAnalysisMixin

logger = logging.getLogger(__name__)


class BaseMemoryLogger(
    ABC,
    SerializationMixin,
    FileOperationsMixin,
    ConfigMixin,
    ClassificationMixin,
    DecaySchedulerMixin,
    BlobDeduplicationMixin,
    MemoryProcessingMixin,
    CostAnalysisMixin,
):
    """
    Base Memory Logger - Abstract base class for all memory logger implementations.

    This class defines the interface and common functionality for persistent memory
    storage across different backends. See module docstring for refactoring details.

    Implementation Requirements:
        - log(): Store orchestration events and memory entries
        - tail(): Retrieve recent entries for debugging
        - cleanup_expired_memories(): Remove expired entries
        - get_memory_stats(): Provide storage statistics
        - Redis-compatible methods: hset, hget, hkeys, hdel, get, set, delete
        - Set operations: smembers, sadd, srem
    """

    def __init__(
        self,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: dict[str, Any] | None = None,
        memory_preset: str | None = None,
    ) -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files.
            decay_config: Configuration for memory decay functionality.
            memory_preset: Name of memory preset to use.
        """
        self.stream_key = stream_key
        self.memory: list[dict[str, Any]] = []
        self.debug_keep_previous_outputs = debug_keep_previous_outputs

        # Handle memory preset configuration
        effective_decay_config = self._resolve_memory_preset(
            memory_preset, decay_config or {}, operation=None
        )

        # Initialize decay configuration
        self.decay_config = self._init_decay_config(effective_decay_config)

        # Decay state management
        self._decay_thread: threading.Thread | None = None
        self._decay_stop_event = threading.Event()
        self._last_decay_check = datetime.now(UTC)

        # Initialize automatic decay if enabled
        if self.decay_config.get("enabled", False):
            self._start_decay_scheduler()

        # Blob deduplication storage
        self._blob_store: dict[str, Any] = {}
        self._blob_usage: dict[str, int] = {}
        self._blob_threshold = 200

    # ========== Abstract Methods ==========

    @abstractmethod
    def cleanup_expired_memories(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Clean up expired memory entries based on decay configuration.

        Args:
            dry_run: If True, return what would be deleted without actually deleting

        Returns:
            Dictionary containing cleanup statistics
        """

    @abstractmethod
    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary containing memory statistics
        """

    @abstractmethod
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
        """Log an event to the memory backend."""

    @abstractmethod
    def tail(self, count: int = 10) -> list[dict[str, Any]]:
        """Retrieve the most recent events."""

    @abstractmethod
    def hset(self, name: str, key: str, value: str | bytes | int | float) -> int:
        """Set a field in a hash structure."""

    @abstractmethod
    def hget(self, name: str, key: str) -> str | None:
        """Get a field from a hash structure."""

    @abstractmethod
    def hkeys(self, name: str) -> list[str]:
        """Get all keys in a hash structure."""

    @abstractmethod
    def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from a hash structure."""

    @abstractmethod
    def smembers(self, name: str) -> list[str]:
        """Get all members of a set."""

    @abstractmethod
    def sadd(self, name: str, *values: str) -> int:
        """Add members to a set."""

    @abstractmethod
    def srem(self, name: str, *values: str) -> int:
        """Remove members from a set."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Get a value by key."""

    @abstractmethod
    def set(self, key: str, value: str | bytes | int | float) -> bool:
        """Set a value by key."""

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """Delete keys."""

    @abstractmethod
    def scan(self, cursor: int = 0, match: str | None = None, count: int = 10):
        """Scan keys matching a pattern."""
