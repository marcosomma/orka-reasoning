import importlib.util
import pathlib
from datetime import datetime

# Load the context_manager module directly to avoid importing the whole package
cm_path = pathlib.Path(__file__).resolve().parents[3] / "orka" / "orchestrator" / "execution" / "context_manager.py"
spec = importlib.util.spec_from_file_location("context_manager", str(cm_path))
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)

ContextManager = cm.ContextManager


class DummyOrch:
    run_id = "run-1"
    step_index = 1
    workflow_name = "wf"


def test_ensure_complete_context_various_patterns():
    ctx = ContextManager(DummyOrch())

    prev = {
        "mem_node": {"memories": [1, 2, 3]},
        "llm_node": {"response": "hello", "confidence": "0.9"},
        "nested_node": {"result": {"response": "ok", "_metrics": {"t": 1}}},
        "fork_node": {"status": "success", "fork_group": "g1", "merged": {"a": {"response": "r"}}},
        "plain": "simple",
    }

    enhanced = ctx.ensure_complete_context(prev)

    assert "mem_node" in enhanced and "memories" in enhanced["mem_node"]
    assert "llm_node" in enhanced and enhanced["llm_node"]["response"] == "hello"
    assert "nested_node" in enhanced and enhanced["nested_node"]["response"] == "ok"
    assert "fork_node" in enhanced and enhanced["fork_node"]["status"] == "success"
    assert enhanced["plain"] == "simple"


def test_simplify_agent_result_for_templates():
    ctx = ContextManager(DummyOrch())

    r1 = {"response": "hi", "confidence": "0.5"}
    s1 = ctx.simplify_agent_result_for_templates(r1)
    assert s1["response"] == "hi"
    assert s1["confidence"] == "0.5"

    r2 = {"result": {"response": "ok", "_metrics": {"a": 1}}}
    s2 = ctx.simplify_agent_result_for_templates(r2)
    assert s2["response"] == "ok"
    assert s2["_metrics"] == {"a": 1}

    r3 = {"memories": ["m1"], "query": "q"}
    s3 = ctx.simplify_agent_result_for_templates(r3)
    assert "memories" in s3


def test_build_template_context_flattening():
    ctx = ContextManager(DummyOrch())
    payload = {
        "input": {"user_input": "hey"},
        "previous_outputs": {"n1": {"result": {"response": "resp"}}},
    }
    tctx = ctx.build_template_context(payload, "agent_x")

    assert tctx["user_input"] == "hey"
    assert "n1" in tctx["previous_outputs"]
    assert tctx["previous_outputs"]["n1"]["response"] == "resp"
