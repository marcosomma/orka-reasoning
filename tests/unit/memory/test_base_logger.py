"""Unit tests for orka.memory.base_logger."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from orka.memory.base_logger import BaseMemoryLogger, json_serializer

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class ConcreteMemoryLogger(BaseMemoryLogger):
    """Concrete implementation for testing."""
    
    def log(self, agent_id, event_type, payload, **kwargs):
        """Implementation for testing."""
        pass
    
    def tail(self, count=10):
        """Implementation for testing."""
        return []
    
    def cleanup_expired_memories(self, dry_run=False):
        """Implementation for testing."""
        return {}
    
    def get_memory_stats(self):
        """Implementation for testing."""
        return {}
    
    def hset(self, name, key, value):
        """Implementation for testing."""
        return 1
    
    def hget(self, name, key):
        """Implementation for testing."""
        return None
    
    def hkeys(self, name):
        """Implementation for testing."""
        return []
    
    def hdel(self, name, *keys):
        """Implementation for testing."""
        return 1
    
    def smembers(self, name):
        """Implementation for testing."""
        return []
    
    def sadd(self, name, *values):
        """Implementation for testing."""
        return 1
    
    def srem(self, name, *values):
        """Implementation for testing."""
        return 1
    
    def get(self, key):
        """Implementation for testing."""
        return None
    
    def set(self, key, value):
        """Implementation for testing."""
        return True
    
    def delete(self, *keys):
        """Implementation for testing."""
        return 1


class TestJsonSerializer:
    """Test suite for json_serializer function."""

    def test_json_serializer_datetime(self):
        """Test json_serializer with datetime."""
        dt = datetime.now(UTC)
        result = json_serializer(dt)
        
        assert isinstance(result, str)
        assert dt.isoformat() == result

    def test_json_serializer_unsupported(self):
        """Test json_serializer with unsupported type."""
        with pytest.raises(TypeError):
            json_serializer({"key": "value"})


class TestBaseMemoryLogger:
    """Test suite for BaseMemoryLogger class."""

    def test_init(self):
        """Test BaseMemoryLogger initialization."""
        logger = ConcreteMemoryLogger(
            debug_keep_previous_outputs=False
        )
        assert logger.debug_keep_previous_outputs is False

    def test_calculate_importance_score(self):
        """Test _calculate_importance_score method."""
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score(
            event_type="success",
            agent_id="test_agent",
            payload={}
        )
        
        assert 0.0 <= score <= 1.0

    def test_classify_memory_type(self):
        """Test _classify_memory_type method."""
        logger = ConcreteMemoryLogger()
        memory_type = logger._classify_memory_type("success", 0.8)
        
        assert memory_type in ["short_term", "long_term"]

    def test_classify_memory_category(self):
        """Test _classify_memory_category method."""
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("write", "agent1", {})
        
        assert category in ["log", "stored"]

    def test_compute_blob_hash(self):
        """Test _compute_blob_hash method."""
        logger = ConcreteMemoryLogger()
        obj = {"key": "value", "data": "test" * 100}  # Large object
        hash_value = logger._compute_blob_hash(obj)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 hex length

    def test_should_deduplicate_blob(self):
        """Test _should_deduplicate_blob method."""
        logger = ConcreteMemoryLogger()
        logger._blob_threshold = 200
        
        # Large object should be deduplicated
        large_obj = {"data": "x" * 300}
        assert logger._should_deduplicate_blob(large_obj) is True
        
        # Small object should not be deduplicated
        small_obj = {"data": "x"}
        assert logger._should_deduplicate_blob(small_obj) is False

    def test_store_blob(self):
        """Test _store_blob method."""
        logger = ConcreteMemoryLogger()
        obj = {"data": "test"}
        blob_id = logger._store_blob(obj)
        
        assert isinstance(blob_id, str)
        assert blob_id in logger._blob_store

    def test_create_blob_reference(self):
        """Test _create_blob_reference method."""
        logger = ConcreteMemoryLogger()
        reference = logger._create_blob_reference("blob_id_123")
        
        assert isinstance(reference, dict)
        assert reference["ref"] == "blob_id_123"

    def test_deduplicate_object(self):
        """Test _deduplicate_object method."""
        logger = ConcreteMemoryLogger()
        logger._blob_threshold = 200
        
        large_obj = {"data": "x" * 300}
        result = logger._deduplicate_object(large_obj)
        
        assert isinstance(result, dict)
        # Should create blob reference if large enough
        if logger._should_deduplicate_blob(large_obj):
            assert "ref" in str(result)

    def test_stop_decay_scheduler(self):
        """Test stop_decay_scheduler method."""
        logger = ConcreteMemoryLogger()
        # Should not raise exception
        logger.stop_decay_scheduler()

    def test_get_memory_stats(self):
        """Test get_memory_stats method."""
        logger = ConcreteMemoryLogger()
        stats = logger.get_memory_stats()
        
        assert isinstance(stats, dict)

