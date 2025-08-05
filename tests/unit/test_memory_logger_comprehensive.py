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
    def test_redisstack_import_error_warning(self, mock_redisstack):
        """Test warning when RedisStack import fails."""
        mock_redisstack.side_effect = ImportError("RedisStack module not found")

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            with patch("logging.getLogger") as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                result = create_memory_logger(backend="redisstack")

                # Should log warning about RedisStack not being available
                mock_log.warning.assert_called_with(
                    "RedisStack not available: RedisStack module not found",
                )
                # Should fallback to basic Redis
                assert result == mock_redis_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_index_failure_warning(self, mock_redisstack):
        """Test warning when RedisStack index test fails."""
        mock_logger_instance = Mock()
        mock_logger_instance.ensure_index.side_effect = Exception("Index creation failed")
        mock_redisstack.return_value = mock_logger_instance

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            with patch("logging.getLogger") as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                result = create_memory_logger(backend="redisstack")

                # Should log warning about index test failure
                mock_log.warning.assert_called_with(
                    "RedisStack index test failed: Index creation failed",
                )
                # Should fallback to basic Redis
                assert result == mock_redis_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_index_false_warning(self, mock_redisstack):
        """Test warning when RedisStack index returns False."""
        mock_logger_instance = Mock()
        mock_logger_instance.ensure_index.return_value = False
        mock_redisstack.return_value = mock_logger_instance

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            with patch("logging.getLogger") as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                result = create_memory_logger(backend="redisstack")

                # Should log warning about index failure
                mock_log.warning.assert_called_with(
                    "⚠️ RedisStack index failed, falling back to basic Redis",
                )
                # Should fallback to basic Redis
                assert result == mock_redis_instance

    @patch(
        "orka.memory.kafka_logger.KafkaMemoryLogger",
        side_effect=ImportError("Kafka not available"),
    )
    def test_kafka_fallback_to_redisstack(self, mock_kafka):
        """Test Kafka fallback to RedisStack when Kafka import fails."""
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_redisstack_instance

            with patch("logging.getLogger") as mock_logger:
                mock_log = Mock()
                mock_logger.return_value = mock_log

                result = create_memory_logger(backend="kafka")

                # Should log warning about Kafka not being available
                mock_log.warning.assert_called_with(
                    "Kafka not available, falling back to RedisStack: Kafka not available",
                )
                # Should fallback to RedisStack
                assert result == mock_redisstack_instance

    @patch.dict(os.environ, {"KAFKA_BOOTSTRAP_SERVERS": "kafka:9092"})
    @patch("orka.memory.kafka_logger.KafkaMemoryLogger")
    def test_kafka_with_environment_bootstrap_servers(self, mock_kafka):
        """Test Kafka backend using environment variable for bootstrap servers."""
        mock_kafka_instance = Mock()
        mock_kafka.return_value = mock_kafka_instance

        result = create_memory_logger(backend="kafka")

        # Should use environment variable for bootstrap servers
        mock_kafka.assert_called_once()
        call_kwargs = mock_kafka.call_args[1]
        assert call_kwargs["bootstrap_servers"] == "kafka:9092"

    @patch("orka.memory.kafka_logger.KafkaMemoryLogger")
    def test_kafka_with_provided_bootstrap_servers(self, mock_kafka):
        """Test Kafka backend with explicitly provided bootstrap servers."""
        mock_kafka_instance = Mock()
        mock_kafka.return_value = mock_kafka_instance

        result = create_memory_logger(
            backend="kafka",
            bootstrap_servers="custom:9092",
        )

        # Should use provided bootstrap servers
        mock_kafka.assert_called_once()
        call_kwargs = mock_kafka.call_args[1]
        assert call_kwargs["bootstrap_servers"] == "custom:9092"

    @patch("orka.memory.kafka_logger.KafkaMemoryLogger")
    def test_kafka_default_bootstrap_servers(self, mock_kafka):
        """Test Kafka backend with default bootstrap servers."""
        mock_kafka_instance = Mock()
        mock_kafka.return_value = mock_kafka_instance

        with patch.dict(os.environ, {}, clear=True):  # Clear environment
            result = create_memory_logger(backend="kafka")

        # Should use default localhost:9092
        mock_kafka.assert_called_once()
        call_kwargs = mock_kafka.call_args[1]
        assert call_kwargs["bootstrap_servers"] == "localhost:9092"

    def test_force_basic_redis_different_backends(self):
        """Test force basic Redis flag with different backend names."""
        with patch.dict(os.environ, {"ORKA_FORCE_BASIC_REDIS": "true"}):
            with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
                mock_redis_instance = Mock()
                mock_redis.return_value = mock_redis_instance

                with patch("logging.getLogger") as mock_logger:
                    mock_log = Mock()
                    mock_logger.return_value = mock_log

                    # Test with "redis" backend
                    result_redis = create_memory_logger(backend="redis")

                    # Test with "redisstack" backend
                    result_redisstack = create_memory_logger(backend="redisstack")

                    # Both should use basic Redis
                    assert mock_redis.call_count == 2
                    mock_log.info.assert_called_with("🔧 Force basic Redis mode enabled")

    def test_complex_fallback_scenario(self):
        """Test complex fallback scenario from Kafka to RedisStack to Redis."""
        with patch(
            "orka.memory.kafka_logger.KafkaMemoryLogger",
            side_effect=ImportError("Kafka unavailable"),
        ):
            with patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger",
                side_effect=ImportError("RedisStack unavailable"),
            ):
                with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
                    mock_redis_instance = Mock()
                    mock_redis.return_value = mock_redis_instance

                    with patch("logging.getLogger") as mock_logger:
                        mock_log = Mock()
                        mock_logger.return_value = mock_log

                        result = create_memory_logger(backend="kafka")

                        # Should eventually use basic Redis
                        assert result == mock_redis_instance

                        # Should log multiple warnings
                        warning_calls = mock_log.warning.call_args_list
                        assert len(warning_calls) >= 2  # Kafka warning and RedisStack warning

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_index_exception_with_fallback_success(self, mock_redisstack):
        """Test RedisStack index exception with successful fallback - targeting missing lines."""
        mock_logger_instance = Mock()
        mock_logger_instance.ensure_index.side_effect = RuntimeError("Connection failed")
        mock_redisstack.return_value = mock_logger_instance

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            result = create_memory_logger(backend="redisstack")

            # Should fallback to basic Redis after index exception
            assert result == mock_redis_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_index_false_with_fallback(self, mock_redisstack):
        """Test RedisStack index returning False with fallback - targeting line 250-252."""
        mock_logger_instance = Mock()
        mock_logger_instance.ensure_index.return_value = False  # Index creation failed
        mock_redisstack.return_value = mock_logger_instance

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            result = create_memory_logger(backend="redisstack")

            # Should fallback to basic Redis when index returns False
            assert result == mock_redis_instance
            mock_redis.assert_called_once()

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_redisstack_import_success_then_fallback(self, mock_redisstack):
        """Test RedisStack import success but fallback due to configuration."""
        mock_logger_instance = Mock()
        mock_logger_instance.ensure_index.side_effect = ConnectionError("Redis not available")
        mock_redisstack.return_value = mock_logger_instance

        with patch("orka.memory.redis_logger.RedisMemoryLogger") as mock_redis:
            mock_redis_instance = Mock()
            mock_redis.return_value = mock_redis_instance

            result = create_memory_logger(backend="redis")

            # Should fallback to basic Redis
            assert result == mock_redis_instance


