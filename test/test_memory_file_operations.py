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

import json
import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from orka.memory.file_operations import FileOperationsMixin


class TestFileOperationsMixin:
    """Test suite for FileOperationsMixin functionality"""

    @pytest.fixture
    def file_ops_instance(self):
        """Create a test instance with FileOperationsMixin"""

        class TestFileOps(FileOperationsMixin):
            def __init__(self):
                self.memory = [
                    {
                        "agent_id": "test1",
                        "event_type": "start",
                        "timestamp": "2025-01-01T00:00:00",
                    },
                    {"agent_id": "test2", "event_type": "end", "timestamp": "2025-01-01T00:01:00"},
                ]
                self._blob_store = {}
                self._blob_threshold = 1000

            def _process_memory_for_saving(self, memory):
                return memory

            def _sanitize_for_json(self, data):
                return data

            def _deduplicate_object(self, obj):
                return obj

            def _should_use_deduplication_format(self):
                return True

        return TestFileOps()

    def test_save_to_file_basic(self, file_ops_instance):
        """Test basic file saving functionality"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            file_ops_instance.save_to_file(tmp_path)

            # Verify file was created and contains expected data
            assert os.path.exists(tmp_path)

            with open(tmp_path) as f:
                data = json.load(f)

            assert "_metadata" in data
            assert "events" in data
            assert data["_metadata"]["deduplication_enabled"] is True
            assert len(data["events"]) == 2

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_with_kafka_producer(self, file_ops_instance):
        """Test file saving with Kafka producer flush"""
        # Add mock producer
        file_ops_instance.producer = MagicMock()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            file_ops_instance.save_to_file(tmp_path)

            # Verify producer flush was called
            file_ops_instance.producer.flush.assert_called_once_with(timeout=3)

            # Verify file was still created
            assert os.path.exists(tmp_path)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_kafka_flush_failure(self, file_ops_instance):
        """Test file saving when Kafka flush fails"""
        # Add mock producer that fails on flush
        file_ops_instance.producer = MagicMock()
        file_ops_instance.producer.flush.side_effect = Exception("Flush failed")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            with patch("orka.memory.file_operations.logger") as mock_logger:
                file_ops_instance.save_to_file(tmp_path)

                # Should log warning but continue
                mock_logger.warning.assert_called_once()

            # File should still be created
            assert os.path.exists(tmp_path)

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_with_deduplication_stats(self, file_ops_instance):
        """Test file saving with blob deduplication statistics"""
        # Mock deduplication to show size reduction
        original_deduplicate = file_ops_instance._deduplicate_object

        def mock_deduplicate(obj):
            # Simulate size reduction by removing a field
            if isinstance(obj, dict) and "timestamp" in obj:
                reduced_obj = obj.copy()
                reduced_obj["_blob_ref"] = "abc123"
                del reduced_obj["timestamp"]
                return reduced_obj
            return obj

        file_ops_instance._deduplicate_object = mock_deduplicate
        file_ops_instance._blob_store = {"abc123": "2025-01-01T00:00:00"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            with patch("orka.memory.file_operations.logger") as mock_logger:
                file_ops_instance.save_to_file(tmp_path)

                # Should log deduplication statistics
                mock_logger.info.assert_called()
                log_message = mock_logger.info.call_args[0][0]
                assert "deduplicated" in log_message

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_legacy_format(self, file_ops_instance):
        """Test file saving in legacy format"""
        # Configure to use legacy format
        file_ops_instance._should_use_deduplication_format = lambda: False

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            file_ops_instance.save_to_file(tmp_path)

            with open(tmp_path) as f:
                data = json.load(f)

            # Should be a list, not a dict with metadata
            assert isinstance(data, list)
            assert len(data) == 2

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_serialization_error(self, file_ops_instance):
        """Test file saving when serialization fails"""
        # Mock to cause serialization error
        file_ops_instance._sanitize_for_json = MagicMock(
            side_effect=Exception("Serialization failed"),
        )

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            with patch("orka.memory.file_operations.logger") as mock_logger:
                file_ops_instance.save_to_file(tmp_path)

                # Should log error and create simplified format
                mock_logger.error.assert_called()
                mock_logger.info.assert_called()

            # File should still be created with simplified content
            assert os.path.exists(tmp_path)

            with open(tmp_path) as f:
                data = json.load(f)

            assert "_metadata" in data
            assert data["_metadata"]["error"] == "Deduplication failed, using simplified format"

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_save_to_file_complete_failure(self, file_ops_instance):
        """Test file saving when everything fails"""
        # Mock to cause all operations to fail
        with patch("builtins.open", side_effect=OSError("Cannot write file")):
            with patch("orka.memory.file_operations.logger") as mock_logger:
                file_ops_instance.save_to_file("nonexistent/path/file.json")

                # Should log error twice (main error and simplified error)
                assert mock_logger.error.call_count == 2

    def test_resolve_blob_references_basic(self, file_ops_instance):
        """Test basic blob reference resolution"""
        blob_store = {"hash123": {"original": "data"}}
        obj_with_ref = {"_type": "blob_reference", "ref": "hash123"}

        result = file_ops_instance._resolve_blob_references(obj_with_ref, blob_store)

        assert result == {"original": "data"}

    def test_resolve_blob_references_missing(self, file_ops_instance):
        """Test blob reference resolution with missing blob"""
        blob_store = {}
        obj_with_ref = {"_type": "blob_reference", "ref": "missing_hash"}

        result = file_ops_instance._resolve_blob_references(obj_with_ref, blob_store)

        assert result["error"] == "Blob reference not found: missing_hash"
        assert result["_type"] == "missing_blob_reference"

    def test_resolve_blob_references_nested(self, file_ops_instance):
        """Test blob reference resolution in nested structures"""
        blob_store = {"hash123": "resolved_value"}
        nested_obj = {
            "level1": {
                "level2": [
                    {"_type": "blob_reference", "ref": "hash123"},
                    "normal_value",
                ],
            },
            "other": "data",
        }

        result = file_ops_instance._resolve_blob_references(nested_obj, blob_store)

        assert result["level1"]["level2"][0] == "resolved_value"
        assert result["level1"]["level2"][1] == "normal_value"
        assert result["other"] == "data"

    def test_resolve_blob_references_list(self, file_ops_instance):
        """Test blob reference resolution in lists"""
        blob_store = {"hash123": "resolved_value"}
        list_obj = [
            {"_type": "blob_reference", "ref": "hash123"},
            "normal_item",
            {"nested": {"_type": "blob_reference", "ref": "hash123"}},
        ]

        result = file_ops_instance._resolve_blob_references(list_obj, blob_store)

        assert result[0] == "resolved_value"
        assert result[1] == "normal_item"
        assert result[2]["nested"] == "resolved_value"

    def test_resolve_blob_references_non_dict_list(self, file_ops_instance):
        """Test blob reference resolution with non-dict/list objects"""
        blob_store = {}

        # Test with string
        result = file_ops_instance._resolve_blob_references("simple_string", blob_store)
        assert result == "simple_string"

        # Test with number
        result = file_ops_instance._resolve_blob_references(42, blob_store)
        assert result == 42

        # Test with None
        result = file_ops_instance._resolve_blob_references(None, blob_store)
        assert result is None

    @patch("orka.memory.file_operations.json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_file_basic(self, mock_file_open, mock_json_load):
        """Test basic file loading functionality"""
        # Mock file content
        mock_data = {
            "_metadata": {"deduplication_enabled": True},
            "blob_store": {"hash123": "blob_data"},
            "events": [{"_type": "blob_reference", "ref": "hash123"}],
        }
        mock_json_load.return_value = mock_data

        result = FileOperationsMixin.load_from_file("test.json")

        # Should resolve blob references by default
        assert result["events"][0] == "blob_data"
        assert result["_resolved"] is True
        mock_file_open.assert_called_once_with("test.json", encoding="utf-8")

    @patch("orka.memory.file_operations.json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_file_no_resolve(self, mock_file_open, mock_json_load):
        """Test file loading without blob resolution"""
        mock_data = {
            "_metadata": {"deduplication_enabled": True},
            "blob_store": {"hash123": "blob_data"},
            "events": [{"_type": "blob_reference", "ref": "hash123"}],
        }
        mock_json_load.return_value = mock_data

        result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=False)

        # Should not resolve blob references
        assert result["events"][0]["_type"] == "blob_reference"
        assert "_resolved" not in result

    @patch("orka.memory.file_operations.json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_file_legacy_format(self, mock_file_open, mock_json_load):
        """Test loading legacy format files"""
        # Legacy format is just a list
        mock_data = [
            {"agent_id": "test1", "event": "data1"},
            {"agent_id": "test2", "event": "data2"},
        ]
        mock_json_load.return_value = mock_data

        result = FileOperationsMixin.load_from_file("test.json")

        # Should return wrapped format for legacy data
        assert result["_metadata"]["version"] == "legacy"
        assert result["_metadata"]["deduplication_enabled"] is False
        assert result["events"] == mock_data

    @patch("orka.memory.file_operations.json.load")
    @patch("builtins.open", side_effect=FileNotFoundError("File not found"))
    def test_load_from_file_not_found(self, mock_file_open, mock_json_load):
        """Test loading non-existent file"""
        result = FileOperationsMixin.load_from_file("nonexistent.json")

        # Should return error structure instead of raising
        assert result["_metadata"]["error"] == "File not found"
        assert result["events"] == []

    @patch(
        "orka.memory.file_operations.json.load",
        side_effect=json.JSONDecodeError("Invalid JSON", "", 0),
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_load_from_file_invalid_json(self, mock_file_open, mock_json_load):
        """Test loading file with invalid JSON"""
        result = FileOperationsMixin.load_from_file("invalid.json")

        # Should return error structure instead of raising
        assert "Invalid JSON" in result["_metadata"]["error"]
        assert result["events"] == []

    def test_resolve_blob_references_static_basic(self):
        """Test static blob reference resolution method"""
        blob_store = {"hash123": {"resolved": "data"}}
        obj_with_ref = {"_type": "blob_reference", "ref": "hash123"}

        result = FileOperationsMixin._resolve_blob_references_static(obj_with_ref, blob_store)

        assert result == {"resolved": "data"}

    def test_resolve_blob_references_static_complex(self):
        """Test static blob reference resolution with complex nested structure"""
        blob_store = {
            "hash1": "value1",
            "hash2": {"nested": "value2"},
        }

        complex_obj = {
            "data": [
                {"_type": "blob_reference", "ref": "hash1"},
                {
                    "nested": {
                        "ref_obj": {"_type": "blob_reference", "ref": "hash2"},
                        "normal": "value",
                    },
                },
            ],
            "other": {"_type": "blob_reference", "ref": "hash1"},
        }

        result = FileOperationsMixin._resolve_blob_references_static(complex_obj, blob_store)

        assert result["data"][0] == "value1"
        assert result["data"][1]["nested"]["ref_obj"] == {"nested": "value2"}
        assert result["data"][1]["nested"]["normal"] == "value"
        assert result["other"] == "value1"

    def test_metadata_generation(self, file_ops_instance):
        """Test metadata generation in saved files"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
            tmp_path = tmp_file.name

        try:
            file_ops_instance.save_to_file(tmp_path)

            with open(tmp_path) as f:
                data = json.load(f)

            metadata = data["_metadata"]
            assert metadata["version"] == "1.0"
            assert metadata["deduplication_enabled"] is True
            assert "generated_at" in metadata
            assert "blob_threshold_chars" in metadata
            assert "stats" in metadata

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
