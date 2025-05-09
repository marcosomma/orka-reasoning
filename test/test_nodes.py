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
import pytest
import json
import time
from orka.nodes.router_node import RouterNode
from orka.nodes.failover_node import FailoverNode
from orka.nodes.failing_node import FailingNode
from orka.nodes.join_node import JoinNode
from orka.nodes.fork_node import ForkNode
from orka.nodes.memory_writer_node import MemoryWriterNode
from orka.nodes.memory_reader_node import MemoryReaderNode
from orka.nodes.rag_node import RAGNode
from orka.agents.google_duck_agents import DuckDuckGoAgent
from orka.memory_logger import RedisMemoryLogger
from fake_redis import FakeRedisClient
from unittest.mock import MagicMock, patch, AsyncMock

class MockRedisClient:
    """Mock Redis client that supports async operations."""
    def __init__(self):
        self.data = {}
        self.streams = {}
        self._ft = MagicMock()

    async def xadd(self, stream_key, entry):
        if stream_key not in self.streams:
            self.streams[stream_key] = []
        entry_id = f"{time.time_ns()}-0"
        self.streams[stream_key].append((entry_id, entry))
        return entry_id

    async def xrange(self, stream_key):
        return self.streams.get(stream_key, [])

    async def hset(self, key, field, value):
        if key not in self.data:
            self.data[key] = {}
        self.data[key][field] = value
        return 1

    async def keys(self, pattern):
        return [k for k in self.data.keys() if k.startswith(pattern.replace("*", ""))]

    def ft(self, index_name):
        return self._ft

def test_router_node_run():
    router = RouterNode(
        node_id="test_router",
        params={
            "decision_key": "needs_search",
            "routing_map": {
                "true": ["search"],
                "false": ["answer"]
            }
        },
        memory_logger=RedisMemoryLogger(FakeRedisClient())
    )
    output = router.run({"previous_outputs": {"needs_search": "true"}})
    assert output == ["search"]

def test_router_node_no_condition():
    router = RouterNode(
        node_id="test_router",
        params={
            "decision_key": "needs_search",
            "routing_map": {
                "true": ["search"],
                "false": ["answer"]
            }
        },
        memory_logger=RedisMemoryLogger(FakeRedisClient())
    )
    output = router.run({"previous_outputs": {"needs_search": "unknown"}})
    assert output == []  # Returns empty list for no matching condition

def test_router_node_invalid_condition():
    router = RouterNode(
        node_id="test_router",
        params={
            "decision_key": "needs_search",
            "routing_map": {
                "true": ["search"],
                "false": ["answer"]
            }
        },
        memory_logger=RedisMemoryLogger(FakeRedisClient())
    )
    output = router.run({"previous_outputs": {}})
    assert output == []  # Returns empty list for no decision found

def test_router_node_validation():
    with pytest.raises(ValueError, match="requires 'params'"):
        RouterNode(
            node_id="test_router",
            params=None,
            memory_logger=RedisMemoryLogger(FakeRedisClient())
        )

def test_router_node_with_complex_condition():
    router = RouterNode(
        node_id="test_router",
        params={
            "decision_key": "test_key",
            "routing_map": {
                "condition1": "branch1",
                "condition2": "branch2",
                "default": "branch3"
            }
        },
        memory_logger=RedisMemoryLogger(FakeRedisClient())
    )
    context = {
        "previous_outputs": {
            "test_key": "condition1"
        }
    }
    result = router.run(context)
    assert result == "branch1"

def test_failover_node_run():
    failing_child = FailingNode(node_id="fail", prompt="Broken", queue="test")
    backup_child = DuckDuckGoAgent(agent_id="backup", prompt="Search", queue="test")
    failover = FailoverNode(node_id="test_failover", children=[failing_child, backup_child], queue="test")
    output = failover.run({"input": "OrKa orchestrator"})
    assert isinstance(output, dict)
    assert "backup" in output
    
@pytest.mark.asyncio
async def test_fork_node_run():
    memory = RedisMemoryLogger(FakeRedisClient())
    fork_node = ForkNode(
        node_id="test_fork",
        targets=[
            ["branch1", "branch2"],
            ["branch3", "branch4"]
        ],
        memory_logger=memory
    )
    orchestrator = MagicMock()
    context = {"previous_outputs": {}}
    result = await fork_node.run(orchestrator=orchestrator, context=context)
    assert result["status"] == "forked"
    assert "fork_group" in result

@pytest.mark.asyncio
async def test_fork_node_empty_targets():
    memory = RedisMemoryLogger(FakeRedisClient())
    fork_node = ForkNode(
        node_id="test_fork",
        targets=[],
        memory_logger=memory
    )
    orchestrator = MagicMock()
    context = {"previous_outputs": {}}
    with pytest.raises(ValueError, match="requires non-empty 'targets'"):
        await fork_node.run(orchestrator=orchestrator, context=context)

@pytest.mark.asyncio
async def test_join_node_run():
    memory = RedisMemoryLogger(FakeRedisClient())
    join_node = JoinNode(
        node_id="test_join",
        group="test_fork",
        memory_logger=memory,
        prompt="Test prompt",
        queue="test_queue"
    )
    input_data = {"previous_outputs": {}}
    result = join_node.run(input_data)
    assert result["status"] in ["waiting", "done", "timeout"]
    if result["status"] == "done":
        assert "merged" in result