class TestMemoryLoggerParameterHandling:
    """Test memory logger parameter handling."""

    def test_backend_case_insensitive(self):
        """Test that backend parameter is case insensitive."""
        with (
            patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack,
            patch("orka.memory.kafka_logger.KafkaMemoryLogger") as mock_kafka,
        ):
            # Setup RedisStack mock
            mock_redisstack_instance = Mock()
            mock_redisstack_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_redisstack_instance

            # Setup Kafka mock
            mock_kafka_instance = Mock()
            mock_kafka.return_value = mock_kafka_instance

            # Test various case combinations
            redis_backends = ["REDIS", "Redis", "REDISSTACK", "RedisStack"]
            kafka_backends = ["KAFKA", "Kafka"]

            # Test Redis/RedisStack backends
            for backend in redis_backends:
                result = create_memory_logger(backend=backend)
                assert isinstance(result, mock_redisstack_instance.__class__)

            # Test Kafka backends
            for backend in kafka_backends:
                result = create_memory_logger(backend=backend)
                assert isinstance(result, mock_kafka_instance.__class__)

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    def test_all_parameters_passed_through(self, mock_redisstack):
        """Test that all parameters are correctly passed to backend loggers."""
        mock_instance = Mock()
        mock_instance.ensure_index.return_value = True
        mock_redisstack.return_value = mock_instance

        custom_params = {
            "redis_url": "redis://custom:6379",
            "stream_key": "custom:stream",
            "debug_keep_previous_outputs": True,
            "enable_hnsw": False,
            "vector_params": {"M": 32, "ef_construction": 400},
        }

        create_memory_logger(backend="redisstack", **custom_params)

        # Verify all parameters were passed
        mock_redisstack.assert_called_once()
        call_kwargs = mock_redisstack.call_args[1]

        for key, value in custom_params.items():
            assert call_kwargs[key] == value

    def test_default_decay_config_creation(self):
        """Test default decay configuration is created when None provided."""
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_instance = Mock()
            mock_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_instance

            create_memory_logger(backend="redisstack", decay_config=None)

            # Should create default decay config
            mock_redisstack.assert_called_once()
            call_kwargs = mock_redisstack.call_args[1]

            decay_config = call_kwargs["decay_config"]
            assert decay_config["enabled"] is True
            assert decay_config["default_short_term_hours"] == 1.0
            assert decay_config["default_long_term_hours"] == 24.0
            assert decay_config["check_interval_minutes"] == 30

    def test_custom_decay_config_preserved(self):
        """Test custom decay configuration is preserved."""
        with patch("orka.memory.redisstack_logger.RedisStackMemoryLogger") as mock_redisstack:
            mock_instance = Mock()
            mock_instance.ensure_index.return_value = True
            mock_redisstack.return_value = mock_instance

            custom_decay = {
                "enabled": False,
                "custom_setting": "value",
            }

            create_memory_logger(backend="redisstack", decay_config=custom_decay)

            # Should preserve custom decay config
            mock_redisstack.assert_called_once()
            call_kwargs = mock_redisstack.call_args[1]

            assert call_kwargs["decay_config"] == custom_decay
