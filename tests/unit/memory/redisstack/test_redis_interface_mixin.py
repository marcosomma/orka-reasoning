# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
"""Tests for RedisInterfaceMixin - thread-safe Redis operations."""

from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack.redis_interface_mixin import RedisInterfaceMixin


class MockRedisInterface(RedisInterfaceMixin):
    """Mock class to test RedisInterfaceMixin."""

    def __init__(self):
        self.mock_client = MagicMock()

    def _get_thread_safe_client(self):
        return self.mock_client


class TestRedisInterfaceHash:
    """Tests for hash operations."""

    def test_hset(self):
        iface = MockRedisInterface()
        iface.mock_client.hset.return_value = 1

        result = iface.hset("hash_name", "field", "value")

        assert result == 1
        iface.mock_client.hset.assert_called_once_with("hash_name", "field", "value")

    def test_hget(self):
        iface = MockRedisInterface()
        iface.mock_client.hget.return_value = "value"

        result = iface.hget("hash_name", "field")

        assert result == "value"
        iface.mock_client.hget.assert_called_once_with("hash_name", "field")

    def test_hkeys(self):
        iface = MockRedisInterface()
        iface.mock_client.hkeys.return_value = ["field1", "field2"]

        result = iface.hkeys("hash_name")

        assert result == ["field1", "field2"]
        iface.mock_client.hkeys.assert_called_once_with("hash_name")

    def test_hdel(self):
        iface = MockRedisInterface()
        iface.mock_client.hdel.return_value = 2

        result = iface.hdel("hash_name", "field1", "field2")

        assert result == 2
        iface.mock_client.hdel.assert_called_once_with("hash_name", "field1", "field2")


class TestRedisInterfaceSet:
    """Tests for set operations."""

    def test_smembers(self):
        iface = MockRedisInterface()
        iface.mock_client.smembers.return_value = {"member1", "member2"}

        result = iface.smembers("set_name")

        assert isinstance(result, list)
        assert len(result) == 2
        iface.mock_client.smembers.assert_called_once_with("set_name")

    def test_sadd(self):
        iface = MockRedisInterface()
        iface.mock_client.sadd.return_value = 2

        result = iface.sadd("set_name", "val1", "val2")

        assert result == 2
        iface.mock_client.sadd.assert_called_once_with("set_name", "val1", "val2")

    def test_srem(self):
        iface = MockRedisInterface()
        iface.mock_client.srem.return_value = 1

        result = iface.srem("set_name", "val1")

        assert result == 1
        iface.mock_client.srem.assert_called_once_with("set_name", "val1")


class TestRedisInterfaceBasic:
    """Tests for basic key-value operations."""

    def test_get(self):
        iface = MockRedisInterface()
        iface.mock_client.get.return_value = "value"

        result = iface.get("key")

        assert result == "value"
        iface.mock_client.get.assert_called_once_with("key")

    def test_set_success(self):
        iface = MockRedisInterface()
        iface.mock_client.set.return_value = True

        result = iface.set("key", "value")

        assert result is True
        iface.mock_client.set.assert_called_once_with("key", "value")

    def test_set_failure(self):
        iface = MockRedisInterface()
        iface.mock_client.set.side_effect = Exception("Redis error")

        result = iface.set("key", "value")

        assert result is False

    def test_delete(self):
        iface = MockRedisInterface()
        iface.mock_client.delete.return_value = 2

        result = iface.delete("key1", "key2")

        assert result == 2
        iface.mock_client.delete.assert_called_once_with("key1", "key2")


class TestRedisInterfaceScan:
    """Tests for scan operation."""

    def test_scan_basic(self):
        iface = MockRedisInterface()
        iface.mock_client.scan.return_value = (0, ["key1", "key2"])

        result = iface.scan(cursor=0, match="prefix:*", count=100)

        assert result == (0, ["key1", "key2"])
        iface.mock_client.scan.assert_called_once_with(
            cursor=0, match="prefix:*", count=100
        )

    def test_scan_defaults(self):
        iface = MockRedisInterface()
        iface.mock_client.scan.return_value = (0, [])

        result = iface.scan()

        iface.mock_client.scan.assert_called_once_with(cursor=0, match=None, count=None)

