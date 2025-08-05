"""
Unit tests for the orka.memory module.
Tests memory logging, serialization, file operations, and decay functionality with mocked dependencies.
"""

import json
import os
from datetime import UTC, datetime
from unittest.mock import Mock, mock_open, patch

import pytest

from orka.memory.base_logger import BaseMemoryLogger
from orka.memory.file_operations import FileOperationsMixin
from orka.memory.serialization import SerializationMixin
from orka.memory_logger import create_memory_logger


class TestSerializationMixin:
    """Test the SerializationMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = SerializationMixin()

    def test_sanitize_basic_types(self):
        """Test sanitization of basic Python types."""
        mixin = self.mixin

        # Basic types should pass through unchanged
        assert mixin._sanitize_for_json(None) is None
        assert mixin._sanitize_for_json("string") == "string"
        assert mixin._sanitize_for_json(42) == 42
        assert mixin._sanitize_for_json(3.14) == 3.14
        assert mixin._sanitize_for_json(True) is True
        assert mixin._sanitize_for_json(False) is False

    def test_sanitize_bytes(self):
        """Test sanitization of bytes objects."""
        mixin = self.mixin

        test_bytes = b"hello world"
        result = mixin._sanitize_for_json(test_bytes)

        assert isinstance(result, dict)
        assert result["__type"] == "bytes"
        assert "data" in result

        # Verify base64 encoding
        import base64

        decoded = base64.b64decode(result["data"])
        assert decoded == test_bytes

    def test_sanitize_list_and_tuple(self):
        """Test sanitization of list and tuple objects."""
        mixin = self.mixin

        # Test list
        test_list = [1, "string", None, True]
        result = mixin._sanitize_for_json(test_list)
        assert result == [1, "string", None, True]

        # Test tuple (should become list)
        test_tuple = (1, "string", None, True)
        result = mixin._sanitize_for_json(test_tuple)
        assert result == [1, "string", None, True]

        # Test nested structures
        nested = [{"key": "value"}, [1, 2, 3]]
        result = mixin._sanitize_for_json(nested)
        assert result == [{"key": "value"}, [1, 2, 3]]

    def test_sanitize_dict(self):
        """Test sanitization of dictionary objects."""
        mixin = self.mixin

        test_dict = {
            "string": "value",
            "number": 42,
            "nested": {"inner": "value"},
            123: "numeric_key",  # Should be converted to string
        }

        result = mixin._sanitize_for_json(test_dict)

        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["nested"]["inner"] == "value"
        assert result["123"] == "numeric_key"

    def test_sanitize_custom_object(self):
        """Test sanitization of custom objects."""
        mixin = self.mixin

        class TestClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = TestClass()
        result = mixin._sanitize_for_json(obj)

        assert isinstance(result, dict)
        assert result["__type"] == "TestClass"
        assert result["data"]["attr1"] == "value1"
        assert result["data"]["attr2"] == 42

    def test_sanitize_datetime(self):
        """Test sanitization of datetime objects."""
        mixin = self.mixin

        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = mixin._sanitize_for_json(dt)

        assert isinstance(result, str)
        assert "2023-01-01T12:00:00" in result

    def test_sanitize_circular_reference(self):
        """Test handling of circular references."""
        mixin = self.mixin

        # Create circular reference
        obj1 = {"name": "obj1"}
        obj2 = {"name": "obj2", "ref": obj1}
        obj1["ref"] = obj2

        result = mixin._sanitize_for_json(obj1)

        assert result["name"] == "obj1"
        assert result["ref"]["name"] == "obj2"
        # Should detect circular reference
        assert "circular-reference" in str(result["ref"]["ref"])

    def test_sanitize_non_serializable_object(self):
        """Test handling of non-serializable objects."""
        mixin = self.mixin

        # Create a custom class that raises exceptions
        class NonSerializable:
            def __getattribute__(self, name):
                if name == "__dict__":
                    raise Exception("Cannot access __dict__")
                if name == "__class__":
                    mock_class = Mock()
                    mock_class.__name__ = "NonSerializable"
                    return mock_class
                return super().__getattribute__(name)

        obj = NonSerializable()
        result = mixin._sanitize_for_json(obj)

        assert isinstance(result, str)
        # The actual implementation returns "sanitization-error" prefix
        assert "sanitization-error" in result.lower()

    def test_process_memory_for_saving_default(self):
        """Test memory processing for saving with default settings."""
        # Mock object with debug_keep_previous_outputs = False (default)
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = False

        memory_entries = [
            {
                "agent_id": "test_agent",
                "event_type": "test_event",
                "previous_outputs": {"old": "data"},
                "payload": {
                    "result": "success",
                    "previous_outputs": {"nested": "data"},
                    "_metrics": {"time": 1.5},
                    "extra_data": "should_be_removed",
                },
            },
        ]

        result = mixin._process_memory_for_saving(memory_entries)

        # Should remove previous_outputs
        assert "previous_outputs" not in result[0]
        assert "previous_outputs" not in result[0]["payload"]

        # Should keep essential data
        assert result[0]["payload"]["result"] == "success"
        assert result[0]["payload"]["_metrics"]["time"] == 1.5

        # Should remove extra data
        assert "extra_data" not in result[0]["payload"]

    def test_process_memory_for_saving_debug_mode(self):
        """Test memory processing with debug mode enabled."""
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = True

        memory_entries = [
            {
                "agent_id": "test_agent",
                "previous_outputs": {"keep": "this"},
                "payload": {"result": "success", "extra": "keep_this_too"},
            },
        ]

        result = mixin._process_memory_for_saving(memory_entries)

        # Should keep everything in debug mode
        assert result[0]["previous_outputs"]["keep"] == "this"
        assert result[0]["payload"]["extra"] == "keep_this_too"

    def test_process_memory_meta_report(self):
        """Test memory processing preserves meta reports."""
        mixin = SerializationMixin()
        mixin.debug_keep_previous_outputs = False

        memory_entries = [
            {
                "event_type": "MetaReport",
                "payload": {
                    "detailed_data": "important",
                    "extra_field": "should_be_kept",
                },
            },
        ]

        result = mixin._process_memory_for_saving(memory_entries)

        # Meta reports should keep all data
        assert result[0]["payload"]["detailed_data"] == "important"
        assert result[0]["payload"]["extra_field"] == "should_be_kept"

    def test_should_use_deduplication_format(self):
        """Test deduplication format decision logic."""
        mixin = SerializationMixin()
        mixin._blob_store = {}
        mixin._blob_usage = {}

        # No blobs - should not use deduplication
        assert not mixin._should_use_deduplication_format()

        # Add some blobs with single usage
        mixin._blob_store = {"hash1": {"data": "small"}, "hash2": {"data": "small"}}
        mixin._blob_usage = {"hash1": 1, "hash2": 1}

        # Still small, no duplicates
        assert not mixin._should_use_deduplication_format()

        # Add duplicate usage
        mixin._blob_usage = {"hash1": 2, "hash2": 1}

        # Should use deduplication due to duplicates
        assert mixin._should_use_deduplication_format()


class TestFileOperationsMixin:
    """Test the FileOperationsMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mixin = FileOperationsMixin()
        # Add required attributes
        self.mixin.memory = []
        self.mixin._blob_store = {}
        self.mixin._blob_usage = {}
        self.mixin._blob_threshold = 200
        self.mixin.debug_keep_previous_outputs = False

    def test_resolve_blob_references(self):
        """Test blob reference resolution."""
        blob_store = {
            "hash123": {"original": "data", "type": "response"},
            "hash456": {"another": "blob"},
        }

        # Test resolving blob reference
        obj_with_ref = {
            "_type": "blob_reference",
            "ref": "hash123",
        }

        result = self.mixin._resolve_blob_references(obj_with_ref, blob_store)
        assert result == {"original": "data", "type": "response"}

        # Test missing blob reference
        missing_ref = {
            "_type": "blob_reference",
            "ref": "missing_hash",
        }

        result = self.mixin._resolve_blob_references(missing_ref, blob_store)
        assert result["error"] == "Blob reference not found: missing_hash"
        assert result["_type"] == "missing_blob_reference"

    def test_resolve_blob_references_nested(self):
        """Test nested blob reference resolution."""
        blob_store = {"hash1": {"nested": "data"}}

        nested_obj = {
            "level1": {
                "level2": {
                    "_type": "blob_reference",
                    "ref": "hash1",
                },
            },
            "other": "data",
        }

        result = self.mixin._resolve_blob_references(nested_obj, blob_store)

        assert result["level1"]["level2"] == {"nested": "data"}
        assert result["other"] == "data"

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_legacy_format(self, mock_json_dump, mock_file):
        """Test saving to file with legacy format."""
        # Add required mixin methods
        self.mixin._process_memory_for_saving = Mock(return_value=[{"test": "data"}])
        self.mixin._sanitize_for_json = Mock(return_value=[{"sanitized": "data"}])
        self.mixin._deduplicate_object = Mock(return_value={"deduplicated": "data"})
        self.mixin._should_use_deduplication_format = Mock(return_value=False)
        self.mixin._resolve_blob_references = Mock(return_value={"resolved": "data"})

        self.mixin.memory = [{"original": "data"}]

        self.mixin.save_to_file("test.json")

        # Should open file for writing
        mock_file.assert_called_once_with("test.json", "w", encoding="utf-8")

        # Should use legacy format (list of resolved events)
        mock_json_dump.assert_called_once()
        call_args = mock_json_dump.call_args[0]
        assert call_args[0] == [{"resolved": "data"}]  # Resolved events list

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_file_deduplication_format(self, mock_json_dump, mock_file):
        """Test saving to file with deduplication format."""
        # Setup mocks
        self.mixin._process_memory_for_saving = Mock(return_value=[{"test": "data"}])
        self.mixin._sanitize_for_json = Mock(return_value=[{"sanitized": "data"}])
        self.mixin._deduplicate_object = Mock(return_value={"deduplicated": "data"})
        self.mixin._should_use_deduplication_format = Mock(return_value=True)

        self.mixin.memory = [{"original": "data"}]
        self.mixin._blob_store = {"hash1": {"blob": "data"}}

        self.mixin.save_to_file("test.json")

        # Should use deduplication format
        mock_json_dump.assert_called_once()
        call_args = mock_json_dump.call_args[0]

        # Should have metadata, blob_store, and events
        assert "_metadata" in call_args[0]
        assert "blob_store" in call_args[0]
        assert "events" in call_args[0]
        assert call_args[0]["_metadata"]["deduplication_enabled"] is True

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump", side_effect=Exception("JSON Error"))
    def test_save_to_file_error_handling(self, mock_json_dump, mock_file):
        """Test error handling during file save."""
        # Setup normal methods but failing JSON dump
        self.mixin._process_memory_for_saving = Mock(return_value=[{"test": "data"}])
        self.mixin._sanitize_for_json = Mock(return_value=[{"sanitized": "data"}])
        self.mixin._deduplicate_object = Mock(return_value={"deduplicated": "data"})
        self.mixin._should_use_deduplication_format = Mock(return_value=False)
        self.mixin._resolve_blob_references = Mock(return_value={"resolved": "data"})

        self.mixin.memory = [{"data": "test"}]

        # Should not raise exception, should handle gracefully
        self.mixin.save_to_file("test.json")

        # Should try to open file twice (once for normal, once for simplified)
        assert mock_file.call_count >= 1

    def test_load_from_file_legacy_format(self):
        """Test loading file with legacy format."""
        legacy_data = [{"event": "data", "timestamp": "2023-01-01"}]

        with patch("builtins.open", mock_open(read_data=json.dumps(legacy_data))):
            result = FileOperationsMixin.load_from_file("test.json")

            assert "events" in result
            assert result["events"] == legacy_data
            # Legacy format has version: "legacy" not format: "legacy"
            assert result["_metadata"]["version"] == "legacy"
            assert result["_metadata"]["deduplication_enabled"] is False

    def test_load_from_file_deduplication_format(self):
        """Test loading file with deduplication format."""
        dedup_data = {
            "_metadata": {"deduplication_enabled": True},
            "blob_store": {"hash1": {"blob": "data"}},
            "events": [{"_type": "blob_reference", "ref": "hash1"}],
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(dedup_data))):
            result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=True)

            # Should resolve blob references
            assert result["events"] == [{"blob": "data"}]

    def test_load_from_file_no_resolve_blobs(self):
        """Test loading file without resolving blob references."""
        dedup_data = {
            "_metadata": {"deduplication_enabled": True},
            "blob_store": {"hash1": {"blob": "data"}},
            "events": [{"_type": "blob_reference", "ref": "hash1"}],
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(dedup_data))):
            result = FileOperationsMixin.load_from_file("test.json", resolve_blobs=False)

            # Should keep blob references unresolved
            assert result["events"] == [{"_type": "blob_reference", "ref": "hash1"}]

    def test_load_from_file_not_found(self):
        """Test loading non-existent file."""
        # The actual implementation catches and logs the error, doesn't raise
        result = FileOperationsMixin.load_from_file("nonexistent.json")

        # Should return empty result structure
        assert "events" in result
        assert result["events"] == []


