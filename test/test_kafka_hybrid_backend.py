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
Tests for Kafka + Redis Hybrid Backend
======================================

Tests to verify that the Kafka backend now uses Redis for memory operations
while maintaining Kafka for event streaming.
"""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fake_redis import FakeRedisClient

from orka.memory_logger import create_memory_logger

# Try to import KafkaMemoryLogger
try:
    from orka.memory.kafka_logger import KafkaMemoryLogger

    kafka_available = True
except ImportError:
    kafka_available = False
    KafkaMemoryLogger = None

# Skip marker for tests that require Kafka
kafka_import_skip = pytest.mark.skipif(
    not kafka_available,
    reason="Kafka dependencies not available",
)


class TestKafkaHybridBackend:
    """Test the Kafka + Redis hybrid backend functionality"""

    @patch("orka.memory.kafka_logger.redis.from_url")
    @patch("orka.memory.kafka_logger.KafkaMemoryLogger._init_kafka_producer")
    def test_kafka_logger_uses_redis_for_memory_operations(
        self,
        mock_init_producer,
        mock_redis_from_url,
    ):
        """Test that KafkaMemoryLogger now uses actual Redis for memory operations"""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_from_url.return_value = mock_redis_client

        # Mock Kafka producer initialization
        mock_producer = Mock()
        mock_init_producer.return_value = mock_producer

        # Create Kafka memory logger
        from orka.memory.kafka_logger import KafkaMemoryLogger

        logger = KafkaMemoryLogger(
            bootstrap_servers="localhost:9092",
            redis_url="redis://localhost:6379/0",
        )

        # Verify Redis client was created
        mock_redis_from_url.assert_called_once_with("redis://localhost:6379/0")

        # Test that Redis operations are delegated to actual Redis client
        logger.hset("test_hash", "key1", "value1")
        mock_redis_client.hset.assert_called_once_with("test_hash", "key1", "value1")

        logger.hget("test_hash", "key1")
        mock_redis_client.hget.assert_called_once_with("test_hash", "key1")

        logger.sadd("test_set", "member1")
        mock_redis_client.sadd.assert_called_once_with("test_set", "member1")

    @patch("orka.memory.kafka_logger.redis.from_url")
    @patch("orka.memory.kafka_logger.KafkaMemoryLogger._init_kafka_producer")
    def test_kafka_logger_has_redis_property(self, mock_init_producer, mock_redis_from_url):
        """Test that KafkaMemoryLogger provides redis property for compatibility"""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_from_url.return_value = mock_redis_client

        # Mock Kafka producer initialization
        mock_producer = Mock()
        mock_init_producer.return_value = mock_producer

        # Create Kafka memory logger
        from orka.memory.kafka_logger import KafkaMemoryLogger

        logger = KafkaMemoryLogger(
            bootstrap_servers="localhost:9092",
            redis_url="redis://localhost:6379/0",
        )

        # Verify redis property returns the Redis client
        assert logger.redis is mock_redis_client

    def test_factory_passes_redis_url_to_kafka_logger(self):
        """Test that create_memory_logger passes redis_url to KafkaMemoryLogger"""
        with patch("orka.memory_logger.KafkaMemoryLogger") as mock_kafka_class:
            create_memory_logger(
                backend="kafka",
                bootstrap_servers="localhost:9092",
                redis_url="redis://test:6379/0",
            )

            # Verify KafkaMemoryLogger was called with redis_url
            mock_kafka_class.assert_called_once()
            call_kwargs = mock_kafka_class.call_args[1]
            assert call_kwargs["redis_url"] == "redis://test:6379/0"

    def test_environment_variable_configuration(self):
        """Test that environment variables are properly configured for hybrid backend"""
        # Test start_kafka.py environment setup
        original_env = os.environ.copy()

        try:
            # Clear relevant environment variables
            for key in ["ORKA_MEMORY_BACKEND", "REDIS_URL", "KAFKA_BOOTSTRAP_SERVERS"]:
                if key in os.environ:
                    del os.environ[key]

            # Import and run the environment setup from start_kafka
            import importlib.util
            import sys
            from pathlib import Path

            # Load start_kafka module
            spec = importlib.util.spec_from_file_location(
                "start_kafka",
                Path(__file__).parent.parent / "orka" / "start_kafka.py",
            )
            start_kafka = importlib.util.module_from_spec(spec)

            # Execute the environment setup part (but not main())
            with patch.object(sys, "argv", ["start_kafka.py"]):
                spec.loader.exec_module(start_kafka)

            # Verify environment variables are set correctly
            assert os.environ["ORKA_MEMORY_BACKEND"] == "kafka"
            assert os.environ["REDIS_URL"] == "redis://localhost:6379/0"
            assert os.environ["KAFKA_BOOTSTRAP_SERVERS"] == "localhost:9092"
            assert os.environ["KAFKA_TOPIC_PREFIX"] == "orka-memory"

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_orchestrator_uses_redis_fork_manager_for_kafka(self):
        """Test that orchestrator uses Redis-based fork manager for Kafka backend"""
        # Set environment for Kafka backend
        with patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "kafka"}):
            with patch("orka.orchestrator.base.YAMLLoader") as mock_loader:
                with patch("orka.orchestrator.base.create_memory_logger") as mock_create_logger:
                    with patch("orka.orchestrator.base.ForkGroupManager") as mock_fork_manager:
                        # Mock the loader to avoid validation errors
                        mock_loader_instance = Mock()
                        mock_loader.return_value = mock_loader_instance
                        mock_loader_instance.validate = Mock()
                        mock_loader_instance.get_orchestrator.return_value = {"agents": []}
                        mock_loader_instance.get_agents.return_value = []

                        # Mock memory logger with redis property
                        mock_memory = Mock()
                        mock_memory.redis = Mock()
                        mock_create_logger.return_value = mock_memory

                        # Import and create orchestrator
                        from orka.orchestrator.base import OrchestratorBase

                        orchestrator = OrchestratorBase("test_config.yml")

                        # Verify that create_memory_logger was called with correct parameters
                        mock_create_logger.assert_called_once()
                        call_kwargs = mock_create_logger.call_args[1]
                        assert call_kwargs["backend"] == "kafka"
                        assert "redis_url" in call_kwargs

                        # Verify that Redis-based fork manager was used
                        mock_fork_manager.assert_called_once_with(mock_memory.redis)


class TestKafkaMemoryLoggerSchemaRegistry:
    """Test schema registry integration."""

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_schema_registry_initialization_success(self, mock_redis):
        """Test successful schema registry initialization."""
        mock_redis.return_value = FakeRedisClient()

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.register_schema.return_value = 123
        mock_schema_manager.get_serializer.return_value = Mock()

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch(
                "orka.memory.schema_manager.create_schema_manager",
                return_value=mock_schema_manager,
            ):
                logger = KafkaMemoryLogger()
                assert logger.redis_client is not None

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_schema_registry_initialization_failure(self, mock_redis):
        """Test schema registry initialization failure fallback."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch(
                "orka.memory.schema_manager.create_schema_manager",
                side_effect=Exception("Schema registry error"),
            ):
                with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "true"}):
                    logger = KafkaMemoryLogger()
                    # Should fallback to JSON serialization
                    assert logger.use_schema_registry is False


