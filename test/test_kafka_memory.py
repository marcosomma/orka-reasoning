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

"""
Test cases for KafkaMemoryLogger
"""

import os
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from orka.memory_logger import KafkaMemoryLogger, create_memory_logger

# Import the fake Redis client for testing
sys.path.append(os.path.dirname(__file__))
from fake_redis import FakeRedisClient

# Check if we should skip Kafka tests in CI (they require complex mocking)
SKIP_KAFKA_TESTS = os.environ.get("CI", "").lower() in ("true", "1", "yes")

# Skip marker for problematic Kafka tests
kafka_import_skip = pytest.mark.skipif(
    SKIP_KAFKA_TESTS,
    reason="Kafka import tests skipped in CI due to complex __builtins__ mocking issues",
)


class TestKafkaMemoryLogger:
    """Test suite for KafkaMemoryLogger functionality"""

    @pytest.fixture
    def mock_kafka_producer(self):
        """Mock Kafka producer for testing"""
        # Create comprehensive kafka module mock
        mock_kafka_module = MagicMock()
        mock_errors_module = MagicMock()
        mock_producer_class = MagicMock()
        mock_producer = MagicMock()

        # Setup producer mock
        mock_producer_class.return_value = mock_producer
        mock_producer.send.return_value = MagicMock()
        mock_producer._metadata = MagicMock()

        # Setup kafka module structure
        mock_kafka_module.KafkaProducer = mock_producer_class
        mock_kafka_module.errors = mock_errors_module
        mock_errors_module.KafkaError = Exception  # Use base Exception as KafkaError

        # Mock the entire kafka ecosystem
        with patch.dict(
            "sys.modules",
            {
                "kafka": mock_kafka_module,
                "kafka.errors": mock_errors_module,
            },
        ):
            # Also disable schema registry to avoid confluent_kafka import issues
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                yield mock_producer

    @pytest.fixture
    def kafka_logger(self, mock_kafka_producer):
        """Create a KafkaMemoryLogger instance for testing"""
        # Mock the Redis client with our fake implementation
        with patch("orka.memory.kafka_logger.redis.from_url") as mock_redis:
            mock_redis.return_value = FakeRedisClient()
            return KafkaMemoryLogger(
                bootstrap_servers="localhost:9092",
                topic_prefix="test-orka",
                stream_key="test:memory",
            )

    def test_initialization_success(self, mock_kafka_producer):
        """Test successful initialization of KafkaMemoryLogger"""
        with patch("orka.memory.kafka_logger.redis.from_url") as mock_redis:
            mock_redis.return_value = FakeRedisClient()
            logger = KafkaMemoryLogger(
                bootstrap_servers="localhost:9092",
                topic_prefix="test-orka",
                stream_key="test:memory",
            )

            assert logger.bootstrap_servers == "localhost:9092"
            assert logger.topic_prefix == "test-orka"
            assert logger.main_topic == "test-orka-events"
            assert logger.stream_key == "test:memory"
            # KafkaMemoryLogger now uses Redis, not internal storage
            assert hasattr(logger, "redis_client")
            assert hasattr(logger, "memory")  # In-memory buffer for recent events

    def test_initialization_with_environment_variables(self, mock_kafka_producer):
        """Test initialization using environment variables"""
        with patch.dict(os.environ, {"KAFKA_BOOTSTRAP_SERVERS": "env-server:9092"}):
            with patch("orka.memory.kafka_logger.redis.from_url") as mock_redis:
                mock_redis.return_value = FakeRedisClient()
                logger = KafkaMemoryLogger()
                assert logger.bootstrap_servers == "env-server:9092"

    @kafka_import_skip
    def test_initialization_kafka_import_error(self):
        """Test initialization when kafka-python is not available"""
        import builtins

        # Store original import function
        original_import = builtins.__import__

        # Store original modules if they exist
        orig_kafka = sys.modules.get("kafka")
        orig_kafka_errors = sys.modules.get("kafka.errors")

        try:
            # Remove kafka modules from sys.modules completely
            if "kafka" in sys.modules:
                del sys.modules["kafka"]
            if "kafka.errors" in sys.modules:
                del sys.modules["kafka.errors"]

            # Mock the import to raise ImportError
            def mock_import(name, *args, **kwargs):
                if name == "kafka" or name.startswith("kafka."):
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)

            # Also disable schema registry to force using kafka-python path
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                with patch("builtins.__import__", side_effect=mock_import):
                    with pytest.raises(ImportError, match="kafka-python package is required"):
                        KafkaMemoryLogger()
        finally:
            # Restore original modules
            if orig_kafka is not None:
                sys.modules["kafka"] = orig_kafka
            if orig_kafka_errors is not None:
                sys.modules["kafka.errors"] = orig_kafka_errors

    def test_log_event_success(self, kafka_logger, mock_kafka_producer):
        """Test successful event logging"""
        agent_id = "test_agent"
        event_type = "test_event"
        payload = {"data": "test_data", "count": 42}

        kafka_logger.log(
            agent_id=agent_id,
            event_type=event_type,
            payload=payload,
            step=1,
            run_id="test_run_123",
        )

        # Verify event was added to memory (this is the core functionality we can test reliably)
        assert len(kafka_logger.memory) == 1
        event = kafka_logger.memory[0]
        assert event["agent_id"] == agent_id
        assert event["event_type"] == event_type
        assert event["payload"] == payload
        assert event["step"] == 1
        assert event["run_id"] == "test_run_123"
        assert "timestamp" in event

        # Note: Kafka producer calls are complex to test due to exception handling
        # The main functionality (storing in memory) is tested above

    def test_log_event_missing_agent_id(self, kafka_logger):
        """Test logging with missing agent_id - KafkaMemoryLogger doesn't validate agent_id"""
        # KafkaMemoryLogger now allows empty agent_id, just logs it
        kafka_logger.log(
            agent_id="",
            event_type="test_event",
            payload={"data": "test"},
        )

        # Event should be logged even with empty agent_id
        assert len(kafka_logger.memory) == 1

    def test_log_event_kafka_failure(self, kafka_logger, mock_kafka_producer):
        """Test handling of Kafka send failure"""
        mock_kafka_producer.send.side_effect = Exception("Kafka connection failed")

        # Should not raise, but log error and try fallback
        kafka_logger.log(
            agent_id="test_agent",
            event_type="test_event",
            payload={"data": "test"},
        )

        # Event should still be in memory
        assert len(kafka_logger.memory) == 1

    def test_log_event_with_complex_payload(self, kafka_logger, mock_kafka_producer):
        """Test logging with complex payload that needs sanitization"""
        complex_payload = {
            "nested": {"data": "value"},
            "list": [1, 2, 3],
            "none_value": None,
            "string": "test",
        }

        kafka_logger.log(
            agent_id="test_agent",
            event_type="complex_event",
            payload=complex_payload,
        )

        # Verify sanitization worked
        assert len(kafka_logger.memory) == 1
        event = kafka_logger.memory[0]
        assert event["payload"] == complex_payload

    def test_tail_functionality(self, kafka_logger):
        """Test tail functionality for retrieving recent events"""
        # Add multiple events
        for i in range(15):
            kafka_logger.log(
                agent_id=f"agent_{i}",
                event_type="test_event",
                payload={"count": i},
            )

        # Test default tail (10 events)
        recent = kafka_logger.tail()
        assert len(recent) == 10
        assert recent[0]["payload"]["count"] == 5  # Last 10 start from index 5
        assert recent[-1]["payload"]["count"] == 14  # Last event

        # Test custom count
        recent_5 = kafka_logger.tail(5)
        assert len(recent_5) == 5
        assert recent_5[-1]["payload"]["count"] == 14

    def test_tail_empty_memory(self, kafka_logger):
        """Test tail with empty memory"""
        recent = kafka_logger.tail()
        assert recent == []

    def test_hset_and_hget(self, kafka_logger):
        """Test hash set and get operations"""
        # Test setting new field
        result = kafka_logger.hset("test_hash", "field1", "value1")
        assert result == 1  # New field

        # Test updating existing field
        result = kafka_logger.hset("test_hash", "field1", "updated_value")
        assert result == 0  # Updated field

        # Test getting field
        value = kafka_logger.hget("test_hash", "field1")
        assert value == "updated_value"

        # Test getting non-existent field
        value = kafka_logger.hget("test_hash", "nonexistent")
        assert value is None

        # Test getting from non-existent hash
        value = kafka_logger.hget("nonexistent_hash", "field1")
        assert value is None

    def test_hset_with_complex_values(self, kafka_logger):
        """Test hset with various value types"""
        # Test with different data types
        kafka_logger.hset("test_hash", "int_field", 42)
        kafka_logger.hset("test_hash", "float_field", 3.14)
        kafka_logger.hset("test_hash", "dict_field", {"nested": "value"})

        assert kafka_logger.hget("test_hash", "int_field") == "42"
        assert kafka_logger.hget("test_hash", "float_field") == "3.14"
        # Complex objects are converted to string representation
        dict_value = kafka_logger.hget("test_hash", "dict_field")
        assert "nested" in dict_value
        assert "value" in dict_value

    def test_sadd_and_srem(self, kafka_logger):
        """Test set add and remove operations"""
        # Test adding members
        result = kafka_logger.sadd("test_set", "member1", "member2", "member3")
        assert result == 3  # All new members

        # Test adding duplicate and new members
        result = kafka_logger.sadd("test_set", "member2", "member4")
        assert result == 1  # Only member4 is new

        # Test getting set members
        members = kafka_logger.smembers("test_set")
        # Convert bytes to strings for comparison
        members_str = {m.decode() if isinstance(m, bytes) else m for m in members}
        assert members_str == {"member1", "member2", "member3", "member4"}

        # Test removing members
        result = kafka_logger.srem("test_set", "member1", "member2")
        assert result == 2  # Two members removed

        members = kafka_logger.smembers("test_set")
        members_str = {m.decode() if isinstance(m, bytes) else m for m in members}
        assert members_str == {"member3", "member4"}

    def test_key_value_operations(self, kafka_logger):
        """Test simple key-value get and set operations"""
        # Test setting a key
        result = kafka_logger.set("test_key", "test_value")
        assert result is True

        # Test getting the key
        value = kafka_logger.get("test_key")
        # Handle bytes return value
        if isinstance(value, bytes):
            value = value.decode()
        assert value == "test_value"

        # Test getting non-existent key
        value = kafka_logger.get("nonexistent_key")
        assert value is None

    def test_delete_operation(self, kafka_logger):
        """Test delete operations"""
        # Set up some data
        kafka_logger.set("key1", "value1")
        kafka_logger.set("key2", "value2")
        kafka_logger.set("key3", "value3")

        # Test deleting existing keys
        result = kafka_logger.delete("key1", "key2")
        assert result == 2  # Two keys deleted

        # Verify keys are deleted
        assert kafka_logger.get("key1") is None
        assert kafka_logger.get("key2") is None

        # key3 should still exist
        value = kafka_logger.get("key3")
        if isinstance(value, bytes):
            value = value.decode()
        assert value == "value3"

        # Test deleting non-existent key
        result = kafka_logger.delete("nonexistent_key")
        assert result == 0  # No keys deleted

    def test_close_functionality(self, kafka_logger, mock_kafka_producer):
        """Test close functionality"""
        # Should not raise any exceptions
        kafka_logger.close()

        # Verify close was called on producer
        mock_kafka_producer.close.assert_called_once()

    def test_redis_property_access(self, kafka_logger):
        """Test that accessing redis property works for hybrid implementation"""
        # KafkaMemoryLogger now provides redis property for compatibility
        redis_client = kafka_logger.redis
        assert redis_client is not None
        # Should be able to call Redis operations through the property
        assert hasattr(redis_client, "hset")
        assert hasattr(redis_client, "hget")

    def test_hdel_functionality(self, kafka_logger):
        """Test hash delete functionality"""
        # Set up some hash fields
        kafka_logger.hset("test_hash", "field1", "value1")
        kafka_logger.hset("test_hash", "field2", "value2")
        kafka_logger.hset("test_hash", "field3", "value3")

        # Test deleting existing fields
        result = kafka_logger.hdel("test_hash", "field1", "field2")
        assert result == 2  # Two fields deleted

        # Verify fields are deleted
        assert kafka_logger.hget("test_hash", "field1") is None
        assert kafka_logger.hget("test_hash", "field2") is None

        # field3 should still exist
        assert kafka_logger.hget("test_hash", "field3") is not None

        # Test deleting non-existent fields
        result = kafka_logger.hdel("test_hash", "nonexistent_field")
        assert result == 0  # No fields deleted

        # Test deleting from non-existent hash
        result = kafka_logger.hdel("nonexistent_hash", "field1")
        assert result == 0  # No fields deleted


