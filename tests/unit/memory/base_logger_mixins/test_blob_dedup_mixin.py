# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for BlobDeduplicationMixin."""

import pytest

from orka.memory.base_logger_mixins.blob_dedup_mixin import (
    BlobDeduplicationMixin,
    json_serializer,
)


class ConcreteBlobDedup(BlobDeduplicationMixin):
    """Concrete implementation for testing."""

    def __init__(self):
        self._blob_store = {}
        self._blob_usage = {}
        self._blob_threshold = 200


class TestBlobDeduplicationMixin:
    """Tests for BlobDeduplicationMixin."""

    @pytest.fixture
    def dedup(self):
        return ConcreteBlobDedup()

    def test_compute_blob_hash_consistent(self, dedup):
        """Test hash is consistent for same object."""
        obj = {"key": "value", "number": 42}
        hash1 = dedup._compute_blob_hash(obj)
        hash2 = dedup._compute_blob_hash(obj)
        assert hash1 == hash2

    def test_compute_blob_hash_different(self, dedup):
        """Test hash is different for different objects."""
        hash1 = dedup._compute_blob_hash({"a": 1})
        hash2 = dedup._compute_blob_hash({"b": 2})
        assert hash1 != hash2

    def test_compute_blob_hash_order_independent(self, dedup):
        """Test hash is independent of key order."""
        hash1 = dedup._compute_blob_hash({"a": 1, "b": 2})
        hash2 = dedup._compute_blob_hash({"b": 2, "a": 1})
        assert hash1 == hash2

    def test_should_deduplicate_blob_small(self, dedup):
        """Test small objects are not deduplicated."""
        small_obj = {"key": "value"}
        assert dedup._should_deduplicate_blob(small_obj) is False

    def test_should_deduplicate_blob_large(self, dedup):
        """Test large objects are deduplicated."""
        large_obj = {"key": "x" * 300}
        assert dedup._should_deduplicate_blob(large_obj) is True

    def test_should_deduplicate_blob_non_dict(self, dedup):
        """Test non-dict objects are not deduplicated."""
        assert dedup._should_deduplicate_blob("string") is False
        assert dedup._should_deduplicate_blob([1, 2, 3]) is False

    def test_store_blob(self, dedup):
        """Test storing a blob."""
        obj = {"test": "data"}
        blob_hash = dedup._store_blob(obj)

        assert blob_hash in dedup._blob_store
        assert dedup._blob_store[blob_hash] == obj
        assert dedup._blob_usage[blob_hash] == 1

    def test_store_blob_increment_usage(self, dedup):
        """Test storing same blob increments usage."""
        obj = {"test": "data"}
        dedup._store_blob(obj)
        dedup._store_blob(obj)

        assert dedup._blob_usage[dedup._compute_blob_hash(obj)] == 2

    def test_create_blob_reference(self, dedup):
        """Test creating blob reference."""
        ref = dedup._create_blob_reference("abc123", ["key1", "key2"])

        assert ref["ref"] == "abc123"
        assert ref["_type"] == "blob_reference"
        assert ref["_original_keys"] == ["key1", "key2"]

    def test_recursive_deduplicate_small(self, dedup):
        """Test small dicts are not replaced."""
        obj = {"key": "value"}
        result = dedup._recursive_deduplicate(obj)
        assert result == obj

    def test_recursive_deduplicate_list(self, dedup):
        """Test list items are processed."""
        obj = [{"a": 1}, {"b": 2}]
        result = dedup._recursive_deduplicate(obj)
        assert len(result) == 2

    def test_deduplicate_dict_content(self, dedup):
        """Test large dict becomes reference."""
        large_obj = {"content": "x" * 300}
        result = dedup._deduplicate_dict_content(large_obj)

        assert result.get("_type") == "blob_reference"
        assert "ref" in result

    def test_should_use_deduplication_format(self, dedup):
        """Test deduplication format detection."""
        assert dedup._should_use_deduplication_format() is False

        dedup._blob_store["hash"] = {"test": "data"}
        assert dedup._should_use_deduplication_format() is True


class TestJsonSerializer:
    """Tests for json_serializer function."""

    def test_datetime_serialization(self):
        """Test datetime is serialized to ISO format."""
        from datetime import datetime, UTC

        dt = datetime(2025, 12, 20, 14, 30, 0, tzinfo=UTC)
        result = json_serializer(dt)
        assert "2025-12-20" in result

    def test_unsupported_type_raises(self):
        """Test unsupported types raise TypeError."""
        with pytest.raises(TypeError):
            json_serializer(object())

