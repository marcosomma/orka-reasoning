"""Test the Kafka memory logger implementation."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from orka.memory.kafka_logger import KafkaMemoryLogger


class TestKafkaMemoryLoggerInitialization:
    """Test initialization of KafkaMemoryLogger."""

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_initialization_default_params(self, mock_redis):
        """Test initialization with default parameters."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack.return_value = Mock()

            logger = KafkaMemoryLogger()

            assert logger.bootstrap_servers == "localhost:9092"
            assert logger.redis_url == "redis://localhost:6380/0"
            assert logger.stream_key == "orka:memory"
            assert logger.main_topic == "orka-memory-events"

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_initialization_custom_params(self, mock_redis):
        """Test initialization with custom parameters."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack.return_value = Mock()

            logger = KafkaMemoryLogger(
                bootstrap_servers="kafka:9093",
                redis_url="redis://custom:6379/1",
                stream_key="custom:stream",
                debug_keep_previous_outputs=True,
                decay_config={"enabled": True},
            )

            assert logger.bootstrap_servers == "kafka:9093"
            assert logger.redis_url == "redis://custom:6379/1"
            assert logger.stream_key == "custom:stream"
            assert logger.debug_keep_previous_outputs is True
            assert logger.decay_config["enabled"] is True

    @patch.dict(os.environ, {"REDIS_URL": "redis://env:6379/2"})
    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_initialization_from_env(self, mock_redis):
        """Test initialization with environment variable."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack.return_value = Mock()

            logger = KafkaMemoryLogger()

            assert logger.redis_url == "redis://env:6379/2"

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_initialization_redisstack_fallback(self, mock_redis):
        """Test fallback to basic Redis when RedisStack is not available."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock RedisStack import failure
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger", side_effect=ImportError):
            logger = KafkaMemoryLogger()

            assert logger._redis_memory_logger is None
            assert logger.redis_client == mock_client

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_redis_property_with_redisstack(self, mock_redis):
        """Test redis property returns RedisStack client when available."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack_instance = Mock()
            mock_redisstack_redis_client = Mock()
            mock_redisstack_instance.redis = mock_redisstack_redis_client
            mock_redisstack.return_value = mock_redisstack_instance

            logger = KafkaMemoryLogger()

            assert logger.redis == mock_redisstack_redis_client

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_redis_property_fallback(self, mock_redis):
        """Test redis property returns fallback client when RedisStack is not available."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger", side_effect=ImportError):
            logger = KafkaMemoryLogger()

            assert logger.redis == mock_client

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_redis_property_interface_compatibility(self, mock_redis):
        """Test that the fix works with both RedisMemoryLogger and RedisStackMemoryLogger interfaces."""

        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            # Simulate RedisStackMemoryLogger interface (has redis_client, redis property)
            mock_redisstack_instance = Mock()
            mock_redisstack_redis_client = Mock()

            # This is the key part - RedisStackMemoryLogger has redis_client attribute
            # and redis property that returns it
            mock_redisstack_instance.redis_client = mock_redisstack_redis_client
            mock_redisstack_instance.redis = mock_redisstack_redis_client

            # This should NOT exist (this was causing the AttributeError)
            del mock_redisstack_instance.client  # Make sure .client doesn't exist

            mock_redisstack.return_value = mock_redisstack_instance

            logger = KafkaMemoryLogger()

            # Should work with both interfaces
            assert logger.redis == mock_redisstack_redis_client

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_redis_property_original_bug_fixed(self, mock_redis):
        """Test that the original AttributeError bug is fixed."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            # Create a mock that simulates the real RedisStackMemoryLogger interface
            mock_redisstack_instance = Mock()

            # RedisStackMemoryLogger has redis_client attribute but NO client attribute
            mock_redisstack_instance.redis_client = Mock()
            mock_redisstack_instance.redis = mock_redisstack_instance.redis_client

            # Remove client attribute to simulate the real interface
            if hasattr(mock_redisstack_instance, "client"):
                delattr(mock_redisstack_instance, "client")

            mock_redisstack.return_value = mock_redisstack_instance

            logger = KafkaMemoryLogger()

            # Should not raise AttributeError
            assert logger.redis == mock_redisstack_instance.redis


