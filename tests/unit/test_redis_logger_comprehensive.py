"""
Comprehensive unit tests for Redis Memory Logger.
Tests all major functionality including logging, Redis operations, and memory management.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from orka.memory.redis_logger import RedisMemoryLogger


class TestRedisMemoryLoggerInitialization:
    """Test Redis memory logger initialization."""

    @patch("orka.memory.redis_logger.redis.from_url")
    def test_initialization_default_params(self, mock_redis):
        """Test initialization with default parameters."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        # Ensure clean environment for this test to work reliably in CI/CD
        with patch.dict("os.environ", {}, clear=True):
            logger = RedisMemoryLogger()

        assert logger.redis_url == "redis://localhost:6379/0"
        assert logger.stream_key == "orka:memory"
        assert logger.debug_keep_previous_outputs is False
        assert logger.client == mock_client
        mock_redis.assert_called_once_with("redis://localhost:6379/0")

    @patch("orka.memory.redis_logger.redis.from_url")
    def test_initialization_custom_params(self, mock_redis):
        """Test initialization with custom parameters."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        logger = RedisMemoryLogger(
            redis_url="redis://custom:6379/1",
            stream_key="custom:stream",
            debug_keep_previous_outputs=True,
            decay_config={"enabled": True},
        )

        assert logger.redis_url == "redis://custom:6379/1"
        assert logger.stream_key == "custom:stream"
        assert logger.debug_keep_previous_outputs is True
        # Decay config gets merged with defaults, so just check enabled flag
        assert logger.decay_config["enabled"] is True
        mock_redis.assert_called_once_with("redis://custom:6379/1")

    @patch.dict(os.environ, {"REDIS_URL": "redis://env:6379/2"})
    @patch("orka.memory.redis_logger.redis.from_url")
    def test_initialization_from_env(self, mock_redis):
        """Test initialization with environment variable."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        logger = RedisMemoryLogger()

        assert logger.redis_url == "redis://env:6379/2"
        mock_redis.assert_called_once_with("redis://env:6379/2")

    @patch("orka.memory.redis_logger.redis.from_url")
    def test_redis_property(self, mock_redis):
        """Test redis property for backward compatibility."""
        mock_client = Mock()
        mock_redis.return_value = mock_client

        logger = RedisMemoryLogger()

        assert logger.redis == mock_client
        assert logger.redis is logger.client


class TestRedisMemoryLoggerLogging:
    """Test Redis memory logger log functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.redis_logger.redis.from_url"):
            self.logger = RedisMemoryLogger()
            self.mock_client = Mock()
            self.logger.client = self.mock_client

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

        # Verify Redis stream write
        self.mock_client.xadd.assert_called_once()
        call_args = self.mock_client.xadd.call_args
        assert call_args[0][0] == "orka:memory"  # stream key

        entry = call_args[0][1]
        assert entry["agent_id"] == "test_agent"
        assert entry["event_type"] == "completion"
        assert entry["run_id"] == "run123"
        assert entry["step"] == "1"

        # Payload should be JSON serialized
        payload_json = json.loads(entry["payload"])
        assert payload_json == payload

    def test_log_missing_agent_id(self):
        """Test logging with missing agent_id raises ValueError."""
        with pytest.raises(ValueError, match="Event must contain 'agent_id'"):
            self.logger.log(
                agent_id="",
                event_type="test",
                payload={"data": "test"},
            )

    def test_log_with_decay_enabled(self):
        """Test logging with decay configuration enabled."""
        # Update the decay config properly
        self.logger.decay_config["enabled"] = True
        self.logger.decay_config["default_long_term_hours"] = 24.0

        with patch.object(self.logger, "_calculate_importance_score", return_value=0.9):
            with patch.object(
                self.logger,
                "_classify_memory_category",
                return_value="stored",
            ):
                with patch.object(self.logger, "_classify_memory_type", return_value="long_term"):
                    with patch("orka.memory.redis_logger.datetime") as mock_datetime:
                        mock_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
                        mock_datetime.now.return_value = mock_now
                        mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                            *args,
                            **kwargs,
                        )

                        self.logger.log(
                            agent_id="test_agent",
                            event_type="memory_storage",
                            payload={"content": "important memory"},
                        )

        # Verify decay metadata was added
        call_args = self.mock_client.xadd.call_args[0][1]
        assert "orka_importance_score" in call_args
        assert "orka_memory_type" in call_args
        assert "orka_memory_category" in call_args

    def test_log_with_redis_error(self):
        """Test logging handles Redis errors gracefully."""
        self.mock_client.xadd.side_effect = Exception("Redis connection failed")

        with patch("orka.memory.redis_logger.logger") as mock_logger:
            self.logger.log(
                agent_id="test_agent",
                event_type="completion",
                payload={"data": "test"},
            )

            # Should log error but not raise
            mock_logger.error.assert_called_once()


class TestRedisMemoryLoggerOperations:
    """Test Redis operation wrappers."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.redis_logger.redis.from_url"):
            self.logger = RedisMemoryLogger()
            self.mock_client = Mock()
            self.logger.client = self.mock_client

    def test_tail_operation(self):
        """Test tail operation."""
        # Mock Redis xrevrange result
        mock_stream_data = [
            (b"1641024000000-0", {"event": "1"}),
            (b"1641024001000-0", {"event": "2"}),
            (b"1641024002000-0", {"event": "3"}),
        ]
        self.mock_client.xrevrange.return_value = mock_stream_data

        with patch.object(self.logger, "_sanitize_for_json", return_value=mock_stream_data):
            result = self.logger.tail(3)

            assert result == mock_stream_data
            self.mock_client.xrevrange.assert_called_once_with("orka:memory", count=3)

    def test_hset_operation(self):
        """Test HSET operation wrapper."""
        self.mock_client.hset.return_value = 1

        result = self.logger.hset("test_hash", "field1", "value1")

        assert result == 1
        self.mock_client.hset.assert_called_once_with("test_hash", "field1", "value1")

    def test_hget_operation(self):
        """Test HGET operation wrapper."""
        self.mock_client.hget.return_value = b"value1"

        result = self.logger.hget("test_hash", "field1")

        assert result == "value1"  # Returns decoded string from Redis
        self.mock_client.hget.assert_called_once_with("test_hash", "field1")

    def test_hget_none_result(self):
        """Test HGET operation with None result."""
        self.mock_client.hget.return_value = None

        result = self.logger.hget("test_hash", "nonexistent")

        assert result is None

    def test_smembers_operation(self):
        """Test SMEMBERS operation wrapper."""
        self.mock_client.smembers.return_value = {b"member1", b"member2"}

        result = self.logger.smembers("test_set")

        assert set(result) == {"member1", "member2"}  # Returns decoded strings from Redis
        self.mock_client.smembers.assert_called_once_with("test_set")

    def test_close_method(self):
        """Test close method closes Redis connection."""
        self.logger.close()

        self.mock_client.close.assert_called_once()


