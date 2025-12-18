import json
from unittest.mock import MagicMock, AsyncMock

from orka.orchestrator.execution.response_processor import ResponseProcessor


import pytest

@pytest.mark.asyncio
async def test_process_logs_and_memory_storage(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 2
    eng.run_id = "run_test"

    # Simple memory mock
    mem = MagicMock()
    eng.memory = mem

    rp = ResponseProcessor(eng)

    class DummyAgent:
        pass

    agent = DummyAgent()

    logs = []
    log_entry = {"agent_id": "a1", "payload": {}}

    payload_out = {"result": "ok", "status": "success"}

    handled = await rp.process(
        "a1",
        "a1",
        {"result": "ok"},
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is False

    # memory.set should be called with JSON stringified payload
    mem.set.assert_called_once()
    key, value = mem.set.call_args[0]
    assert key == "agent_result:a1"
    # value should be a JSON string containing 'result'
    assert json.loads(value)["result"] == "ok"

    # log should be appended
    assert logs[-1]["payload"] == payload_out

    # memory.log should have been called
    mem.log.assert_called_once()


@pytest.mark.asyncio
async def test_process_handles_fork_and_runs_parallel(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 3
    eng.run_id = "run_test"

    mem = MagicMock()
    eng.memory = mem

    # stub run_parallel_agents
    fork_return = [{"agent_id": "forked", "payload": {"result": "v"}}]
    eng.run_parallel_agents = AsyncMock(return_value=fork_return)

    rp = ResponseProcessor(eng)

    class ForkAgent:
        pass

    agent = ForkAgent()
    agent.type = "forknode"

    logs = []
    log_entry = {"agent_id": "forker", "payload": {}}

    agent_result = {"result": {"fork_group": "fg1", "agents": ["a1", "a2"], "mode": "parallel"}}
    payload_out = {"result": "ok"}

    handled = await rp.process(
        "forker",
        "forker",
        agent_result,
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is True

    # initial fork log appended
    assert any(l["agent_id"] == "forker" for l in logs)

    # fork logs extended
    assert any(l.get("agent_id") == "forked" or l.get("agent_id") == "forked" for l in logs)

    # memory.log should be called at least once for the fork entry
    mem.log.assert_called()

    # run_parallel_agents should be called and previous_outputs should include the fork entry
    eng.run_parallel_agents.assert_called_once()
    args = eng.run_parallel_agents.call_args[0]
    assert args[0] == ["a1", "a2"]
    assert args[1] == "fg1"
    assert args[2] == {}
    # previous outputs should reflect the fork entry we just logged
    assert args[3] == {"forker": "ok"}


@pytest.mark.asyncio
async def test_process_handles_fork_sequential_does_not_run_parallel(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 10
    eng.run_id = "run_test"

    mem = MagicMock()
    eng.memory = mem

    # stub run_parallel_agents
    eng.run_parallel_agents = AsyncMock()

    rp = ResponseProcessor(eng)

    class ForkAgent:
        pass

    agent = ForkAgent()
    agent.type = "forknode"

    logs = []
    log_entry = {"agent_id": "forker_seq", "payload": {}}

    # sequential mode (default) should not trigger immediate parallel execution
    agent_result = {"result": {"fork_group": "fg_seq", "agents": ["a1", "a2"], "mode": "sequential"}}
    payload_out = {"result": "ok"}

    handled = await rp.process(
        "forker_seq",
        "forker_seq",
        agent_result,
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is True
    # run_parallel_agents should NOT be called for sequential mode
    eng.run_parallel_agents.assert_not_called()


@pytest.mark.asyncio
async def test_fork_with_empty_agents_still_logs(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 4
    eng.run_id = "run_test"

    mem = MagicMock()
    eng.memory = mem

    # run_parallel_agents should not be called when agents list is empty
    eng.run_parallel_agents = AsyncMock()

    rp = ResponseProcessor(eng)

    class ForkAgent:
        pass

    agent = ForkAgent()
    agent.type = "forknode"

    logs = []
    log_entry = {"agent_id": "forker2", "payload": {}}

    agent_result = {"result": {"fork_group": "fg2", "agents": []}}
    payload_out = {"result": "ok"}

    handled = await rp.process(
        "forker2",
        "forker2",
        agent_result,
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is True
    # No run_parallel_agents calls
    eng.run_parallel_agents.assert_not_called()
    # Memory logging should have been attempted
    mem.log.assert_called()


@pytest.mark.asyncio
async def test_fork_run_parallel_agents_raises_logs_error(temp_config_file, caplog):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 5
    eng.run_id = "run_test"

    mem = MagicMock()
    eng.memory = mem

    # stub run_parallel_agents to raise
    async def bad_runner(*args, **kwargs):
        raise RuntimeError("boom")

    eng.run_parallel_agents = AsyncMock(side_effect=bad_runner)

    rp = ResponseProcessor(eng)

    class ForkAgent:
        pass

    agent = ForkAgent()
    agent.type = "forknode"

    logs = []
    log_entry = {"agent_id": "forker3", "payload": {}}

    agent_result = {"result": {"fork_group": "fg3", "agents": ["x"], "mode": "parallel"}}
    payload_out = {"result": "ok"}

    caplog.clear()
    handled = await rp.process(
        "forker3",
        "forker3",
        agent_result,
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is True
    # ensure the error was logged
    assert any("Fork execution failed for group fg3" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_default_memory_set_and_log_exceptions_are_handled(temp_config_file, caplog):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 6
    eng.run_id = "run_test"

    mem = MagicMock()
    # make set raise and log raise to hit warning branches
    def bad_set(k, v):
        raise RuntimeError("set fail")

    def bad_log(*args, **kwargs):
        raise RuntimeError("log fail")

    mem.set.side_effect = bad_set
    mem.log.side_effect = bad_log
    eng.memory = mem

    rp = ResponseProcessor(eng)

    class DummyAgent:
        pass

    agent = DummyAgent()

    logs = []
    log_entry = {"agent_id": "a2", "payload": {}}

    payload_out = {"result": "ok"}

    caplog.clear()
    handled = await rp.process(
        "a2",
        "a2",
        {"result": "ok"},
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is False
    # warnings should be present for both set and log
    assert any("Warning: memory.set failed for agent_result:a2" in r.message for r in caplog.records)
    assert any("Warning: memory.log failed for a2" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_default_path_without_memory_attribute(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    eng.step_index = 7
    eng.run_id = "run_test"

    # ensure engine has no memory attribute
    if hasattr(eng, "memory"):
        delattr(eng, "memory")

    rp = ResponseProcessor(eng)

    class DummyAgent:
        pass

    agent = DummyAgent()

    logs = []
    log_entry = {"agent_id": "a3", "payload": {}}

    payload_out = {"result": "ok"}

    handled = await rp.process(
        "a3",
        "a3",
        {"result": "ok"},
        payload_out,
        agent,
        {},
        logs,
        log_entry,
        eng.step_index,
    )

    assert handled is False
    assert logs[-1]["payload"] == payload_out
