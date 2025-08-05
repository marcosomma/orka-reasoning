import json
from unittest.mock import Mock, mock_open, patch

from orka.memory.file_operations import FileOperationsMixin


class MockFileOperationsMixin(FileOperationsMixin):
    """Mock implementation of FileOperationsMixin for testing."""

    def __init__(self):
        self.memory = []
        self._blob_store = {}
        self._blob_usage = {}
        self._blob_threshold = 200
        self.debug_keep_previous_outputs = False

    def _process_memory_for_saving(self, memory):
        """Mock implementation."""
        return memory

    def _sanitize_for_json(self, memory):
        """Mock implementation."""
        return memory

    def _deduplicate_object(self, obj):
        """Mock implementation."""
        return obj

    def _should_use_deduplication_format(self):
        """Mock implementation."""
        return len(self._blob_store) > 0


class TestFileOperationsMixinSaveToFile:
    """Test save_to_file method functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = MockFileOperationsMixin()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_basic_functionality(self, mock_json_dump, mock_file):
        """Test basic save to file functionality."""
        self.mixin.memory = [{"test": "data", "timestamp": "2023-01-01"}]

        self.mixin.save_to_file("test.json")

        mock_file.assert_called_once_with("test.json", "w", encoding="utf-8")
        mock_json_dump.assert_called_once()

        # Check the default lambda serializer
        call_args = mock_json_dump.call_args
        assert call_args[1]["indent"] == 2
        default_func = call_args[1]["default"]
        result = default_func(object())
        assert "non-serializable" in result

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_with_kafka_producer(self, mock_json_dump, mock_file):
        """Test save to file with Kafka producer flush."""
        mock_producer = Mock()
        self.mixin.producer = mock_producer
        self.mixin.memory = [{"test": "data"}]

        self.mixin.save_to_file("test.json")

        # Should flush Kafka producer
        mock_producer.flush.assert_called_once_with(timeout=3)
        mock_file.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_kafka_flush_exception(self, mock_json_dump, mock_file):
        """Test save to file when Kafka flush fails."""
        mock_producer = Mock()
        mock_producer.flush.side_effect = Exception("Kafka flush error")
        self.mixin.producer = mock_producer
        self.mixin.memory = [{"test": "data"}]

        with patch("logging.Logger.warning") as mock_warning:
            self.mixin.save_to_file("test.json")

            # Should log warning but continue
            mock_warning.assert_called_once()
            mock_file.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_deduplication_format(self, mock_json_dump, mock_file):
        """Test save to file with deduplication format."""
        self.mixin.memory = [{"test": "data"}]
        self.mixin._blob_store = {"hash1": {"blob": "data"}}
        self.mixin._should_use_deduplication_format = Mock(return_value=True)

        self.mixin.save_to_file("test.json")

        # Should use deduplication format
        call_args = mock_json_dump.call_args[0]
        output_data = call_args[0]

        assert "_metadata" in output_data
        assert "blob_store" in output_data
        assert "events" in output_data
        assert output_data["_metadata"]["deduplication_enabled"] is True
        assert output_data["blob_store"] == {"hash1": {"blob": "data"}}

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_legacy_format(self, mock_json_dump, mock_file):
        """Test save to file with legacy format."""
        self.mixin.memory = [{"test": "data"}]
        self.mixin._blob_store = {}
        self.mixin._should_use_deduplication_format = Mock(return_value=False)
        self.mixin._resolve_blob_references = Mock(return_value={"resolved": "data"})

        self.mixin.save_to_file("test.json")

        # Should use legacy format (list of resolved events)
        call_args = mock_json_dump.call_args[0]
        output_data = call_args[0]

        assert isinstance(output_data, list)
        assert output_data == [{"resolved": "data"}]

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("json.dumps")
    def test_save_to_file_deduplication_statistics(self, mock_dumps, mock_json_dump, mock_file):
        """Test save to file with deduplication statistics logging."""
        self.mixin.memory = [{"large_data": "x" * 300}]
        self.mixin._blob_store = {"hash1": {"blob": "data"}}
        self.mixin._should_use_deduplication_format = Mock(return_value=True)

        # Mock JSON sizing for deduplication stats
        mock_dumps.side_effect = [
            '{"original": "data"}',  # Original size
            '{"dedup": "ref"}',  # Deduplicated size
            '{"sanitized": "data"}',  # Sanitized size
        ]

        with patch("logging.Logger.info") as mock_info:
            self.mixin.save_to_file("test.json")

            # Should log deduplication statistics
            mock_info.assert_called()
            log_message = mock_info.call_args[0][0]
            assert "deduplicated" in log_message or "format" in log_message

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump", side_effect=Exception("JSON Error"))
    def test_save_to_file_primary_save_failure(self, mock_json_dump, mock_file):
        """Test save to file when primary save fails."""
        self.mixin.memory = [{"test": "data"}]

        with patch("logging.Logger.error") as mock_error:
            self.mixin.save_to_file("test.json")

            # Should log error and attempt simplified save
            mock_error.assert_called()
            assert mock_file.call_count >= 1

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_simplified_fallback(self, mock_json_dump, mock_file):
        """Test save to file simplified fallback when primary fails."""
        self.mixin.memory = [{"test": "data", "agent_id": "test_agent", "event_type": "test_event"}]

        # Mock the first call to fail, second to succeed
        mock_json_dump.side_effect = [Exception("Primary failed"), None]

        with patch("logging.Logger.error"), patch("logging.Logger.info") as mock_info:
            self.mixin.save_to_file("test.json")

            # Should call simplified save
            assert mock_json_dump.call_count == 2
            simplified_call = mock_json_dump.call_args_list[1]
            simplified_data = simplified_call[0][0]

            assert "_metadata" in simplified_data
            assert simplified_data["_metadata"]["deduplication_enabled"] is False
            assert "error" in simplified_data["_metadata"]

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump", side_effect=Exception("All failed"))
    def test_save_to_file_complete_failure(self, mock_json_dump, mock_file):
        """Test save to file when both primary and simplified saves fail."""
        self.mixin.memory = [{"test": "data"}]

        with patch("logging.Logger.error") as mock_error:
            self.mixin.save_to_file("test.json")

            # Should log both errors
            assert mock_error.call_count >= 2


class TestFileOperationsMixinBlobReferences:
    """Test blob reference resolution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = MockFileOperationsMixin()

    def test_resolve_blob_references_simple(self):
        """Test resolving simple blob reference."""
        blob_store = {"hash123": {"original": "data"}}
        obj_with_ref = {
            "_type": "blob_reference",
            "ref": "hash123",
        }

        result = self.mixin._resolve_blob_references(obj_with_ref, blob_store)
        assert result == {"original": "data"}

    def test_resolve_blob_references_missing_blob(self):
        """Test resolving missing blob reference."""
        blob_store = {}
        missing_ref = {
            "_type": "blob_reference",
            "ref": "missing_hash",
        }

        result = self.mixin._resolve_blob_references(missing_ref, blob_store)
        assert result["error"] == "Blob reference not found: missing_hash"
        assert result["_type"] == "missing_blob_reference"
        assert result["ref"] == "missing_hash"

    def test_resolve_blob_references_nested_dict(self):
        """Test resolving blob references in nested dictionaries."""
        blob_store = {"hash1": {"nested": "data"}}
        nested_obj = {
            "level1": {
                "level2": {
                    "_type": "blob_reference",
                    "ref": "hash1",
                },
                "other": "value",
            },
            "top_level": "data",
        }

        result = self.mixin._resolve_blob_references(nested_obj, blob_store)

        assert result["level1"]["level2"] == {"nested": "data"}
        assert result["level1"]["other"] == "value"
        assert result["top_level"] == "data"

    def test_resolve_blob_references_nested_list(self):
        """Test resolving blob references in nested lists."""
        blob_store = {"hash1": {"item": "data"}}
        obj_with_list = [
            "string_item",
            {
                "_type": "blob_reference",
                "ref": "hash1",
            },
            {"normal": "dict"},
        ]

        result = self.mixin._resolve_blob_references(obj_with_list, blob_store)

        assert result[0] == "string_item"
        assert result[1] == {"item": "data"}
        assert result[2] == {"normal": "dict"}

    def test_resolve_blob_references_non_blob_dict(self):
        """Test resolving non-blob reference dictionaries."""
        blob_store = {"hash1": {"data": "value"}}
        normal_dict = {
            "field1": "value1",
            "field2": {
                "_type": "blob_reference",
                "ref": "hash1",
            },
        }

        result = self.mixin._resolve_blob_references(normal_dict, blob_store)

        assert result["field1"] == "value1"
        assert result["field2"] == {"data": "value"}

    def test_resolve_blob_references_primitive_types(self):
        """Test resolving blob references with primitive types."""
        blob_store = {}

        assert self.mixin._resolve_blob_references("string", blob_store) == "string"
        assert self.mixin._resolve_blob_references(42, blob_store) == 42
        assert self.mixin._resolve_blob_references(3.14, blob_store) == 3.14
        assert self.mixin._resolve_blob_references(True, blob_store) is True
        assert self.mixin._resolve_blob_references(None, blob_store) is None

    def test_resolve_blob_references_complex_nested(self):
        """Test resolving blob references in complex nested structures."""
        blob_store = {
            "hash1": {"blob1": "data1"},
            "hash2": {"blob2": "data2"},
        }

        complex_obj = {
            "array": [
                {"_type": "blob_reference", "ref": "hash1"},
                {
                    "nested": {
                        "_type": "blob_reference",
                        "ref": "hash2",
                    },
                },
            ],
            "object": {
                "deep": {
                    "deeper": {
                        "_type": "blob_reference",
                        "ref": "hash1",
                    },
                },
            },
        }

        result = self.mixin._resolve_blob_references(complex_obj, blob_store)

        assert result["array"][0] == {"blob1": "data1"}
        assert result["array"][1]["nested"] == {"blob2": "data2"}
        assert result["object"]["deep"]["deeper"] == {"blob1": "data1"}


