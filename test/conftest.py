# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka
import sys
import os
import pytest
import redis
import time
from typing import Generator, Optional
from unittest.mock import patch
from fake_redis import FakeRedisClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global flag to determine if we're using real Redis
USE_REAL_REDIS = os.getenv('USE_REAL_REDIS', 'false').lower() == 'true'

def get_redis_client():
    """Get appropriate Redis client based on configuration."""
    if USE_REAL_REDIS:
        return redis.from_url("redis://localhost:6379/0")
    return FakeRedisClient()

@pytest.fixture(autouse=True, scope="session")
def patch_redis_globally():
    """Patch Redis globally unless using real Redis."""
    if not USE_REAL_REDIS:
        with patch("orka.memory_logger.redis.from_url", return_value=FakeRedisClient()):
            yield
    else:
        yield

def test_remove_group_keyerror():
    mgr = ForkGroupManager()
    with pytest.raises(KeyError):
        mgr.remove_group("nonexistent")

def test_main_invokes_asyncio(monkeypatch):
    called = {}
    def fake_run(coro):
        called["ran"] = True
    monkeypatch.setattr("asyncio.run", fake_run)
    sys_argv = sys.argv
    sys.argv = ["prog", "config.yml", "input"]
    try:
        monkeypatch.setattr("orka.orchestrator.Orchestrator", lambda config_path: type("DummyOrchestrator", (), {"run": lambda self, x: None})())
        import importlib
        importlib.reload(orka_cli)
        assert called.get("ran")
    finally:
        sys.argv = sys_argv

def wait_for_redis(redis_url: str, max_retries: int = 5, retry_delay: float = 1.0) -> bool:
    """
    Wait for Redis to be available.
    
    Args:
        redis_url: Redis connection URL.
        max_retries: Maximum number of connection attempts.
        retry_delay: Delay between retries in seconds.
        
    Returns:
        True if Redis is available, False otherwise.
    """
    for _ in range(max_retries):
        try:
            client = redis.from_url(redis_url)
            client.ping()
            return True
        except redis.ConnectionError:
            time.sleep(retry_delay)
    return False

@pytest.fixture(scope="session", autouse=True)
def ensure_redis() -> Generator[None, None, None]:
    """
    Ensure Redis is available before running tests.
    This fixture runs automatically for all tests.
    """
    if USE_REAL_REDIS:
        redis_url = "redis://localhost:6379/0"
        if not wait_for_redis(redis_url):
            pytest.skip("Redis is not available")
    yield

@pytest.fixture(scope="function")
def redis_client():
    """Create a Redis client for testing."""
    client = get_redis_client()
    yield client
    # Cleanup after tests
    if USE_REAL_REDIS:
        if hasattr(client, 'flushdb'):
            client.flushdb()
    else:
        # For FakeRedisClient, we need to clear all data manually
        # Since FakeRedisClient doesn't support flushdb, we'll clear each key type
        for key in client._keys():
            client.delete(key)
