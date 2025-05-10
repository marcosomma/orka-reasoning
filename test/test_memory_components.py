import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest
import redis.asyncio as redis
from fake_redis import FakeRedisClient

# Mock Redis for testing
redis.Redis = lambda *a, **kw: FakeRedisClient()
redis.StrictRedis = lambda *a, **kw: FakeRedisClient()

from orka.agents.memory_agent import MemoryAgent
from orka.contracts import Context, Registry
from orka.nodes.memory_reader import MemoryReader
from orka.nodes.memory_reader_node import MemoryReaderNode
from orka.nodes.memory_writer import MemoryWriter
from orka.nodes.memory_writer_node import MemoryWriterNode

# --- Test Fixtures ---


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


# --- MemoryAgent Tests ---


@pytest.mark.asyncio
async def test_memory_agent_write(mock_registry, mock_memory, mock_embedder):
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
async def test_memory_agent_read(mock_registry, mock_memory, mock_embedder):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await agent.initialize()

    ctx = Context({"operation": "read", "query": "test query", "limit": 5})

    result = await agent._run_impl(ctx)

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["content"] == "test result"


@pytest.mark.asyncio
async def test_memory_agent_compress(mock_registry, mock_memory, mock_llm):
    agent = MemoryAgent("test_agent", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_llm]
    await agent.initialize()

    ctx = Context({"operation": "compress"})

    result = await agent._run_impl(ctx)

    assert result["status"] == "no_compression_needed"
    assert "entries" in result


# --- MemoryReaderNode Tests ---


@pytest.mark.asyncio
async def test_memory_reader_node():
    node = MemoryReaderNode("test_reader", prompt="Test prompt")
    redis_client = redis.from_url("redis://localhost:6379")

    # Write test data
    test_data = {"content": "Test content", "metadata": {"source": "test"}}
    await redis_client.xadd(
        "orka:memory:test_session",
        {
            "ts": str(time.time_ns()),
            "agent_id": "test_writer",
            "type": "memory.append",
            "session": "test_session",
            "payload": json.dumps(test_data),
        },
    )

    # Test reading
    context = {"session_id": "test_session"}
    result = await node.run(context)

    assert result["status"] == "success"
    assert "memories" in result
    assert len(result["memories"]) > 0
    assert result["memories"][0]["content"] == "Test content"


# --- MemoryReader Tests ---


@pytest.mark.asyncio
async def test_memory_reader(mock_registry, mock_memory, mock_embedder):
    reader = MemoryReader("test_reader", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await reader.initialize()

    ctx = Context({"query": "test query", "limit": 5})

    result = await reader._run_impl(ctx)

    assert result["status"] == "success"
    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["content"] == "test result"


# --- MemoryWriterNode Tests ---


@pytest.mark.asyncio
async def test_memory_writer_node():
    node = MemoryWriterNode("test_writer", prompt="Test prompt")
    redis_client = redis.from_url("redis://localhost:6379")

    context = {
        "input": "Test content",
        "session_id": "test_session",
        "metadata": {"source": "test"},
    }

    result = await node.run(context)

    assert result["status"] == "success"
    assert result["session"] == "test_session"

    # Verify data was written
    stream_key = "orka:memory:test_session"
    entries = await redis_client.xrange(stream_key)
    assert len(entries) > 0
    entry_data = json.loads(entries[0][1][b"payload"].decode())
    assert entry_data["content"] == "Test content"


@pytest.mark.asyncio
async def test_memory_writer_node_with_vector(monkeypatch):
    # Mock the embedder to avoid HuggingFace API calls
    mock_embedder = AsyncMock()
    mock_embedder.encode = AsyncMock(return_value=np.array([0.1, 0.2, 0.3]))

    # Create a more complete mock for SentenceTransformer
    class MockSentenceTransformer:
        def __init__(self, model_name_or_path=None, *args, **kwargs):
            self.model_name = model_name_or_path

        def encode(self, sentences, *args, **kwargs):
            return np.array([0.1, 0.2, 0.3])

        async def encode_async(self, sentences, *args, **kwargs):
            return np.array([0.1, 0.2, 0.3])

    # Create a mock for the AsyncEmbedder
    class MockAsyncEmbedder:
        def __init__(self, model_name):
            self.model = MockSentenceTransformer(model_name)
            self.model_name = model_name

        async def encode(self, text):
            return np.array([0.1, 0.2, 0.3])

    # Mock all the necessary imports
    monkeypatch.setattr("orka.utils.embedder.AsyncEmbedder", MockAsyncEmbedder)
    monkeypatch.setattr("orka.utils.embedder.get_embedder", lambda x: mock_embedder)
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer", MockSentenceTransformer
    )

    # Mock all HuggingFace Hub API calls
    monkeypatch.setattr(
        "huggingface_hub.file_download.hf_hub_download",
        lambda *args, **kwargs: "mock_path",
    )
    monkeypatch.setattr(
        "huggingface_hub.file_download.get_hf_file_metadata", lambda *args, **kwargs: {}
    )
    monkeypatch.setattr(
        "huggingface_hub.utils._http.hf_raise_for_status", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "transformers.utils.hub.cached_file", lambda *args, **kwargs: "mock_path"
    )
    monkeypatch.setattr(
        "transformers.utils.hub.cached_files", lambda *args, **kwargs: ["mock_path"]
    )

    # Set local_files_only to True to avoid network calls
    monkeypatch.setattr("transformers.utils.hub.is_offline_mode", lambda: True)

    # Create a redis mock with real redis client and patch time.time_ns for deterministic doc_id
    redis_client = redis.from_url("redis://localhost:6379")

    # Fixed timestamp for predictable doc_id
    fixed_timestamp = 1698765432123456789  # Example fixed timestamp
    monkeypatch.setattr("time.time_ns", lambda: fixed_timestamp)

    # Create a node with the embedding_model parameter
    node = MemoryWriterNode(
        "test_writer", prompt="Test prompt", vector=True, embedding_model="fake-model"
    )

    # Override the node's redis client with our test client
    node.redis = redis_client

    context = {
        "input": "Test content",
        "session_id": "test_session",
        "metadata": {"source": "test"},
    }

    result = await node.run(context)

    assert result["status"] == "success"
    assert result["session"] == "test_session"

    # Verify vector data was written - using the exact same doc_id format from the implementation
    doc_id = f"mem:{fixed_timestamp}"
    content = await redis_client.hget(doc_id, "content")
    assert content == b"Test content"  # Note: Redis returns bytes


# --- MemoryWriter Tests ---


@pytest.mark.asyncio
async def test_memory_writer(mock_registry, mock_memory, mock_embedder):
    writer = MemoryWriter("test_writer", mock_registry)
    mock_registry.get.side_effect = [mock_memory, mock_embedder]
    await writer.initialize()

    ctx = Context(
        {"content": "Test content", "importance": 0.8, "metadata": {"source": "test"}}
    )

    result = await writer._run_impl(ctx)

    assert result["status"] == "success"
    assert "entry" in result
    assert result["entry"]["content"] == "Test content"
    assert result["entry"]["importance"] == 0.8
    assert result["entry"]["metadata"] == {"source": "test"}
