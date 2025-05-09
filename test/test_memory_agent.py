import pytest
from unittest.mock import MagicMock, patch
import json
import time
import numpy as np
from orka.agents.memory_agent import MemoryAgent

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.xadd.return_value = "test_memory_id"
    mock.xrange.return_value = [
        (b"test_id_1", {
            b"ts": str(int(time.time())).encode(),
            b"payload": json.dumps({
                "content": "test memory 1",
                "metadata": {"key": "value"}
            }).encode()
        })
    ]
    mock.ft.return_value = MagicMock()
    return mock

@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model."""
    mock = MagicMock()
    mock.encode.return_value = np.random.rand(384)  # MiniLM-L6-v2 dimension
    return mock

@pytest.fixture
def memory_agent_config():
    """Create a test configuration for MemoryAgent."""
    return {
        "id": "test_memory",
        "mode": "hybrid",
        "memory_scope": "session",
        "vector": True,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
    }

def test_memory_agent_init(memory_agent_config):
    """Test MemoryAgent initialization."""
    with patch("orka.agents.memory_agent.SentenceTransformer") as mock_st:
        mock_st.return_value = MagicMock()
        agent = MemoryAgent(memory_agent_config)
        
        assert agent.mode == "hybrid"
        assert agent.memory_scope == "session"
        assert agent.vector_enabled is True
        assert agent.embedding_model is not None

def test_memory_agent_write_mode(memory_agent_config, mock_redis, mock_embedding_model):
    """Test MemoryAgent in write mode."""
    with patch("orka.agents.memory_agent.get_redis_client", return_value=mock_redis), \
         patch("orka.agents.memory_agent.SentenceTransformer", return_value=mock_embedding_model):
        
        config = memory_agent_config.copy()
        config["mode"] = "write"
        agent = MemoryAgent(config)
        
        context = {
            "input": "test memory",
            "session_id": "test_session",
            "metadata": {"key": "value"}
        }
        
        result = agent.run(context)
        
        # Verify Redis calls
        assert mock_redis.xadd.call_count == 2  # Global and scoped streams
        assert mock_redis.ft.call_count == 1  # Vector storage
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "episodic" in result
        assert "semantic" in result

def test_memory_agent_read_mode(memory_agent_config, mock_redis, mock_embedding_model):
    """Test MemoryAgent in read mode."""
    with patch("orka.agents.memory_agent.get_redis_client", return_value=mock_redis), \
         patch("orka.agents.memory_agent.SentenceTransformer", return_value=mock_embedding_model):
        
        config = memory_agent_config.copy()
        config["mode"] = "read"
        agent = MemoryAgent(config)
        
        context = {
            "input": "test query",
            "session_id": "test_session"
        }
        
        result = agent.run(context)
        
        # Verify Redis calls
        assert mock_redis.xrange.called  # Episodic retrieval
        assert mock_redis.ft.called  # Vector search
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "episodic" in result
        assert "semantic" in result
        assert len(result["episodic"]) > 0

def test_memory_agent_hybrid_mode(memory_agent_config, mock_redis, mock_embedding_model):
    """Test MemoryAgent in hybrid mode."""
    with patch("orka.agents.memory_agent.get_redis_client", return_value=mock_redis), \
         patch("orka.agents.memory_agent.SentenceTransformer", return_value=mock_embedding_model):
        
        agent = MemoryAgent(memory_agent_config)
        
        context = {
            "input": "test memory and query",
            "session_id": "test_session",
            "metadata": {"key": "value"}
        }
        
        result = agent.run(context)
        
        # Verify Redis calls
        assert mock_redis.xadd.call_count == 2  # Write to streams
        assert mock_redis.xrange.called  # Read from stream
        assert mock_redis.ft.call_count == 2  # Write and read vectors
        
        # Verify result structure
        assert isinstance(result, dict)
        assert "episodic" in result
        assert "semantic" in result

def test_memory_agent_error_handling(memory_agent_config, mock_redis):
    """Test MemoryAgent error handling."""
    with patch("orka.agents.memory_agent.get_redis_client", return_value=mock_redis):
        # Test with invalid JSON in stream
        mock_redis.xrange.return_value = [
            (b"test_id_1", {
                b"ts": str(int(time.time())).encode(),
                b"payload": b"invalid json"
            })
        ]
        
        agent = MemoryAgent(memory_agent_config)
        context = {"input": "test", "session_id": "test_session"}
        
        result = agent.run(context)
        
        # Should handle invalid JSON gracefully
        assert isinstance(result, dict)
        assert "episodic" in result
        assert len(result["episodic"]) == 0 