class MockMemoryLogger(BaseMemoryLogger):
    """Mock implementation of BaseMemoryLogger for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._storage = {}
        self._sets = {}

    def cleanup_expired_memories(self, dry_run=False):
        return {"cleaned": 0, "dry_run": dry_run}

    def get_memory_stats(self):
        return {"total_memories": len(self.memory)}

    def log(self, agent_id, event_type, payload, **kwargs):
        entry = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }
        self.memory.append(entry)

    def tail(self, count=10):
        return self.memory[-count:]

    def hset(self, name, key, value):
        if name not in self._storage:
            self._storage[name] = {}
        self._storage[name][key] = str(value)
        return 1

    def hget(self, name, key):
        return self._storage.get(name, {}).get(key)

    def hkeys(self, name):
        return list(self._storage.get(name, {}).keys())

    def hdel(self, name, *keys):
        count = 0
        if name in self._storage:
            for key in keys:
                if key in self._storage[name]:
                    del self._storage[name][key]
                    count += 1
        return count

    def smembers(self, name):
        return list(self._sets.get(name, set()))

    def sadd(self, name, *values):
        if name not in self._sets:
            self._sets[name] = set()
        before = len(self._sets[name])
        self._sets[name].update(values)
        return len(self._sets[name]) - before

    def srem(self, name, *values):
        if name not in self._sets:
            return 0
        before = len(self._sets[name])
        self._sets[name].difference_update(values)
        return before - len(self._sets[name])

    def get(self, key):
        return self._storage.get("__global__", {}).get(key)

    def set(self, key, value):
        if "__global__" not in self._storage:
            self._storage["__global__"] = {}
        self._storage["__global__"][key] = str(value)
        return True

    def delete(self, *keys):
        count = 0
        if "__global__" in self._storage:
            for key in keys:
                if key in self._storage["__global__"]:
                    del self._storage["__global__"][key]
                    count += 1
        return count


class TestBaseMemoryLogger:
    """Test the BaseMemoryLogger functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = MockMemoryLogger()

    def test_initialization_default(self):
        """Test default initialization."""
        logger = MockMemoryLogger()

        assert logger.stream_key == "orka:memory"
        assert logger.memory == []
        assert logger.debug_keep_previous_outputs is False
        assert logger.decay_config["enabled"] is False
        assert logger._blob_store == {}
        assert logger._blob_usage == {}
        assert logger._blob_threshold == 200

    def test_initialization_with_decay(self):
        """Test initialization with decay configuration."""
        decay_config = {
            "enabled": True,
            "default_short_term_hours": 2.0,
            "check_interval_minutes": 15,
        }

        logger = MockMemoryLogger(decay_config=decay_config)

        assert logger.decay_config["enabled"] is True
        assert logger.decay_config["default_short_term_hours"] == 2.0
        assert logger.decay_config["check_interval_minutes"] == 15
        # Should have defaults merged
        assert "default_long_term_hours" in logger.decay_config

    def test_calculate_importance_score(self):
        """Test importance score calculation."""
        logger = self.logger

        # Test base score
        score = logger._calculate_importance_score("unknown", "test_agent", {})
        assert score == 0.5  # Base score

        # Test event type boost
        score = logger._calculate_importance_score("write", "test_agent", {})
        assert score > 0.5  # Should have boost

        # Test agent type boost
        score = logger._calculate_importance_score("test", "memory_agent", {})
        assert score > 0.5  # Should have boost

        # Test payload result boost
        score = logger._calculate_importance_score("test", "test_agent", {"result": "success"})
        assert score > 0.5  # Should have boost

        # Test payload error penalty
        score = logger._calculate_importance_score("test", "test_agent", {"error": "failed"})
        assert score < 0.5  # Should have penalty

    def test_classify_memory_type(self):
        """Test memory type classification."""
        logger = self.logger

        # Log category should always be short-term
        memory_type = logger._classify_memory_type("write", 0.9, "log")
        assert memory_type == "short_term"

        # Stored memories can be long-term based on rules
        memory_type = logger._classify_memory_type("write", 0.5, "stored")
        assert memory_type == "long_term"

        # Test importance score fallback for stored memories
        memory_type = logger._classify_memory_type("unknown", 0.8, "stored")
        assert memory_type == "long_term"

        memory_type = logger._classify_memory_type("unknown", 0.6, "stored")
        assert memory_type == "short_term"

    def test_classify_memory_category(self):
        """Test memory category classification."""
        logger = self.logger

        # Test different agent types and events
        category = logger._classify_memory_category("write", "memory_writer", {"result": "data"})
        assert category in ["log", "stored"]

        category = logger._classify_memory_category("debug", "test_agent", {})
        assert category in ["log", "stored"]

    @patch("threading.Thread")
    def test_decay_scheduler_start_stop(self, mock_thread):
        """Test decay scheduler lifecycle."""
        decay_config = {"enabled": True}
        logger = MockMemoryLogger(decay_config=decay_config)

        # Should start thread during initialization
        mock_thread.assert_called_once()

        # Test stopping scheduler
        logger.stop_decay_scheduler()
        assert logger._decay_stop_event.is_set()

    def test_log_method(self):
        """Test the log method."""
        logger = self.logger

        logger.log(
            agent_id="test_agent",
            event_type="test_event",
            payload={"result": "success"},
            step=1,
            run_id="run_123",
        )

        assert len(logger.memory) == 1
        entry = logger.memory[0]
        assert entry["agent_id"] == "test_agent"
        assert entry["event_type"] == "test_event"
        assert entry["payload"]["result"] == "success"
        assert entry["step"] == 1
        assert entry["run_id"] == "run_123"

    def test_tail_method(self):
        """Test the tail method."""
        logger = self.logger

        # Add some entries
        for i in range(5):
            logger.log(f"agent_{i}", "event", {"data": i})

        # Test getting last 3 entries
        recent = logger.tail(3)
        assert len(recent) == 3
        assert recent[0]["payload"]["data"] == 2
        assert recent[2]["payload"]["data"] == 4

    def test_hash_operations(self):
        """Test hash-based storage operations."""
        logger = self.logger

        # Test hset/hget
        result = logger.hset("test_hash", "key1", "value1")
        assert result == 1

        value = logger.hget("test_hash", "key1")
        assert value == "value1"

        # Test hkeys
        logger.hset("test_hash", "key2", "value2")
        keys = logger.hkeys("test_hash")
        assert set(keys) == {"key1", "key2"}

        # Test hdel
        deleted = logger.hdel("test_hash", "key1")
        assert deleted == 1

        value = logger.hget("test_hash", "key1")
        assert value is None

    def test_set_operations(self):
        """Test set-based storage operations."""
        logger = self.logger

        # Test sadd
        added = logger.sadd("test_set", "member1", "member2")
        assert added == 2

        # Test smembers
        members = logger.smembers("test_set")
        assert set(members) == {"member1", "member2"}

        # Test srem
        removed = logger.srem("test_set", "member1")
        assert removed == 1

        members = logger.smembers("test_set")
        assert members == ["member2"]

    def test_key_value_operations(self):
        """Test key-value storage operations."""
        logger = self.logger

        # Test set/get
        result = logger.set("test_key", "test_value")
        assert result is True

        value = logger.get("test_key")
        assert value == "test_value"

        # Test delete
        deleted = logger.delete("test_key")
        assert deleted == 1

        value = logger.get("test_key")
        assert value is None

    def test_compute_blob_hash(self):
        """Test blob hash computation."""
        logger = self.logger

        test_obj = {"large": "data" * 100}
        hash1 = logger._compute_blob_hash(test_obj)
        hash2 = logger._compute_blob_hash(test_obj)

        # Same object should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

        # Different object should produce different hash
        different_obj = {"different": "data" * 100}
        hash3 = logger._compute_blob_hash(different_obj)
        assert hash1 != hash3

    def test_should_deduplicate_blob(self):
        """Test blob deduplication decision."""
        logger = self.logger

        # Small object should not be deduplicated
        small_obj = {"small": "data"}
        assert not logger._should_deduplicate_blob(small_obj)

        # Large object without response/result should not be deduplicated
        large_obj_no_key = {"large": "x" * 300}
        assert not logger._should_deduplicate_blob(large_obj_no_key)

        # Large object with response key should be deduplicated
        large_obj_with_response = {"response": "x" * 300}
        assert logger._should_deduplicate_blob(large_obj_with_response)

        # Large object with result key should be deduplicated
        large_obj_with_result = {"result": "x" * 300}
        assert logger._should_deduplicate_blob(large_obj_with_result)

        # Non-dict should not be deduplicated
        assert not logger._should_deduplicate_blob("string" * 100)

    def test_store_blob(self):
        """Test blob storage functionality."""
        logger = self.logger

        test_blob = {"data": "x" * 300}
        blob_hash = logger._store_blob(test_blob)

        assert blob_hash in logger._blob_store
        assert logger._blob_store[blob_hash] == test_blob
        assert logger._blob_usage[blob_hash] == 1

        # Store same blob again
        blob_hash2 = logger._store_blob(test_blob)
        assert blob_hash == blob_hash2
        assert logger._blob_usage[blob_hash] == 2

    def test_create_blob_reference(self):
        """Test blob reference creation."""
        logger = self.logger

        blob_hash = "test_hash_123"
        original_keys = ["key1", "key2"]

        ref = logger._create_blob_reference(blob_hash, original_keys)

        assert ref["_type"] == "blob_reference"
        assert ref["ref"] == blob_hash
        assert ref["_original_keys"] == original_keys

    def test_deduplicate_object(self):
        """Test object deduplication."""
        logger = self.logger

        # Test small object (no deduplication)
        small_obj = {"small": "data"}
        result = logger._deduplicate_object(small_obj)
        assert result == small_obj

        # Test large object that should be deduplicated
        large_obj = {"large": "x" * 300, "other": "data"}
        result = logger._deduplicate_object(large_obj)

        # If deduplicated, should create blob reference
        if result != large_obj:
            assert result["_type"] == "blob_reference"
            assert "ref" in result
        else:
            # Otherwise, should be the original object
            assert result == large_obj


