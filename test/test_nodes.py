import pytest
import json
from orka.nodes.router_node import RouterNode
from orka.nodes.failover_node import FailoverNode
from orka.nodes.failing_node import FailingNode
from orka.nodes.join_node import JoinNode
from orka.nodes.fork_node import ForkNode
from orka.agents.google_duck_agents import DuckDuckGoAgent
from orka.memory_logger import RedisMemoryLogger


def test_router_node_run():
    router = RouterNode(node_id="test_router", params={"decision_key": "needs_search", "routing_map": {"true": ["search"], "false": ["answer"]}}, queue="test")
    output = router.run({"previous_outputs": {"needs_search": "true"}})
    assert output == ["search"]

def test_failover_node_run():
    failing_child = FailingNode(node_id="fail", prompt="Broken", queue="test")
    backup_child = DuckDuckGoAgent(agent_id="backup", prompt="Search", queue="test")
    failover = FailoverNode(node_id="test_failover", children=[failing_child, backup_child], queue="test")
    output = failover.run({"input": "OrKa orchestrator"})
    assert isinstance(output, dict)
    assert "backup" in output
    
@pytest.mark.asyncio
async def test_fork_node_run(monkeypatch):
    memory = RedisMemoryLogger()

    # Patch client with fake Redis
    fake_redis_store = {}
    memory.client = type('', (), {
        "sadd": lambda _, key, *vals: fake_redis_store.setdefault(key, set()).update(vals),
        "scard": lambda _, key: len(fake_redis_store.get(key, set())),
        "smembers": lambda _, key: list(fake_redis_store.get(key, set())),
        "set": lambda _, key, val: fake_redis_store.__setitem__(key, val),
        "get": lambda _, key: fake_redis_store.get(key),
        "hset": lambda _, key, field, val: fake_redis_store.setdefault(key, {}).update({field: val}),
        "hget": lambda _, key, field: fake_redis_store[key][field],
        "hkeys": lambda _, key: list(fake_redis_store.get(key, {}).keys()),
        "delete": lambda _, key: fake_redis_store.pop(key, None),
        "xadd": lambda _, stream, data: fake_redis_store.setdefault(stream, []).append(data),
    })()

    # Initialize ForkNode
    fork_node = ForkNode(
        node_id="fork_test",
        prompt=None,
        queue="test_queue",
        memory_logger=memory,
        targets=["agentA", "agentB", "agentC"],
        mode="sequential",  # or "parallel" if you already implemented parallel fork
    )

      # Fake ForkGroupManager
    class FakeForkGroupManager:
        def __init__(self):
            self.redis = fake_redis_store  
        def generate_group_id(self, base_id):
            return f"{base_id}_testgroup"
        def create_group(self, fork_group_id, agent_ids):
            self.redis.setdefault(f"fork_group:{fork_group_id}", set()).update(agent_ids)

    # Simulate orchestrator object
    class FakeOrchestrator:
        def __init__(self):
            self.queue = []
            self.fork_manager = FakeForkGroupManager()
        def enqueue_fork(self, agent_ids, fork_group_id):
            self.queue = agent_ids + self.queue

    orchestrator = FakeOrchestrator()

    # Initialize ForkNode
    fork_node = ForkNode(
        node_id="fork_test",
        prompt=None,
        queue="test_queue",
        memory_logger=memory,
        targets=["agentA", "agentB", "agentC"],
        mode="sequential",
    )

    # Run fork node
    payload = {"input": "test input"}
    result = await fork_node.run(orchestrator, payload)

    # Assertions
    assert result["status"] == "forked"
    assert "fork_group" in result
    fork_group_id = result["fork_group"]

    # Check fork group was created
    assert f"fork_group:{fork_group_id}" in fake_redis_store
    assert set(fake_redis_store[f"fork_group:{fork_group_id}"]) == {"agentA", "agentB", "agentC"}

    # Check agents are queued
    assert orchestrator.queue == ["agentA", "agentB", "agentC"]
    
@pytest.mark.asyncio
async def test_waitfor_node_run(monkeypatch):
    memory = RedisMemoryLogger()

    # Patch client with fake Redis
    fake_redis = {}
    memory.client = type('', (), {
        "hset": lambda _, key, field, val: fake_redis.setdefault(key, {}).update({field: val}),
        "hkeys": lambda _, key: list(fake_redis.get(key, {}).keys()),
        "hget": lambda _, key, field: fake_redis[key][field],
        "set": lambda _, key, val: fake_redis.__setitem__(key, val),
        "delete": lambda _, key: fake_redis.pop(key, None),
        "xadd": lambda _, stream, data: fake_redis.setdefault(stream, []).append(data),
        "smembers": lambda _, key: list(fake_redis.get(key, {}).keys()),  # ✅ add smembers
    })()

    # Manually create the fake fork group
    fake_redis["fork_group:test_wait"] = {"agent1": "", "agent2": ""}

    wait_node = JoinNode(node_id="test_wait", prompt=None, queue="test", memory_logger=memory, group="test_wait")
    
    
    memory.client.hset(wait_node.state_key, "agent1", json.dumps("yes"))
    payload = {"previous_outputs": {"agent1": "yes"}}
    waiting = wait_node.run(payload)
    assert waiting["status"] == "waiting"  # ✅ Now it will WAIT correctly
    
    memory.client.hset(wait_node.state_key, "agent2", json.dumps("confirmed"))
    payload2 = {"previous_outputs": {"agent2": "confirmed"}}
    done = wait_node.run(payload2)
    assert done["status"] == "done"
    assert "agent1" in done["merged"]
    assert "agent2" in done["merged"]

