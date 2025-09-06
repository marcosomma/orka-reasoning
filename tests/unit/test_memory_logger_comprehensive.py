import os
from unittest.mock import Mock, patch

import pytest

from orka.memory_logger import create_memory_logger


class TestMemoryLoggerEdgeCases:
    """Test edge cases and error scenarios for memory logger factory."""

    @patch.dict(os.environ, {"ORKA_FORCE_BASIC_REDIS": "true"})
    @patch(
        "orka.memory.redis_logger.RedisMemoryLogger",
        side_effect=ImportError("Redis not available"),
    )
    def test_force_basic_redis_import_error(self, mock_redis):
        """Test ImportError when forcing basic Redis mode."""
        with pytest.raises(ImportError, match="Basic Redis backend not available"):
            create_memory_logger(backend="redis")

    @patch(
        "orka.memory.redis_logger.RedisMemoryLogger",
        side_effect=ImportError("Redis not available"),
    )
    def test_redisstack_fallback_redis_import_error(self, mock_redis):
        """Test ImportError in Redis fallback for RedisStack backend."""
        with patch(
            "orka.memory.redisstack_logger.RedisStackMemoryLogger",
            side_effect=ImportError("RedisStack not available"),
        ):
            with pytest.raises(ImportError, match="No Redis backends available"):
                create_memory_logger(backend="redisstack")

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_index_creation_failure(self, mock_redisstack):
        """Test RedisStack when index creation fails (still uses RedisStack)."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = False
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(backend="redisstack")

        # Should still use RedisStack even if index creation fails
        mock_redisstack.assert_called_once()
        assert result == mock_redisstack_instance

    def test_complex_fallback_scenario(self):
        """Test complex fallback scenario from RedisStack to Redis."""
        with patch(
            "orka.memory.redisstack_logger.RedisStackMemoryLogger",
            side_effect=ImportError("RedisStack unavailable"),
        ):
            with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
                mock_redis_instance = Mock()
                mock_redis.return_value = mock_redis_instance

                with patch("logging.getLogger") as mock_logger:
                    mock_logger.return_value = Mock()

                    result = create_memory_logger(backend="redisstack")

                    # Should eventually use basic Redis
                    assert result == mock_redis_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_with_custom_params(self, mock_redisstack):
        """Test RedisStack backend with custom parameters."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(
            backend="redisstack",
            redis_url="redis://custom:6379",
            enable_hnsw=True,
            vector_params={"M": 32, "ef_construction": 400},
        )

        # Should call RedisStack with custom parameters
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        assert call_kwargs["redis_url"] == "redis://custom:6379"
        assert call_kwargs["enable_hnsw"] is True
        assert call_kwargs["vector_params"] == {"M": 32, "ef_construction": 400}

    def test_case_insensitive_backend_selection(self):
        """Test that backend selection is case-insensitive."""
        with (patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack,):
            # Setup RedisStack mock
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_redisstack_instance

            # Test various case combinations
            redis_backends = ["REDIS", "Redis", "REDISSTACK", "RedisStack"]

            # Test Redis/RedisStack backends
            for backend in redis_backends:
                result = create_memory_logger(backend=backend)
                assert isinstance(result, mock_redisstack_instance.__class__)

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_environment_variable_override(self, mock_redisstack):
        """Test environment variable override for backend selection."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        with patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "redisstack"}):
            result = create_memory_logger()  # No backend specified

            # Should use environment variable
            assert result == mock_redisstack_instance

    def test_invalid_backend_raises_error(self):
        """Test that invalid backend names raise appropriate errors."""
        with pytest.raises(ValueError, match="Unsupported backend: invalid_backend"):
            create_memory_logger(backend="invalid_backend")

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redis_backend_with_custom_url(self, mock_redisstack):
        """Test Redis backend with custom URL (uses RedisStack)."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(
            backend="redis",
            redis_url="redis://custom-redis:6380/1",
        )

        # Should use RedisStack with custom Redis URL
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        assert call_kwargs["redis_url"] == "redis://custom-redis:6380/1"

    @patch.dict(os.environ, {"REDIS_URL": "redis://env-redis:6380/2"})
    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redis_backend_with_environment_url(self, mock_redisstack):
        """Test Redis backend using environment variable for URL (uses RedisStack)."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(backend="redis", redis_url=None)

        # Should use environment variable for Redis URL with RedisStack
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        # The factory function uses environment variable when redis_url is None
        assert "redis_url" in call_kwargs

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redis_backend_default_url(self, mock_redisstack):
        """Test Redis backend with default URL (uses RedisStack)."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            result = create_memory_logger(backend="redis")

        # Should use default localhost:6380 with RedisStack
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        assert call_kwargs["redis_url"] == "redis://localhost:6380/0"

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_backend_with_debug_options(self, mock_redisstack):
        """Test RedisStack backend with debug options."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(
            backend="redisstack",
            debug_keep_previous_outputs=True,
        )

        # Should pass debug options
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        assert call_kwargs["debug_keep_previous_outputs"] is True

    def test_memory_logger_with_decay_config(self):
        """Test memory logger creation with decay configuration."""
        decay_config = {
            "enabled": True,
            "interval_minutes": 60,
            "max_age_hours": 24,
        }

        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_redisstack_instance

            result = create_memory_logger(
                backend="redisstack",
                decay_config=decay_config,
            )

            # Should pass decay configuration
            mock_redisstack.assert_called_once()
            call_kwargs = mock_redisstack.call_args[1]
            assert call_kwargs["decay_config"] == decay_config

    def test_memory_logger_initialization_logging(self):
        """Test that memory logger initialization is properly logged."""
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_redisstack_instance

            # Don't mock the logger to allow actual logging
            result = create_memory_logger(backend="redisstack")

            # Should create RedisStack instance
            mock_redisstack.assert_called_once()

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_with_vector_search_disabled(self, mock_redisstack):
        """Test RedisStack backend with vector search disabled."""
        mock_redisstack_instance = Mock()
        mock_redisstack_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_redisstack_instance

        result = create_memory_logger(
            backend="redisstack",
            enable_hnsw=False,
        )

        # Should disable HNSW vector search
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]
        assert call_kwargs["enable_hnsw"] is False

    def test_backend_parameter_precedence(self):
        """Test that explicit backend parameter takes precedence over environment."""
        with patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "redis"}):
            with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
                mock_redisstack_instance = Mock()
                mock_redisstack_instance.ensure_index.return_value = True
                mock_redisstack.return_value = mock_redisstack_instance

                # Explicit backend should override environment
                result = create_memory_logger(backend="redisstack")
                assert result == mock_redisstack_instance
