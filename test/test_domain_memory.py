# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import asyncio
import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest
from fake_redis import FakeRedisClient

from orka.memory_logger import RedisMemoryLogger
from orka.nodes.memory_reader_node import MemoryReaderNode
from orka.nodes.memory_writer_node import MemoryWriterNode

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Memory System Tests
@pytest.mark.asyncio
async def test_memory_system():
    """Test the memory system with various query variations."""
    # Initialize nodes
    writer = MemoryWriterNode("test_writer")
    reader = MemoryReaderNode("test_reader", namespace="test_namespace")

    # Test content
    content = "Artificial Intelligence was born in 1956 at the Dartmouth Conference where the term was coined by John McCarthy."

    # Write to memory
    logger.info(f"Writing content to memory: {content[:50]}...")
    write_result = await writer.run(
        {"input": content, "session_id": "test_session", "namespace": "test_namespace"},
    )
    logger.info(f"Write result: {write_result}")

    # Verify write was successful
    assert write_result["status"] == "success"

    # Give a moment for Redis to update
    await asyncio.sleep(1)

    # Test different query variations
    test_queries = [
        "When did AI born",
        "When was AI created",
        "When was artificial intelligence invented",
        "Who created AI",
        "AI history",
        "origin of artificial intelligence",
    ]

    # Need at least one successful memory retrieval for the test to pass
    found_at_least_one = False

    for query in test_queries:
        logger.info(f"\nTesting query: '{query}'")
        read_result = await reader.run(
            {
                "input": query,
                "session_id": "test_session",
                "namespace": "test_namespace",
            },
        )

        # Ensure the read operation was successful
        assert read_result["status"] == "success"

        if read_result.get("memories") == "NONE":
            logger.warning(f"❌ No memory found for query: '{query}'")
        else:
            logger.info(f"✅ Memory found for query: '{query}'")
            found_at_least_one = True
            for i, memory in enumerate(read_result.get("memories", [])):
                logger.info(f"  Memory {i + 1}:")
                logger.info(f"    Content: {memory.get('content', '')[:50]}...")
                logger.info(f"    Similarity: {memory.get('similarity', 0):.4f}")
                logger.info(f"    Match type: {memory.get('match_type', 'unknown')}")

    # At least one query should find the memory
    assert found_at_least_one, "No memories were found for any query variations"


# Memory Logger Tests
@pytest.fixture
def redis_client():
    return FakeRedisClient()


@pytest.fixture
def memory_logger(redis_client):
    return RedisMemoryLogger(redis_client)


def test_memory_logger_initialization(memory_logger):
    assert memory_logger.redis is not None


def test_memory_logger_log_event(memory_logger):
    event_type = "test_event"
    payload = {
        "agent_id": "test_agent",
        "timestamp": time.time(),
        "data": {"test": "data"},
    }
    memory_logger.log(agent_id="test_agent", event_type=event_type, payload=payload)

    # Verify event was stored in Redis stream
    events = memory_logger.redis.xrevrange("orka:memory", count=1)
    assert len(events) == 1
    event = events[0]
    assert event["agent_id"] == "test_agent"
    assert event["event_type"] == event_type
    assert json.loads(event["payload"])["data"]["test"] == "data"


def test_memory_logger_log_multiple_events(memory_logger):
    events = [
        (
            "event1",
            {"agent_id": "agent1", "timestamp": time.time(), "data": {"test": "data1"}},
        ),
        (
            "event2",
            {"agent_id": "agent2", "timestamp": time.time(), "data": {"test": "data2"}},
        ),
    ]

    for event_type, payload in events:
        memory_logger.log(
            agent_id=payload["agent_id"],
            event_type=event_type,
            payload=payload,
        )

    # Verify events were stored in Redis stream
    stored_events = memory_logger.redis.xrevrange("orka:memory", count=2)
    assert len(stored_events) == 2
    assert stored_events[0]["agent_id"] == "agent2"
    assert stored_events[1]["agent_id"] == "agent1"
    assert json.loads(stored_events[0]["payload"])["data"]["test"] == "data2"
    assert json.loads(stored_events[1]["payload"])["data"]["test"] == "data1"


def test_memory_logger_clear_events(memory_logger):
    event_type = "test_event"
    payload = {
        "agent_id": "test_agent",
        "timestamp": time.time(),
        "data": {"test": "data"},
    }
    memory_logger.log(agent_id="test_agent", event_type=event_type, payload=payload)

    # Clear events by deleting the stream
    memory_logger.redis.delete("orka:memory")

    # Verify events were cleared
    events = memory_logger.redis.xrevrange("orka:memory", count=1)
    assert len(events) == 0