class TestKafkaMemoryLoggerErrorHandling:
    """Test error handling in Kafka logger."""

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_send_to_kafka_error_handling(self, mock_redis):
        """Test error handling in _send_to_kafka method."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka producer that fails
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_producer.send.side_effect = Exception("Kafka send failed")
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                logger = KafkaMemoryLogger()

                # Should not raise exception, just log error
                event = {
                    "agent_id": "test_agent",
                    "event_type": "test",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                # This should not raise an exception
                logger._send_to_kafka(event, "test_run", "test_agent")

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_store_in_redis_namespace_routing(self, mock_redis):
        """Test Redis storage with namespace routing."""
        fake_redis = FakeRedisClient()
        mock_redis.return_value = fake_redis

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                logger = KafkaMemoryLogger()

                # Test stored memory with namespace
                event = {
                    "agent_id": "test_agent",
                    "event_type": "write",
                    "payload": {"namespace": "conversations", "session": "user123", "data": "test"},
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                decay_metadata = {"orka_memory_category": "stored"}

                logger._store_in_redis(event, 1, "test_run", None, None, None, decay_metadata)

                # Should write to namespace-specific stream
                expected_stream = "orka:memory:conversations:user123"
                assert expected_stream in fake_redis.store


class TestKafkaMemoryLoggerCleanupAndStats:
    """Test cleanup and statistics functionality."""

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_cleanup_expired_memories_with_redis_fallback(self, mock_redis):
        """Test cleanup using Redis fallback."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                # Mock RedisMemoryLogger
                mock_redis_logger = Mock()
                mock_redis_logger.cleanup_expired_memories.return_value = {
                    "deleted_count": 5,
                    "streams_processed": 2,
                }

                with patch(
                    "orka.memory.redis_logger.RedisMemoryLogger",
                    return_value=mock_redis_logger,
                ):
                    logger = KafkaMemoryLogger()
                    result = logger.cleanup_expired_memories()

                    assert result["deleted_count"] == 5
                    assert result["backend"] == "kafka+redis"
                    mock_redis_logger.cleanup_expired_memories.assert_called_once()

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_get_memory_stats_with_redis_fallback(self, mock_redis):
        """Test memory stats using Redis fallback."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                # Mock RedisMemoryLogger
                mock_redis_logger = Mock()
                mock_redis_logger.get_memory_stats.return_value = {
                    "total_entries": 100,
                    "backend": "redis",
                }

                with patch(
                    "orka.memory.redis_logger.RedisMemoryLogger",
                    return_value=mock_redis_logger,
                ):
                    logger = KafkaMemoryLogger()
                    result = logger.get_memory_stats()

                    assert result["total_entries"] == 100
                    assert result["backend"] == "kafka+redis"
                    assert "kafka_topic" in result
                    assert "memory_buffer_size" in result
                    mock_redis_logger.get_memory_stats.assert_called_once()


class TestKafkaMemoryLoggerConnectionManagement:
    """Test connection management and producer handling."""

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_json_message_sending_kafka_python(self, mock_redis):
        """Test JSON message sending with kafka-python producer."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka-python producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_future = Mock()
        mock_producer.send.return_value = mock_future

        # Ensure the producer doesn't have "produce" attribute (for kafka-python)
        if hasattr(mock_producer, "produce"):
            delattr(mock_producer, "produce")

        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                logger = KafkaMemoryLogger(synchronous_send=True)

                # Use valid event data with required fields
                event = {
                    "agent_id": "test_agent",
                    "event_type": "test_event",
                    "test": "data",
                }
                logger._send_json_message("test_key", event)

                # Verify producer.send was called
                mock_producer.send.assert_called_once_with(
                    topic="orka-memory-events",
                    key="test_key",
                    value=event,
                )
                # Verify synchronous send (future.get called)
                mock_future.get.assert_called_once_with(timeout=10)

    @kafka_import_skip
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_complex_payload_handling(self, mock_redis):
        """Test handling of complex payloads with non-serializable objects."""
        mock_redis.return_value = FakeRedisClient()

        # Mock kafka producer
        mock_kafka_module = MagicMock()
        mock_producer = MagicMock()
        mock_kafka_module.KafkaProducer.return_value = mock_producer

        with patch.dict("sys.modules", {"kafka": mock_kafka_module}):
            with patch.dict(os.environ, {"KAFKA_USE_SCHEMA_REGISTRY": "false"}):
                logger = KafkaMemoryLogger()

                # Complex payload with non-serializable objects
                class NonSerializable:
                    def __init__(self):
                        self.data = "test"

                complex_payload = {
                    "serializable": "data",
                    "non_serializable": NonSerializable(),
                    "nested": {
                        "list": [1, 2, 3],
                        "none": None,
                    },
                }

                logger.log("test_agent", "test_event", complex_payload)

                # Should be handled without exception
                assert len(logger.memory) == 1
                event = logger.memory[0]
                assert "payload" in event


if __name__ == "__main__":
    pytest.main([__file__])