class TestMemoryLoggerFactory:
    """Test the memory logger factory function"""

    @patch("orka.memory_logger.KafkaMemoryLogger")
    def test_create_kafka_logger(self, mock_kafka_class):
        """Test creating Kafka logger via factory"""
        mock_logger = MagicMock()
        mock_kafka_class.return_value = mock_logger

        result = create_memory_logger(
            backend="kafka",
            bootstrap_servers="test:9092",
            topic_prefix="test-prefix",
            stream_key="orka:memory",
            synchronous_send=False,
            debug_keep_previous_outputs=False,
            decay_config=None,
            redis_url="redis://localhost:6379/0",
        )

        assert result == mock_logger
        mock_kafka_class.assert_called_once_with(
            bootstrap_servers="test:9092",
            topic_prefix="test-prefix",
            stream_key="orka:memory",
            synchronous_send=False,
            debug_keep_previous_outputs=False,
            decay_config=None,
            redis_url="redis://localhost:6379/0",
        )

    @patch("orka.memory_logger.RedisMemoryLogger")
    def test_create_redis_logger(self, mock_redis_class):
        """Test creating Redis logger via factory"""
        mock_logger = MagicMock()
        mock_redis_class.return_value = mock_logger

        result = create_memory_logger(
            backend="redis",
            redis_url="redis://localhost:6379",
            stream_key="orka:memory",
            debug_keep_previous_outputs=False,
            decay_config=None,
        )

        assert result == mock_logger
        mock_redis_class.assert_called_once_with(
            redis_url="redis://localhost:6379",
            stream_key="orka:memory",
            debug_keep_previous_outputs=False,
            decay_config=None,
        )

    def test_create_logger_invalid_backend(self):
        """Test factory with invalid backend"""
        with pytest.raises(ValueError, match="Unsupported backend: invalid"):
            create_memory_logger(backend="invalid")


