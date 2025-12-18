import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from orka.orchestrator.execution.graphscout_handler import GraphScoutHandler


@pytest.mark.asyncio
async def test_graphscout_commit_path_executes_all_targets(temp_config_file, monkeypatch):
    from orka.orchestrator.execution_engine import ExecutionEngine
    from orka.orchestrator.execution.queue_processor import QueueProcessor

    engine = ExecutionEngine(temp_config_file)
    # Start with GraphScout as the only configured agent
    engine.orchestrator_cfg = {"agents": ["graphscout"]}

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

    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    engine.memory = mem

    async def runner(agent_id, input_data, previous_outputs, full_payload=None):
        if agent_id == "graphscout":
            # commit_path with list target
            return agent_id, {"decision": "commit_path", "target": ["a", "b"], "status": "success"}
        return agent_id, {"result": "ok"}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=runner))

    qp = QueueProcessor(engine)

    logs = []
    res = await qp.run_queue({"input": "test"}, logs, return_logs=True)

    # Should have executed a and b (memory.log called for them)
    called_agent_ids = [call.args[0] for call in mem.log.call_args_list]
    assert "a" in called_agent_ids and "b" in called_agent_ids
    assert isinstance(res, list)


@pytest.mark.asyncio
async def test_graphscout_validation_then_validator_routes_final_agent(temp_config_file, monkeypatch):
    from orka.orchestrator.execution_engine import ExecutionEngine
    from orka.orchestrator.execution.queue_processor import QueueProcessor

    engine = ExecutionEngine(temp_config_file)
    # Start with GraphScout as the only configured agent
    engine.orchestrator_cfg = {"agents": ["graphscout"]}

    graphscout = MagicMock()
    graphscout.type = "graph-scout"

    validator = MagicMock()
    validator.type = "routernode"  # validator will route to final_agent via its result

    final_agent = MagicMock()
    final_agent.type = "simple"

    engine.agents = {
        "graphscout": graphscout,
        "validator": validator,
        "final_agent": final_agent,
    }

    mem = MagicMock()
    mem.memory = []
    mem.log = MagicMock()
    engine.memory = mem

    # GraphScout returns a shortlist that selects 'validator'
    shortlist = [{"node_id": "validator"}, {"node_id": "other"}]

    async def runner(agent_id, input_data, previous_outputs, full_payload=None):
        if agent_id == "graphscout":
            return agent_id, {"result": {"decision": "shortlist", "target": shortlist}, "status": "success"}
        if agent_id == "validator":
            # Validator routes to final_agent
            return agent_id, {"result": ["final_agent"], "status": "success"}
        return agent_id, {"result": "ok"}

    monkeypatch.setattr(engine, "_run_agent_async", AsyncMock(side_effect=runner))

    # Provide a selection function that picks the validator
    def select_best(shortlist_, question, context):
        return shortlist_[0]

    engine._select_best_candidate_from_shortlist = select_best

    qp = QueueProcessor(engine)

    logs = []
    res = await qp.run_queue({"input": "test"}, logs, return_logs=True)

    # final_agent should have been executed
    called_agent_ids = [call.args[0] for call in mem.log.call_args_list]
    assert "final_agent" in called_agent_ids
    assert isinstance(res, list)
