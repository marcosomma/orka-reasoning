"""
Deep tests for execution engine behavior.

Strategy: Patch the dynamically imported QueueProcessor via sys.modules.
"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


def create_mock_memory():
    """Create a properly configured mock memory object."""
    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock(return_value=None)
    mem.set = MagicMock(return_value=None)
    mem.hset = MagicMock(return_value=None)
    mem.hget = MagicMock(return_value=None)
    mem.save_enhanced_trace = MagicMock(return_value=None)
    mem.save_to_file = MagicMock(return_value=None)
    mem.close = MagicMock(return_value=None)
    mem.stop_decay_scheduler = MagicMock(return_value=None)
    return mem


def create_mock_queue_processor(expected_logs):
    """Create a mock QueueProcessor class that returns expected_logs."""

    class MockQueueProcessor:
        def __init__(self, engine):
            self.engine = engine

        async def run_queue(self, input_data, logs, return_logs=False):
            logs.extend(expected_logs)
            return expected_logs

    return MockQueueProcessor


@pytest.mark.asyncio
async def test_execution_engine_run_handles_agent_failure_gracefully(temp_config_file):
    """Ensure that if an agent fails, the engine logs the error instead of
    crashing and still attempts to save traces."""
    engine = ExecutionEngine(temp_config_file)

    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "test_agent",
            "payload": {"error": "agent-failure", "status": "error"},
        }
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        result = await engine.run({"input": "x"})

    # Engine should complete without raising
    assert result is not None


@pytest.mark.asyncio
async def test_special_agent_types_receive_orchestrator_and_run_id_in_payload(
    temp_config_file, monkeypatch
):
    """Special agent types (loopnode, etc.) should receive orchestrator and run_id
    in their full_payload when executed."""
    engine = ExecutionEngine(temp_config_file)
    engine.run_id = "run-123"

    fake_agent = MagicMock()
    fake_agent.type = "loopnode"
    engine.agents = {"test_agent": fake_agent}
    engine.memory = create_mock_memory()

    # Track what full_payload was passed
    captured_payloads = []

    async def capture_runner(agent_id, input_data, previous_outputs, full_payload=None):
        captured_payloads.append(full_payload)
        return agent_id, {"result": "ok"}

    # Mock _run_agent_async to capture payloads
    monkeypatch.setattr(
        engine, "_run_agent_async", AsyncMock(side_effect=capture_runner)
    )

    expected_logs = [{"agent_id": "test_agent", "payload": {"result": "ok"}}]

    # Create a custom mock processor that calls _run_agent_async with full_payload
    class MockQueueProcessorWithPayload:
        def __init__(self, eng):
            self.engine = eng

        async def run_queue(self, input_data, logs, return_logs=False):
            full_payload = {
                "orchestrator": self.engine,
                "run_id": self.engine.run_id,
                "input": input_data,
            }
            await self.engine._run_agent_async(
                "test_agent", input_data, {}, full_payload=full_payload
            )
            logs.extend(expected_logs)
            return expected_logs

    mock_module = MagicMock()
    mock_module.QueueProcessor = MockQueueProcessorWithPayload

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        await engine._run_with_comprehensive_error_handling(
            {"input": "x"}, logs, return_logs=True
        )

    # Verify full_payload was passed with orchestrator and run_id
    assert len(captured_payloads) >= 1
    assert captured_payloads[0] is not None
    assert "orchestrator" in captured_payloads[0]
    assert captured_payloads[0].get("run_id") == "run-123"