def test_memory_logger_invalid_event(memory_logger):
    # Clear any existing events
    memory_logger.redis.delete("orka:memory")

    with pytest.raises(ValueError, match="Event must contain 'agent_id'"):
        memory_logger.log(
            agent_id="",
            event_type="test_event",
            payload={"data": "test"},
        )


def test_memory_logger_get_events_by_agent(memory_logger):
    # Clear any existing events
    memory_logger.redis.delete("orka:memory")

    events = [
        (
            "event1",
            {"agent_id": "agent1", "timestamp": time.time(), "data": {"test": "data1"}},
        ),
        (
            "event2",
            {"agent_id": "agent2", "timestamp": time.time(), "data": {"test": "data2"}},
        ),
        (
            "event3",
            {"agent_id": "agent1", "timestamp": time.time(), "data": {"test": "data3"}},
        ),
    ]

    for event_type, payload in events:
        memory_logger.log(
            agent_id=payload["agent_id"],
            event_type=event_type,
            payload=payload,
        )

    # Get all events and filter by agent
    all_events = memory_logger.redis.xrevrange("orka:memory", count=3)
    agent1_events = [e for e in all_events if e["agent_id"] == "agent1"]
    assert len(agent1_events) == 2
    assert all(json.loads(e["payload"])["agent_id"] == "agent1" for e in agent1_events)


def test_memory_logger_get_latest_event(memory_logger):
    # Clear any existing events
    memory_logger.redis.delete("orka:memory")

    events = [
        {"agent_id": "agent1", "timestamp": time.time(), "data": {"test": "data1"}},
        {
            "agent_id": "agent1",
            "timestamp": time.time() + 1,  # Ensure second event is later
            "data": {"test": "data2"},
        },
    ]

    for event in events:
        memory_logger.log(agent_id="agent1", event_type="event_type", payload=event)

    # Get latest event from stream
    all_events = memory_logger.redis.xrevrange("orka:memory", count=2)
    agent1_events = [e for e in all_events if e["agent_id"] == "agent1"]
    latest_event = agent1_events[0]  # First event in xrevrange is the latest
    assert json.loads(latest_event["payload"])["data"]["test"] == "data2"


def test_memory_logger_get_latest_event_nonexistent(memory_logger):
    # Clear any existing events
    memory_logger.redis.delete("orka:memory")

    # Get events for nonexistent agent
    events = memory_logger.redis.xrevrange("orka:memory", count=1)
    assert len(events) == 0


def test_memory_logger_redis_connection_error():
    with patch(
        "orka.memory.redis_logger.redis.from_url",
        side_effect=Exception("Connection error"),
    ):
        with pytest.raises(Exception):
            RedisMemoryLogger("redis://localhost:6379")


def test_memory_logger_redis_operation_error():
    # Create a mock Redis client
    mock_redis = MagicMock()
    mock_redis.xadd = MagicMock(side_effect=Exception("Redis error"))

    # Create memory logger with the mock
    memory_logger = RedisMemoryLogger(mock_redis)
    memory_logger.client = mock_redis  # Ensure we're using the mock client

    event_type = "test_event"
    payload = {
        "agent_id": "test_agent",
        "timestamp": time.time(),
        "data": {"test": "data"},
    }

    # The memory logger now catches exceptions rather than propagating them
    # so we just check that the call doesn't raise an exception
    memory_logger.log(agent_id="test_agent", event_type=event_type, payload=payload)

    # Verify xadd was called at least once (memory logger tries fallback, so it's called twice)
    assert mock_redis.xadd.call_count >= 1


def test_memory_logger_event_serialization(memory_logger):
    # Clear any existing events
    memory_logger.redis.delete("orka:memory")

    event_type = "test_event"
    payload = {
        "agent_id": "test_agent",
        "timestamp": time.time(),
        "data": {"nested": {"complex": [1, 2, 3], "object": {"key": "value"}}},
    }

    memory_logger.log(agent_id="test_agent", event_type=event_type, payload=payload)

    # Verify event was stored in Redis stream
    events = memory_logger.redis.xrevrange("orka:memory", count=1)
    assert len(events) == 1
    event = events[0]
    stored_payload = json.loads(event["payload"])
    assert stored_payload["data"]["nested"]["complex"] == [1, 2, 3]
    assert stored_payload["data"]["nested"]["object"]["key"] == "value"
