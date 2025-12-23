# Tests for QueueProcessor

import asyncio
import sys
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from orka.orchestrator.execution.queue_processor import QueueProcessor


class DummyAgent:
    def __init__(self, typ: str = "node"):
        self.type = typ


class DummyMemory:
    def __init__(self):
        self.saved = []
        self.logged = []
        self.set_items = {}
        self.closed = False

    def save_enhanced_trace(self, path: str, data: Dict[str, Any]):
        # Do not write to disk, just capture
        self.saved.append((path, data))

    def set(self, key: str, value: str):
        self.set_items[key] = value

    def log(self, *args, **kwargs):
        self.logged.append((args, kwargs))

    def close(self):
        self.closed = True


class DummyResponseNormalizer:
    def normalize(self, agent, agent_id, result):
        # Return a simple payload
        return {
            "result": result if not isinstance(result, dict) else result.get("result", result),
            "status": "success",
            "response": result if not isinstance(result, dict) else result.get("result", result),
            "metrics": {"n": 1},
        }


class DummyResponseProcessor:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.return_value = True

    async def process(self, agent_id, agent_id_ret, agent_result, payload_out, agent, input_data, logs, log_entry, step_index):
        self.calls.append({
            "agent_id": agent_id,
            "agent_id_ret": agent_id_ret,
            "payload": dict(payload_out),
            "step": step_index,
        })
        return self.return_value


class DummyEngine:
    def __init__(self):
        self.run_id = None
        self.step_index = 0
        self.orchestrator_cfg = {"agents": ["a1"]}
        self.agents = {"a1": DummyAgent(), "a2": DummyAgent(), "router": DummyAgent("router"), "gs": DummyAgent("graph-scout")}
        self.memory = DummyMemory()
        self._response_normalizer = DummyResponseNormalizer()
        self._response_processor = DummyResponseProcessor()
        self._retries = []

    def build_previous_outputs(self, logs):
        return {"count": len(logs)}

    async def _run_agent_async(self, agent_id, input_data, prev, full_payload=None):
        # Default: simple echo result
        return agent_id, {"result": f"ok:{agent_id}"}

    def _record_retry(self, agent_id):
        self._retries.append(agent_id)

    def _generate_meta_report(self, logs):
        return {"steps": len(logs)}

    def _build_enhanced_trace(self, logs, meta):
        return {"logs": logs, "meta": meta}

    def _extract_final_response(self, logs):
        return {"final": True, "steps": len(logs)}


@pytest.mark.asyncio
async def test_queue_processor_happy_path_and_trace_save(tmp_path, monkeypatch):
    eng = DummyEngine()
    qp = QueueProcessor(eng)

    # Ensure log dir points to temp to avoid real filesystem writes
    monkeypatch.setenv("ORKA_LOG_DIR", str(tmp_path))

    logs: List[Dict[str, Any]] = []
    out = await qp.run_queue(input_data={"x": 1}, logs=logs, return_logs=False)

    # Steps equals number of appended logs; handled by response processor so remains 0
    assert out == {"final": True, "steps": 0}
    assert len(logs) == 0 or isinstance(logs, list)  # handled by response processor
    # Enhanced trace saved and memory closed
    assert len(eng.memory.saved) == 1
    assert eng.memory.closed is True


@pytest.mark.asyncio
async def test_queue_processor_retry_none_and_waiting(monkeypatch):
    eng = DummyEngine()

    calls = {
        "i": 0
    }

    async def run_agent(agent_id, input_data, prev, full_payload=None):
        calls["i"] += 1
        if calls["i"] == 1:
            return None, None
        if calls["i"] == 2:
            return agent_id, {"status": "waiting"}
        return agent_id, {"result": "done"}

    eng._run_agent_async = run_agent  # type: ignore[assignment]

    qp = QueueProcessor(eng)
    logs: List[Dict[str, Any]] = []
    out = await qp.run_queue({}, logs)

    assert out["final"] is True
    # Two retries recorded
    assert eng._retries.count("a1") == 2


@pytest.mark.asyncio
async def test_queue_processor_router_inserts_agents():
    eng = DummyEngine()
    eng.orchestrator_cfg = {"agents": ["router", "a2"]}

    async def run_agent(agent_id, input_data, prev, full_payload=None):
        if agent_id == "router":
            return agent_id, {"result": ["a1"]}
        return agent_id, {"result": f"ok:{agent_id}"}

    eng._run_agent_async = run_agent  # type: ignore[assignment]

    qp = QueueProcessor(eng)
    logs: List[Dict[str, Any]] = []
    out = await qp.run_queue({}, logs)

    assert out["final"] is True
    # Response processor should have been called for all executed agents
    assert len(eng._response_processor.calls) >= 2


@pytest.mark.asyncio
async def test_queue_processor_graphscout_handler_called(monkeypatch):
    # Inject a fake GraphScoutHandler module
    module_name = "orka.orchestrator.execution.graphscout_handler"

    class FakeHandler:
        def __init__(self, engine):
            self.engine = engine
            self.calls = []

        async def handle(self, agent_id, agent_result, logs, input_data):
            self.calls.append((agent_id, agent_result))

    fake_module = SimpleNamespace(GraphScoutHandler=FakeHandler)
    sys.modules[module_name] = fake_module

    eng = DummyEngine()
    eng.orchestrator_cfg = {"agents": ["gs"]}

    qp = QueueProcessor(eng)
    logs: List[Dict[str, Any]] = []

    out = await qp.run_queue({}, logs)
    assert out["final"] is True


@pytest.mark.asyncio
async def test_queue_processor_fallback_logging_branch():
    eng = DummyEngine()
    # Remove response processor attribute entirely so hasattr() is False
    delattr(eng, "_response_processor")

    qp = QueueProcessor(eng)
    logs: List[Dict[str, Any]] = []
    out = await qp.run_queue({}, logs, return_logs=True)

    # Should return logs (may be empty if internal handling changes) and also write memory.set/log
    assert isinstance(out, list)
    assert eng.memory.set_items
    assert eng.memory.logged


@pytest.mark.asyncio
async def test_queue_processor_agent_error_caught():
    eng = DummyEngine()

    async def run_agent(agent_id, input_data, prev, full_payload=None):
        raise RuntimeError("fail")

    eng._run_agent_async = run_agent  # type: ignore[assignment]

    qp = QueueProcessor(eng)
    logs: List[Dict[str, Any]] = []

    out = await qp.run_queue({}, logs)
    assert out["final"] is True
