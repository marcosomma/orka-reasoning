import asyncio
import json
import os
from unittest.mock import MagicMock

import pytest

from orka.orchestrator_error_wrapper import (
    OrkaErrorHandler,
    run_orchestrator_with_error_handling,
)


class DummyOrchestrator:
    def __init__(self):
        self.run_id = "run_1"
        self.step_index = 0
        self.memory = MagicMock()

    async def run(self, input_data):
        # default: return list of logs
        return [{"agent_id": "a1", "payload": {"result": "ok"}}]

    def _generate_meta_report(self, logs):
        return {"meta": "ok", "count": len(logs)}


@pytest.mark.asyncio
async def test_orchestrator_error_handler_save_report(tmp_path, monkeypatch):
    orch = DummyOrchestrator()
    # memory.save_to_file should write a file path — simulate behaviour
    def fake_save(path):
        with open(path, "w") as f:
            f.write("{}")

    orch.memory.save_to_file.side_effect = fake_save
    orch.memory.memory = [{"a": 1}, {"b": 2}]

    monkeypatch.setenv("ORKA_LOG_DIR", str(tmp_path))

    handler = OrkaErrorHandler(orch)

    # Record a sample error
    handler.record_error("test_error", "agent_x", "something went wrong", None, step=2, status_code=500, recovery_action="retry")

    # Save report
    report_path = handler.save_comprehensive_error_report(logs=[{"agent_id": "a1"}], final_error=None)

    assert os.path.exists(report_path)
    with open(report_path, "r") as f:
        data = json.load(f)
    assert "orka_execution_report" in data
    assert data["orka_execution_report"]["error_telemetry"]["errors"]


@pytest.mark.asyncio
async def test_run_orchestrator_with_error_handling_success(tmp_path, monkeypatch):
    orch = DummyOrchestrator()
    def fake_save(path):
        with open(path, "w") as f:
            f.write("{}")

    orch.memory.save_to_file.side_effect = fake_save
    orch.memory.memory = []
    monkeypatch.setenv("ORKA_LOG_DIR", str(tmp_path))

    result = await run_orchestrator_with_error_handling(orch, {"input": "x"})

    assert isinstance(result, dict)
    assert result.get("status") == "success"
    assert "error_telemetry" in result
    assert os.path.exists(result["report_path"]) 


@pytest.mark.asyncio
async def test_run_orchestrator_with_error_handling_critical_failure(tmp_path, monkeypatch):
    class BadOrch(DummyOrchestrator):
        async def run(self, input_data):
            raise RuntimeError("boom")

    orch = BadOrch()
    orch.memory.save_to_file.side_effect = lambda p: None
    orch.memory.close.side_effect = lambda: None
    monkeypatch.setenv("ORKA_LOG_DIR", str(tmp_path))

    result = await run_orchestrator_with_error_handling(orch, {"input": "x"})

    assert isinstance(result, dict)
    assert result.get("status") == "critical_failure"
    assert "error_report_path" in result
    assert os.path.exists(result["error_report_path"]) 
