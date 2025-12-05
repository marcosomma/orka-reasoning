import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.mark.asyncio
async def test_execution_engine_handles_waiting_and_requeue(temp_config_file, monkeypatch):
    engine = ExecutionEngine(temp_config_file)

    fake_agent = MagicMock()
    fake_agent.type = "simple"
    # temp_config_file YAML uses 'test_agent' as the configured agent id
    engine.agents = {"test_agent": fake_agent}

    # First call returns waiting, second returns a real result
    runner = AsyncMock(side_effect=[(None, {"status": "waiting"}), (None, {"result": "ok"})])
    monkeypatch.setattr(engine, "_run_agent_async", runner)

    logs = []
    result = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    assert result is not None
    assert runner.call_count >= 2


@pytest.mark.asyncio
async def test_execution_engine_router_inserts_new_agents(temp_config_file, monkeypatch):
    engine = ExecutionEngine(temp_config_file)

    # Prepare three fake agents: router -> will insert new agent(s), then the new agent returns result
    router = MagicMock()
    router.type = "routernode"
    processor = MagicMock()
    processor.type = "simple"

    # Use 'test_agent' as the initial agent (from temp_config_file), and a second
    # agent id 'test_agent2' which the router will insert into the queue.
    engine.agents = {"test_agent": router, "test_agent2": processor}

    # When router runs it returns OrkaResponse with result field containing new agents
    async_runner = AsyncMock(side_effect=[(None, {"result": ["test_agent2"], "status": "success"}), (None, {"final": "ok"})])
    monkeypatch.setattr(engine, "_run_agent_async", async_runner)

    logs = []
    result = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    # router should have been called first, processor afterwards
    assert async_runner.call_count >= 2
    assert result is not None
