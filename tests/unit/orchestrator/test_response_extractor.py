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


class TestControlFlowDetection:
    """Tests for control-flow node detection."""

    def test_is_control_flow_agent_fork(self):
        """Test ForkNode detection."""
        orch = DummyOrch()
        orch.agents = {"fork1": Agent("forknode", [])}
        re = ResponseExtractor(orch)
        assert re.is_control_flow_agent("fork1") is True

    def test_is_control_flow_agent_join(self):
        """Test JoinNode detection."""
        orch = DummyOrch()
        orch.agents = {"join1": Agent("joinnode", [])}
        re = ResponseExtractor(orch)
        assert re.is_control_flow_agent("join1") is True

    def test_is_control_flow_agent_router(self):
        """Test RouterNode detection."""
        orch = DummyOrch()
        orch.agents = {"router1": Agent("routernode", [])}
        re = ResponseExtractor(orch)
        assert re.is_control_flow_agent("router1") is True

    def test_is_control_flow_agent_graphscout(self):
        """Test GraphScout detection."""
        orch = DummyOrch()
        orch.agents = {"gs": Agent("graph-scout", [])}
        re = ResponseExtractor(orch)
        assert re.is_control_flow_agent("gs") is True

    def test_is_control_flow_agent_llm(self):
        """Test that LLM agents are not control-flow."""
        orch = DummyOrch()
        orch.agents = {"llm": Agent("local_llm", ["response_generation"])}
        re = ResponseExtractor(orch)
        assert re.is_control_flow_agent("llm") is False

    def test_is_control_flow_agent_unknown(self):
        """Test unknown agent returns False."""
        re = ResponseExtractor(DummyOrch())
        assert re.is_control_flow_agent("nonexistent") is False

    def test_control_flow_types_constant(self):
        """Verify CONTROL_FLOW_TYPES contains expected values."""
        assert "forknode" in ResponseExtractor.CONTROL_FLOW_TYPES
        assert "joinnode" in ResponseExtractor.CONTROL_FLOW_TYPES
        assert "routernode" in ResponseExtractor.CONTROL_FLOW_TYPES
        assert "loopnode" in ResponseExtractor.CONTROL_FLOW_TYPES
        assert "graph-scout" in ResponseExtractor.CONTROL_FLOW_TYPES
        assert "graphscout" in ResponseExtractor.CONTROL_FLOW_TYPES
