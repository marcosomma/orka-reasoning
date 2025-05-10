import json
import time
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest
import redis.asyncio as redis
from fake_redis import FakeRedisClient

# Mock Redis for testing
redis.Redis = lambda *a, **kw: FakeRedisClient()
redis.StrictRedis = lambda *a, **kw: FakeRedisClient()

from orka.contracts import Registry
from orka.nodes.memory_reader_node import MemoryReaderNode
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
            "timestamp": time.time(),
            "metadata": {"source": "test"},
            "is_summary": False,
        }
    )
    memory.search = AsyncMock(
        return_value=[
            {
                "content": "test result",
                "importance": 0.8,
                "timestamp": time.time(),
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


# --- MemoryReaderNode Tests ---


@pytest.mark.asyncio
async def test_memory_reader_node():
    # Use a unique namespace and session ID to avoid interference from other tests
    test_namespace = f"test_isolated_ns_{time.time_ns()}"
    test_session = f"test_isolated_session_{time.time_ns()}"

    node = MemoryReaderNode(
        "test_reader", prompt="Test prompt", namespace=test_namespace
    )
    redis_client = redis.from_url("redis://localhost:6379")

    # Write test data
    test_data = {"content": "Test content", "metadata": {"source": "test"}}
    stream_key = f"orka:memory:{test_namespace}:{test_session}"

    await redis_client.xadd(
        stream_key,
        {
            "ts": str(time.time_ns()),
            "agent_id": "test_writer",
            "type": "memory.append",
            "session": test_session,
            "payload": json.dumps(test_data),
        },
    )

    # Test reading
    context = {"session_id": test_session, "namespace": test_namespace}
    result = await node.run(context)

    assert result["status"] == "success"
    assert "memories" in result
    assert len(result["memories"]) > 0
    assert result["memories"][0]["content"] == "Test content"


# --- MemoryWriterNode Tests ---


@pytest.mark.asyncio
async def test_memory_writer_node():
    # Use a unique namespace and session ID to avoid interference from other tests
    test_namespace = f"test_isolated_ns_{time.time_ns()}"
    test_session = f"test_isolated_session_{time.time_ns()}"

    node = MemoryWriterNode(
        "test_writer", prompt="Test prompt", namespace=test_namespace
    )
    redis_client = redis.from_url("redis://localhost:6379")

    context = {
        "input": "Test content",
        "session_id": test_session,
        "namespace": test_namespace,
        "metadata": {"source": "test"},
    }

    result = await node.run(context)

    assert result["status"] == "success"
    assert result["session"] == test_session

    # Verify data was written
    stream_key = f"orka:memory:{test_namespace}:{test_session}"
    entries = await redis_client.xrange(stream_key)
    assert len(entries) > 0
    entry_data = json.loads(entries[0][1][b"payload"].decode())
    assert entry_data["content"] == "Test content"


@pytest.mark.asyncio
async def test_memory_writer_node_with_vector(monkeypatch):
    # Use a unique namespace and session ID to avoid interference from other tests
    test_namespace = f"test_isolated_ns_{time.time_ns()}"
    test_session = f"test_isolated_session_{time.time_ns()}"

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

    # Create a redis mock with real redis client
    redis_client = redis.from_url("redis://localhost:6379")

    # Fixed timestamp for predictable doc_id calculation
    fixed_timestamp = 1698765432123456
    monkeypatch.setattr("time.time", lambda: fixed_timestamp / 1e6)

    # Create a node with the embedding_model parameter
    node = MemoryWriterNode(
        "test_writer",
        prompt="Test prompt",
        vector=True,
        namespace=test_namespace,
        embedding_model="fake-model",
    )

    # Override the node's redis client with our test client
    node.redis = redis_client

    context = {
        "input": "Test content",
        "session_id": test_session,
        "namespace": test_namespace,
        "metadata": {"source": "test"},
    }

    result = await node.run(context)

    assert result["status"] == "success"
    assert result["session"] == test_session

    # Verify vector data was written - the doc_id format matches the implementation in memory_writer_node.py
    doc_id = f"mem:{test_namespace}:{fixed_timestamp}"

    # The vector_id should be returned in the result
    assert "vector_id" in result

    # Use the actual vector_id from the result for verification
    vector_id = result["vector_id"]
    content = await redis_client.hget(vector_id, "content")
    assert content == b"Test content"  # Note: Redis returns bytes
