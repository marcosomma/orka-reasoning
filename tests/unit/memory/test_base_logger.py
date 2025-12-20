from datetime import datetime, timezone

import pytest

from orka.memory.base_logger import BaseMemoryLogger, json_serializer


class DummyMemoryLogger(BaseMemoryLogger):
    # implement abstract methods minimally for testing
    def log(self, *args, **kwargs):
        self.memory.append({"args": args, "kwargs": kwargs})

    def tail(self, count: int = 10):
        return self.memory[-count:]

    def cleanup_expired_memories(self, dry_run: bool = False):
        return 0

    def get_memory_stats(self):
        return {"count": len(self.memory)}
    
    # Redis-compatible minimal methods required by the abstract base
    def hset(self, name: str, key: str, value):
        return 1

    def hget(self, name: str, key: str):
        return None

    def hkeys(self, name: str):
        return []

    def hdel(self, name: str, *keys):
        return 0

    def get(self, key: str):
        return None

    def set(self, key: str, value):
        return True

    def delete(self, *keys):
        return 0

    def smembers(self, name: str):
        return set()

    def sadd(self, name: str, *values):
        return 0

    def srem(self, name: str, *values):
        return 0

    def scan(self, cursor: int = 0, match: str | None = None, count: int = 10):
        return (0, [])


def test_json_serializer_datetime():
    now = datetime.now(timezone.utc)
    s = json_serializer(now)
    assert isinstance(s, str)


def test_dummy_memory_logger_basic_usage():
    logger = DummyMemoryLogger()
    assert logger.get_memory_stats()["count"] == 0

    logger.log("agent1", "event", {"k": "v"})
    assert logger.get_memory_stats()["count"] == 1

    tail = logger.tail(1)
    assert isinstance(tail, list)
    assert len(tail) == 1
import json
import threading
from datetime import UTC, datetime
from unittest.mock import MagicMock, call, patch

import pytest

from orka.memory.base_logger import BaseMemoryLogger, json_serializer


# Concrete implementation for testing abstract methods
class ConcreteMemoryLogger(BaseMemoryLogger):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logged_events = []
        self.stats = {
            "backend": "concrete",
            "decay_enabled": self.decay_config.get("enabled", False),
            "total_streams": 0,
            "total_entries": 0,
            "expired_entries": 0,
            "entries_by_type": {},
            "entries_by_memory_type": {},
            "entries_by_category": {},
            "decay_config": self.decay_config,
        }
        self.hash_store = {}
        self.set_members = {}
        self.key_values = {}

    def log(self, agent_id, event_type, payload, **kwargs):
        entry = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            **kwargs,
        }
        self.logged_events.append(entry)
        self.stats["total_entries"] += 1
        self.stats["entries_by_type"][event_type] = self.stats["entries_by_type"].get(event_type, 0) + 1
        category = self._classify_memory_category(event_type, agent_id, payload, kwargs.get("log_type", "log"))
        memory_type = self._classify_memory_type(event_type, self._calculate_importance_score(event_type, agent_id, payload), category)
        self.stats["entries_by_category"][category] = self.stats["entries_by_category"].get(category, 0) + 1
        self.stats["entries_by_memory_type"][memory_type] = self.stats["entries_by_memory_type"].get(memory_type, 0) + 1

    def tail(self, count=10):
        return self.logged_events[-count:]

    def cleanup_expired_memories(self, dry_run=False):
        deleted_count = 0
        deleted_entries = []
        # For simplicity in this mock, we'll just simulate deleting some entries
        if not dry_run and len(self.logged_events) > 2:
            deleted_entries = self.logged_events[:2]
            self.logged_events = self.logged_events[2:]
            deleted_count = 2
            self.stats["expired_entries"] += deleted_count
            self.stats["total_entries"] -= deleted_count

        return {"status": "completed", "deleted_count": deleted_count, "deleted_entries": deleted_entries}

    def get_memory_stats(self):
        return self.stats

    def hset(self, name, key, value):
        if name not in self.hash_store:
            self.hash_store[name] = {}
        self.hash_store[name][key] = value
        return 1

    def hget(self, name, key):
        return self.hash_store.get(name, {}).get(key)

    def hkeys(self, name):
        return list(self.hash_store.get(name, {}).keys())

    def hdel(self, name, *keys):
        if name not in self.hash_store: return 0
        deleted = 0
        for key in keys:
            if key in self.hash_store[name]:
                del self.hash_store[name][key]
                deleted += 1
        return deleted

    def smembers(self, name):
        return list(self.set_members.get(name, set()))

    def sadd(self, name, *values):
        if name not in self.set_members:
            self.set_members[name] = set()
        added = 0
        for value in values:
            if value not in self.set_members[name]:
                self.set_members[name].add(value)
                added += 1
        return added

    def srem(self, name, *values):
        if name not in self.set_members: return 0
        removed = 0
        for value in values:
            if value in self.set_members[name]:
                self.set_members[name].remove(value)
                removed += 1
        return removed

    def get(self, key):
        return self.key_values.get(key)

    def set(self, key, value):
        self.key_values[key] = value
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.key_values:
                del self.key_values[key]
                deleted += 1
        return deleted

    def scan(self, cursor: int = 0, match: str | None = None, count: int = 10):
        return (0, [])

