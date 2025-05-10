import time
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from orka.agents.memory_agent import MemoryAgent
from orka.contracts import Registry


@pytest.fixture
def mock_registry():
    """Create a mock registry with required resources."""
    registry = MagicMock(spec=Registry)

    # Mock memory
    mock_memory = AsyncMock()
    mock_memory.write = AsyncMock()
    mock_memory.search = AsyncMock(return_value=[])
    mock_memory.get_all = AsyncMock(return_value=[])

    # Mock embedder
    mock_embedder = AsyncMock()
    mock_embedder.encode = AsyncMock(return_value=np.random.rand(384))

    registry.get = MagicMock(
        side_effect=lambda x: {
            "memory": mock_memory,
            "embedder": mock_embedder,
            "llm": AsyncMock(),
        }.get(x)
    )

    return registry


@pytest.fixture
def memory_agent_config():
    """Create a test configuration for MemoryAgent."""
    return {"agent_id": "test_memory", "max_entries": 1000, "importance_threshold": 0.3}


@pytest.mark.asyncio
async def test_memory_agent_init(memory_agent_config, mock_registry):
    """Test MemoryAgent initialization."""
    agent = MemoryAgent(
        agent_id=memory_agent_config["agent_id"],
        registry=mock_registry,
        max_entries=memory_agent_config["max_entries"],
        importance_threshold=memory_agent_config["importance_threshold"],
    )

    await agent.initialize()

    assert agent.agent_id == "test_memory"
    assert agent.compressor.max_entries == 1000
    assert agent.compressor.importance_threshold == 0.3
    assert agent._memory is not None
    assert agent._embedder is not None


@pytest.mark.asyncio
async def test_memory_agent_write_mode(memory_agent_config, mock_registry):
    """Test MemoryAgent in write mode."""
    agent = MemoryAgent(
        agent_id=memory_agent_config["agent_id"],
        registry=mock_registry,
        max_entries=memory_agent_config["max_entries"],
        importance_threshold=memory_agent_config["importance_threshold"],
    )

    await agent.initialize()

    context = {
        "operation": "write",
        "content": "test memory",
        "importance": 0.8,
        "metadata": {"key": "value"},
    }

    output = await agent.run(context)

    assert isinstance(output, dict)
    assert output["status"] == "success"
    assert output["result"]["status"] == "written"
    assert "entry" in output["result"]
    assert output["result"]["entry"]["content"] == "test memory"
    assert output["result"]["entry"]["importance"] == 0.8


@pytest.mark.asyncio
async def test_memory_agent_read_mode(memory_agent_config, mock_registry):
    """Test MemoryAgent in read mode."""
    agent = MemoryAgent(
        agent_id=memory_agent_config["agent_id"],
        registry=mock_registry,
        max_entries=memory_agent_config["max_entries"],
        importance_threshold=memory_agent_config["importance_threshold"],
    )

    await agent.initialize()

    # Mock search results
    mock_results = [
        {"content": "test memory 1", "score": 0.9},
        {"content": "test memory 2", "score": 0.8},
    ]
    mock_registry.get("memory").search.return_value = mock_results

    context = {"operation": "read", "query": "test query", "limit": 5}

    output = await agent.run(context)

    assert isinstance(output, dict)
    assert output["status"] == "success"
    assert output["result"]["results"] == mock_results


@pytest.mark.asyncio
async def test_memory_agent_compress_mode(memory_agent_config, mock_registry):
    """Test MemoryAgent in compress mode."""
    agent = MemoryAgent(
        agent_id=memory_agent_config["agent_id"],
        registry=mock_registry,
        max_entries=memory_agent_config["max_entries"],
        importance_threshold=memory_agent_config["importance_threshold"],
    )

    await agent.initialize()

    # Mock entries that need compression
    mock_entries = [
        MagicMock(importance=0.2, timestamp=time.time() - 86400),  # 1 day old
        MagicMock(importance=0.3, timestamp=time.time() - 86400),  # 1 day old
    ]
    mock_registry.get("memory").get_all.return_value = mock_entries

    context = {"operation": "compress"}

    output = await agent.run(context)

    assert isinstance(output, dict)
    assert output["status"] == "success"
    assert output["result"]["status"] in ["compressed", "no_compression_needed"]


@pytest.mark.asyncio
async def test_memory_agent_error_handling(memory_agent_config, mock_registry):
    """Test MemoryAgent error handling."""
    agent = MemoryAgent(
        agent_id=memory_agent_config["agent_id"],
        registry=mock_registry,
        max_entries=memory_agent_config["max_entries"],
        importance_threshold=memory_agent_config["importance_threshold"],
    )

    await agent.initialize()

    # Test with invalid operation
    context = {"operation": "invalid_operation"}

    output = await agent.run(context)

    assert isinstance(output, dict)
    assert output["status"] == "error"
    assert "Unknown operation" in output["error"]
