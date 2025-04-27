import pytest
import json
from orka.nodes.router_node import RouterNode
from orka.nodes.failover_node import FailoverNode
from orka.nodes.failing_node import FailingNode
from orka.nodes.join_node import JoinNode
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

