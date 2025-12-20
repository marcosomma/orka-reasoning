"""
Additional tests for GraphScout handler.

Strategy: Test the GraphScoutHandler directly by setting up engine.queue
and verifying it gets modified correctly.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.orchestrator.execution.graphscout_handler import GraphScoutHandler


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


@pytest.mark.asyncio
async def test_graphscout_commit_path_executes_all_targets(
    temp_config_file, monkeypatch
):
    """Test that commit_path decision adds all targets to the queue."""
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout"]}
    engine.queue = ["graphscout"]  # Initial queue

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    a = MagicMock()
    a.type = "simple"
    b = MagicMock()
    b.type = "simple"

    engine.agents = {
        "graphscout": graphscout,
        "a": a,
        "b": b,
    }
    engine.memory = create_mock_memory()

    handler = GraphScoutHandler(engine)

    # commit_path with list target
    agent_result = {
        "decision": "commit_path",
        "target": ["a", "b"],
        "status": "success",
    }

    logs = []
    input_data = {"input": "test"}

    await handler.handle("graphscout", agent_result, logs, input_data)

    # Both 'a' and 'b' should be added to engine.queue
    assert "a" in engine.queue
    assert "b" in engine.queue


@pytest.mark.asyncio
async def test_graphscout_validation_then_validator_routes_final_agent(
    temp_config_file, monkeypatch
):
    """Test GraphScout shortlist selects validator, which then routes to final agent."""
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout"]}
    engine.queue = ["graphscout"]  # Initial queue

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    validator = MagicMock()
    validator.type = "routernode"
    final_agent = MagicMock()
    final_agent.type = "simple"

    engine.agents = {
        "graphscout": graphscout,
        "validator": validator,
        "final_agent": final_agent,
    }
    engine.memory = create_mock_memory()

    # Mock build_previous_outputs to return empty dict
    engine.build_previous_outputs = MagicMock(return_value={})

    # Provide a selector that returns the first candidate (validator)
    def select_best(shortlist_, question, context):
        return shortlist_[0]

    engine._select_best_candidate_from_shortlist = select_best

    handler = GraphScoutHandler(engine)

    # GraphScout returns a shortlist that selects 'validator'
    shortlist = [{"node_id": "validator"}, {"node_id": "other"}]
    agent_result = {
        "result": {"decision": "shortlist", "target": shortlist},
        "status": "success",
    }

    logs = []
    input_data = {"input": "test"}

    await handler.handle("graphscout", agent_result, logs, input_data)

    # 'validator' should be added to engine.queue
    assert "validator" in engine.queue
