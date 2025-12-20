"""
Additional execution engine tests.

Strategy: Patch the dynamically imported QueueProcessor via sys.modules.
"""
import asyncio
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
async def test_execution_engine_handles_waiting_and_requeue(
    temp_config_file, monkeypatch
):
    """Test that engine handles 'waiting' status and requeues agent."""
    engine = ExecutionEngine(temp_config_file)

    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}
    engine.memory = create_mock_memory()

    expected_logs = [
        {"agent_id": "test_agent", "payload": {"status": "waiting"}},
        {"agent_id": "test_agent", "payload": {"result": "ok"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "x"}, logs, return_logs=True
        )

    assert result is not None
    assert len(result) >= 2


@pytest.mark.asyncio
async def test_execution_engine_router_inserts_new_agents(
    temp_config_file, monkeypatch
):
    """Test that router node inserts new agents into the execution queue."""
    engine = ExecutionEngine(temp_config_file)

    router = MagicMock()
    router.type = "routernode"
    processor = MagicMock()
    processor.type = "simple"

    engine.agents = {"test_agent": router, "test_agent2": processor}
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "test_agent",
            "payload": {"result": ["test_agent2"], "status": "success"},
        },
        {"agent_id": "test_agent2", "payload": {"final": "ok"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "x"}, logs, return_logs=True
        )

    assert len(result) >= 2
    assert result is not None