def test_join_node_initialization():
    join_node = JoinNode(
        node_id="test_join",
        group="test_fork",
        memory_logger=RedisMemoryLogger(FakeRedisClient()),
        prompt="Test prompt",
        queue="test_queue"
    )
    assert join_node.group_id == "test_fork"

@pytest.mark.asyncio
async def test_fork_node_with_nested_targets():
    memory = RedisMemoryLogger(FakeRedisClient())
    fork_node = ForkNode(
        node_id="test_fork",
        targets=[
            ["branch1", "branch2"],
            ["branch3", "branch4"]
        ],
        memory_logger=memory
    )
    orchestrator = MagicMock()
    context = {"previous_outputs": {}}
    result = await fork_node.run(orchestrator=orchestrator, context=context)
    assert result["status"] == "forked"
    assert "fork_group" in result

@pytest.mark.asyncio
async def test_join_node_with_empty_results():
    memory = RedisMemoryLogger(FakeRedisClient())
    join_node = JoinNode(
        node_id="test_join",
        group="test_fork",
        memory_logger=memory,
        prompt="Test prompt",
        queue="test_queue"
    )
    input_data = {"previous_outputs": {}}
    result = join_node.run(input_data)
    assert result["status"] in ["waiting", "done", "timeout"]
    if result["status"] == "done":
        assert "merged" in result

@pytest.mark.asyncio
async def test_memory_writer_node_stream():
    """Test MemoryWriterNode writes to stream correctly."""
    redis_client = MockRedisClient()
    writer = MemoryWriterNode(
        node_id="test_writer",
        vector=False
    )
    writer.redis = redis_client
    
    context = {
        "input": "test memory content",
        "session_id": "test_session",
        "metadata": {"source": "test"}
    }
    
    result = await writer.run(context)
    assert result["status"] == "success"
    assert result["session"] == "test_session"
    
    # Verify stream entry
    stream_key = "orka:memory:test_session"
    entries = await redis_client.xrange(stream_key)
    assert len(entries) == 1
    entry_id, data = entries[0]
    payload = json.loads(data["payload"])
    assert payload["content"] == "test memory content"
    assert payload["metadata"]["source"] == "test"

@pytest.mark.asyncio
async def test_memory_writer_node_vector():
    """Test MemoryWriterNode writes to vector store when enabled."""
    redis_client = MockRedisClient()
    writer = MemoryWriterNode(
        node_id="test_writer",
        vector=True,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    writer.redis = redis_client
    
    context = {
        "input": "test vector content",
        "session_id": "test_session"
    }
    
    result = await writer.run(context)
    assert result["status"] == "success"
    
    # Verify vector store entry
    keys = await redis_client.keys("mem:*")
    assert len(keys) == 1

@pytest.mark.asyncio
async def test_memory_reader_node():
    """Test MemoryReaderNode reads from stream correctly."""
    redis_client = MockRedisClient()
    reader = MemoryReaderNode(
        node_id="test_reader",
        limit=5
    )
    reader.redis = redis_client
    
    # Pre-populate stream with test data
    stream_key = "orka:memory:test_session"
    for i in range(3):
        entry = {
            "ts": str(time.time_ns()),
            "agent_id": "test_writer",
            "type": "memory.append",
            "session": "test_session",
            "payload": json.dumps({
                "content": f"test content {i}",
                "metadata": {"index": i}
            })
        }
        await redis_client.xadd(stream_key, entry)
    
    context = {"session_id": "test_session"}
    result = await reader.run(context)
    
    assert result["status"] == "success"
    assert len(result["memories"]) == 3
    assert all("content" in mem for mem in result["memories"])
    assert all("metadata" in mem for mem in result["memories"])

@pytest.mark.asyncio
async def test_rag_node():
    """Test RAGNode performs vector similarity search."""
    redis_client = MockRedisClient()
    rag = RAGNode(
        node_id="test_rag",
        top_k=3,
        score_threshold=0.75
    )
    rag.redis = redis_client
    
    # Set up mock search result
    mock_doc = MagicMock()
    mock_doc.content = "test content"
    mock_doc.score = 0.5
    mock_doc.ts = str(int(time.time() * 1e3))
    
    # Create an async mock for the search method
    async def mock_search(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.docs = [mock_doc]
        return mock_result
    
    redis_client._ft.search = AsyncMock(side_effect=mock_search)
    
    context = {
        "input": "test query",
        "session_id": "test_session"
    }
    
    result = await rag.run(context)
    
    assert result["status"] == "success"
    assert len(result["hits"]) == 1
    assert result["hits"][0]["content"] == "test content"
    assert result["hits"][0]["score"] == 0.5

@pytest.mark.asyncio
async def test_memory_nodes_error_handling():
    """Test error handling in memory nodes."""
    redis_client = MockRedisClient()
    
    # Test writer with invalid input
    writer = MemoryWriterNode(node_id="test_writer")
    writer.redis = redis_client
    result = await writer.run({})
    assert result["status"] == "success"  # Should handle empty input gracefully
    
    # Test reader with non-existent session
    reader = MemoryReaderNode(node_id="test_reader")
    reader.redis = redis_client
    result = await reader.run({"session_id": "non_existent"})
    assert result["status"] == "success"
    assert result["memories"] == []
    
    # Test RAG with empty query
    rag = RAGNode(node_id="test_rag")
    rag.redis = redis_client
    result = await rag.run({})
    assert result["status"] == "success"
    assert result["hits"] == []