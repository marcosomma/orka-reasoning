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
Base Memory Logger
=================

Abstract base class for memory loggers that defines the interface that must be
implemented by all memory backends.
"""

import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

from .file_operations import FileOperationsMixin
from .serialization import SerializationMixin

logger = logging.getLogger(__name__)


class BaseMemoryLogger(ABC, SerializationMixin, FileOperationsMixin):
    """
    Abstract base class for memory loggers.
    Defines the interface that must be implemented by all memory backends.
    """

    def __init__(
        self,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
            decay_config: Configuration for memory decay functionality.
        """
        self.stream_key = stream_key
        self.memory: List[Dict[str, Any]] = []  # Local memory buffer
        self.debug_keep_previous_outputs = debug_keep_previous_outputs

        # Initialize decay configuration
        self.decay_config = self._init_decay_config(decay_config or {})

        # Decay state management
        self._decay_thread = None
        self._decay_stop_event = threading.Event()
        self._last_decay_check = datetime.now(UTC)

        # Initialize automatic decay if enabled
        if self.decay_config.get("enabled", False):
            self._start_decay_scheduler()

        # Blob deduplication storage: SHA256 -> actual blob content
        self._blob_store: Dict[str, Any] = {}
        # Track blob usage count for potential cleanup
        self._blob_usage: Dict[str, int] = {}
        # Minimum size threshold for blob deduplication (in chars)
        self._blob_threshold = 200

    def _init_decay_config(self, decay_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize decay configuration with defaults.

        Args:
            decay_config: Raw decay configuration

        Returns:
            Processed decay configuration with defaults applied
        """
        default_config = {
            "enabled": True,  # Enable by default for better memory management
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
            "memory_type_rules": {
                "long_term_events": ["success", "completion", "write", "result"],
                "short_term_events": ["debug", "processing", "start", "progress"],
            },
            "importance_rules": {
                "base_score": 0.5,
                "event_type_boosts": {
                    "write": 0.3,
                    "success": 0.2,
                    "completion": 0.2,
                    "result": 0.1,
                },
                "agent_type_boosts": {
                    "memory": 0.2,
                    "openai-answer": 0.1,
                },
            },
        }

        # Deep merge with defaults
        merged_config = default_config.copy()
        for key, value in decay_config.items():
            if isinstance(value, dict) and key in merged_config:
                merged_config[key].update(value)
            else:
                merged_config[key] = value

        return merged_config

    def _calculate_importance_score(
        self,
        event_type: str,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> float:
        """
        Calculate importance score for a memory entry.

        Args:
            event_type: Type of the event
            agent_id: ID of the agent generating the event
            payload: Event payload

        Returns:
            Importance score between 0.0 and 1.0
        """
        rules = self.decay_config["importance_rules"]
        score = rules["base_score"]

        # Apply event type boosts
        event_boost = rules["event_type_boosts"].get(event_type, 0.0)
        score += event_boost

        # Apply agent type boosts
        for agent_type, boost in rules["agent_type_boosts"].items():
            if agent_type in agent_id:
                score += boost
                break

        # Check payload for result indicators
        if isinstance(payload, dict):
            if payload.get("result") or payload.get("response"):
                score += 0.1
            if payload.get("error"):
                score -= 0.1

        # Clamp score between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _classify_memory_type(self, event_type: str, importance_score: float) -> str:
        """
        Classify memory entry as short-term or long-term.

        Args:
            event_type: Type of the event
            importance_score: Calculated importance score

        Returns:
            "short_term" or "long_term"
        """
        rules = self.decay_config["memory_type_rules"]

        # Check explicit rules first
        if event_type in rules["long_term_events"]:
            return "long_term"
        if event_type in rules["short_term_events"]:
            return "short_term"

        # Fallback to importance score
        return "long_term" if importance_score >= 0.7 else "short_term"

    def _start_decay_scheduler(self):
        """Start the automatic decay scheduler thread."""
        if self._decay_thread is not None:
            return  # Already running

        def decay_scheduler():
            interval_seconds = self.decay_config["check_interval_minutes"] * 60

            while not self._decay_stop_event.wait(interval_seconds):
                try:
                    self.cleanup_expired_memories()
                except Exception as e:
                    logger.error(f"Error during automatic memory decay: {e}")

        self._decay_thread = threading.Thread(target=decay_scheduler, daemon=True)
        self._decay_thread.start()
        logger.info(
            f"Started automatic memory decay scheduler (interval: {self.decay_config['check_interval_minutes']} minutes)",
        )

    def stop_decay_scheduler(self):
        """Stop the automatic decay scheduler."""
        if self._decay_thread is not None:
            self._decay_stop_event.set()
            self._decay_thread.join(timeout=5)
            self._decay_thread = None
            logger.info("Stopped automatic memory decay scheduler")

    @abstractmethod
    def cleanup_expired_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up expired memory entries based on decay configuration.

        Args:
            dry_run: If True, return what would be deleted without actually deleting

        Returns:
            Dictionary containing cleanup statistics
        """

    @abstractmethod
    def get_memory_stats(self) -> Dict[str, Any]:
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
        payload: Dict[str, Any],
        step: Optional[int] = None,
        run_id: Optional[str] = None,
        fork_group: Optional[str] = None,
        parent: Optional[str] = None,
        previous_outputs: Optional[Dict[str, Any]] = None,
        agent_decay_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an event to the memory backend."""

    @abstractmethod
    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the most recent events."""

    @abstractmethod
    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a field in a hash structure."""

    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a field from a hash structure."""

    @abstractmethod
    def hkeys(self, name: str) -> List[str]:
        """Get all keys in a hash structure."""

    @abstractmethod
    def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from a hash structure."""

    @abstractmethod
    def smembers(self, name: str) -> List[str]:
        """Get all members of a set."""

    @abstractmethod
    def sadd(self, name: str, *values: str) -> int:
        """Add members to a set."""

    @abstractmethod
    def srem(self, name: str, *values: str) -> int:
        """Remove members from a set."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""

    @abstractmethod
    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a value by key."""

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """Delete keys."""

    def _compute_blob_hash(self, obj: Any) -> str:
        """
        Compute SHA256 hash of a JSON-serializable object.

        Args:
            obj: Object to hash

        Returns:
            SHA256 hash as hex string
        """
        try:
            # Convert to canonical JSON string for consistent hashing
            json_str = json.dumps(obj, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
        except Exception:
            # If object can't be serialized, return hash of string representation
            return hashlib.sha256(str(obj).encode("utf-8")).hexdigest()

    def _should_deduplicate_blob(self, obj: Any) -> bool:
        """
        Determine if an object should be deduplicated as a blob.

        Args:
            obj: Object to check

        Returns:
            True if object should be deduplicated
        """
        try:
            # Only deduplicate JSON responses and large payloads
            if not isinstance(obj, dict):
                return False

            # Check if it looks like a JSON response
            has_response = "response" in obj
            has_result = "result" in obj

            if not (has_response or has_result):
                return False

            # Check size threshold
            json_str = json.dumps(obj, separators=(",", ":"))
            return len(json_str) >= self._blob_threshold

        except Exception:
            return False

    def _store_blob(self, obj: Any) -> str:
        """
        Store a blob and return its reference hash.

        Args:
            obj: Object to store as blob

        Returns:
            SHA256 hash reference
        """
        blob_hash = self._compute_blob_hash(obj)

        # Store the blob if not already present
        if blob_hash not in self._blob_store:
            self._blob_store[blob_hash] = obj
            self._blob_usage[blob_hash] = 0

        # Increment usage count
        self._blob_usage[blob_hash] += 1

        return blob_hash

    def _create_blob_reference(
        self,
        blob_hash: str,
        original_keys: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a blob reference object.

        Args:
            blob_hash: SHA256 hash of the blob
            original_keys: List of keys that were in the original object (for reference)

        Returns:
            Blob reference dictionary
        """
        ref = {
            "ref": blob_hash,
            "_type": "blob_reference",
        }

        if original_keys:
            ref["_original_keys"] = original_keys

        return ref

    def _deduplicate_object(self, obj: Any) -> Any:
        """
        Recursively deduplicate an object, replacing large blobs with references.

        Args:
            obj: Object to deduplicate

        Returns:
            Deduplicated object with blob references
        """
        if not isinstance(obj, dict):
            return obj

        # Check if this object should be stored as a blob
        if self._should_deduplicate_blob(obj):
            blob_hash = self._store_blob(obj)
            return self._create_blob_reference(blob_hash, list(obj.keys()))

        # Recursively deduplicate nested objects
        deduplicated = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                deduplicated[key] = self._deduplicate_object(value)
            elif isinstance(value, list):
                deduplicated[key] = [
                    self._deduplicate_object(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                deduplicated[key] = value

        return deduplicated
