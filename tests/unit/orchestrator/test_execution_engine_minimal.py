import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.mark.asyncio
async def test_execution_engine_runs_single_agent(temp_config_file, monkeypatch):
    # Instantiate engine with temp YAML (conftest provides file)
    engine = ExecutionEngine(temp_config_file)

    # Prepare a fake agent and inject into engine
    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}

    # Monkeypatch internal agent runner to return a result immediately
    async_runner = AsyncMock(return_value=(None, {"result": "ok"}))
    monkeypatch.setattr(engine, "_run_agent_async", async_runner)

    logs = []
    result = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    # Should return something (logs list or final response)
    assert result is not None


@pytest.mark.asyncio
async def test_execution_engine_retries_on_none(temp_config_file, monkeypatch):
    engine = ExecutionEngine(temp_config_file)
    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}

    # First call returns None (trigger retry), second returns a result
    runner = AsyncMock(side_effect=[(None, None), (None, {"result": "ok"})])
    monkeypatch.setattr(engine, "_run_agent_async", runner)

    logs = []
    result = await engine._run_with_comprehensive_error_handling({"input": "x"}, logs, return_logs=True)

    assert result is not None
    # Ensure our runner was called at least twice due to retry
    assert runner.call_count >= 2
