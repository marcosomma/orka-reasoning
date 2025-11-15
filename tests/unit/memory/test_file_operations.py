"""Unit tests for orka.memory.file_operations."""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from orka.memory.file_operations import FileOperationsMixin

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class ConcreteFileOperations(FileOperationsMixin):
    """Concrete implementation for testing."""
    
    def _process_memory_for_saving(self, memory_entries):
        return memory_entries
    
    def _sanitize_for_json(self, obj):
        return obj
    
    def _deduplicate_object(self, obj):
        return obj
    
    def _should_use_deduplication_format(self):
        return False


class TestFileOperationsMixin:
    """Test suite for FileOperationsMixin class."""

    def test_init(self):
        """Test FileOperationsMixin initialization."""
        mixin = ConcreteFileOperations()
        
        assert mixin.memory == []
        assert mixin._blob_threshold == 0
        assert mixin._blob_store == {}

    def test_save_to_file(self):
        """Test save_to_file method."""
        mixin = ConcreteFileOperations()
        mixin.memory = [
            {"agent_id": "test", "payload": {"result": "output"}}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            mixin.save_to_file(temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify file contains data
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert "events" in data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_to_file_with_redis(self):
        """Test save_to_file with Redis client."""
        mixin = ConcreteFileOperations()
        mixin.memory = [{"agent_id": "test"}]
        mixin.redis_client = Mock()
        mixin.redis_client.ping.return_value = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            mixin.save_to_file(temp_path)
            
            # Should ping Redis before saving
            mixin.redis_client.ping.assert_called_once()
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_from_file(self):
        """Test load_from_file static method."""
        test_data = {
            "events": [
                {"agent_id": "test", "payload": {"result": "output"}}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            result = FileOperationsMixin.load_from_file(temp_path)
            
            assert "events" in result
            assert len(result["events"]) == 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_from_file_with_blobs(self):
        """Test load_from_file with blob store."""
        test_data = {
            "events": [{"agent_id": "test"}],
            "blob_store": {"blob1": {"data": "test"}}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            result = FileOperationsMixin.load_from_file(temp_path, resolve_blobs=True)
            
            assert "events" in result
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_resolve_blob_references(self):
        """Test _resolve_blob_references method."""
        mixin = ConcreteFileOperations()
        
        blob_store = {"blob1": {"data": "test"}}
        obj = {"_type": "blob_reference", "ref": "blob1"}
        
        result = mixin._resolve_blob_references(obj, blob_store)
        
        assert result == {"data": "test"}

    def test_resolve_blob_references_nested(self):
        """Test _resolve_blob_references with nested structure."""
        mixin = ConcreteFileOperations()
        
        blob_store = {"blob1": {"data": "test"}}
        obj = {
            "key": {"_type": "blob_reference", "ref": "blob1"},
            "other": "value"
        }
        
        result = mixin._resolve_blob_references(obj, blob_store)
        
        assert result["key"] == {"data": "test"}
        assert result["other"] == "value"

    def test_resolve_blob_references_static(self):
        """Test _resolve_blob_references_static method."""
        blob_store = {"blob1": {"data": "test"}}
        obj = {"_type": "blob_reference", "ref": "blob1"}
        
        result = FileOperationsMixin._resolve_blob_references_static(obj, blob_store)
        
        assert result == {"data": "test"}