class TestKafkaMemoryLoggerOrchestatorIntegration:
    """Test integration with orchestrator."""

    @patch("orka.memory.kafka_logger.redis.from_url")
    @patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "kafka"})
    def test_orchestrator_fork_manager_initialization(self, mock_redis):
        """Test that orchestrator can initialize fork manager without AttributeError."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            # Simulate real RedisStackMemoryLogger interface
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.redis_client = Mock()
            mock_redisstack_instance.redis = mock_redisstack_instance.redis_client

            # Ensure no .client attribute (this was the bug)
            if hasattr(mock_redisstack_instance, "client"):
                delattr(mock_redisstack_instance, "client")

            mock_redisstack.return_value = mock_redisstack_instance

            # Create KafkaMemoryLogger (this is what happens in orchestrator)
            kafka_logger = KafkaMemoryLogger()

            # Should not raise AttributeError
            assert kafka_logger.redis == mock_redisstack_instance.redis

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_docker_api_scenario(self, mock_redis):
        """Test the exact scenario that was failing in Docker API with Kafka backend."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            # Mock the RedisStackMemoryLogger exactly as it behaves in production
            mock_redisstack_instance = Mock()

            # RedisStackMemoryLogger has these attributes/properties
            mock_redisstack_instance.redis_client = Mock()
            mock_redisstack_instance._get_thread_safe_client = Mock(return_value=Mock())

            # The redis property returns redis_client
            mock_redisstack_instance.redis = mock_redisstack_instance.redis_client

            # CRITICAL: Remove .client attribute (this is what was causing the bug)
            mock_redisstack_instance.client = None
            delattr(mock_redisstack_instance, "client")

            mock_redisstack.return_value = mock_redisstack_instance

            # Simulate the Kafka backend memory logger creation
            kafka_logger = KafkaMemoryLogger(
                bootstrap_servers="localhost:9092",
                redis_url="redis://localhost:6380/0",
                enable_hnsw=True,
                vector_params={"M": 16, "ef_construction": 200, "ef_runtime": 10},
            )

            # Should not raise AttributeError
            assert kafka_logger.redis == mock_redisstack_instance.redis


