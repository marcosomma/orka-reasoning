from datetime import datetime
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from orka.agents.memory_agent import MemoryAgent
from orka.contracts import Context, Registry


@pytest.fixture
def mock_registry():
    registry = Mock(spec=Registry)
    registry.get = AsyncMock()
    return registry


@pytest.fixture
def mock_memory():
    memory = AsyncMock()
    memory.write = AsyncMock(
        return_value={
            "content": "Test content",
            "importance": 0.8,
            "timestamp": datetime.now(),
            "metadata": {"source": "test"},
            "is_summary": False,
        }
    )
    memory.search = AsyncMock(
        return_value=[
            {
                "content": "test result",
                "importance": 0.8,
                "timestamp": datetime.now(),
                "metadata": {"source": "test"},
                "is_summary": False,
            }
        ]
    )
    memory.get_all = AsyncMock(return_value=[])
    memory.replace_all = AsyncMock()
    return memory


@pytest.fixture
def mock_embedder():
    embedder = AsyncMock()
    embedder.encode = AsyncMock(return_value=np.array([0.1, 0.2, 0.3]))
    return embedder


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.compress = AsyncMock(return_value="compressed content")
    return llm


@pytest.fixture
def memory_agent_config():
    """Create a test configuration for MemoryAgent."""
    return {"agent_id": "test_memory", "max_entries": 1000, "importance_threshold": 0.3}


@pytest.mark.asyncio
async def test_memory_agent_init(mock_registry, mock_memory, mock_embedder):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await agent.initialize()

    assert agent.agent_id == "test_agent"
    assert agent._memory == mock_memory
    assert agent._embedder == mock_embedder


@pytest.mark.asyncio
async def test_memory_agent_write_mode(mock_registry, mock_memory, mock_embedder):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await agent.initialize()

    ctx = Context(
        {
            "operation": "write",
            "content": "Test content",
            "importance": 0.8,
            "metadata": {"source": "test"},
        }
    )

    result = await agent._run_impl(ctx)

    assert result["status"] == "written"
    assert "entry" in result
    assert result["entry"]["content"] == "Test content"
    assert result["entry"]["importance"] == 0.8
    assert result["entry"]["metadata"] == {"source": "test"}


@pytest.mark.asyncio
async def test_memory_agent_read_mode(mock_registry, mock_memory, mock_embedder):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await agent.initialize()

    ctx = Context({"operation": "read", "query": "test query", "limit": 5})

    result = await agent._run_impl(ctx)

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["content"] == "test result"


@pytest.mark.asyncio
async def test_memory_agent_compress_mode(mock_registry, mock_memory, mock_llm):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_llm]
    await agent.initialize()

    ctx = Context({"operation": "compress"})

    result = await agent._run_impl(ctx)

    assert result["status"] == "no_compression_needed"
    assert "entries" in result


@pytest.mark.asyncio
async def test_memory_agent_error_handling(mock_registry, mock_memory, mock_embedder):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await agent.initialize()

    # Test missing content
    ctx = Context({"operation": "write"})
    with pytest.raises(ValueError, match="Content is required for write operation"):
        await agent._run_impl(ctx)

    # Test missing query
    ctx = Context({"operation": "read"})
    with pytest.raises(ValueError, match="Query is required for read operation"):
        await agent._run_impl(ctx)

    # Test unknown operation
    ctx = Context({"operation": "unknown"})
    with pytest.raises(ValueError, match="Unknown operation: unknown"):
        await agent._run_impl(ctx)
