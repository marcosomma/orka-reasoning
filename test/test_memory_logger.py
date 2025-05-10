# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fake_redis import FakeRedisClient

from orka.memory_logger import RedisMemoryLogger


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
            agent_id=payload["agent_id"], event_type=event_type, payload=payload
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
            agent_id="", event_type="test_event", payload={"data": "test"}
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
            agent_id=payload["agent_id"], event_type=event_type, payload=payload
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
        "orka.memory_logger.redis.from_url", side_effect=Exception("Connection error")
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
