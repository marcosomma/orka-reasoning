import asyncio

import pytest

from orka.nodes.path_executor_node import PathExecutorNode


def make_node(path_source="validated_path", on_agent_failure="continue"):
    return PathExecutorNode(node_id="p1", path_source=path_source, on_agent_failure=on_agent_failure)


def test_is_logical_agent_checks_patterns():
    node = make_node()
    assert node._is_logical_agent("graph_scout")
    assert node._is_logical_agent("GraphScoutRouter")
    assert node._is_logical_agent("path_validator")
    assert not node._is_logical_agent("my_agent")


def test_parse_agent_list_direct_list_and_graphscout_formats():
    node = make_node()

    # simple list
    data = ["a", "b", "graph_scout"]
    parsed = node._parse_agent_list(data)
    assert parsed == ["a", "b"]

    # graphscout candidate dicts with node_id and path entries
    data2 = [{"node_id": "x"}, {"node_id": "graphscout_router"}, {"path": ["p1", "p2"]}]
    parsed2 = node._parse_agent_list(data2)
    assert parsed2 == ["x", "p1", "p2"]


def test_extract_agent_path_uses_variants():
    # path_source with response/result nested
    node = make_node(path_source="validation_loop.response.result.graphscout_router")

    prev = {
        "validation_loop": {
            "response": {"result": {"graphscout_router": ["a", "b"]}}
        }
    }

    agent_path, error = node._extract_agent_path({"previous_outputs": prev})
    assert error is None
    assert agent_path == ["a", "b"]


def test_extract_agent_path_missing_previous_outputs_returns_error():
    node = make_node()
    agent_path, error = node._extract_agent_path({})
    assert agent_path == []
    assert error is not None


def test_validate_execution_context_missing_orchestrator():
    node = make_node()
    err = node._validate_execution_context({})
    assert "Orchestrator" in err


def test_validate_execution_context_orchestrator_missing_method():
    node = make_node()
    class FakeOrch:
        pass

    err = node._validate_execution_context({"orchestrator": FakeOrch()})
    assert "'_run_agent_async'" in err or "missing" in err


@pytest.mark.asyncio
async def test_execute_agent_sequence_handles_missing_and_success():
    node = make_node(on_agent_failure="continue")

    class FakeOrch:
        def __init__(self):
            self.agents = {"good": {}}

        async def _run_agent_async(self, agent_id, current_input, execution_results, full_payload=None):
            if agent_id == "good":
                return None, {"result": "ok"}
            raise RuntimeError("boom")

    orch = FakeOrch()

    context = {"orchestrator": orch, "input": "inp", "run_id": "r1"}

    # include one missing agent and one that exists but raises
    agent_path = ["missing", "good", "bad"]

    results, errors = await node._execute_agent_sequence(agent_path, context)

    # missing should be recorded in errors and as error in results
    assert any("not found" in e for e in errors)
    assert "missing" in results and "error" in results["missing"]

    # good should be present with result
    assert "good" in results and results["good"].get("result") == "ok"

    # bad should have an error recorded
    assert "bad" in results and "error" in results["bad"]
