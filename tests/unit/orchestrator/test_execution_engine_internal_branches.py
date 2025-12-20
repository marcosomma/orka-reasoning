import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


@pytest.fixture
def engine(temp_config_file):
    eng = ExecutionEngine(temp_config_file)
    eng.memory = MagicMock()
    eng.memory.memory = []
    eng.memory.log = MagicMock()
    eng.memory.set = MagicMock()
    eng.memory.hset = MagicMock()
    eng.memory.get_memory_stats = MagicMock(return_value={"count": 0})
    eng.memory.save_enhanced_trace = MagicMock()
    return eng


def test_ensure_complete_context_expands_common_patterns(engine):
    previous_outputs = {
        "memory_direct": {"memories": [{"content": "m1"}]},
        "llm_direct": {
            "response": "hello",
            "confidence": "0.9",
            "internal_reasoning": "because",
            "_metrics": {"tokens": 1},
            "formatted_prompt": "fp",
        },
        "nested_llm": {"result": {"response": "nested", "confidence": "0.1"}},
        "nested_memory": {
            "result": {
                "memories": [{"content": "m2"}],
                "query": "q",
                "backend": "b",
                "search_type": "s",
                "num_results": 2,
            }
        },
        "status_like": {"status": "ok", "fork_group": "g", "merged": {"a": 1}},
        "plain": "x",
    }

    enhanced = engine._ensure_complete_context(previous_outputs)

    assert enhanced["memory_direct"]["memories"][0]["content"] == "m1"
    assert enhanced["llm_direct"]["response"] == "hello"
    assert enhanced["nested_llm"]["response"] == "nested"
    assert enhanced["nested_memory"]["memories"][0]["content"] == "m2"
    assert enhanced["nested_memory"]["num_results"] == 2
    assert enhanced["status_like"]["status"] == "ok"
    assert enhanced["plain"] == "x"


def test_extract_final_response_prefers_nested_response(engine):
    logs = [
        {"agent_id": "meta_report", "event_type": "MetaReport", "payload": {}},
        {
            "agent_id": "agent_a",
            "event_type": "SomeAgent",
            "payload": {"result": {"response": "A"}},
        },
        {
            "agent_id": "agent_b",
            "event_type": "SomeAgent",
            "payload": {"result": {"result": {"response": "B"}}},
        },
    ]

    assert engine._extract_final_response(logs) == "B"


def test_simplify_agent_result_for_templates_covers_major_shapes(engine):
    assert engine._simplify_agent_result_for_templates({"response": "x"})["response"] == "x"

    nested = engine._simplify_agent_result_for_templates({"result": {"response": "y"}})
    assert nested["response"] == "y"
    assert nested["result"]["response"] == "y"

    mem = engine._simplify_agent_result_for_templates({"memories": [{"c": 1}], "query": "q"})
    assert mem["memories"][0]["c"] == 1
    assert mem["query"] == "q"

    merged = engine._simplify_agent_result_for_templates(
        {"merged": {"a": {"response": "ra"}, "b": {"response": "rb"}}}
    )
    assert merged["a_response"] == "ra"
    assert merged["b_response"] == "rb"


def test_build_template_context_flattens_input_and_previous_outputs(engine):
    payload = {
        "input": {"loop_number": 2, "user_input": "hi"},
        "previous_outputs": {
            "agent1": {"result": {"response": "r1"}},
            "agent2": {"memories": [{"content": "m"}]},
        },
    }

    ctx = engine._build_template_context(payload, agent_id="agentX")

    assert ctx["loop_number"] == 2
    assert ctx["user_input"] == "hi"
    assert ctx["agent_id"] == "agentX"
    assert "run_id" in ctx
    assert "current_time" in ctx

    prev = ctx["previous_outputs"]
    assert prev["agent1"]["response"] == "r1"
    assert prev["agent1_response"] == "r1"
    assert prev["agent2"]["memories"][0]["content"] == "m"
    assert prev["agent2_memories"][0]["content"] == "m"


def test_build_enhanced_trace_adds_template_resolution_and_memory_refs(engine):
    engine.memory.search_memories = MagicMock(
        return_value=[{"key": "k", "timestamp": "t", "content": "hello world"}]
    )

    logs = [
        {
            "agent_id": "agent1",
            "event_type": "SomeAgent",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "prompt": "Hi {{ name }}",
                "formatted_prompt": "Hi Bob",
            },
        }
    ]

    trace = engine._build_enhanced_trace(logs)

    assert "execution_metadata" in trace
    assert "memory_stats" in trace
    assert trace["agent_executions"][0]["memory_references"][0]["key"] == "k"

    tpl = trace["agent_executions"][0]["template_resolution"]
    assert tpl["has_template"] is True
    assert tpl["variable_count"] == 1


