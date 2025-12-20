# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Blob Deduplication Mixin
========================

Methods for blob deduplication to reduce storage overhead.
"""

import hashlib
import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class BlobDeduplicationMixin:
    """Mixin providing blob deduplication methods."""

    # Expected from host class
    _blob_store: dict[str, Any]
    _blob_usage: dict[str, int]
    _blob_threshold: int

    def _compute_blob_hash(self, obj: Any) -> str:
        """
        Compute SHA256 hash of a JSON-serializable object.

        Args:
            obj: Object to hash

        Returns:
            SHA256 hash as hex string
        """
        try:
            json_str = json.dumps(
                obj, sort_keys=True, separators=(",", ":"), default=json_serializer
            )
            return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
        except Exception:
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
            if not isinstance(obj, dict):
                return False

            json_str = json.dumps(obj, separators=(",", ":"), default=json_serializer)
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

        if blob_hash not in self._blob_store:
            self._blob_store[blob_hash] = obj
            self._blob_usage[blob_hash] = 0

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
            original_keys: List of keys from the original object

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

    def _recursive_deduplicate(self, obj: Any) -> Any:
        """Recursively apply deduplication."""
        if isinstance(obj, dict):
            return self._deduplicate_dict_content(obj)
        elif isinstance(obj, list):
            return [self._recursive_deduplicate(item) for item in obj]
        else:
            return obj

    def _deduplicate_dict_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively deduplicate content within a dictionary.
        """
        processed_data = {}
        for key, value in data.items():
            processed_data[key] = self._recursive_deduplicate(value)

        if self._should_deduplicate_blob(processed_data):
            blob_hash = self._store_blob(processed_data)
            return self._create_blob_reference(blob_hash, list(processed_data.keys()))

        return processed_data

    def _should_use_deduplication_format(self) -> bool:
        """
        Determine whether to use deduplication format for saving logs.
        """
        return bool(self._blob_store)

