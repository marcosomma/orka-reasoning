# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
"""Tests for MemoryCRUDMixin - CRUD operations for memory entries."""

import json
from unittest.mock import MagicMock, patch

import pytest

from orka.memory.redisstack.crud_mixin import MemoryCRUDMixin


class MockCRUDLogger(MemoryCRUDMixin):
    """Mock class to test MemoryCRUDMixin."""

    def __init__(self):
        self.mock_client = MagicMock()

    def _get_thread_safe_client(self):
        return self.mock_client

    def _is_expired(self, memory_data):
        expire_time = memory_data.get("orka_expire_time") or memory_data.get(
            b"orka_expire_time"
        )
        if expire_time:
            import time

            return int(expire_time) < int(time.time() * 1000)
        return False

    def _get_ttl_info(self, key, memory_data, current_time_ms):
        return {"ttl_seconds": 3600, "expires_in_human": "1 hour"}


class TestMemoryCRUDMixinGetAll:
    """Tests for get_all_memories method."""

    def test_get_all_memories_returns_list(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = []

        result = logger.get_all_memories()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_all_memories_with_entries(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:abc123"]
        logger.mock_client.hgetall.return_value = {
            b"content": b"test content",
            b"node_id": b"agent_1",
            b"trace_id": b"trace_123",
            b"importance_score": b"0.8",
            b"memory_type": b"long_term",
            b"timestamp": b"1234567890000",
            b"metadata": b"{}",
        }

        result = logger.get_all_memories()

        assert len(result) == 1
        assert result[0]["content"] == "test content"
        assert result[0]["node_id"] == "agent_1"
        assert result[0]["importance_score"] == 0.8

    def test_get_all_memories_filtered_by_trace_id(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [
            b"orka_memory:abc123",
            b"orka_memory:def456",
        ]

        def mock_hgetall(key):
            if key == b"orka_memory:abc123":
                return {
                    b"content": b"content1",
                    b"node_id": b"agent_1",
                    b"trace_id": b"trace_123",
                    b"importance_score": b"0.8",
                    b"memory_type": b"long_term",
                    b"timestamp": b"1234567890000",
                    b"metadata": b"{}",
                }
            return {
                b"content": b"content2",
                b"node_id": b"agent_2",
                b"trace_id": b"other_trace",
                b"importance_score": b"0.5",
                b"memory_type": b"short_term",
                b"timestamp": b"1234567890001",
                b"metadata": b"{}",
            }

        logger.mock_client.hgetall.side_effect = mock_hgetall

        result = logger.get_all_memories(trace_id="trace_123")

        assert len(result) == 1
        assert result[0]["trace_id"] == "trace_123"


class TestMemoryCRUDMixinDelete:
    """Tests for delete_memory method."""

    def test_delete_memory_success(self):
        logger = MockCRUDLogger()
        logger.mock_client.delete.return_value = 1

        result = logger.delete_memory("orka_memory:abc123")

        assert result is True
        logger.mock_client.delete.assert_called_once_with("orka_memory:abc123")

    def test_delete_memory_not_found(self):
        logger = MockCRUDLogger()
        logger.mock_client.delete.return_value = 0

        result = logger.delete_memory("orka_memory:nonexistent")

        assert result is False

    def test_delete_memory_error(self):
        logger = MockCRUDLogger()
        logger.mock_client.delete.side_effect = Exception("Redis error")

        result = logger.delete_memory("orka_memory:abc123")

        assert result is False


class TestMemoryCRUDMixinClear:
    """Tests for clear_all_memories method."""

    def test_clear_all_memories_success(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [
            b"orka_memory:a",
            b"orka_memory:b",
        ]
        logger.mock_client.delete.return_value = 2

        logger.clear_all_memories()

        logger.mock_client.delete.assert_called_once()

    def test_clear_all_memories_empty(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = []

        logger.clear_all_memories()

        logger.mock_client.delete.assert_not_called()


class TestMemoryCRUDMixinTail:
    """Tests for tail method."""

    def test_tail_returns_recent(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [
            b"orka_memory:a",
            b"orka_memory:b",
        ]

        def mock_hgetall(key):
            if key == b"orka_memory:a":
                return {
                    b"content": b"older",
                    b"node_id": b"agent_1",
                    b"trace_id": b"trace",
                    b"importance_score": b"0.5",
                    b"memory_type": b"short_term",
                    b"timestamp": b"1000",
                    b"metadata": b"{}",
                }
            return {
                b"content": b"newer",
                b"node_id": b"agent_1",
                b"trace_id": b"trace",
                b"importance_score": b"0.5",
                b"memory_type": b"short_term",
                b"timestamp": b"2000",
                b"metadata": b"{}",
            }

        logger.mock_client.hgetall.side_effect = mock_hgetall

        result = logger.tail(count=2)

        assert len(result) == 2
        assert result[0]["content"] == "newer"  # Most recent first


class TestMemoryCRUDMixinSafeGet:
    """Tests for _safe_get_redis_value method."""

    def test_safe_get_string_value(self):
        logger = MockCRUDLogger()
        data = {"key": "value"}

        result = logger._safe_get_redis_value(data, "key")

        assert result == "value"

    def test_safe_get_bytes_value(self):
        logger = MockCRUDLogger()
        data = {b"key": b"value"}

        result = logger._safe_get_redis_value(data, "key")

        assert result == "value"

    def test_safe_get_default_value(self):
        logger = MockCRUDLogger()
        data = {"other": "value"}

        result = logger._safe_get_redis_value(data, "key", "default")

        assert result == "default"