class TestKafkaMemoryLoggerLogging:
    """Test logging functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                mock_redisstack.return_value = self.mock_redisstack_instance

                self.logger = KafkaMemoryLogger()

    def test_log_basic_event(self):
        """Test logging a basic event."""
        payload = {"message": "test message", "status": "success"}

        self.logger.log(
            agent_id="test_agent",
            event_type="completion",
            payload=payload,
            step=1,
            run_id="run123",
        )

        # Verify event was added to memory buffer
        assert len(self.logger.memory) == 1
        event = self.logger.memory[0]
        assert event["agent_id"] == "test_agent"
        assert event["event_type"] == "completion"
        assert event["payload"] == payload
        assert event["step"] == 1
        assert event["run_id"] == "run123"

    def test_log_with_decay_enabled(self):
        """Test logging with decay configuration enabled."""
        self.logger.decay_config["enabled"] = True
        self.logger.decay_config["default_long_term_hours"] = 24.0

        with patch.object(self.logger, "_calculate_importance_score", return_value=0.9):
            with patch.object(self.logger, "_classify_memory_category", return_value="stored"):
                with patch.object(self.logger, "_classify_memory_type", return_value="long_term"):
                    self.logger.log(
                        agent_id="test_agent",
                        event_type="memory_storage",
                        payload={"content": "important memory"},
                    )

                    # Verify decay metadata was added
                    event = self.logger.memory[0]
                    assert event["agent_id"] == "test_agent"
                    assert event["event_type"] == "memory_storage"
                    assert "orka_expire_time" in event

    def test_store_in_redis_with_redisstack(self):
        """Test storing event in Redis with RedisStack available."""
        event = {
            "agent_id": "test_agent",
            "event_type": "test",
            "payload": {"message": "test"},
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
        }

        self.logger._store_in_redis(event)

        # Verify RedisStack logger was used
        self.mock_redisstack_instance.log.assert_called_once()

    def test_store_in_redis_fallback(self):
        """Test storing event in Redis with fallback to basic Redis."""
        self.logger._redis_memory_logger = None
        mock_redis_client = Mock()
        self.logger.redis_client = mock_redis_client

        event = {
            "agent_id": "test_agent",
            "event_type": "test",
            "payload": {"message": "test"},
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
        }

        self.logger._store_in_redis(event)

        # Verify basic Redis was used
        mock_redis_client.xadd.assert_called_once()


class TestKafkaMemoryLoggerOperations:
    """Test Redis operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger"):
                self.logger = KafkaMemoryLogger()
                self.mock_redis_client = Mock()
                self.logger.redis_client = self.mock_redis_client

    def test_tail_operation(self):
        """Test tail operation returns from memory buffer."""
        # Add some events to memory buffer
        self.logger.memory = [
            {"event": 1, "timestamp": "2025-01-01T10:00:00Z"},
            {"event": 2, "timestamp": "2025-01-01T11:00:00Z"},
            {"event": 3, "timestamp": "2025-01-01T12:00:00Z"},
            {"event": 4, "timestamp": "2025-01-01T13:00:00Z"},
            {"event": 5, "timestamp": "2025-01-01T14:00:00Z"},
        ]

        # Mock RedisStack logger to return last 3 events
        self.logger._redis_memory_logger = Mock()
        self.logger._redis_memory_logger.tail.return_value = self.logger.memory[-3:]

        result = self.logger.tail(3)

        assert len(result) == 3
        assert result[0]["event"] == 3
        assert result[1]["event"] == 4
        assert result[2]["event"] == 5

    def test_hset_operation(self):
        """Test HSET operation wrapper."""
        self.mock_redis_client.hset.return_value = 1
        self.logger._redis_memory_logger = Mock()
        self.logger._redis_memory_logger.hset.return_value = 1

        result = self.logger.hset("test_hash", "field1", "value1")

        assert result == 1

    def test_hget_operation(self):
        """Test HGET operation wrapper."""
        self.mock_redis_client.hget.return_value = b"value1"
        self.logger._redis_memory_logger = Mock()
        self.logger._redis_memory_logger.hget.return_value = "value1"

        result = self.logger.hget("test_hash", "field1")

        assert result == "value1"  # Decoded from bytes

    def test_hget_none_result(self):
        """Test HGET operation with None result."""
        self.mock_redis_client.hget.return_value = None
        self.logger._redis_memory_logger = Mock()
        self.logger._redis_memory_logger.hget.return_value = None

        result = self.logger.hget("test_hash", "nonexistent")

        assert result is None

    def test_smembers_operation(self):
        """Test SMEMBERS operation wrapper."""
        self.mock_redis_client.smembers.return_value = {b"member1", b"member2"}
        self.logger._redis_memory_logger = Mock()
        self.logger._redis_memory_logger.smembers.return_value = ["member1", "member2"]

        result = self.logger.smembers("test_set")

        assert isinstance(result, list)
        assert len(result) == 2
        assert "member1" in result
        assert "member2" in result

    def test_close_method(self):
        """Test close method closes both Kafka and Redis connections."""
        # Set up the logger to not have RedisStack logger
        self.logger._redis_memory_logger = None

        mock_producer = Mock()
        mock_producer.close = Mock()
        self.logger.producer = mock_producer

        self.logger.close()

        # Verify both connections were closed
        mock_producer.close.assert_called_once()
        self.mock_redis_client.close.assert_called_once()


