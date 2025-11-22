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


def test_is_control_flow_node_detects_by_id_pattern():
    """Test that _is_control_flow_node detects control flow nodes by ID pattern."""
    node = make_node()
    context = {}
    
    # PathExecutor patterns
    assert node._is_control_flow_node("path_executor", context)
    assert node._is_control_flow_node("PathExecutor", context)
    assert node._is_control_flow_node("my_pathexecutor", context)
    
    # GraphScout patterns
    assert node._is_control_flow_node("graph_scout", context)
    assert node._is_control_flow_node("GraphScout_Router", context)
    assert node._is_control_flow_node("graphscout", context)
    
    # Validator patterns
    assert node._is_control_flow_node("validator", context)
    assert node._is_control_flow_node("plan_validator", context)
    assert node._is_control_flow_node("MyValidator", context)
    
    # Classifier patterns
    assert node._is_control_flow_node("classifier", context)
    assert node._is_control_flow_node("query_classifier", context)
    
    # Regular agents should return False
    assert not node._is_control_flow_node("web_search", context)
    assert not node._is_control_flow_node("analyzer", context)
    assert not node._is_control_flow_node("summarizer", context)


def test_is_control_flow_node_detects_by_agent_type():
    """Test that _is_control_flow_node detects control flow nodes by agent type."""
    node = make_node()
    
    # Mock orchestrator with agents
    class MockAgent:
        def __init__(self, agent_type, class_name):
            self.type = agent_type
            self.__class__.__name__ = class_name
    
    class MockOrchestrator:
        def __init__(self):
            self.agents = {
                "custom_executor": MockAgent("path_executor", "CustomExecutor"),
                "my_scout": MockAgent("graph_scout", "MyScout"),
                "val": MockAgent("plan_validator", "PlanValidator"),
                "regular": MockAgent("local_llm", "LocalLLMAgent"),
            }
    
    context = {"orchestrator": MockOrchestrator()}
    
    # Should detect by type
    assert node._is_control_flow_node("custom_executor", context)
    assert node._is_control_flow_node("my_scout", context)
    assert node._is_control_flow_node("val", context)
    
    # Regular agent should return False
    assert not node._is_control_flow_node("regular", context)


def test_is_control_flow_node_detects_by_class_name():
    """Test that _is_control_flow_node detects control flow nodes by class name."""
    node = make_node()
    
    # Mock orchestrator with agents
    class PathExecutorNode:
        def __init__(self):
            self.type = "executor"
    
    class GraphScoutAgent:
        def __init__(self):
            self.type = "router"
    
    class PlanValidatorNode:
        def __init__(self):
            self.type = "validation"
    
    class RegularAgent:
        def __init__(self):
            self.type = "local_llm"
    
    class MockOrchestrator:
        def __init__(self):
            self.agents = {
                "exec": PathExecutorNode(),
                "scout": GraphScoutAgent(),
                "val": PlanValidatorNode(),
                "regular": RegularAgent(),
            }
    
    context = {"orchestrator": MockOrchestrator()}
    
    # Should detect by class name
    assert node._is_control_flow_node("exec", context)
    assert node._is_control_flow_node("scout", context)
    assert node._is_control_flow_node("val", context)
    
    # Regular agent should return False
    assert not node._is_control_flow_node("regular", context)


def test_is_control_flow_node_handles_missing_orchestrator():
    """Test that _is_control_flow_node handles missing orchestrator gracefully."""
    node = make_node()
    
    # Context without orchestrator - should fallback to ID-based check
    context = {}
    assert node._is_control_flow_node("path_executor", context)
    assert not node._is_control_flow_node("web_search", context)


def test_is_control_flow_node_handles_exceptions():
    """Test that _is_control_flow_node handles exceptions gracefully."""
    node = make_node()
    
    # Orchestrator that raises exception
    class BrokenOrchestrator:
        @property
        def agents(self):
            raise RuntimeError("Boom!")
    
    context = {"orchestrator": BrokenOrchestrator()}
    
    # Should fallback to ID-based check
    assert node._is_control_flow_node("path_executor", context)
    assert not node._is_control_flow_node("web_search", context)


@pytest.mark.asyncio
async def test_run_impl_filters_control_flow_nodes_from_path():
    """Test that _run_impl filters control flow nodes from extracted path."""
    node = make_node(path_source="path_proposal")
    
    # Mock orchestrator
    class MockAgent:
        def __init__(self, agent_type):
            self.type = agent_type
            self.__class__.__name__ = "MockAgent"
    
    class MockOrchestrator:
        def __init__(self):
            self.agents = {
                "web_search": MockAgent("duckduckgo"),
                "analyzer": MockAgent("local_llm"),
                "execute_path": MockAgent("path_executor"),
            }
        
        async def _run_agent_async(self, agent_id, current_input, execution_results, full_payload=None):
            return None, {"result": f"output_{agent_id}"}
    
    context = {
        "orchestrator": MockOrchestrator(),
        "input": "test input",
        "run_id": "test_run",
        "previous_outputs": {
            "path_proposal": ["web_search", "execute_path", "analyzer"]
        }
    }
    
    result = await node._run_impl(context)
    
    # Should have filtered out execute_path
    assert result["status"] == "success"
    assert "web_search" in result["executed_path"]
    assert "analyzer" in result["executed_path"]
    assert "execute_path" not in result["executed_path"]
    
    # Should have results for non-control flow nodes only
    assert "web_search" in result["results"]
    assert "analyzer" in result["results"]
    assert "execute_path" not in result["results"]


@pytest.mark.asyncio
async def test_run_impl_filters_self_from_path():
    """Test that _run_impl filters its own node_id from extracted path."""
    node = make_node(path_source="path_proposal")
    node.node_id = "execute_path"
    
    # Mock orchestrator
    class MockAgent:
        def __init__(self):
            self.type = "duckduckgo"
    
    class MockOrchestrator:
        def __init__(self):
            self.agents = {
                "web_search": MockAgent(),
                "execute_path": MockAgent(),
            }
        
        async def _run_agent_async(self, agent_id, current_input, execution_results, full_payload=None):
            return None, {"result": f"output_{agent_id}"}
    
    context = {
        "orchestrator": MockOrchestrator(),
        "input": "test input",
        "run_id": "test_run",
        "previous_outputs": {
            "path_proposal": ["web_search", "execute_path"]
        }
    }
    
    result = await node._run_impl(context)
    
    # Should have filtered out self (execute_path)
    assert result["status"] == "success"
    assert "web_search" in result["executed_path"]
    assert "execute_path" not in result["executed_path"]
    assert len(result["executed_path"]) == 1
