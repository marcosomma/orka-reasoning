"""
Tests for OrKa CLI memory configuration functionality.
"""

import os
from unittest.mock import Mock, patch

import pytest

from orka.memory_logger import create_memory_logger
from orka.orka_cli import memory_configure


class TestMemoryConfigureCLI:
    """Test the memory configure CLI command."""

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_configure_redis_backend(self, mock_print, mock_create_logger):
        """Test memory configure command with Redis backend."""
        # Mock memory logger with decay config
        mock_logger = Mock()
        mock_logger.decay_config = {
            "enabled": True,
            "default_short_term_hours": 2.0,
            "default_long_term_hours": 48.0,
            "check_interval_minutes": 60,
        }
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"

        with patch.dict(
            os.environ,
            {
                "ORKA_MEMORY_BACKEND": "redis",
                "ORKA_MEMORY_DECAY_ENABLED": "true",
                "ORKA_MEMORY_DECAY_SHORT_TERM_HOURS": "2.0",
                "ORKA_MEMORY_DECAY_LONG_TERM_HOURS": "48.0",
            },
        ):
            result = memory_configure(args)

        assert result == 0
        mock_create_logger.assert_called_once_with(backend="redis")

        # Check that configuration was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("=== OrKa Memory Decay Configuration ===" in call for call in print_calls)
        assert any("Backend: redis" in call for call in print_calls)
        assert any("ORKA_MEMORY_BACKEND: redis" in call for call in print_calls)
        assert any("Decay Enabled: True" in call for call in print_calls)

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_configure_kafka_backend(self, mock_print, mock_create_logger):
        """Test memory configure command with Kafka backend."""
        # Mock memory logger with decay config
        mock_logger = Mock()
        mock_logger.decay_config = {
            "enabled": False,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "kafka"

        with patch.dict(
            os.environ,
            {
                "ORKA_MEMORY_BACKEND": "kafka",
                "ORKA_MEMORY_DECAY_ENABLED": "false",
            },
            clear=True,
        ):
            result = memory_configure(args)

        assert result == 0
        mock_create_logger.assert_called_once_with(backend="kafka")

        # Check that configuration was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Backend: kafka" in call for call in print_calls)
        assert any("Decay Enabled: False" in call for call in print_calls)

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_configure_no_backend_specified(self, mock_print, mock_create_logger):
        """Test memory configure command with no backend specified (defaults to redis)."""
        # Mock memory logger
        mock_logger = Mock()
        mock_logger.decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }
        mock_create_logger.return_value = mock_logger

        # Mock args with no backend
        args = Mock()
        args.backend = None

        with patch.dict(os.environ, {}, clear=True):
            result = memory_configure(args)

        assert result == 0
        mock_create_logger.assert_called_once_with(backend="redis")  # Default backend

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_configure_logger_creation_error(self, mock_print, mock_create_logger):
        """Test memory configure command when logger creation fails."""
        # Mock logger creation to raise an exception
        mock_create_logger.side_effect = Exception("Connection failed")

        # Mock args
        args = Mock()
        args.backend = "redis"

        result = memory_configure(args)

        assert result == 0  # Function should not fail, just report error

        # Check that error was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any(
            "Error creating memory logger: Connection failed" in call for call in print_calls
        )

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_configure_logger_without_decay_support(self, mock_print, mock_create_logger):
        """Test memory configure command with logger that doesn't support decay."""
        # Mock memory logger without decay_config attribute
        mock_logger = Mock()
        del mock_logger.decay_config  # Remove the attribute
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"

        result = memory_configure(args)

        assert result == 0

        # Check that appropriate message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any(
            "Memory logger does not support decay configuration" in call for call in print_calls
        )

    @patch("builtins.print")
    def test_memory_configure_environment_variables_display(self, mock_print):
        """Test that all environment variables are displayed correctly."""
        args = Mock()
        args.backend = "redis"

        env_vars = {
            "ORKA_MEMORY_BACKEND": "kafka",
            "ORKA_MEMORY_DECAY_ENABLED": "true",
            "ORKA_MEMORY_DECAY_SHORT_TERM_HOURS": "0.5",
            "ORKA_MEMORY_DECAY_LONG_TERM_HOURS": "12.0",
            "ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES": "15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("orka.orka_cli.create_memory_logger") as mock_create:
                mock_logger = Mock()
                mock_logger.decay_config = {"enabled": True}
                mock_create.return_value = mock_logger

                memory_configure(args)

        # Check that all environment variables were displayed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        for var, value in env_vars.items():
            assert any(f"{var}: {value}" in call for call in print_calls)

    @patch("builtins.print")
    def test_memory_configure_unset_environment_variables(self, mock_print):
        """Test display of unset environment variables."""
        args = Mock()
        args.backend = "redis"

        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            with patch("orka.orka_cli.create_memory_logger") as mock_create:
                mock_logger = Mock()
                mock_logger.decay_config = {"enabled": False}
                mock_create.return_value = mock_logger

                memory_configure(args)

        # Check that unset variables show "not set"
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        expected_vars = [
            "ORKA_MEMORY_BACKEND",
            "ORKA_MEMORY_DECAY_ENABLED",
            "ORKA_MEMORY_DECAY_SHORT_TERM_HOURS",
            "ORKA_MEMORY_DECAY_LONG_TERM_HOURS",
            "ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES",
        ]

        for var in expected_vars:
            assert any(f"{var}: not set" in call for call in print_calls)


class TestMemoryLoggerFactory:
    """Test the enhanced memory logger factory function."""

    def test_create_memory_logger_redis_with_decay(self):
        """Test creating Redis logger with decay configuration."""

        decay_config = {
            "enabled": True,
            "default_short_term_hours": 2.0,
            "default_long_term_hours": 48.0,
        }

        with patch("redis.from_url") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client

            result = create_memory_logger(
                backend="redis",
                redis_url="redis://localhost:6379",
                decay_config=decay_config,
            )

            # Verify it's a RedisMemoryLogger instance
            from orka.memory.redis_logger import RedisMemoryLogger

            assert isinstance(result, RedisMemoryLogger)
            assert result.decay_config["enabled"] is True
            assert result.decay_config["default_short_term_hours"] == 2.0

    def test_create_memory_logger_kafka_with_decay(self):
        """Test creating Kafka logger with decay configuration."""

        decay_config = {
            "enabled": True,
            "default_short_term_hours": 0.5,
            "default_long_term_hours": 12.0,
        }

        with patch("kafka.KafkaProducer") as mock_producer_class:
            mock_producer = Mock()
            mock_producer_class.return_value = mock_producer

            result = create_memory_logger(
                backend="kafka",
                bootstrap_servers="localhost:9092",
                topic_prefix="test-prefix",
                decay_config=decay_config,
            )

            # Verify it's a KafkaMemoryLogger instance
            from orka.memory.kafka_logger import KafkaMemoryLogger

            assert isinstance(result, KafkaMemoryLogger)
            assert result.decay_config["enabled"] is True
            assert result.decay_config["default_short_term_hours"] == 0.5

    def test_create_memory_logger_invalid_backend(self):
        """Test factory with invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported backend: invalid"):
            create_memory_logger(backend="invalid")

    def test_create_memory_logger_default_parameters(self):
        """Test factory with default parameters."""

        with patch("redis.from_url") as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client

            result = create_memory_logger()

            # Verify it's a RedisMemoryLogger instance (default backend)
            from orka.memory.redis_logger import RedisMemoryLogger

            assert isinstance(result, RedisMemoryLogger)
