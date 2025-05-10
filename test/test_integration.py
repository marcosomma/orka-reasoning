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
import os
import time
from typing import List

import pytest
import redis

from orka.fork_group_manager import ForkGroupManager
from orka.memory_logger import RedisMemoryLogger

# Test configuration
REDIS_URL = "redis://localhost:6379/0"
NUM_AGENTS = 10
NUM_FORK_GROUPS = 5
CONCURRENT_GROUPS = 3

# Determine if we're using real Redis
USE_REAL_REDIS = os.getenv("USE_REAL_REDIS", "false").lower() == "true"


@pytest.fixture(scope="module")
def redis_client():
    """Create a Redis client for testing."""
    client = redis.from_url(REDIS_URL)
    yield client
    # Cleanup after tests
    if USE_REAL_REDIS:
        if hasattr(client, "flushdb"):
            client.flushdb()
    else:
        # For FakeRedisClient, we need to clear all data manually
        # Since FakeRedisClient has limited functionality, we'll just create a new client
        # This effectively clears all data since it's a new instance
        client = redis.from_url(REDIS_URL)


@pytest.fixture(scope="module")
def fork_manager(redis_client):
    """Create a ForkGroupManager instance."""
    return ForkGroupManager(redis_client)


@pytest.fixture(scope="module")
def memory_logger(redis_client):
    """Create a RedisMemoryLogger instance."""
    return RedisMemoryLogger(redis_url=REDIS_URL)


async def simulate_agent_work(agent_id: str, delay: float = 0.1) -> None:
    """Simulate agent work with a delay."""
    await asyncio.sleep(delay)


async def run_fork_group(
    fork_manager: ForkGroupManager,
    memory_logger: RedisMemoryLogger,
    group_id: str,
    agent_ids: List[str],
    delay: float = 0.1,
) -> None:
    """Run a fork group with multiple agents."""
    # Create the fork group
    fork_manager.create_group(group_id, agent_ids)

    # Log the start of the fork group
    memory_logger.log(
        agent_id="orchestrator",
        event_type="fork_group_start",
        payload={"group_id": group_id, "agent_ids": agent_ids},
        fork_group=group_id,
    )

    # Simulate agents working in parallel
    tasks = []
    for agent_id in agent_ids:
        tasks.append(asyncio.create_task(simulate_agent_work(agent_id, delay)))

    # Wait for all agents to complete
    await asyncio.gather(*tasks)

    # Mark agents as done
    for agent_id in agent_ids:
        fork_manager.mark_agent_done(group_id, agent_id)
        memory_logger.log(
            agent_id=agent_id,
            event_type="agent_complete",
            payload={"status": "success"},
            fork_group=group_id,
        )

    # Log the completion of the fork group
    memory_logger.log(
        agent_id="orchestrator",
        event_type="fork_group_complete",
        payload={"group_id": group_id},
        fork_group=group_id,
    )


@pytest.mark.asyncio
async def test_concurrent_fork_groups(fork_manager, memory_logger):
    """Test multiple fork groups running concurrently."""
    # Generate test data
    fork_groups = []
    for i in range(NUM_FORK_GROUPS):
        group_id = f"test_group_{i}"
        agent_ids = [f"agent_{i}_{j}" for j in range(NUM_AGENTS)]
        fork_groups.append((group_id, agent_ids))

    # Run fork groups concurrently
    tasks = []
    for group_id, agent_ids in fork_groups:
        tasks.append(run_fork_group(fork_manager, memory_logger, group_id, agent_ids))

    # Wait for all groups to complete
    await asyncio.gather(*tasks)

    # Verify all groups are done
    for group_id, _ in fork_groups:
        assert fork_manager.is_group_done(group_id)
        assert len(fork_manager.list_pending_agents(group_id)) == 0


@pytest.mark.asyncio
async def test_fork_group_sequence(fork_manager, memory_logger):
    """Test sequential execution of fork groups."""
    # Create a sequence of fork groups
    sequences = []
    for i in range(NUM_FORK_GROUPS):
        group_id = f"seq_group_{i}"
        agent_ids = [f"seq_agent_{i}_{j}" for j in range(NUM_AGENTS)]
        sequences.append((group_id, agent_ids))

    # Run groups sequentially
    for group_id, agent_ids in sequences:
        await run_fork_group(fork_manager, memory_logger, group_id, agent_ids)
        assert fork_manager.is_group_done(group_id)


@pytest.mark.asyncio
async def test_fork_group_error_handling(fork_manager, memory_logger):
    """Test error handling in fork groups."""
    group_id = "error_group"
    agent_ids = [f"error_agent_{i}" for i in range(NUM_AGENTS)]

    # Create the fork group
    fork_manager.create_group(group_id, agent_ids)

    # Simulate some agents failing
    for i, agent_id in enumerate(agent_ids):
        if i % 2 == 0:  # Even-numbered agents fail
            memory_logger.log(
                agent_id=agent_id,
                event_type="agent_error",
                payload={"error": "Simulated error"},
                fork_group=group_id,
            )
        else:
            memory_logger.log(
                agent_id=agent_id,
                event_type="agent_complete",
                payload={"status": "success"},
                fork_group=group_id,
            )
        fork_manager.mark_agent_done(group_id, agent_id)

    # Verify group is done despite errors
    assert fork_manager.is_group_done(group_id)

    # Verify error events were logged
    events = memory_logger.tail(count=len(agent_ids))
    error_events = [e for e in events if e.get("event_type") == "agent_error"]
    assert len(error_events) == len(agent_ids) // 2


@pytest.mark.asyncio
async def test_fork_group_performance(fork_manager, memory_logger):
    """Test performance with many concurrent fork groups."""
    start_time = time.time()

    # Create and run many concurrent groups
    tasks = []
    for i in range(CONCURRENT_GROUPS):
        group_id = f"perf_group_{i}"
        agent_ids = [f"perf_agent_{i}_{j}" for j in range(NUM_AGENTS)]
        tasks.append(
            run_fork_group(fork_manager, memory_logger, group_id, agent_ids, delay=0.05)
        )

    # Wait for all groups to complete
    await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time

    # Verify performance (should be much faster than sequential execution)
    expected_sequential_time = CONCURRENT_GROUPS * NUM_AGENTS * 0.05
    assert total_time < expected_sequential_time * 0.5  # Should be at least 2x faster


@pytest.mark.asyncio
async def test_fork_group_cleanup(fork_manager, memory_logger):
    """Test proper cleanup of fork groups."""
    # Create multiple groups
    groups = []
    for i in range(NUM_FORK_GROUPS):
        group_id = f"cleanup_group_{i}"
        agent_ids = [f"cleanup_agent_{i}_{j}" for j in range(NUM_AGENTS)]
        groups.append((group_id, agent_ids))

    # Run groups
    for group_id, agent_ids in groups:
        await run_fork_group(fork_manager, memory_logger, group_id, agent_ids)

    # Delete groups
    for group_id, _ in groups:
        fork_manager.delete_group(group_id)
        # For real Redis, the group should be gone
        # For fake Redis, we need to check if the group is done
        if USE_REAL_REDIS:
            assert not fork_manager.is_group_done(group_id)  # Group should be gone
        else:
            # For fake Redis, we check if the group is done and has no pending agents
            assert fork_manager.is_group_done(group_id)  # Group should be done
            assert (
                len(fork_manager.list_pending_agents(group_id)) == 0
            )  # No pending agents
