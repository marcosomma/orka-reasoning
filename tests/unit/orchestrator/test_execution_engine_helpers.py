import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.mark.asyncio
async def test_run_agent_async_handles_sync_and_async_agents(temp_config_file):
    engine = ExecutionEngine(temp_config_file)

    # minimal memory backend
    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    mem.set = MagicMock()
    mem.hset = MagicMock()
    mem.save_enhanced_trace = MagicMock()
    mem.save_to_file = MagicMock()
    mem.close = MagicMock()
    engine.memory = mem

    class SyncAgent:
        def __init__(self):
            self.type = "simple"

        def run(self, payload):
            # simple synchronous processing
            return {"result": "sync"}

    class AsyncAgent:
        def __init__(self):
            self.type = "simple"

        async def run(self, payload):
            return {"result": "async"}

    engine.agents = {"sync": SyncAgent(), "async": AsyncAgent()}

    # Sync agent should be executed in the executor and return its dict
    aid, res = await engine._run_agent_async("sync", {"input": "x"}, {})
    assert aid == "sync"
    assert isinstance(res, dict) and res.get("result") == "sync"

    # Async agent should be awaited and return its dict
    aid2, res2 = await engine._run_agent_async("async", {"input": "x"}, {})
    assert aid2 == "async"
    assert isinstance(res2, dict) and res2.get("result") == "async"


@pytest.mark.asyncio
async def test_run_branch_with_retry_retries_and_succeeds(temp_config_file, monkeypatch):
    engine = ExecutionEngine(temp_config_file)
    engine.memory = MagicMock()

    calls = {"count": 0}

    async def failing_then_ok(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary-failure")
        return {"branch": "ok"}

    monkeypatch.setattr(engine, "_run_branch_async", AsyncMock(side_effect=failing_then_ok))
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(return_value=None))

    res = await engine._run_branch_with_retry(["a"], {"input": "x"}, {})
    assert res == {"branch": "ok"}


@pytest.mark.asyncio
async def test_run_branch_async_executes_each_agent_in_sequence(temp_config_file, monkeypatch):
    engine = ExecutionEngine(temp_config_file)
    engine.memory = MagicMock()

    # Simulate _run_agent_async returning results for each agent
    async def run_agent(agent_id, input_data, previous_outputs, full_payload=None):
        return agent_id, {"result": f"ok-{agent_id}"}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=run_agent))

    res = await engine._run_branch_async(["a", "b"], {"input": "x"}, {})
    # Should return a mapping agent_id -> result
    assert "a" in res and "b" in res
    assert res["a"]["result"] == "ok-a"
    assert res["b"]["result"] == "ok-b"


def test_enqueue_fork_inserts_at_front(temp_config_file):
    engine = ExecutionEngine(temp_config_file)

    # start with an existing queue
    engine.queue = ["one", "two", "three"]

    engine.enqueue_fork(["x", "y"], "fg_test")

    assert engine.queue[:2] == ["x", "y"]
    assert engine.queue[2:] == ["one", "two", "three"]