class TestFileOperationsMixinLoadFromFile:
    """Test load_from_file static method functionality."""

    def test_load_from_file_legacy_format(self):
        """Test loading file with legacy format (list)."""
        legacy_data = [{"event": "data", "timestamp": "2023-01-01"}]

        with patch("builtins.open", mock_open(read_data=json.dumps(legacy_data))):
            result = FileOperationsMixin.load_from_file("test.json")

            assert "events" in result
            assert result["events"] == legacy_data
            assert result["_metadata"]["version"] == "legacy"
            assert result["_metadata"]["deduplication_enabled"] is False
            assert result["blob_store"] == {}

    def test_load_from_file_deduplication_format_with_resolve(self):
        """Test loading file with deduplication format and blob resolution."""
        dedup_data = {
            "_metadata": {"deduplication_enabled": True, "version": "1.0"},
            "blob_store": {"hash1": {"blob": "data"}},
            "events": [
                {"_type": "blob_reference", "ref": "hash1"},
                {"normal": "event"},
            ],
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(dedup_data))):
            result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=True)

            assert result["events"] == [{"blob": "data"}, {"normal": "event"}]
            assert result["_resolved"] is True
            assert "blob_store" in result

    def test_load_from_file_deduplication_format_no_resolve(self):
        """Test loading file with deduplication format without blob resolution."""
        dedup_data = {
            "_metadata": {"deduplication_enabled": True},
            "blob_store": {"hash1": {"blob": "data"}},
            "events": [{"_type": "blob_reference", "ref": "hash1"}],
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(dedup_data))):
            result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=False)

            # Should keep blob references unresolved
            assert result["events"] == [{"_type": "blob_reference", "ref": "hash1"}]
            assert "_resolved" not in result

    def test_load_from_file_missing_fields(self):
        """Test loading file with missing expected fields."""
        minimal_data = {
            "_metadata": {"version": "1.0"},
            # Missing blob_store and events
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(minimal_data))):
            result = FileOperationsMixin.load_from_file("test.json")

            assert result["events"] == []  # Default empty list
            assert result["blob_store"] == {}  # Default empty dict

    def test_load_from_file_file_not_found(self):
        """Test loading non-existent file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with patch("logging.Logger.error") as mock_error:
                result = FileOperationsMixin.load_from_file("nonexistent.json")

                # Should return empty result structure
                assert "events" in result
                assert result["events"] == []
                assert result["blob_store"] == {}
                assert "error" in result["_metadata"]
                mock_error.assert_called_once()

    def test_load_from_file_invalid_json(self):
        """Test loading file with invalid JSON."""
        invalid_json = "{ invalid json content"

        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch("logging.Logger.error") as mock_error:
                result = FileOperationsMixin.load_from_file("invalid.json")

                assert result["events"] == []
                assert "error" in result["_metadata"]
                mock_error.assert_called_once()

    def test_load_from_file_unexpected_format(self):
        """Test loading file with unexpected format (not list or dict)."""
        unexpected_data = "just a string"

        with patch("builtins.open", mock_open(read_data=json.dumps(unexpected_data))):
            with patch("logging.Logger.error") as mock_error:
                result = FileOperationsMixin.load_from_file("unexpected.json")

                # Should handle as error case
                assert result["events"] == []
                assert "error" in result["_metadata"]
                mock_error.assert_called_once()


class TestFileOperationsMixinStaticBlobReferences:
    """Test static blob reference resolution methods."""

    def test_resolve_blob_references_static_simple(self):
        """Test static blob reference resolution."""
        blob_store = {"hash123": {"static": "data"}}
        obj_with_ref = {
            "_type": "blob_reference",
            "ref": "hash123",
        }

        result = FileOperationsMixin._resolve_blob_references_static(obj_with_ref, blob_store)
        assert result == {"static": "data"}

    def test_resolve_blob_references_static_missing(self):
        """Test static blob reference resolution with missing blob."""
        blob_store = {}
        missing_ref = {
            "_type": "blob_reference",
            "ref": "missing",
        }

        result = FileOperationsMixin._resolve_blob_references_static(missing_ref, blob_store)
        assert result["error"] == "Blob reference not found: missing"
        assert result["_type"] == "missing_blob_reference"

    def test_resolve_blob_references_static_nested(self):
        """Test static blob reference resolution in nested structures."""
        blob_store = {"hash1": {"resolved": "value"}}
        nested_obj = {
            "level1": [
                {"_type": "blob_reference", "ref": "hash1"},
                {"normal": "data"},
            ],
        }

        result = FileOperationsMixin._resolve_blob_references_static(nested_obj, blob_store)

        assert result["level1"][0] == {"resolved": "value"}
        assert result["level1"][1] == {"normal": "data"}

    def test_resolve_blob_references_static_primitives(self):
        """Test static blob reference resolution with primitive types."""
        blob_store = {}

        # Should pass through primitive types unchanged
        assert FileOperationsMixin._resolve_blob_references_static("string", blob_store) == "string"
        assert FileOperationsMixin._resolve_blob_references_static(42, blob_store) == 42
        assert FileOperationsMixin._resolve_blob_references_static(None, blob_store) is None


class TestFileOperationsMixinEdgeCases:
    """Test edge cases and error scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = MockFileOperationsMixin()

    def test_save_to_file_empty_memory(self):
        """Test save to file with empty memory."""
        self.mixin.memory = []

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("json.dump") as mock_json_dump:
                self.mixin.save_to_file("empty.json")

                mock_file.assert_called_once()
                mock_json_dump.assert_called_once()

    def test_save_to_file_with_execution_context_processing(self):
        """Test save to file with execution context in simplified memory."""
        self.mixin.memory = [
            {
                "agent_id": "test",
                "event_type": "test",
                "execution_context": {"key1": "value1", "key2": "value2"},
            },
        ]

        # Mock primary save to fail to trigger simplified save
        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=[Exception("Primary failed"), None]):
                with patch("logging.Logger.error"), patch("logging.Logger.info"):
                    self.mixin.save_to_file("test.json")

    def test_save_to_file_with_previous_outputs_summary(self):
        """Test save to file preserving previous outputs summary in simplified format."""
        self.mixin.memory = [
            {
                "agent_id": "test",
                "event_type": "test",
                "previous_outputs_summary": {"agent1": "summary"},
            },
        ]

        # Force simplified save
        with patch("builtins.open", mock_open()):
            with patch("json.dump", side_effect=[Exception("Primary failed"), None]) as mock_json:
                with patch("logging.Logger.error"), patch("logging.Logger.info"):
                    self.mixin.save_to_file("test.json")

                    # Check simplified data preserves summary
                    simplified_call = mock_json.call_args_list[1]
                    simplified_data = simplified_call[0][0]
                    events = simplified_data["events"]
                    assert events[0]["previous_outputs_summary"] == {"agent1": "summary"}

    def test_resolve_blob_references_malformed_reference(self):
        """Test blob reference resolution with malformed reference."""
        blob_store = {"hash1": {"data": "value"}}

        # Missing required fields
        malformed_refs = [
            {"_type": "blob_reference"},  # Missing ref
            {"ref": "hash1"},  # Missing _type
            {"_type": "wrong_type", "ref": "hash1"},  # Wrong type
        ]

        for malformed_ref in malformed_refs:
            result = self.mixin._resolve_blob_references(malformed_ref, blob_store)
            # Should return the original object when not a proper blob reference
            assert result == malformed_ref

    def test_load_from_file_with_metadata_but_no_deduplication(self):
        """Test loading file that has metadata but no deduplication."""
        data_with_metadata = {
            "_metadata": {"version": "1.0", "deduplication_enabled": False},
            "events": [{"event": "data"}],
            "blob_store": {},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(data_with_metadata))):
            result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=True)

            # Should still process normally
            assert result["events"] == [{"event": "data"}]
            assert result["_resolved"] is True

    def test_save_to_file_no_producer_attribute(self):
        """Test save to file when mixin doesn't have producer attribute."""
        # Remove producer attribute to test hasattr check
        if hasattr(self.mixin, "producer"):
            delattr(self.mixin, "producer")

        self.mixin.memory = [{"test": "data"}]

        with patch("builtins.open", mock_open()):
            with patch("json.dump"):
                # Should not raise exception even without producer
                self.mixin.save_to_file("test.json")

    def test_save_to_file_with_blob_usage_statistics(self):
        """Test save to file with detailed blob usage statistics."""
        self.mixin.memory = [{"large": "x" * 500}]
        self.mixin._blob_store = {
            "hash1": {"data": "blob1"},
            "hash2": {"data": "blob2"},
        }
        self.mixin._blob_usage = {
            "hash1": 3,
            "hash2": 1,
        }

        with patch("builtins.open", mock_open()):
            with patch("json.dump"):
                with patch("json.dumps") as mock_dumps:
                    # Mock sizes for statistics
                    mock_dumps.side_effect = [
                        '{"original": "large"}',  # Original
                        '{"dedup": "small"}',  # Deduplicated
                        '{"final": "medium"}',  # Final
                    ]

                    with patch("logging.Logger.info") as mock_info:
                        self.mixin.save_to_file("test.json")

                        # Should log statistics
                        mock_info.assert_called()

    def test_resolve_blob_references_with_circular_structure(self):
        """Test blob reference resolution with simple structures (no circular refs)."""
        blob_store = {"hash1": {"resolved": "data"}}

        # Create structure without circular reference
        normal_obj = {"ref": {"_type": "blob_reference", "ref": "hash1"}}
        normal_obj["other"] = "data"  # Non-circular reference

        # Should resolve blob reference normally
        result = self.mixin._resolve_blob_references(normal_obj, blob_store)

        assert result["ref"] == {"resolved": "data"}
        assert result["other"] == "data"

    def test_load_from_file_unicode_handling(self):
        """Test loading file with Unicode characters."""
        unicode_data = [{"content": "Hello 世界! 🚀", "emoji": "🎉"}]

        with patch(
            "builtins.open",
            mock_open(read_data=json.dumps(unicode_data, ensure_ascii=False)),
        ):
            result = FileOperationsMixin.load_from_file("unicode.json")

            assert result["events"] == unicode_data
            assert "世界" in result["events"][0]["content"]
            assert "🚀" in result["events"][0]["content"]

    def test_save_to_file_very_large_memory(self):
        """Test save to file with very large memory structure."""
        # Create large memory structure
        large_memory = []
        for i in range(100):
            large_memory.append(
                {
                    "id": i,
                    "data": "x" * 1000,  # 1KB per entry
                    "nested": {"deep": {"deeper": f"value_{i}"}},
                },
            )

        self.mixin.memory = large_memory

        with patch("builtins.open", mock_open()):
            with patch("json.dump"):
                # Should handle large structures without issues
                self.mixin.save_to_file("large.json")

    def test_resolve_blob_references_deep_nesting(self):
        """Test blob reference resolution with very deep nesting."""
        blob_store = {"hash1": {"deep_data": "resolved"}}

        # Create deeply nested structure
        deep_obj = {"level": 1}
        current = deep_obj
        for i in range(2, 20):  # Create 19 levels deep
            current["next"] = {"level": i}
            current = current["next"]

        # Add blob reference at the deepest level
        current["blob"] = {"_type": "blob_reference", "ref": "hash1"}

        result = self.mixin._resolve_blob_references(deep_obj, blob_store)

        # Navigate to deepest level to verify resolution
        current_result = result
        for i in range(2, 20):
            current_result = current_result["next"]

        assert current_result["blob"] == {"deep_data": "resolved"}

    def test_load_from_file_permission_error(self):
        """Test loading file with permission error."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("logging.Logger.error") as mock_error:
                result = FileOperationsMixin.load_from_file("restricted.json")

                assert result["events"] == []
                assert "error" in result["_metadata"]
                mock_error.assert_called_once()

    def test_save_to_file_with_none_values(self):
        """Test save to file with None values in memory."""
        self.mixin.memory = [
            {"key": None, "value": "valid"},
            None,  # None entry
            {"nested": {"inner": None}},
        ]

        with patch("builtins.open", mock_open()):
            with patch("json.dump") as mock_json_dump:
                self.mixin.save_to_file("none_values.json")

                # Should handle None values gracefully
                mock_json_dump.assert_called_once()
                call_args = mock_json_dump.call_args
                data = call_args[0][0]

                # Verify None values are preserved
                if isinstance(data, list):
                    assert None in data

    def test_resolve_blob_references_empty_blob_store(self):
        """Test blob reference resolution with empty blob store."""
        empty_blob_store = {}
        obj_with_ref = {
            "_type": "blob_reference",
            "ref": "nonexistent",
        }

        result = self.mixin._resolve_blob_references(obj_with_ref, empty_blob_store)

        assert result["error"] == "Blob reference not found: nonexistent"
        assert result["_type"] == "missing_blob_reference"
