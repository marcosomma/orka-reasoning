# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
import json

import pytest

from orka.fork_group_manager import ForkGroupManager
from orka.memory_logger import RedisMemoryLogger
from orka.nodes.fork_node import ForkNode
from orka.nodes.join_node import JoinNode
from orka.nodes.router_node import RouterNode

# --- ForkGroupManager uncovered branches ---


def test_fork_group_manager_list_pending_agents_decodes_bytes():
    class FakeRedis:
        def smembers(self, key):
            return [b"agent1", b"agent2"]

    mgr = ForkGroupManager(FakeRedis())
    assert mgr.list_pending_agents("group") == ["agent1", "agent2"]


def test_fork_group_manager_next_in_sequence_returns_none():
    class FakeRedis:
        def hget(self, key, agent_id):
            return None

    mgr = ForkGroupManager(FakeRedis())
    assert mgr.next_in_sequence("group", "agent") is None


def test_fork_group_manager_track_branch_sequence_and_next():
    class FakeRedis:
        def __init__(self):
            self.data = {}

        def hset(self, key, current, next_one):
            self.data[(key, current)] = next_one

        def hget(self, key, agent_id):
            return self.data.get((key, agent_id), None)

    mgr = ForkGroupManager(FakeRedis())
    mgr.track_branch_sequence("group", ["a", "b", "c"])
    # Should set a->b and b->c
    assert mgr.redis.data[("fork_branch:group", "a")] == "b"
    assert mgr.redis.data[("fork_branch:group", "b")] == "c"


# --- RouterNode uncovered branches ---


def test_router_node_bool_key_variants():
    node = RouterNode(
        node_id="test",
        params={"decision_key": "d", "routing_map": {True: ["yes"], False: ["no"]}},
        queue="test",
    )
    # Should match True
    assert node.run({"previous_outputs": {"d": "true"}}) == ["yes"]
    # Should match False
    assert node.run({"previous_outputs": {"d": "no"}}) == ["no"]
    # Should fallback to val
    assert node._bool_key("maybe") == "maybe"


# --- ForkNode uncovered error branch ---


@pytest.mark.asyncio
async def test_fork_node_raises_on_no_targets():
    memory = RedisMemoryLogger()
    fork_node = ForkNode(
        node_id="fork_test", prompt=None, queue="test", memory_logger=memory
    )

    class DummyOrchestrator:
        fork_manager = None

        def enqueue_fork(self, *a, **k):
            pass

    with pytest.raises(ValueError, match="requires non-empty 'targets'"):
        await fork_node.run(DummyOrchestrator(), {})


# --- JoinNode._complete uncovered code ---


def test_join_node_complete_merges_and_cleans():
    class FakeMemoryLogger:
        def __init__(self):
            self._h = {"agentA": json.dumps("foo"), "agentB": json.dumps("bar")}
            self.redis = self
            self.deleted = []
            self.set_keys = []

        def hget(self, state_key, agent_id):
            return self._h[agent_id]

        def set(self, key, val):
            self.set_keys.append((key, val))

        def delete(self, key):
            self.deleted.append(key)

    join = JoinNode(
        node_id="join",
        prompt=None,
        queue="test",
        memory_logger=FakeMemoryLogger(),
        group=None,
    )
    result = join._complete(["agentA", "agentB"], "state_key")
    assert result["status"] == "done"
    assert "agentA" in result["merged"]
    assert "agentB" in result["merged"]


# --- RedisMemoryLogger uncovered methods ---


def test_memory_logger_hdel_and_smembers():
    logger = RedisMemoryLogger()

    # Patch client with dict
    class FakeClient:
        def __init__(self):
            self.h = {"foo": {"a": 1, "b": 2}}
            self.s = {"bar": set(["x", "y"])}

        def hdel(self, name, *keys):
            for k in keys:
                self.h[name].pop(k, None)
            return len(keys)

        def smembers(self, name):
            return self.s[name]

    logger.client = FakeClient()
    assert logger.hdel("foo", "a", "b") == 2
    assert logger.smembers("bar") == set(["x", "y"])