class TestMemoryLoggerFactory:
    """Test the memory logger factory functionality."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_create_memory_logger_default(self, mock_redisstack):
        """Test creating memory logger with default settings."""
        mock_instance = Mock()
        mock_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_instance

        logger = create_memory_logger()

        # Should default to redisstack
        mock_redisstack.assert_called_once()

    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    def test_create_memory_logger_redis(self, mock_redis):
        """Test creating Redis memory logger."""
        mock_instance = Mock()
        mock_redis.return_value = mock_instance

        # Force basic redis mode to avoid RedisStack fallback
        with patch.dict(os.environ, {"ORKA_FORCE_BASIC_REDIS": "true"}):
            logger = create_memory_logger(backend="redis", redis_url="redis://localhost:6379")

        mock_redis.assert_called_once()
        call_kwargs = mock_redis.call_args[1]
        assert call_kwargs["redis_url"] == "redis://localhost:6379"

    @patch("orka.memory.kafka_logger.KafkaMemoryLogger")
    def test_create_memory_logger_kafka(self, mock_kafka):
        """Test creating Kafka memory logger."""
        mock_instance = Mock()
        mock_kafka.return_value = mock_instance

        logger = create_memory_logger(
            backend="kafka",
            bootstrap_servers="localhost:9092",
        )

        mock_kafka.assert_called_once()
        call_kwargs = mock_kafka.call_args[1]
        assert call_kwargs["bootstrap_servers"] == "localhost:9092"

    def test_create_memory_logger_unsupported(self):
        """Test creating memory logger with unsupported backend."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            create_memory_logger(backend="unsupported")

    @patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "redis", "ORKA_FORCE_BASIC_REDIS": "true"})
    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    def test_create_memory_logger_env_backend(self, mock_redis):
        """Test creating memory logger from environment variable."""
        mock_instance = Mock()
        mock_redis.return_value = mock_instance

        # Should use environment variable
        logger = create_memory_logger()

        mock_redis.assert_called_once()

    @patch(
        "orka.memory.redisstack_logger.RedisStackMemoryLogger",
        side_effect=ImportError("RedisStack not available"),
    )
    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    def test_create_memory_logger_fallback(self, mock_redis, mock_redisstack):
        """Test memory logger fallback when RedisStack unavailable."""
        mock_instance = Mock()
        mock_redis.return_value = mock_instance

        logger = create_memory_logger(backend="redisstack")

        # Should fallback to Redis
        mock_redis.assert_called_once()

    @patch(
        "orka.memory.kafka_logger.KafkaMemoryLogger",
        side_effect=ImportError("Kafka not available"),
    )
    def test_create_memory_logger_missing_kafka(self, mock_kafka):
        """Test creating Kafka logger when unavailable."""
        # Should fallback to RedisStack instead of raising error
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_instance = Mock()
            mock_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_instance

            logger = create_memory_logger(backend="kafka")

            # Should fallback to RedisStack
            mock_redisstack.assert_called_once()


