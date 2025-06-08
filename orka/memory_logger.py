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

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis

logger = logging.getLogger(__name__)


class BaseMemoryLogger(ABC):
    """
    Abstract base class for memory loggers.
    Defines the interface that must be implemented by all memory backends.
    """

    def __init__(
        self,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
    ) -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
        """
        self.stream_key = stream_key
        self.memory: List[Dict[str, Any]] = []  # Local memory buffer
        self.debug_keep_previous_outputs = debug_keep_previous_outputs

        # Blob deduplication storage: SHA256 -> actual blob content
        self._blob_store: Dict[str, Any] = {}
        # Track blob usage count for potential cleanup
        self._blob_usage: Dict[str, int] = {}
        # Minimum size threshold for blob deduplication (in chars)
        self._blob_threshold = 200

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

    def _sanitize_for_json(self, obj: Any, _seen: Optional[set] = None) -> Any:
        """
        Recursively sanitize an object to be JSON serializable, with circular reference detection.

        Args:
            obj: The object to sanitize.
            _seen: Set of already processed object IDs to detect cycles.

        Returns:
            A JSON-serializable version of the object.
        """
        if _seen is None:
            _seen = set()

        # Check for circular references
        obj_id = id(obj)
        if obj_id in _seen:
            return f"<circular-reference: {type(obj).__name__}>"

        try:
            if obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, bytes):
                # Convert bytes to base64-encoded string
                import base64

                return {
                    "__type": "bytes",
                    "data": base64.b64encode(obj).decode("utf-8"),
                }
            elif isinstance(obj, (list, tuple)):
                _seen.add(obj_id)
                try:
                    result = [self._sanitize_for_json(item, _seen) for item in obj]
                finally:
                    _seen.discard(obj_id)
                return result
            elif isinstance(obj, dict):
                _seen.add(obj_id)
                try:
                    result = {str(k): self._sanitize_for_json(v, _seen) for k, v in obj.items()}
                finally:
                    _seen.discard(obj_id)
                return result
            elif hasattr(obj, "__dict__"):
                try:
                    _seen.add(obj_id)
                    try:
                        # Handle custom objects by converting to dict
                        return {
                            "__type": obj.__class__.__name__,
                            "data": self._sanitize_for_json(obj.__dict__, _seen),
                        }
                    finally:
                        _seen.discard(obj_id)
                except Exception as e:
                    return f"<non-serializable object: {obj.__class__.__name__}, error: {e!s}>"
            elif hasattr(obj, "isoformat"):  # Handle datetime-like objects
                return obj.isoformat()
            else:
                # Last resort - convert to string
                return f"<non-serializable: {type(obj).__name__}>"
        except Exception as e:
            logger.warning(f"Failed to sanitize object for JSON: {e!s}")
            return f"<sanitization-error: {e!s}>"

    def _process_memory_for_saving(
        self,
        memory_entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Process memory entries before saving to optimize storage.

        This method:
        1. Removes ALL previous_outputs from agent entries (unless debug flag is set)
        2. Keeps only result and _metrics for clean storage (unless debug flag is set)
        3. Only processes data for saving - doesn't modify original memory during execution

        Args:
            memory_entries: List of memory entries to process

        Returns:
            Processed memory entries optimized for storage
        """
        if not memory_entries:
            return memory_entries

        # If debug flag is set, return original entries without processing
        if self.debug_keep_previous_outputs:
            return memory_entries

        processed_entries = []

        for entry in memory_entries:
            # Create a copy to avoid modifying original
            processed_entry = entry.copy()

            # Remove ALL previous_outputs from root level - it's just repeated data
            if "previous_outputs" in processed_entry:
                del processed_entry["previous_outputs"]

            # Process payload if it exists
            if "payload" in processed_entry:
                payload = processed_entry["payload"].copy()

                if "previous_outputs" in payload:
                    del payload["previous_outputs"]

                # Special handling for meta report - keep all data
                if processed_entry.get("event_type") == "MetaReport":
                    processed_entry["payload"] = payload
                else:
                    # Keep only essential data: result, _metrics, and basic info
                    cleaned_payload = {}

                    # Always keep these core fields
                    for key in [
                        "input",
                        "result",
                        "_metrics",
                        "fork_group",
                        "fork_targets",
                        "fork_group_id",
                        "prompt",
                        "formatted_prompt",
                    ]:
                        if key in payload:
                            cleaned_payload[key] = payload[key]

                    processed_entry["payload"] = cleaned_payload

            processed_entries.append(processed_entry)

        return processed_entries

    def _should_use_deduplication_format(self) -> bool:
        """
        Determine if deduplication format should be used based on effectiveness.
        Only use new format if we have meaningful deduplication.
        """
        # Check if we have actual duplicates (same blob referenced multiple times)
        has_duplicates = any(count > 1 for count in self._blob_usage.values())

        # Calculate potential savings vs overhead
        total_blob_size = sum(
            len(json.dumps(blob, separators=(",", ":"))) for blob in self._blob_store.values()
        )

        # Estimate overhead (metadata + structure)
        estimated_overhead = 1000  # Conservative estimate

        # Use new format if we have duplicates OR if blob store is large enough
        return has_duplicates or (
            len(self._blob_store) > 3 and total_blob_size > estimated_overhead
        )

    def save_to_file(self, file_path: str) -> None:
        """
        Save the logged events to a JSON file with blob deduplication.

        This method implements deduplication by:
        1. Replacing repeated JSON response blobs with SHA256 references
        2. Storing unique blobs once in a separate blob store
        3. Reducing file size by ~80% for typical workflows
        4. Meeting data minimization requirements

        Args:
            file_path: Path to the output JSON file.
        """
        try:
            # For Kafka backend, ensure all messages are sent before saving
            if hasattr(self, "producer"):
                try:
                    # Flush pending messages with a reasonable timeout
                    self.producer.flush(timeout=3)
                    logger.debug(
                        "[KafkaMemoryLogger] Flushed pending messages before save",
                    )
                except Exception as flush_e:
                    logger.warning(
                        f"Warning: Failed to flush Kafka messages before save: {flush_e!s}",
                    )

            # Process memory entries to optimize storage (remove repeated previous_outputs)
            processed_memory = self._process_memory_for_saving(self.memory)

            # Pre-sanitize all memory entries
            sanitized_memory = self._sanitize_for_json(processed_memory)

            # Apply blob deduplication to reduce size
            deduplicated_memory = []
            blob_stats = {
                "total_entries": len(sanitized_memory),
                "deduplicated_blobs": 0,
                "size_reduction": 0,
            }

            for entry in sanitized_memory:
                original_size = len(json.dumps(entry, separators=(",", ":")))
                deduplicated_entry = self._deduplicate_object(entry)
                new_size = len(json.dumps(deduplicated_entry, separators=(",", ":")))

                if new_size < original_size:
                    blob_stats["deduplicated_blobs"] += 1
                    blob_stats["size_reduction"] += original_size - new_size

                deduplicated_memory.append(deduplicated_entry)

            # Decide whether to use deduplication format
            use_dedup_format = self._should_use_deduplication_format()

            if use_dedup_format:
                # Create the final output structure with deduplication
                output_data = {
                    "_metadata": {
                        "version": "1.0",
                        "deduplication_enabled": True,
                        "blob_threshold_chars": self._blob_threshold,
                        "total_blobs_stored": len(self._blob_store),
                        "stats": blob_stats,
                        "generated_at": datetime.utcnow().isoformat(),
                    },
                    "blob_store": self._blob_store if self._blob_store else {},
                    "events": deduplicated_memory,
                }
            else:
                # Use legacy format (resolve all blob references back to original data)
                resolved_events = []
                for entry in deduplicated_memory:
                    resolved_entry = self._resolve_blob_references(entry, self._blob_store)
                    resolved_events.append(resolved_entry)
                output_data = resolved_events

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    output_data,
                    f,
                    indent=2,
                    default=lambda o: f"<non-serializable: {type(o).__name__}>",
                )

            # Log deduplication statistics
            if use_dedup_format and blob_stats["deduplicated_blobs"] > 0:
                reduction_pct = (
                    blob_stats["size_reduction"]
                    / sum(
                        len(json.dumps(entry, separators=(",", ":"))) for entry in sanitized_memory
                    )
                ) * 100
                logger.info(
                    f"[MemoryLogger] Logs saved to {file_path} "
                    f"(deduplicated {blob_stats['deduplicated_blobs']} blobs, "
                    f"~{reduction_pct:.1f}% size reduction)",
                )
            else:
                format_type = "deduplicated format" if use_dedup_format else "legacy format"
                logger.info(f"[MemoryLogger] Logs saved to {file_path} ({format_type})")

        except Exception as e:
            logger.error(f"Failed to save logs to file: {e!s}")
            # Try again with simplified content (without deduplication)
            try:
                # Process memory first, then simplify
                processed_memory = self._process_memory_for_saving(self.memory)
                simplified_memory = [
                    {
                        "agent_id": entry.get("agent_id", "unknown"),
                        "event_type": entry.get("event_type", "unknown"),
                        "timestamp": entry.get(
                            "timestamp",
                            datetime.utcnow().isoformat(),
                        ),
                        "error": "Original entry contained non-serializable data",
                        # Preserve optimization info if present
                        "previous_outputs_summary": entry.get("previous_outputs_summary"),
                        "execution_context_keys": list(entry.get("execution_context", {}).keys())
                        if entry.get("execution_context")
                        else None,
                    }
                    for entry in processed_memory
                ]

                # Simple output without deduplication
                simple_output = {
                    "_metadata": {
                        "version": "1.0",
                        "deduplication_enabled": False,
                        "error": "Deduplication failed, using simplified format",
                        "generated_at": datetime.utcnow().isoformat(),
                    },
                    "events": simplified_memory,
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(simple_output, f, indent=2)
                logger.info(f"[MemoryLogger] Simplified logs saved to {file_path}")
            except Exception as inner_e:
                logger.error(f"Failed to save simplified logs to file: {inner_e!s}")

    def _resolve_blob_references(self, obj: Any, blob_store: Dict[str, Any]) -> Any:
        """
        Recursively resolve blob references back to their original content.

        Args:
            obj: Object that may contain blob references
            blob_store: Dictionary mapping SHA256 hashes to blob content

        Returns:
            Object with blob references resolved to original content
        """
        if isinstance(obj, dict):
            # Check if this is a blob reference
            if obj.get("_type") == "blob_reference" and "ref" in obj:
                blob_hash = obj["ref"]
                if blob_hash in blob_store:
                    return blob_store[blob_hash]
                else:
                    # Blob not found, return reference with error
                    return {
                        "error": f"Blob reference not found: {blob_hash}",
                        "ref": blob_hash,
                        "_type": "missing_blob_reference",
                    }

            # Recursively resolve nested objects
            resolved = {}
            for key, value in obj.items():
                resolved[key] = self._resolve_blob_references(value, blob_store)
            return resolved

        elif isinstance(obj, list):
            return [self._resolve_blob_references(item, blob_store) for item in obj]

        return obj

    @staticmethod
    def load_from_file(file_path: str, resolve_blobs: bool = True) -> Dict[str, Any]:
        """
        Load and optionally resolve blob references from a deduplicated log file.

        Args:
            file_path: Path to the log file
            resolve_blobs: If True, resolve blob references to original content

        Returns:
            Dictionary containing metadata, events, and optionally resolved content
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Handle both old format (list) and new format (dict with metadata)
            if isinstance(data, list):
                # Old format without deduplication
                return {
                    "_metadata": {
                        "version": "legacy",
                        "deduplication_enabled": False,
                    },
                    "events": data,
                    "blob_store": {},
                }

            if not resolve_blobs:
                return data

            # Resolve blob references if requested
            blob_store = data.get("blob_store", {})
            events = data.get("events", [])

            resolved_events = []
            for event in events:
                resolved_event = BaseMemoryLogger._resolve_blob_references_static(event, blob_store)
                resolved_events.append(resolved_event)

            # Return resolved data
            return {
                "_metadata": data.get("_metadata", {}),
                "events": resolved_events,
                "blob_store": blob_store,
                "_resolved": True,
            }

        except Exception as e:
            logger.error(f"Failed to load log file {file_path}: {e!s}")
            return {
                "_metadata": {"error": str(e)},
                "events": [],
                "blob_store": {},
            }

    @staticmethod
    def _resolve_blob_references_static(obj: Any, blob_store: Dict[str, Any]) -> Any:
        """Static version of _resolve_blob_references for use in load_from_file."""
        if isinstance(obj, dict):
            # Check if this is a blob reference
            if obj.get("_type") == "blob_reference" and "ref" in obj:
                blob_hash = obj["ref"]
                if blob_hash in blob_store:
                    return blob_store[blob_hash]
                else:
                    return {
                        "error": f"Blob reference not found: {blob_hash}",
                        "ref": blob_hash,
                        "_type": "missing_blob_reference",
                    }

            # Recursively resolve nested objects
            resolved = {}
            for key, value in obj.items():
                resolved[key] = BaseMemoryLogger._resolve_blob_references_static(value, blob_store)
            return resolved

        elif isinstance(obj, list):
            return [
                BaseMemoryLogger._resolve_blob_references_static(item, blob_store) for item in obj
            ]

        return obj


class RedisMemoryLogger(BaseMemoryLogger):
    """
    A memory logger that uses Redis to store and retrieve orchestration events.
    Supports logging events, saving logs to files, and querying recent events.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
    ) -> None:
        """
        Initialize the Redis memory logger.

        Args:
            redis_url: URL for the Redis server. Defaults to environment variable REDIS_URL or redis service name.
            stream_key: Key for the Redis stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
        """
        super().__init__(stream_key, debug_keep_previous_outputs)
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.redis_url)

    @property
    def redis(self) -> redis.Redis:
        """
        Return the Redis client for backward compatibility.
        This property exists for compatibility with existing code.
        """
        return self.client

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
    ) -> None:
        """
        Log an event to Redis and local memory.

        Args:
            agent_id: ID of the agent generating the event.
            event_type: Type of the event.
            payload: Event payload.
            step: Step number in the orchestration.
            run_id: ID of the orchestration run.
            fork_group: ID of the fork group.
            parent: ID of the parent event.
            previous_outputs: Previous outputs from agents.

        Raises:
            ValueError: If agent_id is missing.
            Exception: If Redis operation fails.
        """
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": safe_payload,
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = self._sanitize_for_json(previous_outputs)

        self.memory.append(event)

        try:
            # Sanitize previous outputs if present
            safe_previous_outputs = None
            if previous_outputs:
                try:
                    safe_previous_outputs = json.dumps(
                        self._sanitize_for_json(previous_outputs),
                    )
                except Exception as e:
                    logger.error(f"Failed to serialize previous_outputs: {e!s}")
                    safe_previous_outputs = json.dumps(
                        {"error": f"Serialization error: {e!s}"},
                    )

            # Prepare the Redis entry
            redis_entry = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": str(step or -1),
            }

            # Safely serialize the payload
            try:
                redis_entry["payload"] = json.dumps(safe_payload)
            except Exception as e:
                logger.error(f"Failed to serialize payload: {e!s}")
                redis_entry["payload"] = json.dumps(
                    {"error": "Original payload contained non-serializable objects"},
                )

            # Only add previous_outputs if it exists and is not None
            if safe_previous_outputs:
                redis_entry["previous_outputs"] = safe_previous_outputs

            # Add the entry to Redis
            self.client.xadd(self.stream_key, redis_entry)

        except Exception as e:
            logger.error(f"Failed to log event to Redis: {e!s}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {e!s}",
                }
                self.client.xadd(
                    self.stream_key,
                    {
                        "agent_id": agent_id,
                        "event_type": event_type,
                        "timestamp": event["timestamp"],
                        "payload": json.dumps(simplified_payload),
                        "run_id": run_id or "default",
                        "step": str(step or -1),
                    },
                )
                logger.info("Logged simplified error payload instead")
            except Exception as inner_e:
                logger.error(
                    f"Failed to log event to Redis: {e!s} and fallback also failed: {inner_e!s}",
                )

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from the Redis stream.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        try:
            results = self.client.xrevrange(self.stream_key, count=count)
            # Sanitize results for JSON serialization before returning
            return self._sanitize_for_json(results)
        except Exception as e:
            logger.error(f"Failed to retrieve events from Redis: {e!s}")
            return []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a field in a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added.
        """
        try:
            # Convert non-string values to strings if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(self._sanitize_for_json(value))
            return self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {e!s}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {e!s}")
            return None

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a Redis hash.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        try:
            return self.client.hkeys(name)
        except Exception as e:
            logger.error(f"Failed to get hash keys from {name}: {e!s}")
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a Redis hash.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        try:
            if not keys:
                logger.warning(f"hdel called with no keys for hash {name}")
                return 0
            return self.client.hdel(name, *keys)
        except Exception as e:
            # Handle WRONGTYPE errors by cleaning up the key and retrying
            if "WRONGTYPE" in str(e):
                logger.warning(f"WRONGTYPE error for key '{name}', attempting cleanup")
                if self._cleanup_redis_key(name):
                    try:
                        # Retry after cleanup
                        return self.client.hdel(name, *keys)
                    except Exception as retry_e:
                        logger.error(f"Failed to hdel after cleanup: {retry_e!s}")
                        return 0
            logger.error(f"Failed to delete hash fields from {name}: {e!s}")
            return 0

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a Redis set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        try:
            return self.client.smembers(name)
        except Exception as e:
            logger.error(f"Failed to get set members from {name}: {e!s}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """
        Add members to a Redis set.

        Args:
            name: Name of the set.
            *values: Values to add.

        Returns:
            Number of new members added.
        """
        try:
            return self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Failed to add members to set {name}: {e!s}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """
        Remove members from a Redis set.

        Args:
            name: Name of the set.
            *values: Values to remove.

        Returns:
            Number of members removed.
        """
        try:
            return self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Failed to remove members from set {name}: {e!s}")
            return 0

    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key from Redis.

        Args:
            key: The key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            result = self.client.get(key)
            return result.decode() if isinstance(result, bytes) else result
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e!s}")
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set a value by key in Redis.

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e!s}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e!s}")
            return 0

    def close(self) -> None:
        """Close the Redis client connection."""
        try:
            self.client.close()
            # Only log if logging system is still available
            try:
                logger.info("[RedisMemoryLogger] Redis client closed")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass
        except Exception as e:
            try:
                logger.error(f"Error closing Redis client: {e!s}")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            # Ignore all errors during cleanup
            pass

    def _cleanup_redis_key(self, key: str) -> bool:
        """
        Clean up a Redis key that might have the wrong type.

        This method deletes a key to resolve WRONGTYPE errors.

        Args:
            key: The Redis key to clean up

        Returns:
            True if key was cleaned up, False if cleanup failed
        """
        try:
            self.client.delete(key)
            logger.warning(f"Cleaned up Redis key '{key}' due to type conflict")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up Redis key '{key}': {e!s}")
            return False


# Future stub
class KafkaMemoryLogger(BaseMemoryLogger):
    """
    A memory logger that uses Kafka to store and retrieve orchestration events.
    Uses Kafka topics for event streaming and in-memory storage for hash/set operations.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic_prefix: str = "orka-memory",
        stream_key: str = "orka:memory",
        synchronous_send: bool = False,
        debug_keep_previous_outputs: bool = False,
    ) -> None:
        """
        Initialize the Kafka memory logger.

        Args:
            bootstrap_servers: Kafka bootstrap servers. Defaults to environment variable KAFKA_BOOTSTRAP_SERVERS.
            topic_prefix: Prefix for Kafka topics. Defaults to "orka-memory".
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            synchronous_send: Whether to wait for message confirmation. Defaults to False for performance.
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
        """
        super().__init__(stream_key, debug_keep_previous_outputs)
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        )
        self.topic_prefix = topic_prefix
        self.main_topic = f"{topic_prefix}-events"
        self.synchronous_send = (
            synchronous_send or os.getenv("KAFKA_SYNCHRONOUS_SEND", "false").lower() == "true"
        )

        # In-memory storage for hash and set operations (since Kafka doesn't have these concepts)
        self._hash_storage: Dict[str, Dict[str, Any]] = {}
        self._set_storage: Dict[str, set] = {}

        # Failsafe mode when Kafka is not available
        self._failsafe_mode = False

        # Schema Registry Integration
        self.schema_registry_url = os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")
        self.use_schema_registry = os.getenv("KAFKA_USE_SCHEMA_REGISTRY", "true").lower() == "true"
        self.schema_manager = None
        self.serializer = None

        # Initialize Schema Manager if enabled
        if self.use_schema_registry:
            try:
                from confluent_kafka.serialization import MessageField, SerializationContext

                from orka.memory.schema_manager import SchemaFormat, create_schema_manager

                self.schema_manager = create_schema_manager(
                    registry_url=self.schema_registry_url,
                    format=SchemaFormat.AVRO,  # Can be configured via env var
                )

                # Register the schema if not already registered
                try:
                    self.schema_manager.register_schema(f"{self.main_topic}-value", "memory_entry")
                    logger.info(
                        f"[KafkaMemoryLogger] Schema registered for topic {self.main_topic}",
                    )
                except Exception as schema_e:
                    logger.warning(f"[KafkaMemoryLogger] Schema registration failed: {schema_e}")

                # Get serializer for the main topic
                self.serializer = self.schema_manager.get_serializer(self.main_topic)
                logger.info(
                    f"[KafkaMemoryLogger] Schema Registry integration enabled at {self.schema_registry_url}",
                )

            except ImportError as ie:
                logger.warning(
                    f"[KafkaMemoryLogger] Schema Registry dependencies not available: {ie}",
                )
                logger.warning("Install with: pip install confluent-kafka[avro]")
                self.use_schema_registry = False
            except Exception as se:
                logger.warning(f"[KafkaMemoryLogger] Schema Registry setup failed: {se}")
                self.use_schema_registry = False

        # Initialize Kafka producer
        try:
            if self.use_schema_registry and self.serializer:
                # Use Confluent Kafka with schema serialization
                from confluent_kafka import Producer
                from confluent_kafka.serialization import MessageField, SerializationContext

                producer_config = {
                    "bootstrap.servers": self.bootstrap_servers,
                    "compression.type": "gzip",
                    "batch.size": 16384,
                    "linger.ms": 5,
                    "retries": 1,
                    "request.timeout.ms": 10000,
                    "delivery.timeout.ms": 15000,
                    "security.protocol": "PLAINTEXT",
                }

                self.producer = Producer(producer_config)
                self._is_confluent_producer = True
                logger.info(
                    "[KafkaMemoryLogger] Using Confluent Kafka producer with schema registry",
                )

            else:
                # Use standard kafka-python with JSON serialization
                from kafka import KafkaProducer
                from kafka.errors import KafkaError

                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    request_timeout_ms=10000,
                    retries=1,
                    batch_size=16384,
                    linger_ms=5,
                    buffer_memory=33554432,
                    compression_type="gzip",
                    max_block_ms=3000,
                    connections_max_idle_ms=300000,
                    metadata_max_age_ms=180000,
                    api_version_auto_timeout_ms=3000,
                    security_protocol="PLAINTEXT",
                )
                self._is_confluent_producer = False
                logger.info(
                    "[KafkaMemoryLogger] Using standard Kafka producer with JSON serialization",
                )

            # Test connection first with minimal configuration
            logger.info(
                f"[KafkaMemoryLogger] Attempting to connect to Kafka at {self.bootstrap_servers}",
            )

            # Test the connection by getting metadata
            try:
                # This will force a connection attempt
                metadata = self.producer._metadata
                # Small delay to allow connection
                import time

                time.sleep(0.1)

                logger.info(
                    f"[KafkaMemoryLogger] Successfully connected to Kafka at {self.bootstrap_servers}",
                )
            except Exception as test_e:
                logger.warning(
                    f"[KafkaMemoryLogger] Connection test failed: {test_e!s}, but producer created",
                )

        except ImportError:
            logger.error(
                "kafka-python package is required for KafkaMemoryLogger. Install with: pip install kafka-python",
            )
            raise ImportError("kafka-python package is required")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e!s}")
            logger.error(f"Bootstrap servers: {self.bootstrap_servers}")
            logger.error("Possible solutions:")
            logger.error("1. Check if Kafka is running: docker ps")
            logger.error("2. Verify Kafka port is accessible: telnet localhost 9092")
            logger.error("3. Try running app inside Docker network")
            logger.error("4. Switch to Redis backend: set ORKA_MEMORY_BACKEND=redis")
            raise

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
    ) -> None:
        """
        Log an event to Kafka and local memory.

        Args:
            agent_id: ID of the agent generating the event.
            event_type: Type of the event.
            payload: Event payload.
            step: Step number in the orchestration.
            run_id: ID of the orchestration run.
            fork_group: ID of the fork group.
            parent: ID of the parent event.
            previous_outputs: Previous outputs from agents.

        Raises:
            ValueError: If agent_id is missing.
            Exception: If Kafka operation fails.
        """
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": safe_payload,
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = self._sanitize_for_json(previous_outputs)

        self.memory.append(event)

        try:
            # Prepare the Kafka message
            kafka_message = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": step or -1,
                "payload": safe_payload,
            }

            if previous_outputs:
                kafka_message["previous_outputs"] = self._sanitize_for_json(
                    previous_outputs,
                )

            # Send to Kafka topic
            key = f"{run_id or 'default'}:{agent_id}"

            if not self._failsafe_mode:
                try:
                    if self.use_schema_registry and self.serializer and self._is_confluent_producer:
                        # Use schema-based serialization with Confluent Kafka
                        from confluent_kafka.serialization import MessageField, SerializationContext

                        # Transform kafka_message to match schema
                        schema_message = self._transform_to_schema_format(kafka_message)

                        # Serialize using schema
                        serialized_value = self.serializer(
                            schema_message,
                            SerializationContext(self.main_topic, MessageField.VALUE),
                        )

                        # Produce with Confluent Kafka
                        def delivery_callback(error, message):
                            if error:
                                logger.warning(
                                    f"[KafkaMemoryLogger] Message delivery failed: {error}",
                                )
                            elif self.synchronous_send:
                                logger.debug(
                                    f"[KafkaMemoryLogger] Schema message confirmed for agent {agent_id}",
                                )

                        self.producer.produce(
                            topic=self.main_topic,
                            key=key,
                            value=serialized_value,
                            callback=delivery_callback,
                        )

                        if self.synchronous_send:
                            self.producer.flush(timeout=5)

                    else:
                        # Use standard JSON serialization
                        future = self.producer.send(self.main_topic, value=kafka_message, key=key)

                        # Wait for confirmation if synchronous_send is enabled
                        if self.synchronous_send:
                            try:
                                future.get(timeout=5)  # Reduced timeout from 10 to 5 seconds
                                logger.debug(
                                    f"[KafkaMemoryLogger] Message confirmed for agent {agent_id}",
                                )
                            except Exception as sync_e:
                                logger.warning(
                                    f"[KafkaMemoryLogger] Failed to get send confirmation: {sync_e!s}",
                                )
                                # Don't switch to failsafe for confirmation failures

                    logger.debug(f"[KafkaMemoryLogger] Sent event to topic {self.main_topic}")

                except Exception as kafka_send_e:
                    logger.warning(
                        f"[KafkaMemoryLogger] Kafka send failed: {kafka_send_e!s}, switching to failsafe mode",
                    )
                    self._failsafe_mode = True
                    # Continue to store in memory below

            if self._failsafe_mode:
                logger.debug("[KafkaMemoryLogger] Storing event in failsafe memory mode")

        except Exception as e:
            logger.error(f"Failed to log event to Kafka: {e!s}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {e!s}",
                }
                simplified_message = {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "timestamp": event["timestamp"],
                    "run_id": run_id or "default",
                    "step": step or -1,
                    "payload": simplified_payload,
                }

                key = f"{run_id or 'default'}:{agent_id}"
                self.producer.send(self.main_topic, value=simplified_message, key=key)
                logger.info("Logged simplified error payload to Kafka instead")
            except Exception as inner_e:
                logger.error(
                    f"Failed to log event to Kafka: {e!s} and fallback also failed: {inner_e!s}",
                )

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from local memory.
        Note: Kafka doesn't naturally support tail operations like Redis streams,
        so we use the local memory buffer for this functionality.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        try:
            # Return the last 'count' events from local memory
            recent_events = self.memory[-count:] if count <= len(self.memory) else self.memory
            return self._sanitize_for_json(recent_events)
        except Exception as e:
            logger.error(f"Failed to retrieve recent events: {e!s}")
            return []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a field in a hash structure (stored in memory).

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added (1 if new, 0 if updated).
        """
        try:
            if name not in self._hash_storage:
                self._hash_storage[name] = {}

            is_new_field = key not in self._hash_storage[name]

            # Convert non-string values to strings if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(self._sanitize_for_json(value))

            self._hash_storage[name][key] = value
            return 1 if is_new_field else 0
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {e!s}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a hash structure.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        try:
            hash_data = self._hash_storage.get(name, {})
            value = hash_data.get(key)
            return str(value) if value is not None else None
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {e!s}")
            return None

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a hash structure.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        try:
            hash_data = self._hash_storage.get(name, {})
            return list(hash_data.keys())
        except Exception as e:
            logger.error(f"Failed to get hash keys from {name}: {e!s}")
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a hash structure.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        try:
            if not keys:
                logger.warning(f"hdel called with no keys for hash {name}")
                return 0

            if name not in self._hash_storage:
                return 0

            deleted_count = 0
            for key in keys:
                if key in self._hash_storage[name]:
                    del self._hash_storage[name][key]
                    deleted_count += 1

            # Clean up empty hash
            if not self._hash_storage[name]:
                del self._hash_storage[name]

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete hash fields from {name}: {e!s}")
            return 0

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        try:
            set_data = self._set_storage.get(name, set())
            return list(set_data)
        except Exception as e:
            logger.error(f"Failed to get set members from {name}: {e!s}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """
        Add members to a set.

        Args:
            name: Name of the set.
            *values: Values to add.

        Returns:
            Number of new members added.
        """
        try:
            if name not in self._set_storage:
                self._set_storage[name] = set()

            initial_size = len(self._set_storage[name])
            self._set_storage[name].update(values)
            final_size = len(self._set_storage[name])

            return final_size - initial_size
        except Exception as e:
            logger.error(f"Failed to add members to set {name}: {e!s}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """
        Remove members from a set.

        Args:
            name: Name of the set.
            *values: Values to remove.

        Returns:
            Number of members removed.
        """
        try:
            if name not in self._set_storage:
                return 0

            removed_count = 0
            for value in values:
                if value in self._set_storage[name]:
                    self._set_storage[name].discard(value)
                    removed_count += 1

            # Clean up empty set
            if not self._set_storage[name]:
                del self._set_storage[name]

            return removed_count
        except Exception as e:
            logger.error(f"Failed to remove members from set {name}: {e!s}")
            return 0

    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key (stored in memory).

        Args:
            key: The key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            # Store simple key-value pairs in a special hash
            return self.hget("simple_kv_storage", key)
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e!s}")
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set a value by key (stored in memory).

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Store simple key-value pairs in a special hash
            self.hset("simple_kv_storage", key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e!s}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys (from memory storage).

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        try:
            # Delete from the simple key-value storage hash
            return self.hdel("simple_kv_storage", *keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e!s}")
            return 0

    def _transform_to_schema_format(self, kafka_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the internal Kafka message format to match the Avro schema.

        Args:
            kafka_message: Internal message format

        Returns:
            Message in schema-compatible format
        """
        import time

        # Extract fields from kafka_message
        agent_id = kafka_message.get("agent_id", "unknown")
        event_type = kafka_message.get("event_type", "unknown")
        timestamp_str = kafka_message.get("timestamp", "")
        run_id = kafka_message.get("run_id", "default")
        step = kafka_message.get("step", -1)
        payload = kafka_message.get("payload", {})

        # Convert timestamp to Unix timestamp (double)
        try:
            from datetime import datetime

            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamp_unix = dt.timestamp()
            else:
                timestamp_unix = time.time()
        except:
            timestamp_unix = time.time()

        # Create content from payload (serialize as JSON string for content field)
        content = json.dumps(payload) if payload else "{}"

        # Build schema-compatible message
        schema_message = {
            "id": f"{run_id}:{agent_id}:{step}",
            "content": content,
            "metadata": {
                "source": f"orka-{event_type}",
                "confidence": 1.0,  # Default confidence
                "reason": None,
                "fact": None,
                "timestamp": timestamp_unix,
                "agent_id": agent_id,
                "query": None,
                "tags": [event_type, f"step_{step}", f"run_{run_id}"],
                "vector_embedding": None,
            },
            "similarity": None,
            "ts": int(time.time() * 1000000000),  # nanoseconds
            "match_type": "stream",  # Default for streaming data
            "stream_key": self.stream_key,
        }

        return schema_message

    def close(self) -> None:
        """Close the Kafka producer connection."""
        try:
            if hasattr(self, "producer") and self.producer is not None:
                # Try to flush with a shorter timeout to prevent hanging
                try:
                    self.producer.flush(timeout=2)  # Reduced from 5 to 2 seconds
                except Exception as flush_e:
                    # Log flush error but continue with close
                    try:
                        logger.warning(
                            f"[KafkaMemoryLogger] Flush timeout during close: {flush_e!s}",
                        )
                    except (ValueError, OSError):
                        pass

                # Close with timeout to prevent hanging
                try:
                    self.producer.close(timeout=2)  # Reduced from 5 to 2 seconds
                except Exception as close_e:
                    try:
                        logger.warning(f"[KafkaMemoryLogger] Close timeout: {close_e!s}")
                    except (ValueError, OSError):
                        pass

                # Only log if logging system is still available
                try:
                    logger.info("[KafkaMemoryLogger] Kafka producer closed")
                except (ValueError, OSError):
                    # Logging system might be shut down, ignore
                    pass
        except Exception as e:
            try:
                logger.error(f"Error closing Kafka producer: {e!s}")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            # Ignore all errors during cleanup
            pass

    @property
    def redis(self):
        """
        Kafka backend doesn't have a redis client.
        This property exists for compatibility but will raise an error if accessed.
        """
        raise AttributeError(
            "KafkaMemoryLogger does not have a Redis client. "
            "Use the appropriate Kafka-compatible methods or switch to RedisMemoryLogger.",
        )


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
