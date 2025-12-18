import pytest
from types import SimpleNamespace

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.fixture
def engine(temp_config_file):
    eng = ExecutionEngine(temp_config_file)
    from unittest.mock import MagicMock

    eng.memory = SimpleNamespace()
    eng.memory.hset = MagicMock()
    eng.memory.set = MagicMock()
    eng.memory.log = MagicMock()
    eng.memory.get_memory_stats = MagicMock(return_value={"count": 0})
    eng.memory.save_enhanced_trace = MagicMock()
    # Provide a simple fork_manager stub
    eng.fork_manager = SimpleNamespace()
    eng.fork_manager.mark_agent_done = lambda fg, aid: None
    eng.fork_manager.next_in_sequence = lambda fg, aid: None
    return eng


@pytest.mark.asyncio
async def test_parallel_executor_writes_join_and_group_hashes(engine):
    class AgentA:
        def __init__(self):
            self.type = "simple"

        async def run(self, payload):
            return {"response": "A", "confidence": "0.9"}

    class AgentB:
        def __init__(self):
            self.type = "simple"

        async def run(self, payload):
            return {"response": "B", "confidence": "0.8"}

    engine.agents = {"a": AgentA(), "b": AgentB()}

    results = await engine._parallel_executor.run_parallel_agents(["a", "b"], "fork_group_1", "input", {})

    # Should have created logs for both agents
    assert any(r["agent_id"] == "a" for r in results if r["event_type"].startswith("ForkedAgent-"))
    assert any(r["agent_id"] == "b" for r in results if r["event_type"].startswith("ForkedAgent-"))

    calls = [c.args for c in engine.memory.hset.call_args_list]

    group_key = "fork_group_results:fork_group_1"
    join_key = "waitfor:join_parallel_checks:inputs"

    assert any(call[0] == group_key and call[1] == "a" for call in calls)
    assert any(call[0] == group_key and call[1] == "b" for call in calls)
    assert any(call[0] == join_key and call[1] == "a" for call in calls)
    assert any(call[0] == join_key and call[1] == "b" for call in calls)
