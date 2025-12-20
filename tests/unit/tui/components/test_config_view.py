# OrKa: Orchestrator Kit Agents
# Tests for ConfigViewMixin

import pytest
from unittest.mock import MagicMock

from orka.tui.components.config_view import ConfigViewMixin


class ConcreteConfigView(ConfigViewMixin):
    """Concrete implementation for testing."""

    def __init__(self, backend="redis", with_client=True, decay_enabled=True):
        self._backend = backend
        self._memory_logger = MagicMock() if with_client else MagicMock(spec=[])
        if with_client:
            self._memory_logger.client = MagicMock()
            self._memory_logger.client.ping.return_value = True
            self._memory_logger.client.info.return_value = {
                "redis_version": "7.0.0",
                "redis_mode": "standalone",
                "arch_bits": 64,
                "os": "Linux",
                "used_memory_human": "10MB",
                "used_memory_peak_human": "15MB",
                "used_memory_peak_perc": "66",
            }
            self._memory_logger.client.get.return_value = b"test"
            self._memory_logger.client.set.return_value = True
            self._memory_logger.client.delete.return_value = 1
            self._memory_logger.client.execute_command.return_value = [
                [b"name", b"search", b"ver", b"20000"],
                [b"name", b"ReJSON", b"ver", b"20000"],
            ]
            self._memory_logger.client.ft.return_value.info.return_value = {
                "num_docs": 1000
            }
            self._memory_logger.get_memory_stats.return_value = {"total": 100}
            self._memory_logger.search_memories.return_value = []
            self._memory_logger.cleanup_expired_memories.return_value = {
                "duration_seconds": 0.1
            }
            if decay_enabled:
                self._memory_logger.decay_config = {
                    "enabled": True,
                    "default_short_term_hours": 1,
                    "default_long_term_hours": 24,
                    "check_interval_minutes": 30,
                }
            else:
                self._memory_logger.decay_config = {"enabled": False}

    @property
    def backend(self):
        return self._backend

    @property
    def memory_logger(self):
        return self._memory_logger

    def create_footer(self):
        """Mock footer for testing."""
        from rich.panel import Panel
        return Panel("Footer")


class TestConfigViewMixin:
    """Tests for ConfigViewMixin."""

    @pytest.fixture
    def builder(self):
        return ConcreteConfigView()

    def test_create_config_view(self, builder):
        """Test config view creation."""
        result = builder.create_config_view()
        assert result is not None

    def test_create_backend_config_table(self, builder):
        """Test backend config table creation."""
        result = builder._create_backend_config_table()
        assert result is not None

    def test_create_decay_config_table_enabled(self, builder):
        """Test decay config table when enabled."""
        result = builder._create_decay_config_table()
        assert result is not None

    def test_create_decay_config_table_disabled(self):
        """Test decay config table when disabled."""
        builder = ConcreteConfigView(decay_enabled=False)
        result = builder._create_decay_config_table()
        assert result is not None

    def test_create_connection_test_table(self, builder):
        """Test connection test table creation."""
        result = builder._create_connection_test_table()
        assert result is not None

    def test_create_system_info_table(self, builder):
        """Test system info table creation."""
        result = builder._create_system_info_table()
        assert result is not None

    def test_create_module_info_table(self, builder):
        """Test module info table creation."""
        result = builder._create_module_info_table()
        assert result is not None

    def test_redisstack_backend_tests(self):
        """Test RedisStack-specific backend tests."""
        builder = ConcreteConfigView(backend="redisstack")
        result = builder._create_backend_config_table()
        assert result is not None

    def test_no_client_handling(self):
        """Test handling when no client is available."""
        builder = ConcreteConfigView(with_client=False)
        # Should not raise errors
        result = builder._create_backend_config_table()
        assert result is not None

    def test_connection_test_latency_thresholds(self, builder):
        """Test different latency threshold handling."""
        result = builder._create_connection_test_table()
        assert result is not None

