import importlib
from unittest.mock import MagicMock


def test_redisstack_logger_init_and_basic_ops(monkeypatch):
    # Patch ConnectionPool.from_url to avoid creating real connections
    rs_mod = importlib.import_module("orka.memory.redisstack_logger")

    monkeypatch.setattr(rs_mod.ConnectionPool, "from_url", lambda *a, **k: MagicMock())

    # Patch redis.Redis to return a mock client with necessary methods
    mock_client = MagicMock()
    mock_client.ping = MagicMock(return_value=None)
    mock_client.hset = MagicMock(return_value=1)
    mock_client.hget = MagicMock(return_value=b"val")
    mock_client.keys = MagicMock(return_value=[b"k1"]) 
    monkeypatch.setattr(rs_mod.redis, "Redis", lambda *a, **k: mock_client)

    # Patch bootstrap helpers to avoid index operations
    bm = importlib.import_module("orka.utils.bootstrap_memory_index")
    monkeypatch.setattr(bm, "ensure_enhanced_memory_index", lambda *a, **k: True)
    monkeypatch.setattr(bm, "verify_memory_index", lambda *a, **k: {"exists": True, "vector_field_exists": True, "content_field_exists": True, "fields": []})

    # Create logger instance; pass a fake embedder with embedding_dim
    embedder = MagicMock()
    embedder.embedding_dim = 384

    from orka.memory.redisstack_logger import RedisStackMemoryLogger

    logger = RedisStackMemoryLogger(redis_url="redis://test:6379/0", embedder=embedder)

    assert hasattr(logger, "index_name")

    # Test simple hset/hget wrappers that delegate to client
    ret = logger.hset("name", "key", "value")
    assert ret == 1
    got = logger.hget("name", "key")
    assert got == b"val"
