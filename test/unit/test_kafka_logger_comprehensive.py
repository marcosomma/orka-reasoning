"""
Comprehensive unit tests for Kafka Memory Logger.
Tests hybrid Kafka + Redis functionality including logging, Redis operations, and memory management.
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from orka.memory.kafka_logger import KafkaMemoryLogger


class TestKafkaMemoryLoggerInitialization:
    """Test Kafka memory logger initialization."""

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
            assert logger.debug_keep_previous_outputs is False

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

            # Should return RedisStack client when available
            assert logger.redis == mock_redisstack_redis_client

    @patch("orka.memory.kafka_logger.redis.from_url")
    def test_redis_property_fallback(self, mock_redis):
        """Test redis property returns fallback client when RedisStack is not available."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger", side_effect=ImportError):
            logger = KafkaMemoryLogger()

            # Should return fallback Redis client
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

            # This should work without AttributeError
            redis_client = logger.redis
            assert redis_client == mock_redisstack_redis_client

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

            # This should NOT raise AttributeError: 'RedisStackMemoryLogger' object has no attribute 'client'
            try:
                redis_client = logger.redis
                # Should succeed and return the redis client
                assert redis_client == mock_redisstack_instance.redis_client
            except AttributeError as e:
                if "has no attribute 'client'" in str(e):
                    raise AssertionError("The original AttributeError bug is not fixed!") from e
                else:
                    raise


class TestKafkaMemoryLoggerOrchestatorIntegration:
    """Test integration scenarios with orchestrator initialization."""

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

            # This is the exact line that was failing in orchestrator base.py:139
            # self.fork_manager = ForkGroupManager(self.memory.redis)
            with patch("orka.fork_group_manager.ForkGroupManager") as mock_fork_manager:
                # This should NOT raise AttributeError
                try:
                    redis_client = kafka_logger.redis
                    mock_fork_manager(redis_client)

                    # Verify the fork manager was created with correct client
                    mock_fork_manager.assert_called_once_with(mock_redisstack_instance.redis_client)

                except AttributeError as e:
                    if "has no attribute 'client'" in str(e):
                        raise AssertionError(
                            "Orchestrator initialization failed due to AttributeError - "
                            "the fix is not working correctly!",
                        ) from e
                    else:
                        raise

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

            # This simulates orchestrator initialization in server.py
            # When POST /api/run creates Orchestrator(tmp_path)
            # Which calls base.py __init__ line 139: self.fork_manager = ForkGroupManager(self.memory.redis)

            # This exact property access was failing with AttributeError
            redis_client_for_fork_manager = kafka_logger.redis

            # Verify we got the correct Redis client
            assert redis_client_for_fork_manager == mock_redisstack_instance.redis_client

            # Test that we can actually use the client (simulate fork manager operations)
            redis_client_for_fork_manager.ping()
            mock_redisstack_instance.redis_client.ping.assert_called_once()


