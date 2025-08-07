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
from typing import Any, Dict, List, Set

from .file_operations import FileOperationsMixin
from .serialization import SerializationMixin

logger = logging.getLogger(__name__)


class BaseMemoryLogger(ABC, SerializationMixin, FileOperationsMixin):
    """
    Base Memory Logger
    =================

    Abstract base class that defines the interface and common functionality for all
    memory logger implementations in OrKa. This class provides the foundation for
    persistent memory storage across different backends.

    Core Responsibilities
    --------------------

    **Interface Definition**
    - Defines abstract methods that all memory backends must implement
    - Provides common initialization and configuration patterns
    - Establishes consistent behavior across different storage backends

    **Memory Lifecycle Management**
    - Automatic memory decay based on configurable rules
    - Importance scoring for memory retention decisions
    - Memory type classification (short-term vs long-term)
    - Category-based memory organization (logs vs stored memories)

    **Data Optimization**
    - Blob deduplication for large objects to reduce storage overhead
    - Serialization mixins for consistent data handling
    - File operation mixins for export/import functionality
    - Configurable thresholds for optimization decisions

    **Thread Safety**
    - Thread-safe decay scheduling and management
    - Concurrent access patterns for multi-threaded environments
    - Proper resource cleanup and lifecycle management

    Architecture Details
    -------------------

    **Memory Classification System**
    - **Categories**: "log" (orchestration events) vs "stored" (persistent memories)
    - **Types**: "short_term" (temporary) vs "long_term" (persistent)
    - **Importance Scoring**: 0.0-1.0 scale based on event type and content
    - **Decay Rules**: Configurable retention policies per category/type

    **Blob Deduplication**
    - SHA256 hashing for content identification
    - Reference counting for cleanup decisions
    - Configurable size threshold (default: 200 characters)
    - Automatic cleanup of unused blobs

    **Decay Management**
    - Background thread for automatic cleanup
    - Configurable check intervals (default: 30 minutes)
    - Dry-run support for testing cleanup operations
    - Graceful shutdown with proper thread cleanup

    Implementation Requirements
    --------------------------

    **Required Abstract Methods**
    All concrete implementations must provide:

    - `log()` - Store orchestration events and memory entries
    - `tail()` - Retrieve recent entries for debugging
    - `cleanup_expired_memories()` - Remove expired entries
    - `get_memory_stats()` - Provide storage statistics
    - Redis-compatible methods: `hset`, `hget`, `hkeys`, `hdel`, `get`, `set`, `delete`
    - Set operations: `smembers`, `sadd`, `srem`

    **Optional Enhancements**
    Implementations may provide:

    - Vector search capabilities for semantic similarity
    - Advanced filtering and querying options
    - Performance optimizations for specific use cases
    - Integration with external systems (Redis, Kafka, etc.)

    Configuration Options
    --------------------

    **Decay Configuration**
    ```python
    decay_config = {
        "enabled": True,
        "default_short_term_hours": 1.0,
        "default_long_term_hours": 24.0,
        "check_interval_minutes": 30,
        "memory_type_rules": {
            "long_term_events": ["success", "completion", "write", "result"],
            "short_term_events": ["debug", "processing", "start", "progress"]
        },
        "importance_rules": {
            "base_score": 0.5,
            "event_type_boosts": {"write": 0.3, "success": 0.2},
            "agent_type_boosts": {"memory": 0.2, "openai-answer": 0.1}
        }
    }
    ```

    **Blob Deduplication**
    - `_blob_threshold`: Minimum size for deduplication (default: 200 chars)
    - Automatic reference counting and cleanup
    - SHA256 hashing for content identification

    Usage Patterns
    --------------

    **Implementing a Custom Backend**
    ```python
    from orka.memory.base_logger import BaseMemoryLogger

    class CustomMemoryLogger(BaseMemoryLogger):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._storage = {}  # Your storage implementation

        def log(self, agent_id, event_type, payload, **kwargs):
            # Implement storage logic
            pass

        def cleanup_expired_memories(self, dry_run=False):
            # Implement cleanup logic
            pass

        # ... implement other abstract methods
    ```

    **Memory Classification Logic**
    - Orchestration logs are always classified as short-term
    - Only "stored" memories can be classified as long-term
    - Importance scoring influences retention decisions
    - Event types and agent types affect classification

    **Thread Safety Considerations**
    - Decay scheduler runs in background thread
    - Proper synchronization for concurrent access
    - Graceful shutdown handling with stop events
    - Resource cleanup on object destruction
    """

    def __init__(
        self,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
            decay_config: Configuration for memory decay functionality.
        """
        self.stream_key = stream_key
        self.memory: list[dict[str, Any]] = []  # Local memory buffer
        self.debug_keep_previous_outputs = debug_keep_previous_outputs

        # Initialize decay configuration
        self.decay_config = self._init_decay_config(decay_config or {})

        # Decay state management
        self._decay_thread: threading.Thread | None = None
        self._decay_stop_event = threading.Event()
        self._last_decay_check = datetime.now(UTC)

        # Initialize automatic decay if enabled
        if self.decay_config.get("enabled", False):
            self._start_decay_scheduler()

        # Blob deduplication storage: SHA256 -> actual blob content
        self._blob_store: dict[str, Any] = {}
        # Track blob usage count for potential cleanup
        self._blob_usage: dict[str, int] = {}
        # Minimum size threshold for blob deduplication (in chars)
        self._blob_threshold = 200

    def _init_decay_config(self, decay_config: dict[str, Any]) -> dict[str, Any]:
        """
        Initialize decay configuration with defaults.

        Args:
            decay_config: Raw decay configuration

        Returns:
            Processed decay configuration with defaults applied
        """
        default_config = {
            "enabled": False,  # Disable by default to prevent logs from disappearing
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
                target_dict = merged_config.get(key)
                if isinstance(target_dict, dict):
                    target_dict.update(value)
                else:
                    # If merged_config[key] is not a dict, replace it entirely
                    merged_config[key] = value
            else:
                merged_config[key] = value

        return merged_config

    def _calculate_importance_score(
        self,
        event_type: str,
        agent_id: str,
        payload: dict[str, Any],
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
        rules = self.decay_config.get("importance_rules", {})
        score = rules.get("base_score", 0.5)

        # Apply event type boosts
        event_boost = rules.get("event_type_boosts", {}).get(event_type, 0.0)
        score += event_boost

        # Apply agent type boosts
        for agent_type, boost in rules.get("agent_type_boosts", {}).items():
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
        return_value: float = max(0.0, min(1.0, score))
        return return_value

    def _classify_memory_type(
        self,
        event_type: str,
        importance_score: float,
        category: str = "log",
    ) -> str:
        """
        Classify memory entry as short-term or long-term.

        Args:
            event_type: Type of the event
            importance_score: Calculated importance score
            category: Memory category ("stored" or "log")

        Returns:
            "short_term" or "long_term"
        """
        # CRITICAL: Only "stored" memories should be classified as long-term
        # Orchestration logs should always be short-term to avoid confusion
        if category == "log":
            return "short_term"

        rules = self.decay_config.get("memory_type_rules", {})

        # Check explicit rules first (only for stored memories)
        if event_type in rules.get("long_term_events", []):
            return "long_term"
        if event_type in rules.get("short_term_events", []):
            return "short_term"

        # Fallback to importance score (only for stored memories)
        return "long_term" if importance_score >= 0.7 else "short_term"

    def _classify_memory_category(
        self,
        event_type: str,
        agent_id: str,
        payload: dict[str, Any],
        log_type: str = "log",
    ) -> str:
        """
        Classify memory entry category for separation between logs and stored memories.

        Args:
            event_type: Type of the event
            agent_id: ID of the agent generating the event
            payload: Event payload
            log_type: Explicit log type ("log" or "memory")

        Returns:
            "stored" for memory writer outputs, "log" for other events
        """
        # 🎯 CRITICAL: Use explicit log_type parameter first
        if log_type == "memory":
            return "stored"
        elif log_type == "log":
            return "log"

        # Fallback to legacy detection (for backward compatibility)
        # Memory writes from memory writer nodes should be categorized as "stored"
        if event_type == "write" and ("memory" in agent_id.lower() or "writer" in agent_id.lower()):
            return "stored"

        # Check payload for memory content indicators
        if isinstance(payload, dict):
            # If payload contains content field, it's likely stored memory
            if payload.get("content") and payload.get("metadata"):
                return "stored"

            # If it's a memory operation result
            if payload.get("memory_object") or payload.get("memories"):
                return "stored"

        # Default to log for orchestration events
        return "log"

    def _start_decay_scheduler(self):
        """Start the automatic decay scheduler thread."""
        if self._decay_thread is not None:
            return  # Already running

        def decay_scheduler() -> None:
            interval_seconds = self.decay_config.get("check_interval_minutes", 30) * 60

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
        log_type: str = "log",  # 🎯 NEW: "log" for orchestration, "memory" for stored memories
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
            # Only deduplicate large dictionary payloads
            if not isinstance(obj, dict):
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
        original_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a blob reference object.

        Args:
            blob_hash: SHA256 hash of the blob
            original_keys: List of keys that were in the original object (for reference)

        Returns:
            Blob reference dictionary
        """
        ref: dict[str, Any] = {
            "ref": blob_hash,
            "_type": "blob_reference",
            "_original_keys": None,
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
            deduplicated[key] = self._recursive_deduplicate(value)

        return deduplicated

    def _recursive_deduplicate(self, obj: Any) -> Any:
        """
        Helper method to recursively apply deduplication.
        """
        if isinstance(obj, dict):
            return self._deduplicate_object(obj)
        elif isinstance(obj, list):
            return [self._recursive_deduplicate(item) for item in obj]
        else:
            return obj

    def _process_memory_for_saving(
        self, memory_entries: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Process memory entries before saving, e.g., removing previous_outputs.
        """
        processed_entries = []
        for entry in memory_entries:
            new_entry = entry.copy()
            if not self.debug_keep_previous_outputs:
                # Remove previous_outputs to reduce log size unless debugging is enabled
                if "previous_outputs" in new_entry:
                    # Store a summary instead of the full object
                    new_entry["previous_outputs_summary"] = {
                        "count": len(new_entry["previous_outputs"]),
                        "keys": list(new_entry["previous_outputs"].keys()),
                    }
                    del new_entry["previous_outputs"]
            processed_entries.append(new_entry)
        return processed_entries

    def _sanitize_for_json(self, obj: Any, _seen: Set[Any] | None = None) -> Any:
        """
        Sanitize an object to ensure it's JSON serializable.
        Converts non-serializable types (like objects, functions) to strings.
        """
        if isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        else:
            # Fallback for non-serializable objects
            return f"<non-serializable: {type(obj).__name__}>"

    def _should_use_deduplication_format(self) -> bool:
        """
        Determine whether to use the deduplication format for saving logs.
        This is based on whether any blobs were actually stored.
        """
        return bool(self._blob_store)

    def _build_previous_outputs(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build a dictionary of previous agent outputs from the execution logs.
        Used to provide context to downstream agents.
        """
        outputs = {}

        # First, try to get results from Redis
        try:
            # Get all agent results from Redis hash
            group_key = "agent_results"
            result_keys = self.hkeys(group_key)
            for agent_id in result_keys:
                result_str = self.hget(group_key, agent_id)
                if result_str:
                    result = json.loads(result_str)
                    outputs[agent_id] = result
                    logger.debug(f"- Loaded result for agent {agent_id} from Redis")
        except Exception as e:
            logger.warning(f"Failed to load results from Redis: {e}")

        # Then process logs to update/add any missing results
        for log in logs:
            agent_id = str(log.get("agent_id"))
            if not agent_id:
                continue
            payload = log.get("payload", {})

            # Case: regular agent output
            if "result" in payload:
                outputs[agent_id] = payload["result"]

            # Case: JoinNode with merged dict
            if "result" in payload and isinstance(payload["result"], dict):
                merged = payload["result"].get("merged")
                if isinstance(merged, dict):
                    outputs.update(merged)

            # Case: Current run agent responses
            if "response" in payload:
                outputs[agent_id] = {
                    "response": payload["response"],
                    "confidence": payload.get("confidence", "0.0"),
                    "internal_reasoning": payload.get("internal_reasoning", ""),
                    "_metrics": payload.get("_metrics", {}),
                    "formatted_prompt": payload.get("formatted_prompt", ""),
                }

            # Case: Memory agent responses
            if "memories" in payload:
                outputs[agent_id] = {
                    "memories": payload["memories"],
                    "query": payload.get("query", ""),
                    "backend": payload.get("backend", ""),
                    "search_type": payload.get("search_type", ""),
                    "num_results": payload.get("num_results", 0),
                }

            # Store the result in Redis for future access
            try:
                # Store individual result
                result_key = f"agent_result:{agent_id}"
                self.set(result_key, json.dumps(outputs[agent_id]))
                logger.debug(f"- Stored result for agent {agent_id}")

                # Store in group hash
                self.hset(group_key, agent_id, json.dumps(outputs[agent_id]))
                logger.debug(f"- Stored result in group for agent {agent_id}")
            except Exception as e:
                logger.warning(f"Failed to store result in Redis: {e}")

        return outputs

    def save_enhanced_trace(self, file_path: str, enhanced_data: Dict[str, Any]) -> None:
        """Save enhanced trace data with memory backend references and blob deduplication."""
        try:
            # Apply blob deduplication to the enhanced trace data
            deduplicated_data = self._apply_deduplication_to_enhanced_trace(enhanced_data)

            import json

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(deduplicated_data, f, indent=2, default=str)

            # Log deduplication statistics
            if (
                "_metadata" in deduplicated_data
                and "deduplication_enabled" in deduplicated_data["_metadata"]
            ):
                if deduplicated_data["_metadata"]["deduplication_enabled"]:
                    stats = deduplicated_data["_metadata"].get("stats", {})
                    blob_count = deduplicated_data["_metadata"].get("total_blobs_stored", 0)
                    size_reduction = stats.get("size_reduction", 0)
                    logger.info(
                        f"Enhanced trace saved with deduplication: {blob_count} blobs, {size_reduction} bytes saved"
                    )
                else:
                    logger.info(f"Enhanced trace saved (no deduplication needed)")
            else:
                logger.info(f"Enhanced trace saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save enhanced trace with deduplication: {e}")
            # Fallback to simple JSON dump
            try:
                import json

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(enhanced_data, f, indent=2, default=str)
                logger.info(f"Enhanced trace saved (fallback mode) to {file_path}")
            except Exception as fallback_e:
                logger.error(f"Fallback save also failed: {fallback_e}")
                # Last resort: use the original save_to_file method
                self.save_to_file(file_path)

    def _apply_deduplication_to_enhanced_trace(
        self, enhanced_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply blob deduplication to enhanced trace data using original events format."""
        try:
            import json
            from datetime import UTC, datetime

            # Reset blob store for this operation
            original_blob_store = getattr(self, "_blob_store", {})
            self._blob_store = {}

            # Convert enhanced trace format to original events format for deduplication
            events = []
            blob_stats = {
                "total_entries": 0,
                "deduplicated_blobs": 0,
                "size_reduction": 0,
            }

            # Process agent_executions into events format
            if "agent_executions" in enhanced_data:
                for execution in enhanced_data["agent_executions"]:
                    blob_stats["total_entries"] += 1

                    # Create event preserving original structure (agent_id, event_type, timestamp)
                    event = {
                        "agent_id": execution.get("agent_id"),
                        "event_type": execution.get("event_type"),
                        "timestamp": execution.get("timestamp"),
                    }

                    # Add other top-level fields if they exist
                    for key in ["step", "run_id", "fork_group", "parent"]:
                        if key in execution:
                            event[key] = execution[key]

                    # Handle payload separately - only deduplicate if large
                    if "payload" in execution:
                        payload = execution["payload"]

                        # Calculate payload size to decide if it needs deduplication
                        payload_size = len(json.dumps(payload, separators=(",", ":")))

                        if payload_size > getattr(self, "_blob_threshold", 200):
                            # Payload is large, deduplicate it
                            original_size = payload_size
                            deduplicated_payload = self._deduplicate_object(payload)
                            new_size = len(json.dumps(deduplicated_payload, separators=(",", ":")))

                            if new_size < original_size:
                                blob_stats["deduplicated_blobs"] += 1
                                blob_stats["size_reduction"] += original_size - new_size

                            event["payload"] = deduplicated_payload
                        else:
                            # Payload is small, keep as-is
                            event["payload"] = payload

                    # Add enhanced trace specific fields (memory_references, template_resolution)
                    for key in ["memory_references", "template_resolution"]:
                        if key in execution:
                            event[key] = execution[key]

                    events.append(event)

            # Decide whether to use deduplication format
            use_dedup_format = bool(self._blob_store)

            if use_dedup_format:
                # Extract token and cost data from agent executions
                cost_analysis = self._extract_cost_analysis(enhanced_data, events)

                # Create the original blob_store + events format with cost analysis
                result = {
                    "_metadata": {
                        "version": "1.2.0",  # Use original version for compatibility
                        "deduplication_enabled": True,
                        "blob_threshold_chars": getattr(self, "_blob_threshold", 200),
                        "total_blobs_stored": len(self._blob_store),
                        "stats": blob_stats,
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                    "blob_store": self._blob_store.copy(),
                    "events": events,  # Use 'events' key like original format
                    "cost_analysis": cost_analysis,  # New key for token/cost data
                }
            else:
                # No deduplication needed - use enhanced format with metadata
                result = enhanced_data.copy()
                result["_metadata"] = {
                    "version": "1.2.0",
                    "deduplication_enabled": False,
                    "generated_at": datetime.now(UTC).isoformat(),
                }
                # Add cost analysis even when no deduplication
                result["cost_analysis"] = self._extract_cost_analysis(enhanced_data, events)

            # Restore original blob store
            self._blob_store = original_blob_store

            return result

        except Exception as e:
            logger.error(f"Failed to apply deduplication to enhanced trace: {e}")
            # Restore original blob store on error
            if "original_blob_store" in locals():
                self._blob_store = original_blob_store
            # Return original data if deduplication fails
            return enhanced_data

    def _extract_cost_analysis(
        self, enhanced_data: Dict[str, Any], events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract token and cost analysis from agent executions."""
        try:
            cost_analysis: Dict[str, Any] = {
                "summary": {
                    "total_agents": 0,
                    "total_tokens": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_latency_ms": 0.0,
                    "models_used": set(),
                    "providers_used": set(),
                },
                "agents": {},
                "by_model": {},
                "by_provider": {},
            }

            # Process each agent execution to extract cost data
            for event in events:
                agent_id = event.get("agent_id")
                event_type = event.get("event_type")

                # Only process LLM agents that have cost data
                if not agent_id or not event_type or "LLMAgent" not in str(event_type):
                    continue

                # Extract metrics from payload or blob_store
                metrics = self._extract_agent_metrics(event, enhanced_data)

                if metrics:
                    # Update agent-specific data
                    if agent_id not in cost_analysis["agents"]:
                        cost_analysis["agents"][agent_id] = {
                            "executions": 0,
                            "total_tokens": 0,
                            "total_prompt_tokens": 0,
                            "total_completion_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                            "models": set(),
                            "providers": set(),
                            "event_type": event_type,
                        }

                    agent_data = cost_analysis["agents"][agent_id]
                    agent_data["executions"] += 1
                    agent_data["total_tokens"] += metrics.get("tokens", 0)
                    agent_data["total_prompt_tokens"] += metrics.get("prompt_tokens", 0)
                    agent_data["total_completion_tokens"] += metrics.get("completion_tokens", 0)
                    agent_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    agent_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

                    model = metrics.get("model", "unknown")
                    provider = metrics.get("provider", "unknown")
                    agent_data["models"].add(model)
                    agent_data["providers"].add(provider)

                    # Update summary
                    summary = cost_analysis["summary"]
                    summary["total_agents"] += 1
                    summary["total_tokens"] += metrics.get("tokens", 0)
                    summary["total_prompt_tokens"] += metrics.get("prompt_tokens", 0)
                    summary["total_completion_tokens"] += metrics.get("completion_tokens", 0)
                    summary["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    summary["total_latency_ms"] += metrics.get("latency_ms", 0.0)
                    summary["models_used"].add(model)
                    summary["providers_used"].add(provider)

                    # Update by_model aggregation
                    if model not in cost_analysis["by_model"]:
                        cost_analysis["by_model"][model] = {
                            "agents": 0,
                            "total_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                        }
                    model_data = cost_analysis["by_model"][model]
                    model_data["agents"] += 1
                    model_data["total_tokens"] += metrics.get("tokens", 0)
                    model_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    model_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

                    # Update by_provider aggregation
                    if provider not in cost_analysis["by_provider"]:
                        cost_analysis["by_provider"][provider] = {
                            "agents": 0,
                            "total_tokens": 0,
                            "total_cost_usd": 0.0,
                            "total_latency_ms": 0.0,
                        }
                    provider_data = cost_analysis["by_provider"][provider]
                    provider_data["agents"] += 1
                    provider_data["total_tokens"] += metrics.get("tokens", 0)
                    provider_data["total_cost_usd"] += metrics.get("cost_usd", 0.0)
                    provider_data["total_latency_ms"] += metrics.get("latency_ms", 0.0)

            # Convert sets to lists for JSON serialization
            cost_analysis["summary"]["models_used"] = list(cost_analysis["summary"]["models_used"])
            cost_analysis["summary"]["providers_used"] = list(
                cost_analysis["summary"]["providers_used"]
            )

            for agent_data in cost_analysis["agents"].values():
                agent_data["models"] = list(agent_data["models"])
                agent_data["providers"] = list(agent_data["providers"])

            return cost_analysis

        except Exception as e:
            logger.error(f"Failed to extract cost analysis: {e}")
            return {"error": str(e)}

    def _extract_agent_metrics(
        self, event: Dict[str, Any], enhanced_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract metrics from an agent event, resolving blob references if needed."""
        try:
            payload = event.get("payload", {})

            # If payload is a blob reference, resolve it
            if isinstance(payload, dict) and payload.get("_type") == "blob_reference":
                blob_ref = payload.get("ref")
                if blob_ref and hasattr(self, "_blob_store") and blob_ref in self._blob_store:
                    # Get from current blob store
                    resolved_payload = self._blob_store[blob_ref]
                elif (
                    blob_ref
                    and "blob_store" in enhanced_data
                    and blob_ref in enhanced_data["blob_store"]
                ):
                    # Get from enhanced_data blob store
                    resolved_payload = enhanced_data["blob_store"][blob_ref]
                else:
                    return {}
            else:
                resolved_payload = payload

            # Look for metrics in various locations within the resolved payload
            metrics = {}

            # Check if there's a direct _metrics field
            if "_metrics" in resolved_payload:
                metrics = resolved_payload["_metrics"]

            # Check in previous_outputs for agent responses with _metrics
            elif "previous_outputs" in resolved_payload:
                prev_outputs = resolved_payload["previous_outputs"]
                for agent_response in prev_outputs.values():
                    if isinstance(agent_response, dict) and "_metrics" in agent_response:
                        # Merge metrics from all agent responses
                        agent_metrics = agent_response["_metrics"]
                        for key, value in agent_metrics.items():
                            if key in ["tokens", "prompt_tokens", "completion_tokens"]:
                                metrics[key] = metrics.get(key, 0) + value
                            elif key in ["cost_usd", "latency_ms"]:
                                metrics[key] = metrics.get(key, 0.0) + value
                            else:
                                metrics[key] = value  # model, provider, etc.

            # Check for response field with _metrics
            elif "response" in resolved_payload and isinstance(resolved_payload["response"], dict):
                response = resolved_payload["response"]
                if "_metrics" in response:
                    metrics = response["_metrics"]

            return metrics

        except Exception as e:
            logger.error(f"Failed to extract agent metrics: {e}")
            return {}
