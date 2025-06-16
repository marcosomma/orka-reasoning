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

import base64
from datetime import datetime
from unittest.mock import patch

import pytest

from orka.memory.serialization import SerializationMixin


class TestSerializationMixin:
    """Test suite for SerializationMixin functionality"""

    @pytest.fixture
    def serialization_instance(self):
        """Create a test instance with SerializationMixin"""

        class TestSerialization(SerializationMixin):
            def __init__(self):
                self.debug_keep_previous_outputs = False
                self._blob_store = {}
                self._blob_usage = {}

        return TestSerialization()

    def test_sanitize_for_json_basic_types(self, serialization_instance):
        """Test sanitization of basic JSON-serializable types"""
        # Test None
        assert serialization_instance._sanitize_for_json(None) is None

        # Test string
        assert serialization_instance._sanitize_for_json("test") == "test"

        # Test int
        assert serialization_instance._sanitize_for_json(42) == 42

        # Test float
        assert serialization_instance._sanitize_for_json(3.14) == 3.14

        # Test bool
        assert serialization_instance._sanitize_for_json(True) is True
        assert serialization_instance._sanitize_for_json(False) is False

    def test_sanitize_for_json_bytes(self, serialization_instance):
        """Test sanitization of bytes objects"""
        test_bytes = b"hello world"
        result = serialization_instance._sanitize_for_json(test_bytes)

        assert result["__type"] == "bytes"
        assert result["data"] == base64.b64encode(test_bytes).decode("utf-8")

    def test_sanitize_for_json_list(self, serialization_instance):
        """Test sanitization of lists"""
        test_list = [1, "test", None, True]
        result = serialization_instance._sanitize_for_json(test_list)

        assert result == [1, "test", None, True]

    def test_sanitize_for_json_tuple(self, serialization_instance):
        """Test sanitization of tuples"""
        test_tuple = (1, "test", None)
        result = serialization_instance._sanitize_for_json(test_tuple)

        assert result == [1, "test", None]  # Tuples become lists

    def test_sanitize_for_json_dict(self, serialization_instance):
        """Test sanitization of dictionaries"""
        test_dict = {
            "string": "value",
            "number": 42,
            "nested": {"inner": "value"},
        }
        result = serialization_instance._sanitize_for_json(test_dict)

        assert result == test_dict

    def test_sanitize_for_json_dict_non_string_keys(self, serialization_instance):
        """Test sanitization of dictionaries with non-string keys"""
        test_dict = {
            1: "number_key",
            "string": "string_key",
            (1, 2): "tuple_key",
        }
        result = serialization_instance._sanitize_for_json(test_dict)

        assert result["1"] == "number_key"
        assert result["string"] == "string_key"
        assert result["(1, 2)"] == "tuple_key"

    def test_sanitize_for_json_custom_object(self, serialization_instance):
        """Test sanitization of custom objects with __dict__"""

        class TestObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = TestObject()
        result = serialization_instance._sanitize_for_json(obj)

        assert result["__type"] == "TestObject"
        assert result["data"]["attr1"] == "value1"
        assert result["data"]["attr2"] == 42

    def test_sanitize_for_json_datetime(self, serialization_instance):
        """Test sanitization of datetime objects"""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = serialization_instance._sanitize_for_json(dt)

        assert result == dt.isoformat()

    def test_sanitize_for_json_circular_reference(self, serialization_instance):
        """Test handling of circular references"""
        # Create circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2

        result = serialization_instance._sanitize_for_json(obj1)

        assert result["name"] == "obj1"
        assert result["ref"]["name"] == "obj2"
        assert "<circular-reference:" in result["ref"]["ref"]

    def test_sanitize_for_json_circular_reference_list(self, serialization_instance):
        """Test handling of circular references in lists"""
        # Create circular reference with list
        test_list = [1, 2]
        test_list.append(test_list)  # Circular reference

        result = serialization_instance._sanitize_for_json(test_list)

        assert result[0] == 1
        assert result[1] == 2
        assert "<circular-reference:" in result[2]

    def test_sanitize_for_json_non_serializable_object(self, serialization_instance):
        """Test handling of non-serializable objects"""
        # Object without __dict__
        obj = object()
        result = serialization_instance._sanitize_for_json(obj)

        assert result.startswith("<non-serializable:")
        assert "object" in result

    def test_sanitize_for_json_object_with_exception(self, serialization_instance):
        """Test handling of objects that raise exceptions during serialization"""

        class ProblematicObject:
            @property
            def __dict__(self):
                raise ValueError("Cannot access __dict__")

        obj = ProblematicObject()
        result = serialization_instance._sanitize_for_json(obj)

        # The exception is caught at the top level and becomes a sanitization-error
        assert result.startswith("<sanitization-error:")
        assert "Cannot access __dict__" in result

    def test_sanitize_for_json_exception_handling(self, serialization_instance):
        """Test exception handling in sanitization"""
        # Mock to cause an exception
        with patch("orka.memory.serialization.logger") as mock_logger:
            # Create an object that will cause an exception
            class BadObject:
                def __init__(self):
                    pass

                def __getattribute__(self, name):
                    if name == "__class__":
                        raise RuntimeError("Bad object")
                    return super().__getattribute__(name)

            obj = BadObject()
            result = serialization_instance._sanitize_for_json(obj)

            assert result.startswith("<sanitization-error:")
            mock_logger.warning.assert_called_once()

    def test_process_memory_for_saving_empty(self, serialization_instance):
        """Test processing empty memory entries"""
        result = serialization_instance._process_memory_for_saving([])
        assert result == []

    def test_process_memory_for_saving_debug_mode(self, serialization_instance):
        """Test processing with debug mode enabled"""
        serialization_instance.debug_keep_previous_outputs = True

        entries = [
            {
                "agent_id": "test",
                "previous_outputs": {"old": "data"},
                "payload": {"result": "test"},
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        # Should return original entries unchanged in debug mode
        assert result == entries

    def test_process_memory_for_saving_remove_previous_outputs(self, serialization_instance):
        """Test removal of previous_outputs from entries"""
        entries = [
            {
                "agent_id": "test",
                "previous_outputs": {"old": "data"},
                "payload": {
                    "result": "test",
                    "previous_outputs": {"more": "old_data"},
                },
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        assert "previous_outputs" not in result[0]
        assert "previous_outputs" not in result[0]["payload"]
        assert result[0]["payload"]["result"] == "test"

    def test_process_memory_for_saving_meta_report(self, serialization_instance):
        """Test processing of meta report entries (should keep all data)"""
        entries = [
            {
                "agent_id": "meta",
                "event_type": "MetaReport",
                "payload": {
                    "result": "meta_data",
                    "previous_outputs": {"should": "keep"},
                    "extra_data": "important",
                },
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        # Meta reports keep all payload data except previous_outputs is removed everywhere
        assert "previous_outputs" not in result[0]  # Removed from root level
        assert "previous_outputs" not in result[0]["payload"]  # Also removed from payload
        assert result[0]["payload"]["extra_data"] == "important"  # Other data kept
        assert result[0]["payload"]["result"] == "meta_data"

    def test_process_memory_for_saving_keep_essential_fields(self, serialization_instance):
        """Test that essential fields are kept during processing"""
        entries = [
            {
                "agent_id": "test",
                "payload": {
                    "input": "test_input",
                    "result": "test_result",
                    "_metrics": {"tokens": 100},
                    "fork_group": "group1",
                    "fork_targets": ["target1"],
                    "fork_group_id": "id123",
                    "prompt": "test prompt",
                    "formatted_prompt": "formatted",
                    "extra_field": "should_be_removed",
                    "previous_outputs": {"old": "data"},
                },
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        payload = result[0]["payload"]

        # Essential fields should be kept
        assert payload["input"] == "test_input"
        assert payload["result"] == "test_result"
        assert payload["_metrics"] == {"tokens": 100}
        assert payload["fork_group"] == "group1"
        assert payload["fork_targets"] == ["target1"]
        assert payload["fork_group_id"] == "id123"
        assert payload["prompt"] == "test prompt"
        assert payload["formatted_prompt"] == "formatted"

        # Non-essential fields should be removed
        assert "extra_field" not in payload
        assert "previous_outputs" not in payload

    def test_process_memory_for_saving_no_payload(self, serialization_instance):
        """Test processing entries without payload"""
        entries = [
            {
                "agent_id": "test",
                "event_type": "start",
                "previous_outputs": {"old": "data"},
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        assert "previous_outputs" not in result[0]
        assert result[0]["agent_id"] == "test"
        assert result[0]["event_type"] == "start"

    def test_should_use_deduplication_format_no_duplicates_small(self, serialization_instance):
        """Test deduplication format decision with no duplicates and small blob store"""
        serialization_instance._blob_usage = {"blob1": 1, "blob2": 1}  # No duplicates
        serialization_instance._blob_store = {"blob1": "small", "blob2": "data"}

        result = serialization_instance._should_use_deduplication_format()

        assert result is False

    def test_should_use_deduplication_format_has_duplicates(self, serialization_instance):
        """Test deduplication format decision with duplicates"""
        serialization_instance._blob_usage = {"blob1": 3, "blob2": 1}  # Has duplicates
        serialization_instance._blob_store = {"blob1": "data", "blob2": "more"}

        result = serialization_instance._should_use_deduplication_format()

        assert result is True

    def test_should_use_deduplication_format_large_blob_store(self, serialization_instance):
        """Test deduplication format decision with large blob store"""
        serialization_instance._blob_usage = {"blob1": 1, "blob2": 1, "blob3": 1, "blob4": 1}
        serialization_instance._blob_store = {
            "blob1": "large_data_" * 100,
            "blob2": "more_large_data_" * 100,
            "blob3": "even_more_data_" * 100,
            "blob4": "lots_of_data_" * 100,
        }

        result = serialization_instance._should_use_deduplication_format()

        assert result is True

    def test_should_use_deduplication_format_medium_store_no_duplicates(
        self,
        serialization_instance,
    ):
        """Test deduplication format decision with medium store but no duplicates"""
        serialization_instance._blob_usage = {"blob1": 1, "blob2": 1, "blob3": 1}
        serialization_instance._blob_store = {
            "blob1": "medium_data",
            "blob2": "more_medium",
            "blob3": "even_more",
        }

        result = serialization_instance._should_use_deduplication_format()

        # Should be False because not enough blobs (<=3) and no duplicates
        assert result is False

    def test_sanitize_for_json_nested_complex(self, serialization_instance):
        """Test sanitization of complex nested structures"""
        complex_obj = {
            "list": [1, {"nested": "value"}, b"bytes_data"],
            "tuple": (1, 2, 3),
            "bytes": b"test_bytes",
            "datetime": datetime(2025, 1, 1),
            "custom": type("TestClass", (), {"attr": "value"})(),
        }

        result = serialization_instance._sanitize_for_json(complex_obj)

        assert result["list"][0] == 1
        assert result["list"][1]["nested"] == "value"
        assert result["list"][2]["__type"] == "bytes"
        assert result["tuple"] == [1, 2, 3]
        assert result["bytes"]["__type"] == "bytes"
        assert result["datetime"] == "2025-01-01T00:00:00"
        assert result["custom"]["__type"] == "TestClass"

    def test_process_memory_for_saving_partial_essential_fields(self, serialization_instance):
        """Test processing when only some essential fields are present"""
        entries = [
            {
                "agent_id": "test",
                "payload": {
                    "result": "test_result",
                    "_metrics": {"tokens": 100},
                    "extra_field": "should_be_removed",
                    "another_extra": "also_removed",
                },
            },
        ]

        result = serialization_instance._process_memory_for_saving(entries)

        payload = result[0]["payload"]

        # Only present essential fields should be kept
        assert payload["result"] == "test_result"
        assert payload["_metrics"] == {"tokens": 100}
        assert len(payload) == 2  # Only these two fields
        assert "extra_field" not in payload
        assert "another_extra" not in payload
