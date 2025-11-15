import pytest
from unittest.mock import patch, MagicMock

from orka.agents.utils.redis_client import get_redis_client

def test_get_redis_client():
    """Test that get_redis_client returns a Redis client instance with correct parameters."""
    with patch("orka.agents.utils.redis_client.redis.Redis") as MockRedis:
        client = get_redis_client()
        MockRedis.assert_called_once_with(host="localhost", port=6380, db=0)
        assert client == MockRedis.return_value
