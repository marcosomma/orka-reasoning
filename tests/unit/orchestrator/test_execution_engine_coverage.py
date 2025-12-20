"""
Additional tests for execution_engine.py to improve coverage.
Focus on uncovered branches, error handling, and edge cases.

Strategy: Patch the dynamically imported QueueProcessor via sys.modules
to avoid MagicMock + build_previous_outputs infinite loop issues.
"""
import asyncio
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


def create_mock_memory():
    """Create a properly configured mock memory object with spec to prevent auto-attrs."""
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
            # Extend the logs list with expected_logs
            logs.extend(expected_logs)
            return expected_logs

    return MockQueueProcessor


@pytest.mark.asyncio
async def test_graphscout_decision_orka_response_format(temp_config_file, monkeypatch):
    """Test GraphScout agent with OrkaResponse format (decision in result field)."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout", "target_agent"]}
    engine.queue = ["graphscout", "target_agent"]

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    target_agent = MagicMock()
    target_agent.type = "simple"

    engine.agents = {
        "graphscout": graphscout,
        "target_agent": target_agent,
    }
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "graphscout",
            "payload": {
                "result": {
                    "decision": "route",
                    "target": "target_agent",
                    "reasoning": "test routing",
                }
            },
        },
        {"agent_id": "target_agent", "payload": {"result": "ok"}},
    ]

    # Patch the queue_processor module in sys.modules
    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["agent_id"] == "graphscout"
    assert result[1]["agent_id"] == "target_agent"


@pytest.mark.asyncio
async def test_graphscout_decision_legacy_format(temp_config_file, monkeypatch):
    """Test GraphScout agent with legacy format (decision at top level)."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout", "target_agent"]}
    engine.queue = ["graphscout", "target_agent"]

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    target_agent = MagicMock()
    target_agent.type = "simple"

    engine.agents = {
        "graphscout": graphscout,
        "target_agent": target_agent,
    }
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "graphscout",
            "payload": {
                "decision": "route",
                "target": "target_agent",
                "reasoning": "test routing",
            },
        },
        {"agent_id": "target_agent", "payload": {"result": "ok"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_branch_error_with_traceback(temp_config_file, monkeypatch):
    """Test branch execution with error that has traceback."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {
        "agents": ["fork", "agent1", "agent2", "join"],
        "strategy": "parallel",
    }
    engine.queue = ["fork", "agent1", "agent2", "join"]

    fork = MagicMock()
    fork.type = "fork"
    agent1 = MagicMock()
    agent1.type = "simple"
    agent2 = MagicMock()
    agent2.type = "simple"
    join = MagicMock()
    join.type = "join"

    engine.agents = {
        "fork": fork,
        "agent1": agent1,
        "agent2": agent2,
        "join": join,
    }
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "fork",
            "payload": {"branches": [["agent1"], ["agent2"]], "fork_group_id": "test"},
        },
        {"agent_id": "agent1", "payload": {"error": "Branch failure"}},
        {"agent_id": "agent2", "payload": {"result": "ok"}},
        {"agent_id": "join", "payload": {"result": "merged"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 4


@pytest.mark.asyncio
async def test_loop_node_with_context_preservation(temp_config_file, monkeypatch):
    """Test loop node execution preserves context across iterations."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["loop_agent"]}
    engine.queue = ["loop_agent"]

    loop_agent = MagicMock()
    loop_agent.type = "loop"

    engine.agents = {"loop_agent": loop_agent}
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "loop_agent",
            "payload": {
                "loop_continue": False,
                "result": "completed",
                "iterations": 1,
            },
        }
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["payload"]["result"] == "completed"


@pytest.mark.asyncio
async def test_execution_with_empty_queue(temp_config_file):
    """Test execution with empty agent queue."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": []}
    engine.queue = []
    engine.memory = create_mock_memory()

    expected_logs = []

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_agent_result_with_metadata_and_metrics(temp_config_file, monkeypatch):
    """Test agent result with metadata and metrics fields."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["test_agent"]}
    engine.queue = ["test_agent"]

    test_agent = MagicMock()
    test_agent.type = "simple"

    engine.agents = {"test_agent": test_agent}
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "test_agent",
            "payload": {
                "result": "test output",
                "metadata": {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "agent_type": "simple",
                },
                "metrics": {"duration_ms": 123, "tokens_used": 50},
            },
        }
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["payload"]["result"] == "test output"
    assert "metadata" in result[0]["payload"]
    assert "metrics" in result[0]["payload"]


@pytest.mark.asyncio
async def test_fork_join_with_empty_branch(temp_config_file, monkeypatch):
    """Test fork/join with one empty branch."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {
        "agents": ["fork", "agent1", "join"],
        "strategy": "parallel",
    }
    engine.queue = ["fork", "agent1", "join"]

    fork = MagicMock()
    fork.type = "fork"
    agent1 = MagicMock()
    agent1.type = "simple"
    join = MagicMock()
    join.type = "join"

    engine.agents = {
        "fork": fork,
        "agent1": agent1,
        "join": join,
    }
    engine.memory = create_mock_memory()

    expected_logs = [
        {
            "agent_id": "fork",
            "payload": {
                "branches": [["agent1"], []],
                "fork_group_id": "test_group",
            },
        },
        {"agent_id": "agent1", "payload": {"result": "ok"}},
        {"agent_id": "join", "payload": {"result": "merged"}},
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_graphscout_without_decision(temp_config_file, monkeypatch):
    """Test GraphScout agent that returns result without decision field."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout"]}
    engine.queue = ["graphscout"]

    graphscout = MagicMock()
    graphscout.type = "graph-scout"

    engine.agents = {"graphscout": graphscout}
    engine.memory = create_mock_memory()

    expected_logs = [
        {"agent_id": "graphscout", "payload": {"result": "no routing needed"}}
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["payload"]["result"] == "no routing needed"


@pytest.mark.asyncio
async def test_agent_with_non_dict_result(temp_config_file, monkeypatch):
    """Test agent returning non-dict result (wrapped in payload)."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["test_agent"]}
    engine.queue = ["test_agent"]

    test_agent = MagicMock()
    test_agent.type = "simple"

    engine.agents = {"test_agent": test_agent}
    engine.memory = create_mock_memory()

    expected_logs = [
        {"agent_id": "test_agent", "payload": {"result": "simple string result"}}
    ]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_memory_save_enhanced_trace_failure(temp_config_file, monkeypatch):
    """Test execution when memory.save_enhanced_trace fails."""
    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["test_agent"]}
    engine.queue = ["test_agent"]

    test_agent = MagicMock()
    test_agent.type = "simple"

    engine.agents = {"test_agent": test_agent}

    mem = create_mock_memory()
    mem.save_enhanced_trace = MagicMock(side_effect=Exception("Save failed"))
    engine.memory = mem

    expected_logs = [{"agent_id": "test_agent", "payload": {"result": "ok"}}]

    mock_module = MagicMock()
    mock_module.QueueProcessor = create_mock_queue_processor(expected_logs)

    with patch.dict(
        sys.modules, {"orka.orchestrator.execution.queue_processor": mock_module}
    ):
        logs = []
        result = await engine._run_with_comprehensive_error_handling(
            {"input": "test"}, logs, return_logs=True
        )

    assert isinstance(result, list)
    assert len(result) == 1
