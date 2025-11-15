"""Unit tests for orka.memory_logger."""

from unittest.mock import Mock, patch

import pytest

from orka.memory_logger import apply_memory_preset_to_config, create_memory_logger

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryLogger:
    """Test suite for memory_logger factory functions."""

    def test_apply_memory_preset_to_config_short_term(self):
        """Test apply_memory_preset_to_config with short_term preset."""
        config = {}
        result = apply_memory_preset_to_config(config, "short_term")

        assert isinstance(result, dict)

    def test_apply_memory_preset_to_config_long_term(self):
        """Test apply_memory_preset_to_config with long_term preset."""
        config = {}
        result = apply_memory_preset_to_config(config, "long_term")

        assert isinstance(result, dict)

    def test_apply_memory_preset_to_config_custom(self):
        """Test apply_memory_preset_to_config with custom preset."""
        config = {}
        result = apply_memory_preset_to_config(config, "custom")

        assert isinstance(result, dict)

        @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
        @patch("orka.memory.redis_logger.RedisMemoryLogger")
        def test_create_memory_logger_redis(self, MockRedisLogger, MockRedisStackLogger):
            """Test create_memory_logger with redis backend."""
            mock_redis_instance = Mock()
            MockRedisLogger.return_value = mock_redis_instance

            # Ensure RedisStackLogger is not used
            MockRedisStackLogger.side_effect = ImportError("RedisStack not available")

            result = create_memory_logger("redis", redis_url="redis://localhost:6379")

            MockRedisLogger.assert_called_once_with(
                redis_url="redis://localhost:6379",
                stream_key="orka:memory",
                debug_keep_previous_outputs=False,
                decay_config={
                    "enabled": True,
                    "default_short_term_hours": 1.0,
                    "default_long_term_hours": 24.0,
                    "check_interval_minutes": 30,
                },
                memory_preset=None,
            )
            assert result == mock_redis_instance
            MockRedisLogger.assert_called_once()

        @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
        @patch("orka.memory.redis_logger.RedisMemoryLogger")
        def test_create_memory_logger_redisstack(self, MockRedisLogger, MockRedisStackLogger):
            """Test create_memory_logger with redisstack backend."""
            mock_redisstack_instance = Mock()
            MockRedisStackLogger.return_value = mock_redisstack_instance

            result = create_memory_logger("redisstack", redis_url="redis://localhost:6380")

            MockRedisStackLogger.assert_called_once_with(
                redis_url="redis://localhost:6380/0",
                index_name="orka_enhanced_memory",
                embedder=ANY,  # Embedder is initialized internally
                memory_decay_config={
                    "enabled": True,
                    "default_short_term_hours": 1.0,
                    "default_long_term_hours": 24.0,
                    "check_interval_minutes": 30,
                },
                stream_key="orka:memory",
                debug_keep_previous_outputs=False,
                decay_config={
                    "enabled": True,
                    "default_short_term_hours": 1.0,
                    "default_long_term_hours": 24.0,
                    "check_interval_minutes": 30,
                },
                memory_preset=None,
                enable_hnsw=True,
                vector_params={
                    "M": 16,
                    "ef_construction": 200,
                    "ef_runtime": 10,
                },
                format_params=None,
                vector_dim=384,
                force_recreate_index=False,
            )
            assert result == mock_redisstack_instance
            MockRedisStackLogger.assert_called_once()

    def test_create_memory_logger_invalid_backend(self):
        """Test create_memory_logger with invalid backend raises ValueError."""
        with pytest.raises(
            ValueError, match="Unsupported backend: invalid_backend. Supported: redisstack, redis"
        ):
            create_memory_logger("invalid_backend")
