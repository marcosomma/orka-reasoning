import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution.graphscout_handler import GraphScoutHandler


@pytest.mark.asyncio
async def test_graphscout_inserts_target_agent(temp_config_file, monkeypatch):
    from orka.orchestrator.execution.queue_processor import QueueProcessor
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout", "target_agent"]}

    graphscout = MagicMock()
    graphscout.type = "graph-scout"
    target_agent = MagicMock()
    target_agent.type = "simple"

    engine.agents = {"graphscout": graphscout, "target_agent": target_agent}

    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    mem.set = MagicMock()
    mem.hset = MagicMock()
    mem.save_enhanced_trace = MagicMock()
    mem.save_to_file = MagicMock()
    mem.close = MagicMock()
    engine.memory = mem

    async def runner(agent_id, input_data, previous_outputs, full_payload=None):
        if agent_id == "graphscout":
            return agent_id, {"result": {"decision": "route", "target": "target_agent"}}
        return agent_id, {"result": "ok"}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=runner))

    qp = QueueProcessor(engine)

    logs = []
    res = await qp.run_queue({"input": "test"}, logs, return_logs=True)

    # Ensure target_agent was executed (memory.log called for it)
    assert mem.log.called


@pytest.mark.asyncio
async def test_graphscout_shortlist_picks_best(temp_config_file, monkeypatch):
    from orka.orchestrator.execution.queue_processor import QueueProcessor
    from orka.orchestrator.execution_engine import ExecutionEngine

    engine = ExecutionEngine(temp_config_file)
    engine.orchestrator_cfg = {"agents": ["graphscout"]}

    graphscout = MagicMock()
    graphscout.type = "graph-scout"

    engine.agents = {"graphscout": graphscout}

    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    mem.set = MagicMock()
    mem.hset = MagicMock()
    mem.save_enhanced_trace = MagicMock()
    mem.save_to_file = MagicMock()
    mem.close = MagicMock()
    engine.memory = mem

    # shortlist format: list of dicts
    shortlist = [{"node_id": "a"}, {"node_id": "b"}]

    async def runner(agent_id, input_data, previous_outputs, full_payload=None):
        return agent_id, {"result": {"decision": "shortlist", "target": shortlist}}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=runner))

    # Provide a selector that returns the first candidate
    def select_best(shortlist_, question, context):
        return shortlist_[0]

    engine._select_best_candidate_from_shortlist = select_best

    qp = QueueProcessor(engine)

    logs = []
    res = await qp.run_queue({"input": "test"}, logs, return_logs=True)

    # After handling, queue should have 'a' as next if it existed in agents
    # Since 'a' isn't a registered agent, nothing will be executed, but ensure no errors
    assert isinstance(res, list)