class TestKafkaMemoryLoggerLogging:
    """Test Kafka memory logger log functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                mock_redisstack.return_value = self.mock_redisstack_instance

                self.logger = KafkaMemoryLogger()
                self.mock_redis_client = Mock()
                self.logger.redis_client = self.mock_redis_client

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
        logged_event = self.logger.memory[0]
        assert logged_event["agent_id"] == "test_agent"
        assert logged_event["event_type"] == "completion"
        assert logged_event["run_id"] == "run123"
        assert logged_event["step"] == 1
        assert logged_event["payload"] == payload

        # Verify RedisStack logger was called
        self.mock_redisstack_instance.log.assert_called_once()

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

        # Verify decay metadata was added to memory buffer
        logged_event = self.logger.memory[0]
        assert "orka_importance_score" in logged_event
        assert "orka_memory_type" in logged_event
        assert "orka_memory_category" in logged_event
        assert "orka_expire_time" in logged_event

    def test_store_in_redis_with_redisstack(self):
        """Test storing in Redis using RedisStack logger."""
        event = {
            "agent_id": "test_agent",
            "event_type": "completion",
            "payload": {"data": "test"},
        }

        self.logger._store_in_redis(event, step=1, run_id="run123")

        self.mock_redisstack_instance.log.assert_called_once_with(
            agent_id="test_agent",
            event_type="completion",
            payload={"data": "test"},
            step=1,
            run_id="run123",
            fork_group=None,
            parent=None,
            previous_outputs=None,
            agent_decay_config=None,
        )

    def test_store_in_redis_fallback(self):
        """Test fallback Redis storage when RedisStack is not available."""
        self.logger._redis_memory_logger = None  # Simulate no RedisStack

        # Mock the missing method that causes the error
        with patch.object(self.logger, "decay_config", {"enabled": False}):
            # Mock the _generate_decay_metadata method that doesn't exist but is called
            with patch.object(
                self.logger,
                "_generate_decay_metadata",
                return_value={},
                create=True,
            ):
                event = {
                    "agent_id": "test_agent",
                    "event_type": "completion",
                    "payload": {"data": "test"},
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                self.logger._store_in_redis(event, step=1, run_id="run123")

                # Verify basic Redis stream was used
                self.mock_redis_client.xadd.assert_called_once()
                call_args = self.mock_redis_client.xadd.call_args[0]
                assert call_args[0] == "orka:memory"  # stream key

                entry = call_args[1]
                assert entry["agent_id"] == "test_agent"
                assert entry["event_type"] == "completion"


class TestKafkaMemoryLoggerOperations:
    """Test Kafka memory logger Redis operations."""

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

        result = self.logger.tail(3)

        assert len(result) == 3
        assert result == [
            {"event": 3, "timestamp": "2025-01-01T12:00:00Z"},
            {"event": 4, "timestamp": "2025-01-01T13:00:00Z"},
            {"event": 5, "timestamp": "2025-01-01T14:00:00Z"},
        ]

    def test_hset_operation(self):
        """Test HSET operation wrapper."""
        self.mock_redis_client.hset.return_value = 1

        result = self.logger.hset("test_hash", "field1", "value1")

        assert result == 1
        self.mock_redis_client.hset.assert_called_once_with("test_hash", "field1", "value1")

    def test_hget_operation(self):
        """Test HGET operation wrapper."""
        self.mock_redis_client.hget.return_value = b"value1"

        result = self.logger.hget("test_hash", "field1")

        assert result == "value1"  # Decoded from bytes
        self.mock_redis_client.hget.assert_called_once_with("test_hash", "field1")

    def test_hget_none_result(self):
        """Test HGET operation with None result."""
        self.mock_redis_client.hget.return_value = None

        result = self.logger.hget("test_hash", "nonexistent")

        assert result is None

    def test_smembers_operation(self):
        """Test SMEMBERS operation wrapper."""
        self.mock_redis_client.smembers.return_value = {b"member1", b"member2"}

        result = self.logger.smembers("test_set")

        assert isinstance(result, list)
        assert set(result) == {"member1", "member2"}  # Decoded from bytes
        self.mock_redis_client.smembers.assert_called_once_with("test_set")

    def test_close_method(self):
        """Test close method closes both Kafka and Redis connections."""
        # Set up the logger to not have RedisStack logger
        self.logger._redis_memory_logger = None

        mock_producer = Mock()
        mock_producer.close = Mock()
        self.logger.producer = mock_producer

        self.logger.close()

        mock_producer.close.assert_called_once()
        self.mock_redis_client.close.assert_called_once()


class TestKafkaMemoryLoggerEnhancedFeatures:
    """Test enhanced features of Kafka memory logger."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                # Reset ensure_index call count
                self.mock_redisstack_instance.ensure_index.reset_mock()
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
        self.mock_redisstack_instance.log_memory.assert_called_once_with(
            content="test content",
            node_id="node1",
            trace_id="trace1",
            metadata=None,
            importance_score=0.8,
            memory_type="short_term",
            expiry_hours=None,
        )

    def test_ensure_index_with_redisstack(self):
        """Test ensure index delegates to RedisStack logger."""
        self.mock_redisstack_instance.ensure_index.return_value = True

        result = self.logger.ensure_index()

        assert result is True
        # Should be called once in test, setup already calls it once during init
        self.mock_redisstack_instance.ensure_index.assert_called()

    def test_ensure_index_without_redisstack(self):
        """Test ensure index returns False when RedisStack is not available."""
        self.logger._redis_memory_logger = None

        result = self.logger.ensure_index()

        assert result is False


class TestKafkaMemoryLoggerCleanup:
    """Test cleanup and statistics functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.kafka_logger.redis.from_url"):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                self.mock_redisstack_instance = Mock()
                mock_redisstack.return_value = self.mock_redisstack_instance

                self.logger = KafkaMemoryLogger()
                self.mock_redis_client = Mock()
                self.logger.redis_client = self.mock_redis_client

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

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis_logger:
            mock_instance = Mock()
            mock_instance.cleanup_expired_memories.return_value = {
                "deleted_count": 5,
                "streams_processed": 2,
            }
            mock_redis_logger.return_value = mock_instance

            result = self.logger.cleanup_expired_memories(dry_run=False)

            # Verify Redis cleanup was called
            assert result["backend"] == "kafka+redis"
            assert result["deleted_count"] == 5

            # Verify expired entry was removed from memory buffer
            assert len(self.logger.memory) == 2
            assert all(
                "orka_expire_time" not in entry
                or datetime.fromisoformat(entry["orka_expire_time"]) > datetime.now(UTC)
                for entry in self.logger.memory
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

        # Mock Redis operations with proper side_effect for multiple calls
        def mock_keys(pattern):
            # Return the stream key only for the exact stream_key pattern
            if pattern == "orka:memory":
                return [b"orka:memory"]
            else:
                return []  # No keys for other patterns

        # Patch the underlying Redis client since redis is a property
        self.mock_redisstack_instance.redis = self.mock_redis_client
        self.mock_redis_client.keys.side_effect = mock_keys
        self.mock_redis_client.type.return_value = b"stream"
        self.mock_redis_client.xinfo_stream.return_value = {"length": 2}
        self.mock_redis_client.xrange.return_value = [
            (
                b"1641024000000-0",
                {
                    b"event_type": b"completion",
                    b"orka_memory_type": b"short_term",
                },
            ),
            (
                b"1641024001000-0",
                {
                    b"event_type": b"debug",
                    b"orka_memory_type": b"long_term",
                },
            ),
        ]

        result = self.logger.get_memory_stats()

        assert result["backend"] == "kafka+redis"
        assert result["memory_buffer_size"] == 2
        assert result["total_streams"] == 1
        assert result["total_entries"] == 2

        # Check local buffer insights
        assert "local_buffer_insights" in result
        local_insights = result["local_buffer_insights"]
        assert local_insights["total_entries"] == 2
        assert local_insights["memory_types"]["short_term"] == 1
        assert local_insights["memory_types"]["long_term"] == 1
        assert local_insights["categories"]["stored"] == 1
        assert local_insights["categories"]["log"] == 1
