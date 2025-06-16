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
Serialization utilities for memory loggers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SerializationMixin:
    """
    Mixin class providing JSON serialization capabilities for memory loggers.
    """

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
