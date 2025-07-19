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

"""Provide file operations for memory loggers."""

import json
import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, TypeVar, Union, cast

logger = logging.getLogger(__name__)

# Type aliases
MemoryEntry = Dict[str, Any]
BlobStore = Dict[str, Any]
BlobStats = Dict[str, Union[int, float]]
OutputData = Dict[str, Any]
JsonSerializable = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]

# Generic type for collections
T = TypeVar("T")


class FileOperationsMixin:
    """Provide file operations for memory loggers."""

    def __init__(self) -> None:
        """Initialize file operations mixin."""
        self.memory: List[MemoryEntry] = []
        self._blob_store: BlobStore = {}
        self._blob_threshold: int = 1000  # Characters threshold for blob deduplication
        self.producer: Optional[Any] = None  # Kafka producer if used

    def _process_memory_for_saving(self, memory_entries: List[MemoryEntry]) -> List[MemoryEntry]:
        """
        Process memory entries before saving.

        Args:
            memory_entries: List of memory entries to process

        Returns:
            Processed memory entries
        """
        raise NotImplementedError("Subclass must implement _process_memory_for_saving")

    def _sanitize_for_json(self, obj: Any) -> JsonSerializable:
        """
        Sanitize object for JSON serialization.

        Args:
            obj: Object to sanitize

        Returns:
            JSON-serializable version of the object
        """
        raise NotImplementedError("Subclass must implement _sanitize_for_json")

    def _deduplicate_object(self, obj: Any) -> Any:
        """
        Deduplicate object by replacing repeated content with references.

        Args:
            obj: Object to deduplicate

        Returns:
            Deduplicated object
        """
        raise NotImplementedError("Subclass must implement _deduplicate_object")

    def _should_use_deduplication_format(self) -> bool:
        """
        Determine if deduplication format should be used.

        Returns:
            True if deduplication format should be used, False otherwise
        """
        raise NotImplementedError("Subclass must implement _should_use_deduplication_format")

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
            if hasattr(self, "producer") and self.producer is not None:
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
            sanitized_memory = cast(List[MemoryEntry], self._sanitize_for_json(processed_memory))

            # Apply blob deduplication to reduce size
            deduplicated_memory: List[MemoryEntry] = []
            blob_stats: BlobStats = {
                "total_entries": len(sanitized_memory),
                "deduplicated_blobs": 0,
                "size_reduction": 0.0,
            }

            for entry in sanitized_memory:
                original_size = len(json.dumps(entry, separators=(",", ":")))
                deduplicated_entry = cast(MemoryEntry, self._deduplicate_object(entry))
                new_size = len(json.dumps(deduplicated_entry, separators=(",", ":")))

                if new_size < original_size:
                    blob_stats["deduplicated_blobs"] = (
                        cast(int, blob_stats["deduplicated_blobs"]) + 1
                    )
                    blob_stats["size_reduction"] = cast(
                        float, blob_stats["size_reduction"]
                    ) + float(original_size - new_size)

                deduplicated_memory.append(deduplicated_entry)

            # Decide whether to use deduplication format
            use_dedup_format = self._should_use_deduplication_format()

            if use_dedup_format:
                # Create the final output structure with deduplication
                output_data: OutputData = {
                    "_metadata": {
                        "version": "1.0",
                        "deduplication_enabled": True,
                        "blob_threshold_chars": self._blob_threshold,
                        "total_blobs_stored": len(self._blob_store),
                        "stats": blob_stats,
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                    "blob_store": self._blob_store if self._blob_store else {},
                    "events": deduplicated_memory,
                }
            else:
                # Use legacy format (resolve all blob references back to original data)
                resolved_events: List[MemoryEntry] = []
                for entry in deduplicated_memory:
                    resolved_entry = cast(
                        MemoryEntry, self._resolve_blob_references(entry, self._blob_store)
                    )
                    resolved_events.append(resolved_entry)
                output_data = {
                    "_metadata": {
                        "version": "1.0",
                        "deduplication_enabled": False,
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                    "events": resolved_events,
                }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    output_data,
                    f,
                    indent=2,
                    default=lambda o: f"<non-serializable: {type(o).__name__}>",
                )

            # Log deduplication statistics
            if use_dedup_format and cast(int, blob_stats["deduplicated_blobs"]) > 0:
                total_size = sum(
                    len(json.dumps(entry, separators=(",", ":"))) for entry in sanitized_memory
                )
                reduction_pct = (
                    cast(float, blob_stats["size_reduction"]) / float(total_size)
                ) * 100.0
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
                simplified_memory: List[MemoryEntry] = [
                    {
                        "agent_id": entry.get("agent_id", "unknown"),
                        "event_type": entry.get("event_type", "unknown"),
                        "timestamp": entry.get(
                            "timestamp",
                            datetime.now(UTC).isoformat(),
                        ),
                        "error": "Original entry contained non-serializable data",
                        # Preserve optimization info if present
                        "previous_outputs_summary": entry.get("previous_outputs_summary"),
                        "execution_context_keys": (
                            list(entry.get("execution_context", {}).keys())
                            if entry.get("execution_context")
                            else None
                        ),
                    }
                    for entry in processed_memory
                ]

                # Simple output without deduplication
                simple_output: OutputData = {
                    "_metadata": {
                        "version": "1.0",
                        "deduplication_enabled": False,
                        "error": "Deduplication failed, using simplified format",
                        "generated_at": datetime.now(UTC).isoformat(),
                    },
                    "events": simplified_memory,
                }

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(simple_output, f, indent=2)
                logger.info(f"[MemoryLogger] Simplified logs saved to {file_path}")
            except Exception as inner_e:
                logger.error(f"Failed to save simplified logs to file: {inner_e!s}")

    def _resolve_blob_references(self, obj: Any, blob_store: BlobStore) -> Any:
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
            resolved: Dict[str, Any] = {}
            for key, value in obj.items():
                resolved[key] = self._resolve_blob_references(value, blob_store)
            return resolved

        elif isinstance(obj, list):
            return [self._resolve_blob_references(item, blob_store) for item in obj]

        return obj

    @staticmethod
    def load_from_file(file_path: str, resolve_blobs: bool = True) -> OutputData:
        """
        Load and resolve blob references from a deduplicated log file.

        Args:
            file_path: Path to the log file
            resolve_blobs: If True, resolve blob references to original content

        Returns:
            Dictionary containing the loaded log data
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not resolve_blobs:
            return data

        # Check if this is a deduplicated file
        if not isinstance(data, dict) or "_metadata" not in data:
            return data

        metadata = data.get("_metadata", {})
        if not metadata.get("deduplication_enabled", False):
            return data

        # Get blob store and events
        blob_store = data.get("blob_store", {})
        events = data.get("events", [])

        # Resolve all blob references
        resolved_events = [
            FileOperationsMixin._resolve_blob_references_static(event, blob_store)
            for event in events
        ]

        # Return resolved data
        return {
            "_metadata": metadata,
            "events": resolved_events,
        }

    @staticmethod
    def _resolve_blob_references_static(obj: Any, blob_store: BlobStore) -> Any:
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
            resolved: Dict[str, Any] = {}
            for key, value in obj.items():
                resolved[key] = FileOperationsMixin._resolve_blob_references_static(
                    value, blob_store
                )
            return resolved

        elif isinstance(obj, list):
            return [
                FileOperationsMixin._resolve_blob_references_static(item, blob_store)
                for item in obj
            ]

        return obj
