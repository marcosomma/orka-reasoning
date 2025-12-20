# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# Tests for MemoryDecayMixin - isolated, mocked, GitHub Actions compatible

import time
from unittest.mock import MagicMock

import pytest


class MockDecayHost:
    """Mock host class that provides required methods for MemoryDecayMixin."""

    def __init__(self):
        self.memory_decay_config = {"enabled": True, "short_term_hours": 2.0, "long_term_hours": 168.0}
        self._connection_pool = MagicMock()
        self._mock_client = MagicMock()

    def _get_thread_safe_client(self):
        return self._mock_client

    def _safe_get_redis_value(self, memory_data, key, default=None):
        value = memory_data.get(key, memory_data.get(key.encode("utf-8") if isinstance(key, str) else key, default))
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return default
        return value


class TestDecayMixinIsExpired:
    """Tests for _is_expired method."""

    def test_is_expired_true(self):
        """_is_expired should return True for expired memories."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        # Create a class that uses the mixin
        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()

        # Memory expired 1 hour ago
        past_time = int((time.time() - 3600) * 1000)
        memory_data = {"orka_expire_time": str(past_time)}

        assert host._is_expired(memory_data) is True

    def test_is_expired_false(self):
        """_is_expired should return False for non-expired memories."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()

        # Memory expires in 1 hour
        future_time = int((time.time() + 3600) * 1000)
        memory_data = {"orka_expire_time": str(future_time)}

        assert host._is_expired(memory_data) is False

    def test_is_expired_no_expiry(self):
        """_is_expired should return False when no expiry time is set."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        memory_data = {"content": "test"}

        assert host._is_expired(memory_data) is False


class TestDecayMixinTTLInfo:
    """Tests for _get_ttl_info method."""

    def test_get_ttl_info_from_redis_ttl(self):
        """_get_ttl_info should use Redis TTL when available."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host._mock_client.ttl = MagicMock(return_value=3600)  # 1 hour

        current_time_ms = int(time.time() * 1000)
        memory_data = {}

        result = host._get_ttl_info(b"test_key", memory_data, current_time_ms)

        assert result["ttl_seconds"] == 3600
        assert result["has_expiry"] is True
        assert "1h" in result["ttl_formatted"]

    def test_get_ttl_info_from_orka_expire_time(self):
        """_get_ttl_info should use orka_expire_time when Redis TTL is not set."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host._mock_client.ttl = MagicMock(return_value=-1)  # No TTL

        current_time_ms = int(time.time() * 1000)
        future_time = current_time_ms + (7200 * 1000)  # 2 hours from now
        memory_data = {"orka_expire_time": str(future_time)}

        result = host._get_ttl_info(b"test_key", memory_data, current_time_ms)

        assert result["ttl_seconds"] > 0
        assert result["has_expiry"] is True

    def test_get_ttl_info_no_expiry(self):
        """_get_ttl_info should return no expiry when neither is set."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host._mock_client.ttl = MagicMock(return_value=-1)

        current_time_ms = int(time.time() * 1000)
        memory_data = {}

        result = host._get_ttl_info(b"test_key", memory_data, current_time_ms)

        assert result["has_expiry"] is False
        assert result["ttl_formatted"] == "N/A"

    def test_get_ttl_info_formatting(self):
        """_get_ttl_info should format TTL correctly."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()

        # Test different TTL ranges
        test_cases = [
            (30, "30s"),  # Seconds
            (90, "1m 30s"),  # Minutes
            (3661, "1h 1m"),  # Hours
            (90000, "1d"),  # Days
        ]

        for ttl, expected_format in test_cases:
            host._mock_client.ttl = MagicMock(return_value=ttl)
            current_time_ms = int(time.time() * 1000)
            result = host._get_ttl_info(b"test_key", {}, current_time_ms)
            assert expected_format in result["ttl_formatted"], f"Failed for TTL {ttl}"


class TestDecayMixinCalculateExpiry:
    """Tests for _calculate_expiry_hours method."""

    def test_calculate_expiry_short_term(self):
        """_calculate_expiry_hours should calculate short-term expiry."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host.memory_decay_config = {"enabled": True, "short_term_hours": 2.0}

        result = host._calculate_expiry_hours("short_term", 0.5, None)

        # Base 2 hours * (1 + 0.5 importance) = 3 hours
        assert result == 3.0

    def test_calculate_expiry_long_term(self):
        """_calculate_expiry_hours should calculate long-term expiry."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host.memory_decay_config = {"enabled": True, "long_term_hours": 168.0}

        result = host._calculate_expiry_hours("long_term", 0.0, None)

        # Base 168 hours * (1 + 0.0 importance) = 168 hours
        assert result == 168.0

    def test_calculate_expiry_disabled(self):
        """_calculate_expiry_hours should return None when decay is disabled."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host.memory_decay_config = {"enabled": False}

        result = host._calculate_expiry_hours("short_term", 0.5, None)
        assert result is None

    def test_calculate_expiry_with_agent_config(self):
        """_calculate_expiry_hours should use agent-specific config when provided."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host.memory_decay_config = {"enabled": True, "short_term_hours": 2.0}

        agent_config = {"enabled": True, "short_term_hours": 4.0}
        result = host._calculate_expiry_hours("short_term", 0.5, agent_config)

        # Base 4 hours (from agent config) * (1 + 0.5 importance) = 6 hours
        assert result == 6.0


class TestDecayMixinCleanup:
    """Tests for cleanup_expired_memories method."""

    def test_cleanup_dry_run(self):
        """cleanup_expired_memories should not delete in dry-run mode."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()

        # Setup mock with expired memory
        past_time = int((time.time() - 3600) * 1000)
        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(
            return_value={"orka_expire_time": str(past_time)}
        )

        result = host.cleanup_expired_memories(dry_run=True)

        assert result["dry_run"] is True
        assert result["expired_found"] == 1
        assert result["cleaned"] == 0
        host._mock_client.delete.assert_not_called()

    def test_cleanup_actual_delete(self):
        """cleanup_expired_memories should delete expired memories."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()

        # Setup mock with expired memory
        past_time = int((time.time() - 3600) * 1000)
        host._mock_client.keys = MagicMock(return_value=[b"orka_memory:1"])
        host._mock_client.hgetall = MagicMock(
            return_value={"orka_expire_time": str(past_time)}
        )
        host._mock_client.delete = MagicMock(return_value=1)

        result = host.cleanup_expired_memories(dry_run=False)

        assert result["dry_run"] is False
        assert result["cleaned"] == 1
        host._mock_client.delete.assert_called()

    def test_cleanup_no_pool(self):
        """cleanup_expired_memories should handle missing connection pool."""
        from orka.memory.redisstack.decay_mixin import MemoryDecayMixin

        class TestHost(MockDecayHost, MemoryDecayMixin):
            pass

        host = TestHost()
        host._connection_pool = None

        result = host.cleanup_expired_memories()

        assert result["cleanup_type"] == "redisstack_not_ready"
        assert result["cleaned"] == 0

