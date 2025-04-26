from orka.nodes.router_node import RouterNode
from orka.nodes.failover_node import FailoverNode
from orka.nodes.failing_node import FailingNode
from orka.nodes.wait_for_node import WaitForNode
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

def test_waitfor_node_run(monkeypatch):
    memory = RedisMemoryLogger()

    # Patch client instead of redis
    fake_redis = {}
    memory.client = type('', (), {
        "hset": lambda _, key, field, val: fake_redis.setdefault(key, {}).update({field: val}),
        "hkeys": lambda _, key: list(fake_redis.get(key, {}).keys()),
        "hget": lambda _, key, field: fake_redis[key][field],
        "set": lambda _, key, val: fake_redis.__setitem__(key, val),
        "delete": lambda _, key: fake_redis.pop(key, None),
        "xadd": lambda _, stream, data: fake_redis.setdefault(stream, []).append(data),
    })()


    wait_node = WaitForNode(node_id="test_wait", prompt=None, queue="test", memory_logger=memory, inputs=["agent1", "agent2"])
    payload = {"previous_outputs": {"agent1": "yes"}}
    waiting = wait_node.run(payload)
    assert waiting["status"] == "waiting"

    payload2 = {"previous_outputs": {"agent2": "confirmed"}}
    done = wait_node.run(payload2)
    assert done["status"] == "done"
    assert "agent1" in done["merged"]
    assert "agent2" in done["merged"]

