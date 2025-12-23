# OrKa: Orchestrator Kit Agents
# Additional tests for MemoryCRUDMixin to boost coverage

import json
import time
from unittest.mock import MagicMock

import pytest

from orka.memory.redisstack.crud_mixin import MemoryCRUDMixin


class MockCRUDLogger(MemoryCRUDMixin):
    def __init__(self):
        self.mock_client = MagicMock()

    def _get_thread_safe_client(self):
        return self.mock_client

    def _is_expired(self, memory_data):
        ts = memory_data.get("orka_expire_time") or memory_data.get(b"orka_expire_time")
        if ts is None:
            return False
        try:
            return int(ts) < int(time.time() * 1000)
        except Exception:
            return False

    def _get_ttl_info(self, key, memory_data, current_time_ms):
        return {
            "ttl_seconds": 100,
            "expires_at": current_time_ms + 100000,
            "expires_in_human": "1m40s",
        }


class TestGetAllMemoriesMore:
    def test_skips_expired_and_handles_bad_metadata(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:1", b"orka_memory:2"]

        now_ms = int(time.time() * 1000)
        expired_ms = str(now_ms - 1000).encode("utf-8")

        def hgetall(key):
            if key == b"orka_memory:1":
                # expired -> skipped
                return {
                    b"content": b"old",
                    b"node_id": b"n",
                    b"trace_id": b"t",
                    b"importance_score": b"0.1",
                    b"memory_type": b"short",
                    b"timestamp": b"10",
                    b"metadata": b"{}",
                    b"orka_expire_time": expired_ms,
                }
            # malformed metadata -> recovered to {}
            return {
                b"content": b"fresh",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.9",
                b"memory_type": b"short",
                b"timestamp": b"20",
                b"metadata": b"{not-json}",
            }

        logger.mock_client.hgetall.side_effect = hgetall

        out = logger.get_all_memories()
        assert len(out) == 1
        assert out[0]["content"] == "fresh"
        assert isinstance(out[0]["metadata"], dict)

    def test_handles_per_item_exception(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:1", b"orka_memory:2"]

        def hgetall(key):
            if key == b"orka_memory:1":
                raise RuntimeError("boom")
            return {
                b"content": b"ok",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.5",
                b"memory_type": b"short",
                b"timestamp": b"30",
                b"metadata": b"{}",
            }

        logger.mock_client.hgetall.side_effect = hgetall

        out = logger.get_all_memories()
        assert len(out) == 1
        assert out[0]["content"] == "ok"

    def test_top_level_exception_returns_empty(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.side_effect = Exception("keys fail")
        out = logger.get_all_memories()
        assert out == []


class TestClearAllMemoriesMore:
    def test_exception_during_delete_is_caught(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:1"]
        logger.mock_client.delete.side_effect = Exception("del fail")
        # Should not raise
        logger.clear_all_memories()


class TestRecentStoredMemories:
    def test_filters_and_limits_and_includes_ttl(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:1", b"orka_memory:2", b"orka_memory:3", b"orka_memory:4"]
        now = str(int(time.time() * 1000)).encode("utf-8")

        data = {
            b"orka_memory:1": {
                b"content": b"mem1",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.5",
                b"memory_type": b"short",
                b"timestamp": now,
                b"metadata": json.dumps({"log_type": "memory", "category": "stored"}).encode("utf-8"),
            },
            b"orka_memory:2": {
                b"content": b"mem2",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.6",
                b"memory_type": b"short",
                b"timestamp": str(int(time.time() * 1000) - 1).encode("utf-8"),
                # category stored should include even if log_type is log
                b"metadata": json.dumps({"log_type": "log", "category": "stored"}).encode("utf-8"),
            },
            b"orka_memory:3": {
                b"content": b"nope",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.7",
                b"memory_type": b"short",
                b"timestamp": now,
                b"metadata": json.dumps({"log_type": "log", "category": "log"}).encode("utf-8"),
            },
            b"orka_memory:4": {
                b"content": b"expired",
                b"node_id": b"n",
                b"trace_id": b"t",
                b"importance_score": b"0.8",
                b"memory_type": b"short",
                b"timestamp": now,
                b"metadata": json.dumps({"log_type": "memory", "category": "stored"}).encode("utf-8"),
                b"orka_expire_time": str(int(time.time() * 1000) - 1000).encode("utf-8"),
            },
        }

        logger.mock_client.hgetall.side_effect = lambda k: data[k]

        out = logger.get_recent_stored_memories(count=2)
        # Only mem1 and mem2 qualify; mem1 newer so first
        assert len(out) == 2
        assert out[0]["content"] in ("mem1", "mem2")
        assert "ttl_seconds" in out[0]

    def test_metadata_parse_error_means_excluded(self):
        logger = MockCRUDLogger()
        logger.mock_client.keys.return_value = [b"orka_memory:1"]
        logger.mock_client.hgetall.return_value = {
            b"content": b"X",
            b"node_id": b"n",
            b"trace_id": b"t",
            b"importance_score": b"0.1",
            b"memory_type": b"short",
            b"timestamp": b"0",
            b"metadata": b"{not-json}",
        }
        out = logger.get_recent_stored_memories(count=5)
        assert out == []


class TestTailErrors:
    def test_tail_handles_exception(self, monkeypatch):
        logger = MockCRUDLogger()
        monkeypatch.setattr(logger, "get_all_memories", lambda: (_ for _ in ()).throw(RuntimeError("oops")))
        out = logger.tail(3)
        assert out == []


class TestSafeGetDecode:
    def test_bad_bytes_returns_default(self):
        logger = MockCRUDLogger()
        data = {b"key": b"\xff\xfe"}
        assert logger._safe_get_redis_value(data, "key", "d") == "d"
