"""
Tests for GraphScout handler.

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
async def test_graphscout_inserts_target_agent(temp_config_file, monkeypatch):
    """Test that GraphScout handler inserts target agent into the queue."""
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout", "target_agent"]}
    engine.queue = ["graphscout"]  # Initial queue

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    target_agent = MagicMock()
    target_agent.type = "simple"

    engine.agents = {"graphscout": graphscout, "target_agent": target_agent}
    engine.memory = create_mock_memory()

    # Create handler
    handler = GraphScoutHandler(engine)

    # Agent result with routing decision
    agent_result = {"result": {"decision": "route", "target": "target_agent"}}

    logs = []
    input_data = {"input": "test"}

    # Call handler directly (only 4 args, no queue param)
    await handler.handle("graphscout", agent_result, logs, input_data)

    # Verify target_agent was added to engine.queue
    assert "target_agent" in engine.queue


@pytest.mark.asyncio
async def test_graphscout_shortlist_picks_best(temp_config_file, monkeypatch):
    """Test that GraphScout handler picks best candidate from shortlist."""
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout"]}
    engine.queue = ["graphscout"]  # Initial queue

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    a_agent = MagicMock()
    a_agent.type = "simple"
    b_agent = MagicMock()
    b_agent.type = "simple"

    engine.agents = {"graphscout": graphscout, "a": a_agent, "b": b_agent}
    engine.memory = create_mock_memory()

    # Mock build_previous_outputs to return empty dict (avoid MagicMock issues)
    engine.build_previous_outputs = MagicMock(return_value={})

    # Provide a selector that returns the first candidate
    def select_best(shortlist_, question, context):
        return shortlist_[0]

    engine._select_best_candidate_from_shortlist = select_best

    handler = GraphScoutHandler(engine)

    # shortlist format: list of dicts with node_id
    shortlist = [{"node_id": "a"}, {"node_id": "b"}]
    agent_result = {"result": {"decision": "shortlist", "target": shortlist}}

    logs = []
    input_data = {"input": "test"}

    await handler.handle("graphscout", agent_result, logs, input_data)

    # 'a' should be added to engine.queue (first in shortlist)
    assert "a" in engine.queue
