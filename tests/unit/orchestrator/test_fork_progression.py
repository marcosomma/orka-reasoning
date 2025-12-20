import json
import pytest
from unittest.mock import MagicMock, Mock

from orka.orchestrator.execution.response_processor import ResponseProcessor


@pytest.mark.asyncio
async def test_mark_done_and_enqueue_next_in_sequence(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 1
    eng.run_id = "run_test"

    mem = MagicMock()
    # Simulate fork group lookup for this agent
    mem.hget.return_value = "fg1"
    eng.memory = mem

    eng.fork_manager = Mock()
    eng.fork_manager.next_in_sequence.return_value = "agent_next"
    eng.fork_manager.mark_agent_done = Mock()
    eng.enqueue_fork = Mock()

    rp = ResponseProcessor(eng)

    class DummyAgent:
        pass

    agent = DummyAgent()

    logs = []
    log_entry = {"agent_id": "agent1", "payload": {}}

    payload_out = {"result": "ok"}

    handled = await rp.process(
        "agent1",
        "agent1",
        {"result": "ok"},
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is False
    eng.fork_manager.mark_agent_done.assert_called_once_with("fg1", "agent1")
    eng.enqueue_fork.assert_called_once_with(["agent_next"], "fg1")
    # Ensure join state and group results were updated with the final payload
    state_key = "waitfor:fg1:inputs"
    eng.memory.hset.assert_any_call(state_key, "agent1", json.dumps(payload_out, default=str))
    group_key = f"fork_group_results:fg1"
    eng.memory.hset.assert_any_call(group_key, "agent1", json.dumps(payload_out, default=str))
    # Ensure agent_result key for the fork group was set as well
    set_calls = [c for c in eng.memory.set.call_args_list]
    assert any("agent_result:fg1:agent1" in str(c) for c in set_calls)
