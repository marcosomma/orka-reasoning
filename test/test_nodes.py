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
from orka.nodes.router_node import RouterNode
from orka.nodes.failover_node import FailoverNode
from orka.nodes.failing_node import FailingNode
from orka.nodes.join_node import JoinNode
from orka.nodes.fork_node import ForkNode
from orka.agents.google_duck_agents import DuckDuckGoAgent
from orka.memory_logger import RedisMemoryLogger
from fake_redis import FakeRedisClient
from unittest.mock import MagicMock, patch



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