def test_validate_and_enforce_terminal_agent_appends_builder(engine):
    class RegularAgent:
        def __init__(self):
            self.type = "tool"
            self.capabilities = []

    class ResponseBuilderAgent:
        def __init__(self):
            self.type = "answer_builder"
            self.capabilities = ["response_generation"]

    engine.agents = {
        "a": RegularAgent(),
        "resp": ResponseBuilderAgent(),
    }
    engine.orchestrator_cfg["agents"] = ["a", "resp"]

    assert engine._validate_and_enforce_terminal_agent(["a"]) == ["a", "resp"]
    assert engine._validate_and_enforce_terminal_agent(["a", "resp"]) == ["a", "resp"]


def test_apply_memory_routing_logic_orders_readers_writers_and_appends_response_builder(engine):
    MemoryReaderNode = type("MemoryReaderNode", (), {})
    MemoryWriterNode = type("MemoryWriterNode", (), {})

    class ToolAgent:
        def __init__(self):
            self.type = "tool"
            self.capabilities = []

    class ResponseBuilderAgent:
        def __init__(self):
            self.type = "local_llm_response_builder"
            self.capabilities = ["response_generation"]

    engine.agents = {
        "mem_read": MemoryReaderNode(),
        "tool": ToolAgent(),
        "mem_write": MemoryWriterNode(),
        "resp": ResponseBuilderAgent(),
    }
    engine.orchestrator_cfg["agents"] = ["mem_read", "tool", "mem_write", "resp"]

    shortlist = [
        {"path": ["mem_read", "tool", "mem_write"], "node_id": "tool", "score": 0.8},
        {"node_id": "tool", "score": 0.5},
    ]

    sequence = engine._apply_memory_routing_logic(shortlist)

    assert sequence[0] == "mem_read"
    assert "tool" in sequence
    assert "mem_write" in sequence
    assert sequence[-1] == "resp"


@pytest.mark.asyncio
async def test_run_parallel_agents_raises_for_missing_agents(engine):
    engine.agents = {"a": SimpleNamespace(type="simple", run=lambda payload: {"result": "ok"})}

    with pytest.raises(ValueError, match="Missing agents"):
        await engine.run_parallel_agents(["a", "missing"], "fork_group_1", "x", {})


@pytest.mark.asyncio
async def test_run_parallel_agents_adds_formatted_prompt_and_wraps_non_dict_results(engine):
    class DictAgent:
        def __init__(self):
            self.type = "simple"
            self.prompt = "Hello {{ input }}"

        async def run(self, payload):
            return {"result": "d"}

    class StringAgent:
        def __init__(self):
            self.type = "simple"
            self.prompt = "Hello {{ input }}"

        async def run(self, payload):
            return "s"

    engine.agents = {
        "a": DictAgent(),
        "b": StringAgent(),
    }

    results = await engine.run_parallel_agents(["a", "b"], "fork_group_1", "INPUT", {})

    assert len(results) == 2
    by_id = {r["agent_id"]: r for r in results}

    assert by_id["a"]["payload"]["result"] == "d"
    assert by_id["a"]["payload"]["prompt"] == "Hello {{ input }}"
    assert "Hello INPUT" in by_id["a"]["payload"]["formatted_prompt"]

    assert by_id["b"]["payload"]["result"] == "s"
    assert by_id["b"]["payload"]["prompt"] == "Hello {{ input }}"
    assert "Hello INPUT" in by_id["b"]["payload"]["formatted_prompt"]

    # join-state and fork group result writes happen for each agent (join_state + group hash)
    assert engine.memory.hset.call_count == 4
    calls = [c.args for c in engine.memory.hset.call_args_list]
    join_calls = [call for call in calls if call[0] == "waitfor:fork_group_1:inputs"]
    group_calls = [call for call in calls if call[0] == f"fork_group_results:fork_group_1"]
    assert len(join_calls) == 2
    assert len(group_calls) == 2


@pytest.mark.asyncio
async def test_run_parallel_agents_emits_branch_error_log_without_sleep(engine, monkeypatch):
    class OkAgent:
        def __init__(self):
            self.type = "simple"
            self.prompt = "P"

    engine.agents = {"a": OkAgent(), "b": OkAgent()}

    async def fake_branch_with_retry(branch, input_data, previous_outputs, max_retries=2, retry_delay=1.0):
        if branch == ["a"]:
            raise RuntimeError("boom")
        return {"b": {"result": "ok"}}

    monkeypatch.setattr(engine, "_run_branch_with_retry", fake_branch_with_retry)

    results = await engine.run_parallel_agents(["a", "b"], "fork_group_1", "x", {})

    # Should include one BranchError and one normal log
    event_types = {r["event_type"] for r in results}
    assert "BranchError" in event_types
    assert any(et.startswith("ForkedAgent-") for et in event_types)
