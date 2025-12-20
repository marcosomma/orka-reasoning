import importlib
import asyncio
from datetime import datetime

TraceBuilder = importlib.import_module("orka.orchestrator.execution.trace_builder").TraceBuilder


class DummyMemory:
    def search_memories(self, query, node_id, num_results, log_type):
        return [{"key": "k", "timestamp": "t", "content": "hello world"}]

    def get_memory_stats(self):
        return {"count": 1}


class DummyOrch:
    def __init__(self):
        self.run_id = "run-1"
        self.memory = DummyMemory()


def test_trace_builder_builds_enhanced_trace():
    orch = DummyOrch()
    tb = TraceBuilder(orch)

    logs = [
        {
            "agent_id": "agent1",
            "event_type": "SomeAgent",
            "timestamp": datetime.now().isoformat(),
            "payload": {"prompt": "Hi {{ name }}", "formatted_prompt": "Hi Bob"},
        }
    ]

    trace = tb.build_enhanced_trace(logs)

    assert "execution_metadata" in trace
    assert "memory_stats" in trace
    assert trace["agent_executions"][0]["memory_references"][0]["key"] == "k"


def test_check_unresolved_variables_and_extracters():
    orch = DummyOrch()
    tb = TraceBuilder(orch)

    assert tb.check_unresolved_variables("Hi {{ name }}") is True
    vars = tb.extract_template_variables("Hi {{ name }} and {{ who }}")
    assert "name" in vars and "who" in vars
