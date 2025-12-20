from unittest.mock import MagicMock

import pytest


def test_redis_memory_logger_init_and_log(monkeypatch):
    # Patch redis.from_url to return a mock client
    mock_client = MagicMock()
    mock_client.xadd = MagicMock()
    mock_client.xrevrange = MagicMock(return_value=[{"a": 1}])

    import redis

    monkeypatch.setattr(redis, "from_url", lambda url: mock_client)

    from orka.memory.redis_logger import RedisMemoryLogger

    logger = RedisMemoryLogger(redis_url="redis://test:6379/0")

    # client was installed
    assert logger.client is mock_client

    # log without agent_id should raise
    with pytest.raises(ValueError):
        logger.log("", "evt", {"k": "v"})

    # valid log should call xadd on the client
    logger.log("agent1", "evt", {"k": "v"})
    assert mock_client.xadd.called

    # tail should return sanitized list
    res = logger.tail(5)
    assert isinstance(res, list)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from orka.memory.redis_logger import RedisMemoryLogger


@pytest.fixture
def mock_redis_client():
    with patch("orka.memory.redis_logger.redis.from_url") as mock_from_url:
        mock_client = MagicMock()
        mock_from_url.return_value = mock_client
        yield mock_client

def test_redis_logger_initialization(mock_redis_client):
    logger = RedisMemoryLogger(redis_url="redis://localhost:6379/0")
    assert logger.client is mock_redis_client

def test_redis_logger_log(mock_redis_client):
    logger = RedisMemoryLogger()
    payload = {"data": "test"}
    logger.log("agent1", "test_event", payload, step=1, run_id="run1")
    
    mock_redis_client.xadd.assert_called_once()
    args, kwargs = mock_redis_client.xadd.call_args
    assert args[0] == "orka:memory"
    log_data = args[1]
    assert log_data["agent_id"] == "agent1"
    assert log_data["event_type"] == "test_event"
    assert '"data": "test"' in log_data["payload"]

def test_redis_logger_tail(mock_redis_client):
    mock_redis_client.xrevrange.return_value = [
        (b'123-0', {b'agent_id': b'agent1', b'payload': b'{"data": "test"}'})
    ]
    logger = RedisMemoryLogger()
    logs = logger.tail(count=1)
    
    mock_redis_client.xrevrange.assert_called_once_with("orka:memory", count=1)
    assert len(logs) == 1
    # After _sanitize_for_json: tuple becomes list, bytes keys become strings,
    # bytes values become {"__type": "bytes", "data": base64_encoded}
    result = logs[0]
    assert isinstance(result, list)
    # String keys after sanitization
    assert "b'agent_id'" in result[1] or "agent_id" in str(result)

def test_redis_logger_hset_hget(mock_redis_client):
    logger = RedisMemoryLogger()
    logger.hset("my_hash", "key1", "value1")
    mock_redis_client.hset.assert_called_once_with("my_hash", "key1", "value1")
    
    mock_redis_client.hget.return_value = b"value1"
    value = logger.hget("my_hash", "key1")
    assert value == "value1"

from datetime import datetime, timedelta, timezone


def test_cleanup_expired_memories(mock_redis_client):
    logger = RedisMemoryLogger(decay_config={"enabled": True})
    now = datetime.now(timezone.utc)
    future_time = now + timedelta(hours=1)
    
    mock_redis_client.keys.return_value = [b"orka:memory"]
    mock_redis_client.xrange.return_value = [
        (b'123-0', {b'orka_expire_time': b'2000-01-01T00:00:00+00:00'}), # expired
        (b'124-0', {b'orka_expire_time': future_time.isoformat().encode()}) # not expired
    ]
    
    result = logger.cleanup_expired_memories()
    
    mock_redis_client.xdel.assert_called_once_with(b"orka:memory", b'123-0')
    assert result["deleted_count"] == 1

def test_get_memory_stats(mock_redis_client):
    logger = RedisMemoryLogger()
    mock_redis_client.keys.return_value = [b"orka:memory"]
    mock_redis_client.xinfo_stream.return_value = {"length": 2}
    mock_redis_client.xrange.return_value = [
        (b'123-0', {b'event_type': b'type1', b'orka_memory_type': b'short_term', b'orka_memory_category': b'log'}),
        (b'124-0', {b'event_type': b'type2', b'orka_memory_type': b'long_term', b'orka_memory_category': b'stored'})
    ]
    
    stats = logger.get_memory_stats()
    
    assert stats["total_entries"] == 2
    assert stats["entries_by_type"]["type1"] == 1
    assert stats["entries_by_memory_type"]["short_term"] == 0 # logs are not counted here
    assert stats["entries_by_memory_type"]["long_term"] == 1
    assert stats["entries_by_category"]["log"] == 1
    assert stats["entries_by_category"]["stored"] == 1
