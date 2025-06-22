"""
Tests for memory decay functionality across all memory backends.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from orka.memory.base_logger import BaseMemoryLogger
from orka.memory.kafka_logger import KafkaMemoryLogger
from orka.memory.redis_logger import RedisMemoryLogger


class TestMemoryDecayBaseLogger:
    """Test memory decay functionality in the base logger."""

    def test_init_decay_config_defaults(self):
        """Test decay configuration initialization with defaults."""

        class TestLogger(BaseMemoryLogger):
            def cleanup_expired_memories(self, dry_run=False):
                return {}

            def get_memory_stats(self):
                return {}

            def log(self, agent_id, event_type, payload, **kwargs):
                pass

            # Implement all required abstract methods from mixins
            def delete(self, key):
                pass

            def get(self, key):
                pass

            def hdel(self, key, field):
                pass

            def hget(self, key, field):
                pass

            def hkeys(self, key):
                pass

            def hset(self, key, field, value):
                pass

            def sadd(self, key, value):
                pass

            def set(self, key, value):
                pass

            def smembers(self, key):
                pass

            def srem(self, key, value):
                pass

            def tail(self, key, count=None):
                pass

        logger = TestLogger()

        config = logger.decay_config
        assert config["enabled"] is True
        assert config["default_short_term_hours"] == 1.0
        assert config["default_long_term_hours"] == 24.0
        assert config["check_interval_minutes"] == 30
        assert "memory_type_rules" in config
        assert "importance_rules" in config

    def test_calculate_importance_score(self):
        """Test importance score calculation."""

        class TestLogger(BaseMemoryLogger):
            def cleanup_expired_memories(self, dry_run=False):
                return {}

            def get_memory_stats(self):
                return {}

            def log(self, agent_id, event_type, payload, **kwargs):
                pass

            # Implement all required abstract methods from mixins
            def delete(self, key):
                pass

            def get(self, key):
                pass

            def hdel(self, key, field):
                pass

            def hget(self, key, field):
                pass

            def hkeys(self, key):
                pass

            def hset(self, key, field, value):
                pass

            def sadd(self, key, value):
                pass

            def set(self, key, value):
                pass

            def smembers(self, key):
                pass

            def srem(self, key, value):
                pass

            def tail(self, key, count=None):
                pass

        logger = TestLogger()

        # Base score test
        score = logger._calculate_importance_score("unknown", "test-agent", {})
        assert score == 0.5  # base_score

        # Event type boost test
        score = logger._calculate_importance_score("write", "test-agent", {})
        assert score == 0.8  # base_score + write boost (0.5 + 0.3)

        # Agent type boost test
        score = logger._calculate_importance_score("unknown", "memory-agent", {})
        assert score == 0.7  # base_score + memory boost (0.5 + 0.2)

    def test_classify_memory_type(self):
        """Test memory type classification."""

        class TestLogger(BaseMemoryLogger):
            def cleanup_expired_memories(self, dry_run=False):
                return {}

            def get_memory_stats(self):
                return {}

            def log(self, agent_id, event_type, payload, **kwargs):
                pass

            # Implement all required abstract methods from mixins
            def delete(self, key):
                pass

            def get(self, key):
                pass

            def hdel(self, key, field):
                pass

            def hget(self, key, field):
                pass

            def hkeys(self, key):
                pass

            def hset(self, key, field, value):
                pass

            def sadd(self, key, value):
                pass

            def set(self, key, value):
                pass

            def smembers(self, key):
                pass

            def srem(self, key, value):
                pass

            def tail(self, key, count=None):
                pass

        logger = TestLogger()

        # Long-term event type for stored memories
        memory_type = logger._classify_memory_type("success", 0.1, "stored")
        assert memory_type == "long_term"

        # Short-term event type for stored memories
        memory_type = logger._classify_memory_type("debug", 0.1, "stored")
        assert memory_type == "short_term"

        # High importance score fallback for stored memories
        memory_type = logger._classify_memory_type("unknown", 0.8, "stored")
        assert memory_type == "long_term"

        # Low importance score fallback for stored memories
        memory_type = logger._classify_memory_type("unknown", 0.1, "stored")
        assert memory_type == "short_term"

        # Log category should always be short-term regardless of importance
        memory_type = logger._classify_memory_type("success", 0.9, "log")
        assert memory_type == "short_term"


class TestRedisMemoryDecay:
    """Test Redis-specific memory decay functionality."""

    @patch("redis.from_url")
    def test_redis_cleanup_expired_memories(self, mock_redis):
        """Test Redis expired memory cleanup."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Mock stream data with expired entries
        past_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        future_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

        mock_stream_data = [
            (
                b"stream1",
                [
                    (b"1-0", {b"orka_expire_time": past_time.encode(), b"agent_id": b"agent1"}),
                    (b"1-1", {b"orka_expire_time": future_time.encode(), b"agent_id": b"agent2"}),
                ],
            ),
        ]

        mock_client.keys.return_value = [b"orka:memory"]
        mock_client.xread.return_value = mock_stream_data
        mock_client.xdel = Mock()

        # Mock xrange to return proper data structure
        mock_client.xrange.return_value = [
            (b"1-0", {b"orka_expire_time": past_time.encode(), b"agent_id": b"agent1"}),
            (b"1-1", {b"orka_expire_time": future_time.encode(), b"agent_id": b"agent2"}),
        ]

        decay_config = {"enabled": True}
        logger = RedisMemoryLogger(decay_config=decay_config)

        stats = logger.cleanup_expired_memories(dry_run=False)

        assert stats["deleted_count"] == 1
        assert not stats["dry_run"]
        mock_client.xdel.assert_called_once_with(b"orka:memory", b"1-0")

    @patch("redis.from_url")
    def test_redis_log_with_decay_metadata(self, mock_redis):
        """Test Redis logging with decay metadata generation."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
        }

        logger = RedisMemoryLogger(decay_config=decay_config)

        # Mock xadd to capture the logged data
        mock_client.xadd = Mock()

        logger.log(
            agent_id="test-agent",
            event_type="write",
            payload={"result": "success"},
            run_id="test-run",
        )

        # Verify xadd was called
        mock_client.xadd.assert_called_once()
        call_args = mock_client.xadd.call_args
        logged_data = call_args[0][1]  # Second argument is the data dict

        # Check decay metadata was added
        assert "orka_importance_score" in logged_data
        assert "orka_memory_type" in logged_data
        assert "orka_expire_time" in logged_data
        assert "orka_created_time" in logged_data


class TestKafkaMemoryDecay:
    """Test Kafka-specific memory decay functionality."""

    @patch("kafka.KafkaProducer")
    def test_kafka_cleanup_expired_memories(self, mock_producer_class):
        """Test Kafka expired memory cleanup."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        decay_config = {"enabled": True}
        logger = KafkaMemoryLogger(
            bootstrap_servers="localhost:9092",
            decay_config=decay_config,
        )

        # Add test data with expired and active entries
        past_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        future_time = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

        logger.memory = [
            {
                "agent_id": "agent1",
                "event_type": "write",
                "orka_expire_time": past_time,
                "orka_memory_type": "short_term",
            },
            {
                "agent_id": "agent2",
                "event_type": "success",
                "orka_expire_time": future_time,
                "orka_memory_type": "long_term",
            },
        ]

        stats = logger.cleanup_expired_memories(dry_run=False)

        assert stats["deleted_count"] == 1
        assert stats["total_entries_after"] == 1
        assert len(logger.memory) == 1

    @patch("kafka.KafkaProducer")
    def test_kafka_log_with_decay_metadata(self, mock_producer_class):
        """Test Kafka logging with decay metadata generation."""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer

        decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
        }

        logger = KafkaMemoryLogger(
            bootstrap_servers="localhost:9092",
            decay_config=decay_config,
        )

        logger.log(
            agent_id="test-agent",
            event_type="write",
            payload={"result": "success"},
            run_id="test-run",
        )

        # Check that data was added to in-memory storage with decay metadata
        assert len(logger.memory) == 1
        entry = logger.memory[0]

        assert "orka_importance_score" in entry
        assert "orka_memory_type" in entry
        assert "orka_expire_time" in entry
        assert "orka_created_time" in entry
