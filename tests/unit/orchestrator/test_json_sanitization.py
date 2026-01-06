"""Unit tests for JSON sanitization utilities in execution_engine."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from orka.orchestrator.execution_engine import json_serializer, sanitize_for_json

# Mark all tests in this file to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestJsonSerializer:
    """Test suite for json_serializer function."""

    def test_json_serializer_datetime(self):
        """Test json_serializer with datetime object."""
        dt = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        result = json_serializer(dt)
        assert isinstance(result, str)
        assert result == "2025-12-06T10:30:45+00:00"

    def test_json_serializer_datetime_naive(self):
        """Test json_serializer with naive datetime object."""
        dt = datetime(2025, 12, 6, 10, 30, 45)
        result = json_serializer(dt)
        assert isinstance(result, str)
        assert result == "2025-12-06T10:30:45"

    def test_json_serializer_unsupported_type(self):
        """Test json_serializer with unsupported type raises TypeError."""
        mock_obj = Mock()
        with pytest.raises(TypeError, match="is not JSON serializable"):
            json_serializer(mock_obj)

    def test_json_serializer_with_none(self):
        """Test json_serializer with None raises TypeError."""
        with pytest.raises(TypeError):
            json_serializer(None)


class TestSanitizeForJson:
    """Test suite for sanitize_for_json function."""

    def test_sanitize_datetime(self):
        """Test sanitizing a datetime object."""
        dt = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        result = sanitize_for_json(dt)
        assert isinstance(result, str)
        assert result == "2025-12-06T10:30:45+00:00"

    def test_sanitize_dict_with_datetime(self):
        """Test sanitizing a dict containing datetime objects."""
        dt = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        data = {
            "timestamp": dt,
            "name": "test",
            "value": 123,
        }
        result = sanitize_for_json(data)
        assert isinstance(result, dict)
        assert result["timestamp"] == "2025-12-06T10:30:45+00:00"
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_sanitize_nested_dict_with_datetime(self):
        """Test sanitizing nested dict with datetime objects."""
        dt1 = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        dt2 = datetime(2025, 12, 6, 11, 45, 30, tzinfo=UTC)
        data = {
            "outer": {
                "inner": {
                    "created_at": dt1,
                    "updated_at": dt2,
                },
                "count": 5,
            },
            "status": "active",
        }
        result = sanitize_for_json(data)
        assert isinstance(result, dict)
        assert result["outer"]["inner"]["created_at"] == "2025-12-06T10:30:45+00:00"
        assert result["outer"]["inner"]["updated_at"] == "2025-12-06T11:45:30+00:00"
        assert result["outer"]["count"] == 5
        assert result["status"] == "active"

    def test_sanitize_list_with_datetime(self):
        """Test sanitizing a list containing datetime objects."""
        dt1 = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        dt2 = datetime(2025, 12, 6, 11, 45, 30, tzinfo=UTC)
        data = [dt1, "text", 123, dt2, True]
        result = sanitize_for_json(data)
        assert isinstance(result, list)
        assert result[0] == "2025-12-06T10:30:45+00:00"
        assert result[1] == "text"
        assert result[2] == 123
        assert result[3] == "2025-12-06T11:45:30+00:00"
        assert result[4] is True

    def test_sanitize_list_of_dicts_with_datetime(self):
        """Test sanitizing a list of dicts containing datetime objects."""
        dt1 = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        dt2 = datetime(2025, 12, 6, 11, 45, 30, tzinfo=UTC)
        data = [
            {"timestamp": dt1, "value": 100},
            {"timestamp": dt2, "value": 200},
        ]
        result = sanitize_for_json(data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["timestamp"] == "2025-12-06T10:30:45+00:00"
        assert result[0]["value"] == 100
        assert result[1]["timestamp"] == "2025-12-06T11:45:30+00:00"
        assert result[1]["value"] == 200

    def test_sanitize_tuple_with_datetime(self):
        """Test sanitizing a tuple containing datetime objects."""
        dt = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        data = (dt, "text", 123)
        result = sanitize_for_json(data)
        assert isinstance(result, list)  # Tuples become lists
        assert result[0] == "2025-12-06T10:30:45+00:00"
        assert result[1] == "text"
        assert result[2] == 123

    def test_sanitize_primitive_types(self):
        """Test sanitizing primitive types (no conversion needed)."""
        assert sanitize_for_json("text") == "text"
        assert sanitize_for_json(123) == 123
        assert sanitize_for_json(45.67) == 45.67
        assert sanitize_for_json(True) is True
        assert sanitize_for_json(False) is False
        assert sanitize_for_json(None) is None

    def test_sanitize_unknown_type(self):
        """Test sanitizing unknown type converts to string."""
        mock_obj = Mock()
        mock_obj.__str__ = Mock(return_value="MockObject")
        result = sanitize_for_json(mock_obj)
        assert isinstance(result, str)
        assert "Mock" in result or "mock" in result.lower()

    def test_sanitize_unknown_type_without_str(self):
        """Test sanitizing unknown type that can't be converted to string."""
        class UnstringableObject:
            def __str__(self):
                raise RuntimeError("Cannot stringify")
        
        obj = UnstringableObject()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)
        assert result.startswith("<")
        assert "UnstringableObject" in result

    def test_sanitize_complex_nested_structure(self):
        """Test sanitizing a complex nested structure with multiple datetime objects."""
        dt1 = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        dt2 = datetime(2025, 12, 6, 11, 45, 30, tzinfo=UTC)
        dt3 = datetime(2025, 12, 6, 12, 15, 20, tzinfo=UTC)
        
        data = {
            "agent_results": [
                {
                    "agent_id": "agent1",
                    "timestamp": dt1,
                    "result": {
                        "response": "answer1",
                        "metadata": {
                            "created_at": dt2,
                            "scores": [0.95, 0.87],
                        }
                    }
                },
                {
                    "agent_id": "agent2",
                    "timestamp": dt3,
                    "result": {
                        "response": "answer2",
                        "metrics": (100, 200, 300),  # Tuple
                    }
                }
            ],
            "workflow_start": dt1,
            "status": "completed",
        }
        
        result = sanitize_for_json(data)
        
        assert isinstance(result, dict)
        assert result["agent_results"][0]["timestamp"] == "2025-12-06T10:30:45+00:00"
        assert result["agent_results"][0]["result"]["metadata"]["created_at"] == "2025-12-06T11:45:30+00:00"
        assert result["agent_results"][0]["result"]["metadata"]["scores"] == [0.95, 0.87]
        assert result["agent_results"][1]["timestamp"] == "2025-12-06T12:15:20+00:00"
        assert result["agent_results"][1]["result"]["metrics"] == [100, 200, 300]  # Tuple -> list
        assert result["workflow_start"] == "2025-12-06T10:30:45+00:00"
        assert result["status"] == "completed"

    def test_sanitize_empty_structures(self):
        """Test sanitizing empty data structures."""
        assert sanitize_for_json({}) == {}
        assert sanitize_for_json([]) == []
        assert sanitize_for_json(()) == []

    def test_sanitize_dict_with_mixed_values(self):
        """Test sanitizing dict with various value types including datetime."""
        dt = datetime(2025, 12, 6, 10, 30, 45, tzinfo=UTC)
        data = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "datetime": dt,
            "list": [1, 2, 3],
            "nested_dict": {"key": "value"},
        }
        result = sanitize_for_json(data)
        
        assert result["string"] == "value"
        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["bool"] is True
        assert result["none"] is None
        assert result["datetime"] == "2025-12-06T10:30:45+00:00"
        assert result["list"] == [1, 2, 3]
        assert result["nested_dict"] == {"key": "value"}

    def test_sanitize_preserves_none_values(self):
        """Test that sanitize_for_json preserves None values in structures."""
        data = {
            "field1": None,
            "field2": "value",
            "field3": [None, "item", None],
        }
        result = sanitize_for_json(data)
        
        assert result["field1"] is None
        assert result["field2"] == "value"
        assert result["field3"] == [None, "item", None]
