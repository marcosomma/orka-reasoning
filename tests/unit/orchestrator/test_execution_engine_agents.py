import asyncio
from unittest.mock import MagicMock


def make_engine(monkeypatch):
    from orka.orchestrator.execution_engine import ExecutionEngine

    # Instantiate using dummy YAML path (loader is mocked in conftest)
    eng = ExecutionEngine("tests/unit/orchestrator/dummy_path.yml")
    # Ensure orchestrator_cfg and queue exist
    eng.orchestrator_cfg = {"agents": []}
    eng.queue = []
    return eng


def test_run_agent_sync(monkeypatch):
    eng = make_engine(monkeypatch)

    class SyncAgent:
        def __init__(self):
            self.type = "local_llm"

        def run(self, payload):
            # simple sync processing
            return {"ok": True, "input": payload.get("input")}

    agent = SyncAgent()
    eng.agents = {"sync": agent}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        aid, result = loop.run_until_complete(eng._run_agent_async("sync", "hello", {}))
    finally:
        loop.close()

    assert aid == "sync"
    assert isinstance(result, dict) and result.get("ok") is True


def test_run_agent_async(monkeypatch):
    eng = make_engine(monkeypatch)

    class AsyncAgent:
        def __init__(self):
            self.type = "local_llm"

        async def run(self, payload):
            return {"async": True, "input": payload.get("input")}

    agent = AsyncAgent()
    eng.agents = {"a": agent}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        aid, result = loop.run_until_complete(eng._run_agent_async("a", "x", {}))
    finally:
        loop.close()

    assert aid == "a"
    assert result.get("async") is True


def test_run_agent_needs_orchestrator(monkeypatch):
    eng = make_engine(monkeypatch)

    class NeedsOrch:
        def __init__(self):
            self.type = "pathexecutornode"

        def run(self, context):
            # context should contain orchestrator key when needs_orchestrator is detected
            return {"has_orch": "orchestrator" in context}

    agent = NeedsOrch()
    eng.agents = {"node": agent}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        aid, res = loop.run_until_complete(eng._run_agent_async("node", {}, {}, full_payload={"orchestrator": eng}))
    finally:
        loop.close()

    assert aid == "node"
    assert res.get("has_orch") is True


def test_run_branch_and_parallel(monkeypatch):
    eng = make_engine(monkeypatch)

    class A:
        async def run(self, payload):
            return {"a": 1}

    class B:
        def run(self, payload):
            return {"b": 2}

    eng.agents = {"a": A(), "b": B(), "fork": MagicMock()}

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        # run branch async
        branch_res = loop.run_until_complete(eng._run_branch_async(["a", "b"], {}, {}))
        assert "a" in branch_res and "b" in branch_res

        # parallel execution with missing fork node should treat each as separate branch
        par = loop.run_until_complete(eng.run_parallel_agents(["a", "b"], "group_1", {}, {}))
    finally:
        loop.close()

    assert isinstance(par, list)
