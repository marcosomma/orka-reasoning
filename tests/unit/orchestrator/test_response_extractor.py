import importlib

ResponseExtractor = importlib.import_module("orka.orchestrator.execution.response_extractor").ResponseExtractor


class DummyOrch:
    def __init__(self):
        self.agents = {}
        self.orchestrator_cfg = {"agents": []}


class Agent:
    def __init__(self, t, caps=None):
        self.type = t
        self.capabilities = caps or []


def test_is_response_builder_and_get_best():
    orch = DummyOrch()
    orch.agents = {
        "b1": Agent("local_llm", ["response_generation"]),
        "b2": Agent("response_builder", ["response_generation"]),
        "c": Agent("other", []),
    }
    orch.orchestrator_cfg = {"agents": ["c", "b1", "b2"]}

    re = ResponseExtractor(orch)
    assert re.is_response_builder("b1")
    result = re._get_best_response_builder()
    assert result in {"b1", "b2"}

    # If an agent id contains 'response_builder' it should be preferred
    orch.agents["response_builder"] = Agent("response_builder", ["response_generation"])
    orch.orchestrator_cfg = {"agents": ["b1", "response_builder"]}
    assert ResponseExtractor(orch)._get_best_response_builder() == "response_builder"


def test_extract_final_response_prefers_payload_response():
    re = ResponseExtractor(DummyOrch())
    logs = [
        {"agent_id": "a1", "event_type": "SomeNode", "payload": {"result": {"response": "x"}}},
        {"agent_id": "a2", "event_type": "MetaReport", "payload": {}},
    ]
    assert re.extract_final_response(logs) == "x"


def test_validate_and_enforce_terminal_agent():
    orch = DummyOrch()
    orch.agents = {"rb": Agent("response_builder", ["response_generation"])}
    orch.orchestrator_cfg = {"agents": ["rb"]}
    re = ResponseExtractor(orch)
    q = ["a", "b"]
    res = re.validate_and_enforce_terminal_agent(q)
    assert res[-1] == "rb"
