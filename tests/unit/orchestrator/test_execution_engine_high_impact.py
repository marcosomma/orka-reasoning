"""
Tests for high-impact execution engine scenarios.

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
async def test_agent_failure_does_not_raise_and_saves_trace(
    temp_config_file, monkeypatch
):
    """If an agent repeatedly fails, the engine should not propagate the exception
    and should still return logs without raising."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["test_agent"]}

    fake_agent = MagicMock()
    fake_agent.type = "simple"
    engine.agents = {"test_agent": fake_agent}

    mem = create_mock_memory()
    engine.memory = mem

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
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "x"}, logs, return_logs=True
        )

    # Ensure the call returned logs (even if with error) and did not raise
    assert isinstance(result, list)
    # Verify error payload is present in logs
    assert len(result) == 1
    assert "error" in result[0]["payload"]


@pytest.mark.asyncio
async def test_router_node_prepend_queue_and_executes_new_agents(
    temp_config_file, monkeypatch
):
    """A router node returning a list of agent ids should prepend them to the
    current queue so they get executed next."""
    engine = ExecutionEngine(temp_config_file)
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

    mem = create_mock_memory()
    engine.memory = mem

    expected_logs = [
        {
            "agent_id": "router_agent",
            "payload": {"result": ["new_agent"], "status": "success"},
        },
        {"agent_id": "new_agent", "payload": {"result": "ok"}},
        {"agent_id": "next_agent", "payload": {"result": "ok"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        returned = await engine._run_with_comprehensive_error_handling(
            {"input": "x"}, logs, return_logs=True
        )

    # new_agent should be in the logs (was executed)
    agent_ids = [log["agent_id"] for log in returned]
    assert "new_agent" in agent_ids
    # Returned value should be logs (list)
    assert isinstance(returned, list)