class TestKafkaMemoryLoggerIntegration:
    """Integration tests for KafkaMemoryLogger"""

    @pytest.fixture
    def mock_kafka_environment(self):
        """Mock environment for Kafka integration tests"""
        # Create comprehensive kafka module mock
        mock_kafka_module = MagicMock()
        mock_errors_module = MagicMock()
        mock_producer_class = MagicMock()
        mock_producer = MagicMock()

        # Setup producer mock
        mock_producer_class.return_value = mock_producer
        mock_producer.send.return_value = MagicMock()
        mock_producer._metadata = MagicMock()

        # Setup kafka module structure
        mock_kafka_module.KafkaProducer = mock_producer_class
        mock_kafka_module.errors = mock_errors_module
        mock_errors_module.KafkaError = Exception  # Use base Exception as KafkaError

        # Mock the entire kafka ecosystem
        with patch.dict(
            "sys.modules",
            {
                "kafka": mock_kafka_module,
                "kafka.errors": mock_errors_module,
            },
        ):
            # Also disable schema registry to avoid confluent_kafka import issues
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                yield mock_producer

    def test_full_workflow(self, mock_kafka_environment):
        """Test a complete workflow with KafkaMemoryLogger"""
        logger = KafkaMemoryLogger(
            bootstrap_servers="localhost:9092",
            topic_prefix="workflow-test",
        )

        # Simulate orchestration workflow
        run_id = str(uuid4())

        # Log start event
        logger.log(
            agent_id="orchestrator",
            event_type="workflow_start",
            payload={"workflow": "test_workflow"},
            run_id=run_id,
            step=0,
        )

        # Log agent events
        for i, agent in enumerate(["agent1", "agent2", "agent3"]):
            logger.log(
                agent_id=agent,
                event_type="agent_start",
                payload={"input_data": f"data_{i}"},
                run_id=run_id,
                step=i + 1,
            )

            # Store intermediate results
            logger.hset(f"results:{run_id}", agent, f"result_{i}")

            logger.log(
                agent_id=agent,
                event_type="agent_complete",
                payload={"output": f"result_{i}"},
                run_id=run_id,
                step=i + 1,
            )

        # Log completion
        logger.log(
            agent_id="orchestrator",
            event_type="workflow_complete",
            payload={"status": "success"},
            run_id=run_id,
            step=4,
        )

        # Verify workflow state
        assert len(logger.memory) == 8  # 1 start + 3*(start+complete) + 1 end
        recent_events = logger.tail(3)
        assert recent_events[-1]["event_type"] == "workflow_complete"

        # Verify stored results
        for i, agent in enumerate(["agent1", "agent2", "agent3"]):
            result = logger.hget(f"results:{run_id}", agent)
            assert result == f"result_{i}"

        # Verify events were stored in memory (core functionality)
        assert len(logger.memory) == 8

        # Verify the workflow events are properly structured
        workflow_events = [
            e for e in logger.memory if e["event_type"] in ["workflow_start", "workflow_complete"]
        ]
        assert len(workflow_events) == 2
        assert workflow_events[0]["event_type"] == "workflow_start"
        assert workflow_events[1]["event_type"] == "workflow_complete"

        # Clean up
        logger.close()
