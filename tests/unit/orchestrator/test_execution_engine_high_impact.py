import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.mark.asyncio
async def test_agent_failure_does_not_raise_and_saves_trace(temp_config_file, monkeypatch):
    """If an agent repeatedly fails, the engine should not propagate the exception
    and should still attempt to save the enhanced trace via the memory backend."""
    engine = ExecutionEngine(temp_config_file)

    # Ensure the orchestrator config points to our single test agent
    engine.orchestrator_cfg = {"agents": ["test_agent"]}

    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}

    # Provide a simple memory backend mock with the methods used by the engine
    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    mem.set = MagicMock()
    mem.hset = MagicMock()
    mem.save_enhanced_trace = MagicMock()
    mem.save_to_file = MagicMock()
    mem.close = MagicMock()
    engine.memory = mem

    async def raise_exc(*args, **kwargs):
        raise RuntimeError("agent-failure")

    # Force the runner to raise on every attempt (exhaust retries)
    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=raise_exc))
    # Speed up retry sleeps
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(return_value=None))

    # Run the engine; it should complete without re-raising the agent exception
    logs = []
    result = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    # The engine should have attempted to persist an enhanced trace via memory
    assert mem.save_enhanced_trace.called
    # Ensure the call returned logs (even if empty) and did not raise
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_router_node_prepend_queue_and_executes_new_agents(temp_config_file, monkeypatch):
    """A router node returning a list of agent ids should prepend them to the
    current queue so they get executed next."""
    engine = ExecutionEngine(temp_config_file)

    # initial queue: router_agent then next_agent
    engine.orchestrator_cfg = {"agents": ["router_agent", "next_agent"]}

    router_agent = MagicMock()
    router_agent.type = "routernode"
    next_agent = MagicMock()
    next_agent.type = "simple"
    new_agent = MagicMock()
    new_agent.type = "simple"

    engine.agents = {
        "router_agent": router_agent,
        "next_agent": next_agent,
        "new_agent": new_agent,
    }

    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    mem.set = MagicMock()
    mem.hset = MagicMock()
    mem.save_enhanced_trace = MagicMock()
    mem.save_to_file = MagicMock()
    mem.close = MagicMock()
    engine.memory = mem

    async def runner(agent_id, input_data, previous_outputs, full_payload=None):
        # Router returns OrkaResponse with result field containing the list
        if agent_id == "router_agent":
            return agent_id, {"result": ["new_agent"], "status": "success"}
        return agent_id, {"result": "ok"}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=runner))

    logs = []
    returned = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    # Memory.log should have been called for new_agent when it executed
    called_agent_ids = [call.args[0] for call in mem.log.call_args_list]
    assert "new_agent" in called_agent_ids
    # Returned value should be logs (list)
    assert isinstance(returned, list)