class TestKafkaMemoryLoggerEnhancedFeatures:
    """Test enhanced features like search and vector operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                mock_redisstack.return_value = self.mock_redisstack_instance

                self.logger = KafkaMemoryLogger()

    def test_search_memories_with_redisstack(self):
        """Test search memories delegates to RedisStack logger."""
        expected_results = [{"content": "test memory", "score": 0.9}]
        self.mock_redisstack_instance.search_memories.return_value = expected_results

        result = self.logger.search_memories(
            query="test query",
            num_results=5,
            memory_type="long_term",
        )

        assert result == expected_results
        self.mock_redisstack_instance.search_memories.assert_called_once_with(
            query="test query",
            num_results=5,
            trace_id=None,
            node_id=None,
            memory_type="long_term",
            min_importance=None,
            log_type="memory",
            namespace=None,
        )

    def test_search_memories_without_redisstack(self):
        """Test search memories returns empty when RedisStack is not available."""
        self.logger._redis_memory_logger = None

        result = self.logger.search_memories("test query")

        assert result == []

    def test_log_memory_with_redisstack(self):
        """Test log memory delegates to RedisStack logger."""
        expected_id = "memory_123"
        self.mock_redisstack_instance.log_memory.return_value = expected_id

        result = self.logger.log_memory(
            content="test content",
            node_id="node1",
            trace_id="trace1",
            importance_score=0.8,
        )

        assert result == expected_id
        self.mock_redisstack_instance.log_memory.assert_called_once()

    def test_ensure_index_with_redisstack(self):
        """Test ensure index delegates to RedisStack logger."""
        # Reset ensure_index call count since it's called during initialization
        self.mock_redisstack_instance.ensure_index.reset_mock()
        self.mock_redisstack_instance.ensure_index.return_value = True

        result = self.logger.ensure_index()

        assert result is True
        self.mock_redisstack_instance.ensure_index.assert_called_once()

    def test_ensure_index_without_redisstack(self):
        """Test ensure index returns False when RedisStack is not available."""
        self.logger._redis_memory_logger = None

        result = self.logger.ensure_index()

        assert result is False


class TestKafkaMemoryLoggerCleanup:
    """Test memory cleanup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                mock_redisstack.return_value = self.mock_redisstack_instance

                self.logger = KafkaMemoryLogger()

    def test_cleanup_expired_memories(self):
        """Test cleanup expired memories functionality."""
        self.logger.decay_config["enabled"] = True

        # Add expired entries to memory buffer
        expired_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

        self.logger.memory = [
            {"agent_id": "agent1", "orka_expire_time": expired_time},
            {"agent_id": "agent2", "orka_expire_time": future_time},
            {"agent_id": "agent3"},  # No expiry time
        ]

        # Mock RedisStack logger to return cleanup stats
        self.mock_redisstack_instance.cleanup_expired_memories.return_value = 5

        result = self.logger.cleanup_expired_memories(dry_run=False)

        assert result == 5
        self.mock_redisstack_instance.cleanup_expired_memories.assert_called_once_with(
            dry_run=False
        )

    def test_get_memory_stats(self):
        """Test get memory stats functionality."""
        # Add some entries to memory buffer
        self.logger.memory = [
            {
                "agent_id": "agent1",
                "event_type": "completion",
                "orka_memory_type": "short_term",
                "orka_memory_category": "stored",
            },
            {
                "agent_id": "agent2",
                "event_type": "debug",
                "orka_memory_type": "long_term",
                "orka_memory_category": "log",
            },
        ]

        # Mock RedisStack logger to return memory stats
        expected_stats = {
            "total_memories": 2,
            "memory_types": {"short_term": 1, "long_term": 1},
            "expired_count": 0,
            "backend": "kafka+redis",
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
        }
        self.mock_redisstack_instance.get_memory_stats.return_value = expected_stats

        result = self.logger.get_memory_stats()

        assert result == expected_stats
        self.mock_redisstack_instance.get_memory_stats.assert_called_once()