@pytest.fixture
def mock_logger():
    with patch("orka.memory.base_logger.logger") as mock_log:
        yield mock_log

@pytest.fixture
def mock_threading_thread():
    with patch("threading.Thread") as mock_thread:
        yield mock_thread

@pytest.fixture
def mock_threading_event():
    with patch("threading.Event") as mock_event:
        yield mock_event

class TestBaseMemoryLogger:
    @patch("threading.Event")
    def test_init_default_config(self, mock_event):
        logger = ConcreteMemoryLogger()
        assert logger.stream_key == "orka:memory"
        assert not logger.debug_keep_previous_outputs
        assert not logger.decay_config["enabled"]
        assert logger._decay_thread is None
        assert logger._decay_stop_event is mock_event.return_value
        assert logger._blob_threshold == 200

    def test_init_custom_config(self):
        custom_config = {"enabled": True, "default_short_term_hours": 2.0}
        logger = ConcreteMemoryLogger(debug_keep_previous_outputs=True, decay_config=custom_config)
        assert logger.debug_keep_previous_outputs
        assert logger.decay_config["enabled"]
        assert logger.decay_config["default_short_term_hours"] == 2.0

    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Thread")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Event")
    def test_init_decay_scheduler_starts_if_enabled(self, mock_event, mock_thread):
        custom_config = {"enabled": True}
        logger = ConcreteMemoryLogger(decay_config=custom_config)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
        logger.stop_decay_scheduler()

    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Thread")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Event")
    def test_init_decay_scheduler_does_not_start_if_disabled(self, mock_event, mock_thread):
        custom_config = {"enabled": False}
        logger = ConcreteMemoryLogger(decay_config=custom_config)
        mock_thread.assert_not_called()

    def test_resolve_memory_preset_no_preset(self):
        config = {"test": 1}
        logger = ConcreteMemoryLogger()
        resolved = logger._resolve_memory_preset(None, config)
        assert resolved == config

    @patch("orka.memory.presets.merge_preset_with_config")
    def test_resolve_memory_preset_with_preset(self, mock_merge):
        mock_merge.return_value = {"preset_config": True}
        logger = ConcreteMemoryLogger()
        resolved = logger._resolve_memory_preset("sensory", {"custom": True})
        mock_merge.assert_called_once_with("sensory", {"custom": True}, None)
        assert resolved == {"preset_config": True}

    @patch("orka.memory.base_logger_mixins.config_mixin.logger")
    @patch("orka.memory.presets.merge_preset_with_config")
    def test_resolve_memory_preset_import_error(self, mock_merge, mock_log):
        mock_merge.side_effect = ImportError("No presets")
        logger_instance = ConcreteMemoryLogger()
        resolved = logger_instance._resolve_memory_preset("sensory", {"custom": True})
        mock_log.warning.assert_called_once_with("Memory presets not available, using custom config only")
        assert resolved == {"custom": True}

    @patch("orka.memory.base_logger_mixins.config_mixin.logger")
    @patch("orka.memory.presets.merge_preset_with_config")
    def test_resolve_memory_preset_general_exception(self, mock_merge, mock_log):
        mock_merge.side_effect = Exception("Error loading preset")
        logger_instance = ConcreteMemoryLogger()
        resolved = logger_instance._resolve_memory_preset("sensory", {"custom": True})
        mock_log.error.assert_called_once_with("Failed to load memory preset 'sensory': Error loading preset")
        mock_log.warning.assert_called_once_with("Falling back to custom decay config")
        assert resolved == {"custom": True}

    def test_init_decay_config_defaults(self):
        logger = ConcreteMemoryLogger(decay_config={})
        config = logger.decay_config
        assert not config["enabled"]
        assert config["default_short_term_hours"] == 1.0
        assert config["check_interval_minutes"] == 30

    def test_init_decay_config_merge(self):
        custom = {
            "enabled": True,
            "default_short_term_hours": 5.0,
            "importance_rules": {"base_score": 0.8, "new_rule": 0.1},
        }
        logger = ConcreteMemoryLogger(decay_config=custom)
        config = logger.decay_config
        assert config["enabled"]
        assert config["default_short_term_hours"] == 5.0
        assert config["default_long_term_hours"] == 24.0  # Default not overridden
        assert config["importance_rules"]["base_score"] == 0.8
        assert config["importance_rules"]["new_rule"] == 0.1
        assert "event_type_boosts" in config["importance_rules"]

    def test_calculate_importance_score_base(self):
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score("event", "agent", {})
        assert score == 0.5

    def test_calculate_importance_score_event_boost(self):
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score("write", "agent", {})
        assert score == 0.8  # 0.5 (base) + 0.3 (write boost)

    def test_calculate_importance_score_agent_boost(self):
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score("event", "memory-agent", {})
        assert score == 0.7  # 0.5 (base) + 0.2 (memory agent boost)

    def test_calculate_importance_score_payload_result_boost(self):
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score("event", "agent", {"result": True})
        assert score == 0.6  # 0.5 (base) + 0.1 (result in payload)

    def test_calculate_importance_score_payload_error_deduction(self):
        logger = ConcreteMemoryLogger()
        score = logger._calculate_importance_score("event", "agent", {"error": "some error"})
        assert score == 0.4  # 0.5 (base) - 0.1 (error in payload)

    def test_calculate_importance_score_clamped(self):
        logger = ConcreteMemoryLogger()
        # Test upper clamp
        logger.decay_config["importance_rules"]["base_score"] = 1.0
        logger.decay_config["importance_rules"]["event_type_boosts"]["high_boost"] = 0.5
        score = logger._calculate_importance_score("high_boost", "agent", {})
        assert score == 1.0

        # Test lower clamp
        logger.decay_config["importance_rules"]["base_score"] = 0.0
        logger.decay_config["importance_rules"]["event_type_boosts"]["low_boost"] = -0.5
        score = logger._calculate_importance_score("low_boost", "agent", {})
        assert score == 0.0

    def test_classify_memory_type_log_category_always_short_term(self):
        logger = ConcreteMemoryLogger()
        memory_type = logger._classify_memory_type("event", 0.9, "log")
        assert memory_type == "short_term"

    def test_classify_memory_type_stored_long_term_event(self):
        logger = ConcreteMemoryLogger()
        memory_type = logger._classify_memory_type("success", 0.5, "stored")
        assert memory_type == "long_term"

    def test_classify_memory_type_stored_short_term_event(self):
        logger = ConcreteMemoryLogger()
        memory_type = logger._classify_memory_type("debug", 0.9, "stored")
        assert memory_type == "short_term"

    def test_classify_memory_type_stored_importance_score_fallback_long(self):
        logger = ConcreteMemoryLogger()
        # Event type not in rules, score >= 0.7
        memory_type = logger._classify_memory_type("unknown_event", 0.8, "stored")
        assert memory_type == "long_term"

    def test_classify_memory_type_stored_importance_score_fallback_short(self):
        logger = ConcreteMemoryLogger()
        # Event type not in rules, score < 0.7
        memory_type = logger._classify_memory_type("unknown_event", 0.6, "stored")
        assert memory_type == "short_term"

    def test_classify_memory_category_explicit_memory(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {}, log_type="memory")
        assert category == "stored"

    def test_classify_memory_category_explicit_log(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {}, log_type="log")
        assert category == "log"

    def test_classify_memory_category_legacy_memory_writer(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("write", "memory-writer-agent", {}, log_type="memory")
        assert category == "stored"

    def test_classify_memory_category_payload_content(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {"content": "some content", "metadata": {}}, log_type="memory")
        assert category == "stored"

    def test_classify_memory_category_payload_memory_object(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {"memory_object": {}}, log_type="memory")
        assert category == "stored"

    def test_classify_memory_category_payload_memories(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {"memories": []}, log_type="memory")
        assert category == "stored"

    def test_classify_memory_category_default_to_log(self):
        logger = ConcreteMemoryLogger()
        category = logger._classify_memory_category("event", "agent", {"other_field": "value"})
        assert category == "log"

    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Thread")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Event")
    @patch.object(ConcreteMemoryLogger, "cleanup_expired_memories")
    def test_decay_scheduler_starts_and_stops(self, mock_cleanup, mock_event, mock_thread):
        mock_event_instance = mock_event.return_value
        mock_event_instance.wait.side_effect = [False, False, True] # Run twice, then stop

        logger_instance = ConcreteMemoryLogger(decay_config={"enabled": True, "check_interval_minutes": 0.01})
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

        # Manually call the target function of the thread to simulate its execution
        # In a real scenario, the thread would run this in the background
        thread_target_func = mock_thread.call_args[1]["target"]
        thread_target_func()

        assert mock_cleanup.call_count == 2
        mock_event_instance.set.assert_not_called() # Should not be called until stop_decay_scheduler

        logger_instance.stop_decay_scheduler()
        mock_event_instance.set.assert_called_once()
        mock_thread.return_value.join.assert_called_once_with(timeout=5)

    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Thread")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Event")
    @patch.object(ConcreteMemoryLogger, "cleanup_expired_memories")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.logger")
    def test_decay_scheduler_handles_exceptions(self, mock_log, mock_cleanup, mock_event, mock_thread):
        mock_event_instance = mock_event.return_value
        mock_event_instance.wait.side_effect = [False, False, True] # Run twice, then stop
        mock_cleanup.side_effect = [Exception("Cleanup failed"), None, None] # First call fails

        logger_instance = ConcreteMemoryLogger(decay_config={"enabled": True, "check_interval_minutes": 0.01})

        thread_target_func = mock_thread.call_args[1]["target"]
        thread_target_func()

        assert mock_cleanup.call_count == 2
        mock_log.error.assert_called_once_with("Error during automatic memory decay (failure 1): Cleanup failed")
        mock_log.warning.assert_not_called()
        logger_instance.stop_decay_scheduler()

    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Thread")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.threading.Event")
    @patch.object(ConcreteMemoryLogger, "cleanup_expired_memories")
    @patch("orka.memory.base_logger_mixins.decay_scheduler_mixin.logger")
    def test_decay_scheduler_increases_interval_on_consecutive_failures(self, mock_log, mock_cleanup, mock_event, mock_thread):
        mock_event_instance = mock_event.return_value
        mock_event_instance.wait.side_effect = [False, False, False, False, True] # 4 failures, then stop
        mock_cleanup.side_effect = [Exception("Fail1"), Exception("Fail2"), Exception("Fail3"), None, None]

        logger_instance = ConcreteMemoryLogger(decay_config={"enabled": True, "check_interval_minutes": 0.01})

        thread_target_func = mock_thread.call_args[1]["target"]
        thread_target_func()

        assert mock_cleanup.call_count == 4
        assert mock_log.error.call_count == 3
        mock_log.warning.assert_called_once()
        mock_log.warning.assert_called_with(
            "Memory decay has failed 3 times. Increasing interval to prevent resource exhaustion."
        )
        logger_instance.stop_decay_scheduler()

    def test_json_serializer_datetime(self):
        dt = datetime(2025, 1, 1, 12, 30, 0, tzinfo=UTC)
        serialized = json.dumps(dt, default=json_serializer)
        assert serialized == '"2025-01-01T12:30:00+00:00"'

    def test_json_serializer_unserializable_type(self):
        class Unserializable:
            pass
        with pytest.raises(TypeError):
            json.dumps(Unserializable(), default=json_serializer)

    def test_compute_blob_hash_dict(self):
        logger = ConcreteMemoryLogger()
        obj = {"key": "value", "num": 123}
        hash1 = logger._compute_blob_hash(obj)
        obj2 = {"num": 123, "key": "value"} # Same content, different order
        hash2 = logger._compute_blob_hash(obj2)
        assert hash1 == hash2

    def test_compute_blob_hash_non_serializable(self):
        logger = ConcreteMemoryLogger()
        class NonSerializable:
            def __str__(self): return "non_serializable_object"
        obj = NonSerializable()
        hash_val = logger._compute_blob_hash(obj)
        expected_hash = "be58f7ef27d7a8221be07d9bf21cbc51157e272cc27df7796099e848e991a4c3"
        assert hash_val == expected_hash # SHA256 of "non_serializable_object"

    def test_should_deduplicate_blob_not_dict(self):
        logger = ConcreteMemoryLogger()
        assert not logger._should_deduplicate_blob("string")
        assert not logger._should_deduplicate_blob(123)

    def test_should_deduplicate_blob_below_threshold(self):
        logger = ConcreteMemoryLogger()
        obj = {"short": "a" * 10}
        assert not logger._should_deduplicate_blob(obj)

    def test_should_deduplicate_blob_above_threshold(self):
        logger = ConcreteMemoryLogger()
        obj = {"long": "a" * 250}
        assert logger._should_deduplicate_blob(obj)

    def test_should_deduplicate_blob_serialization_error(self):
        logger = ConcreteMemoryLogger()
        class Unserializable:
            pass
        obj = {"key": Unserializable()}
        assert not logger._should_deduplicate_blob(obj)

    def test_store_blob_new_blob(self):
        logger = ConcreteMemoryLogger()
        obj = {"data": "some data"}
        blob_hash = logger._store_blob(obj)
        assert blob_hash in logger._blob_store
        assert logger._blob_store[blob_hash] == obj
        assert logger._blob_usage[blob_hash] == 1

    def test_store_blob_existing_blob(self):
        logger = ConcreteMemoryLogger()
        obj = {"data": "some data"}
        blob_hash1 = logger._store_blob(obj)
        blob_hash2 = logger._store_blob(obj)
        assert blob_hash1 == blob_hash2
        assert logger._blob_usage[blob_hash1] == 2

    def test_create_blob_reference(self):
        logger = ConcreteMemoryLogger()
        ref = logger._create_blob_reference("test_hash", ["key1", "key2"])
        assert ref == {"ref": "test_hash", "_type": "blob_reference", "_original_keys": ["key1", "key2"]}

    def test_deduplicate_object_no_deduplication(self):
        logger = ConcreteMemoryLogger()
        obj = {"small": "a" * 10}
        deduplicated = logger._recursive_deduplicate(obj)
        assert deduplicated == obj
        assert not logger._blob_store

    def test_deduplicate_object_with_deduplication(self):
        logger = ConcreteMemoryLogger()
        obj = {"large": "a" * 250}
        deduplicated = logger._recursive_deduplicate(obj)
        assert "ref" in deduplicated
        assert deduplicated["_type"] == "blob_reference"
        assert deduplicated["_original_keys"] == ["large"]
        assert len(logger._blob_store) == 1

    def test_deduplicate_object_nested_dict(self):
        logger = ConcreteMemoryLogger()
        nested_obj = {"nested_large": "b" * 250}
        obj = {"small": "c" * 10, "nested": nested_obj}
        deduplicated = logger._recursive_deduplicate(obj)

        assert deduplicated["small"] == "c" * 10
        assert "ref" in deduplicated["nested"]
        assert deduplicated["nested"]["_type"] == "blob_reference"
        assert len(logger._blob_store) == 1

    def test_deduplicate_object_nested_list(self):
        logger = ConcreteMemoryLogger()
        list_item = {"list_large": "d" * 250}
        obj = {"list": [{"small": "e" * 10}, list_item]}
        deduplicated = logger._recursive_deduplicate(obj)

        assert deduplicated["list"][0] == {"small": "e" * 10}
        assert "ref" in deduplicated["list"][1]
        assert deduplicated["list"][1]["_type"] == "blob_reference"
        assert len(logger._blob_store) == 1

    def test_process_memory_for_saving_removes_previous_outputs(self):
        logger = ConcreteMemoryLogger()
        entry = {"agent_id": "test", "payload": {}, "previous_outputs": {"output1": "data"}}
        processed = logger._process_memory_for_saving([entry])
        # SerializationMixin removes previous_outputs without adding summary
        assert "previous_outputs" not in processed[0]

    def test_process_memory_for_saving_keeps_previous_outputs_if_debug_enabled(self):
        logger = ConcreteMemoryLogger(debug_keep_previous_outputs=True)
        entry = {"agent_id": "test", "payload": {}, "previous_outputs": {"output1": "data"}}
        processed = logger._process_memory_for_saving([entry])
        assert "previous_outputs" in processed[0]
        assert "previous_outputs_summary" not in processed[0]

    def test_sanitize_for_json_basic_types(self):
        logger = ConcreteMemoryLogger()
        assert logger._sanitize_for_json(123) == 123
        assert logger._sanitize_for_json("string") == "string"
        assert logger._sanitize_for_json(True) is True
        assert logger._sanitize_for_json(None) is None

    def test_sanitize_for_json_list_and_dict(self):
        logger = ConcreteMemoryLogger()
        obj = {"key": [1, "two", {"nested": True}]}
        sanitized = logger._sanitize_for_json(obj)
        assert sanitized == {"key": [1, "two", {"nested": True}]}

    def test_sanitize_for_json_unserializable_object(self):
        logger = ConcreteMemoryLogger()
        class CustomObject:
            pass
        obj = {"custom": CustomObject()}
        sanitized = logger._sanitize_for_json(obj)
        # SerializationMixin converts objects with __dict__ to typed dict
        assert sanitized["custom"]["__type"] == "CustomObject"
        assert "data" in sanitized["custom"]

    def test_should_use_deduplication_format(self):
        logger = ConcreteMemoryLogger()
        assert not logger._should_use_deduplication_format()
        # SerializationMixin requires duplicates OR enough blobs to justify overhead
        # Add multiple blobs with usage count > 1 to trigger True
        logger._blob_store["hash1"] = {"data": "blob1"}
        logger._blob_store["hash2"] = {"data": "blob2"} 
        logger._blob_store["hash3"] = {"data": "blob3"}
        logger._blob_store["hash4"] = {"data": "large" * 100}  # large enough blob
        logger._blob_usage["hash1"] = 2  # Mark as duplicate
        assert logger._should_use_deduplication_format()

    @pytest.mark.asyncio
    async def test_build_previous_outputs_from_redis(self):
        logger_instance = ConcreteMemoryLogger()
        logger_instance.hset("agent_results", "agent1", json.dumps({"result": "redis_result"}))
        logger_instance.set("agent_result:agent1", json.dumps({"result": "redis_result"}))

        outputs = logger_instance._build_previous_outputs([])
        assert outputs == {"agent1": {"result": "redis_result"}}

    @pytest.mark.asyncio
    async def test_build_previous_outputs_from_logs_regular_output(self):
        logger_instance = ConcreteMemoryLogger()
        logs = [
            {"agent_id": "agent2", "payload": {"result": "log_result"}}
        ]
        outputs = logger_instance._build_previous_outputs(logs)
        assert outputs == {"agent2": "log_result"}

    @pytest.mark.asyncio
    async def test_build_previous_outputs_from_logs_join_node(self):
        logger_instance = ConcreteMemoryLogger()
        logs = [
            {"agent_id": "join_agent", "payload": {"result": {"merged": {"agent3": "merged_result"}}}}
        ]
        outputs = logger_instance._build_previous_outputs(logs)
        assert outputs == {"join_agent": {"merged": {"agent3": "merged_result"}}, "agent3": "merged_result"}

    @pytest.mark.asyncio
    async def test_build_previous_outputs_from_logs_current_run_response(self):
        logger_instance = ConcreteMemoryLogger()
        logs = [
            {"agent_id": "llm_agent", "payload": {"response": "LLM response", "confidence": "0.9", "_metrics": {"tokens": 100}}}
        ]
        outputs = logger_instance._build_previous_outputs(logs)
        assert outputs["llm_agent"]["response"] == "LLM response"
        assert outputs["llm_agent"]["confidence"] == "0.9"
        assert outputs["llm_agent"]["_metrics"] == {"tokens": 100}

    @pytest.mark.asyncio
    async def test_build_previous_outputs_from_logs_memory_agent_response(self):
        logger_instance = ConcreteMemoryLogger()
        logs = [
            {"agent_id": "memory_agent", "payload": {"memories": ["mem1"], "query": "test query"}}
        ]
        outputs = logger_instance._build_previous_outputs(logs)
        assert outputs["memory_agent"]["memories"] == ["mem1"]
        assert outputs["memory_agent"]["query"] == "test query"

    @patch("orka.memory.base_logger_mixins.memory_processing_mixin.logger")
    @pytest.mark.asyncio
    async def test_build_previous_outputs_redis_store_failure(self, mock_log):
        logger_instance = ConcreteMemoryLogger()
        logger_instance.set = MagicMock(side_effect=Exception("Redis set error"))
        logger_instance.hset = MagicMock(side_effect=Exception("Redis hset error"))
        logs = [
            {"agent_id": "agent_fail", "payload": {"result": "fail_result"}}
        ]
        outputs = logger_instance._build_previous_outputs(logs)
        assert outputs == {"agent_fail": "fail_result"}
        assert mock_log.warning.call_count == 2
        mock_log.warning.assert_has_calls([
            call("Failed to store result in Redis: Redis set error"),
            call("Failed to store result in Redis: Redis hset error")
        ], any_order=True)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.dump")
    @patch("orka.memory.base_logger_mixins.cost_analysis_mixin.logger")
    def test_save_enhanced_trace_no_deduplication(self, mock_log, mock_json_dump, mock_open):
        logger_instance = ConcreteMemoryLogger()
        enhanced_data = {"agent_executions": [], "other_data": "value"}
        file_path = "test_trace.json"

        logger_instance.save_enhanced_trace(file_path, enhanced_data)

        mock_open.assert_called_once_with(file_path, "w", encoding="utf-8")
        mock_json_dump.assert_called_once()
        dumped_data = mock_json_dump.call_args[0][0]
        assert "_metadata" in dumped_data
        assert not dumped_data["_metadata"]["deduplication_enabled"]
        mock_log.info.assert_called_once_with(f"Enhanced trace saved (no deduplication needed)")

    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.dump")
    @patch("orka.memory.base_logger_mixins.cost_analysis_mixin.logger")
    def test_save_enhanced_trace_with_deduplication(self, mock_log, mock_json_dump, mock_open):
        logger_instance = ConcreteMemoryLogger()
        logger_instance._blob_threshold = 10 # Lower threshold for testing
        large_payload = {"data": "a" * 20}
        enhanced_data = {"agent_executions": [
            {"agent_id": "test", "event_type": "write", "payload": large_payload}
        ]}
        file_path = "test_trace.json"

        logger_instance.save_enhanced_trace(file_path, enhanced_data)

        mock_open.assert_called_once_with(file_path, "w", encoding="utf-8")
        mock_json_dump.assert_called_once()
        dumped_data = mock_json_dump.call_args[0][0]
        assert "_metadata" in dumped_data
        assert dumped_data["_metadata"]["deduplication_enabled"]
        assert "blob_store" in dumped_data
        assert "events" in dumped_data
        assert "ref" in dumped_data["events"][0]["payload"]
        mock_log.info.assert_called_once_with("Enhanced trace saved with deduplication: 1 blobs, 0 bytes saved")

    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.dump", side_effect=Exception("Dump error"))
    @patch("orka.memory.base_logger_mixins.cost_analysis_mixin.logger")
    @patch.object(ConcreteMemoryLogger, "save_to_file")
    def test_save_enhanced_trace_dump_failure_fallback(self, mock_save_to_file, mock_log, mock_json_dump, mock_open):
        logger_instance = ConcreteMemoryLogger()
        enhanced_data = {"agent_executions": []}
        file_path = "test_trace.json"

        logger_instance.save_enhanced_trace(file_path, enhanced_data)

        assert mock_log.error.call_count == 2
        mock_log.error.assert_has_calls([
            call("Failed to save enhanced trace with deduplication: Dump error"),
            call("Fallback save also failed: Dump error")
        ], any_order=True)
        assert mock_log.info.call_count == 0
        mock_save_to_file.assert_called_once_with(file_path)

    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.dump", side_effect=Exception("Dump error"))
    @patch("orka.memory.base_logger_mixins.cost_analysis_mixin.logger")
    @patch.object(ConcreteMemoryLogger, "save_to_file", side_effect=Exception("Fallback save error"))
    def test_save_enhanced_trace_all_failure_fallback_to_original_save(self, mock_save_to_file, mock_log, mock_json_dump, mock_open):
        logger_instance = ConcreteMemoryLogger()
        enhanced_data = {"agent_executions": []}
        file_path = "test_trace.json"

        with pytest.raises(Exception, match="Fallback save error"):
            logger_instance.save_enhanced_trace(file_path, enhanced_data)

        assert mock_log.error.call_count == 2
        mock_log.error.assert_has_calls([
            call("Failed to save enhanced trace with deduplication: Dump error"),
            call("Fallback save also failed: Dump error")
        ], any_order=True)
        mock_save_to_file.assert_called_once_with(file_path)

    def test_apply_deduplication_to_enhanced_trace_no_deduplication(self):
        logger_instance = ConcreteMemoryLogger()
        enhanced_data = {"agent_executions": []}
        deduplicated_data = logger_instance._apply_deduplication_to_enhanced_trace(enhanced_data)
        assert "_metadata" in deduplicated_data
        assert not deduplicated_data["_metadata"]["deduplication_enabled"]
        assert "cost_analysis" in deduplicated_data

    def test_apply_deduplication_to_enhanced_trace_with_deduplication(self):
        logger_instance = ConcreteMemoryLogger()
        logger_instance._blob_threshold = 10
        large_payload = {"data": "a" * 20}
        enhanced_data = {"agent_executions": [
            {"agent_id": "test", "event_type": "write", "payload": large_payload, "timestamp": datetime.now(UTC).isoformat()}
        ]}
        deduplicated_data = logger_instance._apply_deduplication_to_enhanced_trace(enhanced_data)
        assert "_metadata" in deduplicated_data
        assert deduplicated_data["_metadata"]["deduplication_enabled"]
        assert "blob_store" in deduplicated_data
        assert "events" in deduplicated_data
        assert "ref" in deduplicated_data["events"][0]["payload"]
        assert deduplicated_data["_metadata"]["stats"]["deduplicated_blobs"] == 0

    def test_extract_cost_analysis_empty(self):
        logger_instance = ConcreteMemoryLogger()
        cost_analysis = logger_instance._extract_cost_analysis({}, [])
        assert cost_analysis["summary"]["total_agents"] == 0

    def test_extract_cost_analysis_llm_agent(self):
        logger_instance = ConcreteMemoryLogger()
        enhanced_data = {"blob_store": {}}
        events = [
            {
                "agent_id": "llm_agent_1",
                "event_type": "LLMAgent",
                "payload": {
                    "_metrics": {
                        "tokens": 100,
                        "prompt_tokens": 50,
                        "completion_tokens": 50,
                        "cost_usd": 0.01,
                        "latency_ms": 200,
                        "model": "gpt-4",
                        "provider": "openai",
                    }
                },
            }
        ]
        cost_analysis = logger_instance._extract_cost_analysis(enhanced_data, events)
        assert cost_analysis["summary"]["total_agents"] == 1
        assert cost_analysis["summary"]["total_tokens"] == 100
        assert cost_analysis["agents"]["llm_agent_1"]["total_cost_usd"] == 0.01
        assert "gpt-4" in cost_analysis["summary"]["models_used"]

    def test_extract_cost_analysis_llm_agent_with_blob_reference(self):
        logger_instance = ConcreteMemoryLogger()
        large_payload = {
            "_metrics": {
                "tokens": 200,
                "prompt_tokens": 100,
                "completion_tokens": 100,
                "cost_usd": 0.02,
                "latency_ms": 300,
                "model": "claude-3",
                "provider": "anthropic",
            }
        }
        blob_hash = logger_instance._compute_blob_hash(large_payload)
        logger_instance._blob_store[blob_hash] = large_payload

        enhanced_data = {"blob_store": {blob_hash: large_payload}}
        events = [
            {
                "agent_id": "llm_agent_2",
                "event_type": "LLMAgent",
                "payload": {"_type": "blob_reference", "ref": blob_hash},
            }
        ]
        cost_analysis = logger_instance._extract_cost_analysis(enhanced_data, events)
        assert cost_analysis["summary"]["total_agents"] == 1
        assert cost_analysis["summary"]["total_tokens"] == 200
        assert cost_analysis["agents"]["llm_agent_2"]["total_cost_usd"] == 0.02
        assert "claude-3" in cost_analysis["summary"]["models_used"]

    def test_extract_agent_metrics_direct_metrics(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": {"_metrics": {"tokens": 50}}}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics == {"tokens": 50}

    def test_extract_agent_metrics_nested_metrics(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": {"output": {"data": "abc", "_metrics": {"tokens": 75}}}}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics == {"tokens": 75}

    def test_extract_agent_metrics_blob_reference_current_store(self):
        logger_instance = ConcreteMemoryLogger()
        blob_payload = {"_metrics": {"tokens": 120}}
        blob_hash = logger_instance._store_blob(blob_payload)
        event = {"payload": {"_type": "blob_reference", "ref": blob_hash}}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics == {"tokens": 120}

    def test_extract_agent_metrics_blob_reference_enhanced_data_store(self):
        logger_instance = ConcreteMemoryLogger()
        blob_payload = {"_metrics": {"tokens": 150}}
        blob_hash = logger_instance._compute_blob_hash(blob_payload)
        enhanced_data = {"blob_store": {blob_hash: blob_payload}}
        event = {"payload": {"_type": "blob_reference", "ref": blob_hash}}
        metrics = logger_instance._extract_agent_metrics(event, enhanced_data)
        assert metrics == {"tokens": 150}

    def test_extract_agent_metrics_multiple_nested_metrics(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": {
            "step1": {"_metrics": {"tokens": 10, "cost_usd": 0.001, "model": "m1"}},
            "step2": {"sub_step": {"_metrics": {"tokens": 20, "cost_usd": 0.002, "model": "m2"}}},
            "step3": {"_metrics": {"tokens": 5, "cost_usd": 0.0005, "provider": "p1"}}
        }}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics["tokens"] == 35
        assert metrics["cost_usd"] == pytest.approx(0.0035)
        assert metrics["model"] == "m1" # First one found
        assert metrics["provider"] == "p1"

    def test_extract_agent_metrics_list_of_dicts(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": [
            {"item1": {"_metrics": {"tokens": 15}}},
            {"item2": {"sub_item": {"_metrics": {"tokens": 25}}}}
        ]}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics["tokens"] == 40

    def test_extract_agent_metrics_max_depth(self):
        logger_instance = ConcreteMemoryLogger()
        deep_nested = {"_metrics": {"tokens": 100}}
        for _ in range(15):
            deep_nested = {"nest": deep_nested}
        event = {"payload": deep_nested}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert "tokens" not in metrics # Max depth exceeded

    def test_extract_agent_metrics_non_dict_payload(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": "just a string"}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics == {}

    def test_extract_agent_metrics_blob_reference_not_found(self):
        logger_instance = ConcreteMemoryLogger()
        event = {"payload": {"_type": "blob_reference", "ref": "non_existent_hash"}}
        metrics = logger_instance._extract_agent_metrics(event, {})
        assert metrics == {}