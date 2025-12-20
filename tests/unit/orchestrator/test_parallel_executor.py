import importlib.util
import pathlib
import asyncio
import json
from datetime import datetime

import importlib

ParallelExecutor = importlib.import_module("orka.orchestrator.execution.parallel_executor").ParallelExecutor
ContextManager = importlib.import_module("orka.orchestrator.execution.context_manager").ContextManager
AgentRunner = importlib.import_module("orka.orchestrator.execution.agent_runner").AgentRunner


class MemoryStub:
    def __init__(self):
        self.store = {}
        self.logs = []
        self.memory = []

    def hset(self, key, field, value):
        self.store[(key, field)] = value

    def log(self, agent_id, event_type, payload, **kwargs):
        self.logs.append((agent_id, event_type, payload, kwargs))


class DummyOrch:
    def __init__(self):
        self.agents = {}
        self.run_id = "run-1"
        self.step_index = 1
        self.memory = MemoryStub()
        self._context_manager = ContextManager(self)
        self._agent_runner = AgentRunner(self)

    def _add_prompt_to_payload(self, agent, payload_out, payload):
        # simple behavior for tests
        if hasattr(agent, "prompt"):
            payload_out.setdefault("formatted_prompt", agent.prompt)


class SyncAgent:
    def run(self, payload):
        return {"result": "ok", "payload_input": payload.get("input")}


async def _run_test():
    orch = DummyOrch()
    orch.agents["a1"] = SyncAgent()
    orch.agents["a2"] = SyncAgent()

    executor = ParallelExecutor(orch)
    logs = await executor.run_parallel_agents(["a1", "a2"], "group_1_1", {"x": 1}, {})
    assert isinstance(logs, list)
    # Two agents should produce two entries
    assert any(l["agent_id"] == "a1" for l in logs)
    assert any(l["agent_id"] == "a2" for l in logs)


def test_parallel_executor_event_loop():
    # Use asyncio.run which creates and manages its own event loop to avoid
    # interacting with test-suite event loop lifecycle.
    asyncio.run(_run_test())