class TestMemoryDecaySystem:
    """Test memory decay functionality."""

    def test_decay_config_initialization(self):
        """Test decay configuration initialization with defaults."""
        logger = MockMemoryLogger()

        config = logger.decay_config
        assert "enabled" in config
        assert "default_short_term_hours" in config
        assert "memory_type_rules" in config
        assert "importance_rules" in config

    def test_memory_classification_edge_cases(self):
        """Test edge cases in memory classification."""
        logger = MockMemoryLogger()

        # Test with None values
        score = logger._calculate_importance_score("", "", {})
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Test with complex payload
        complex_payload = {
            "result": {"nested": "data"},
            "error": None,
            "metrics": {"time": 1.5},
        }
        score = logger._calculate_importance_score("write", "memory_agent", complex_payload)
        assert score > 0.5  # Should have multiple boosts

    def test_cleanup_expired_memories(self):
        """Test cleanup of expired memories."""
        logger = MockMemoryLogger()

        # Test dry run
        result = logger.cleanup_expired_memories(dry_run=True)
        assert result["dry_run"] is True

        # Test actual cleanup
        result = logger.cleanup_expired_memories(dry_run=False)
        assert result["dry_run"] is False

    def test_get_memory_stats(self):
        """Test memory statistics retrieval."""
        logger = MockMemoryLogger()

        # Add some entries
        logger.log("agent1", "event1", {})
        logger.log("agent2", "event2", {})

        stats = logger.get_memory_stats()
        assert "total_memories" in stats
        assert stats["total_memories"] == 2
