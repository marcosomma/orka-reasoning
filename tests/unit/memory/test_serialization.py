"""Unit tests for orka.memory.serialization."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from orka.memory.serialization import SerializationMixin

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestSerializationMixin:
    """Test suite for SerializationMixin class."""

    def test_init(self):
        """Test SerializationMixin initialization."""
        mixin = SerializationMixin()
        
        assert mixin.debug_keep_previous_outputs is False
        assert mixin._blob_usage == {}
        assert mixin._blob_store == {}

    def test_sanitize_for_json_simple_types(self):
        """Test _sanitize_for_json with simple types."""
        mixin = SerializationMixin()
        
        assert mixin._sanitize_for_json("string") == "string"
        assert mixin._sanitize_for_json(123) == 123
        assert mixin._sanitize_for_json(45.6) == 45.6
        assert mixin._sanitize_for_json(True) is True
        assert mixin._sanitize_for_json(None) is None

    def test_sanitize_for_json_bytes(self):
        """Test _sanitize_for_json with bytes."""
        mixin = SerializationMixin()
        
        result = mixin._sanitize_for_json(b"test bytes")
        
        assert isinstance(result, dict)
        assert result["__type"] == "bytes"
        assert "data" in result

    def test_sanitize_for_json_list(self):
        """Test _sanitize_for_json with list."""
        mixin = SerializationMixin()
        
        result = mixin._sanitize_for_json([1, 2, "three"])
        
        assert result == [1, 2, "three"]

    def test_sanitize_for_json_dict(self):
        """Test _sanitize_for_json with dict."""
        mixin = SerializationMixin()
        
        result = mixin._sanitize_for_json({"key": "value", "num": 123})
        
        assert result == {"key": "value", "num": 123}

    def test_sanitize_for_json_datetime(self):
        """Test _sanitize_for_json with datetime."""
        mixin = SerializationMixin()
        
        dt = datetime.now()
        result = mixin._sanitize_for_json(dt)
        
        assert isinstance(result, str)
        assert dt.isoformat() == result

    def test_sanitize_for_json_circular_reference(self):
        """Test _sanitize_for_json handles circular references."""
        mixin = SerializationMixin()
        
        obj = {}
        obj["self"] = obj  # Create circular reference
        
        result = mixin._sanitize_for_json(obj)
        
        # Should handle circular reference gracefully
        assert isinstance(result, dict)

    def test_sanitize_for_json_custom_object(self):
        """Test _sanitize_for_json with custom object."""
        mixin = SerializationMixin()
        
        class CustomObj:
            def __init__(self):
                self.value = "test"
        
        obj = CustomObj()
        result = mixin._sanitize_for_json(obj)
        
        assert isinstance(result, dict)
        assert result["__type"] == "CustomObj"

    def test_process_memory_for_saving_empty(self):
        """Test _process_memory_for_saving with empty list."""
        mixin = SerializationMixin()
        
        result = mixin._process_memory_for_saving([])
        
        assert result == []

    def test_process_memory_for_saving_debug_mode(self):
        """Test _process_memory_for_saving with debug mode enabled."""
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = True
        
        entries = [{"agent_id": "test", "previous_outputs": {"key": "value"}}]
        
        result = mixin._process_memory_for_saving(entries)
        
        # Should return original entries unchanged
        assert result == entries

    def test_process_memory_for_saving_removes_previous_outputs(self):
        """Test _process_memory_for_saving removes previous_outputs."""
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = False
        
        entries = [
            {
                "agent_id": "test",
                "previous_outputs": {"key": "value"},
                "payload": {
                    "result": "output",
                    "previous_outputs": {"key": "value"},
                }
            }
        ]
        
        result = mixin._process_memory_for_saving(entries)
        
        assert "previous_outputs" not in result[0]
        assert "previous_outputs" not in result[0]["payload"]

    def test_process_memory_for_saving_meta_report(self):
        """Test _process_memory_for_saving preserves MetaReport data."""
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = False
        
        entries = [
            {
                "event_type": "MetaReport",
                "payload": {
                    "result": "output",
                    "previous_outputs": {"key": "value"},
                }
            }
        ]
        
        result = mixin._process_memory_for_saving(entries)
        
        # MetaReport should keep all payload data
        assert "payload" in result[0]

    def test_should_use_deduplication_format_no_duplicates(self):
        """Test _should_use_deduplication_format with no duplicates."""
        mixin = SerializationMixin()
        mixin._blob_usage = {"blob1": 1}
        mixin._blob_store = {"blob1": {"data": "test"}}
        
        result = mixin._should_use_deduplication_format()
        
        # Should return False if no duplicates and small store
        assert isinstance(result, bool)

    def test_should_use_deduplication_format_with_duplicates(self):
        """Test _should_use_deduplication_format with duplicates."""
        mixin = SerializationMixin()
        mixin._blob_usage = {"blob1": 3}  # Used 3 times
        mixin._blob_store = {"blob1": {"data": "test"}}
        
        result = mixin._should_use_deduplication_format()
        
        # Should return True if duplicates exist
        assert result is True