class TestRedisMemoryLoggerCleanup:
    """Test cleanup and lifecycle management."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("orka.memory.redis_logger.redis.from_url"):
            self.logger = RedisMemoryLogger()
            self.mock_client = Mock()
            self.logger.client = self.mock_client

    def test_cleanup_expired_memories_dry_run(self):
        """Test cleanup expired memories in dry run mode."""
        self.logger.decay_config["enabled"] = True  # Enable decay for test

        # Mock Redis keys for patterns
        self.mock_client.keys.return_value = [b"orka:memory"]

        # Mock stream entries
        expired_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

        self.mock_client.xrange.return_value = [
            (
                b"1641024000000-0",
                {
                    b"agent_id": b"test_agent",
                    b"event_type": b"test_event",
                    b"orka_expire_time": expired_time.encode(),
                    b"orka_memory_type": b"short_term",
                },
            ),
            (
                b"1641024001000-0",
                {
                    b"agent_id": b"test_agent2",
                    b"event_type": b"test_event2",
                    b"orka_expire_time": future_time.encode(),
                    b"orka_memory_type": b"short_term",
                },
            ),
        ]

        result = self.logger.cleanup_expired_memories(dry_run=True)

        assert result["streams_processed"] == 1
        assert result["total_entries_checked"] == 2
        assert result["deleted_count"] == 1
        assert result["error_count"] == 0
        assert result["dry_run"] is True

    def test_get_memory_stats(self):
        """Test get memory stats functionality."""
        # Mock Redis keys for patterns
        self.mock_client.keys.return_value = [b"orka:memory"]

        # Mock stream info
        self.mock_client.xinfo_stream.return_value = {"length": 3}

        # Mock stream entries
        self.mock_client.xrange.return_value = [
            (
                b"1641024000000-0",
                {
                    b"event_type": b"completion",
                    b"orka_memory_type": b"short_term",
                    b"orka_memory_category": b"stored",
                },
            ),
            (
                b"1641024001000-0",
                {
                    b"event_type": b"success",
                    b"orka_memory_type": b"long_term",
                    b"orka_memory_category": b"stored",
                },
            ),
            (
                b"1641024002000-0",
                {
                    b"event_type": b"debug",
                    b"orka_memory_type": b"short_term",
                    b"orka_memory_category": b"log",
                },
            ),
        ]

        result = self.logger.get_memory_stats()

        assert result["total_streams"] == 1
        assert result["total_entries"] == 3
        assert result["entries_by_memory_type"]["short_term"] == 1  # Only stored memories counted
        assert result["entries_by_memory_type"]["long_term"] == 1
        assert result["entries_by_category"]["stored"] == 2
        assert result["entries_by_category"]["log"] == 1
