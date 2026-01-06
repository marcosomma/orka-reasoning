import pytest

from unittest.mock import MagicMock

from orka.orchestrator.execution.response_normalizer import ResponseNormalizer


def test_normalize_loopnode_preserves_metadata(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    rn = ResponseNormalizer(eng)

    agent = MagicMock()
    agent.type = "loopnode"

    agent_result = {"result": {"result": "value", "loops_completed": 3, "final_score": 0.95, "threshold_met": True}}

    payload = rn.normalize(agent, "loop_agent", agent_result)

    assert payload["result"] == "value"
    assert payload["loops_completed"] == 3
    assert payload["final_score"] == 0.95
    assert payload["response"]["result"] == "value"


def test_normalize_llm_response(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    rn = ResponseNormalizer(eng)

    agent = MagicMock()
    agent.type = "llm_agent"

    agent_result = {"response": "hello", "formatted_prompt": "p", "_metrics": {"tokens": 5}}

    payload = rn.normalize(agent, "llm_agent", agent_result)

    assert payload["result"] == "hello"
    assert payload["formatted_prompt"] == "p"
    assert payload["_metrics"]["tokens"] == 5


def test_normalize_non_dict_tool_response(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    rn = ResponseNormalizer(eng)

    agent = MagicMock()
    agent.type = "tool"

    agent_result = "a simple string"

    payload = rn.normalize(agent, "tool_agent", agent_result)

    assert payload["result"] == "a simple string"
    assert payload["status"] == "success"


def test_normalize_preserves_confidence_and_internal_reasoning(temp_config_file):
    from orka.orchestrator.execution_engine import ExecutionEngine

    eng = ExecutionEngine(temp_config_file)
    rn = ResponseNormalizer(eng)

    agent = MagicMock()
    agent.type = "llm_agent"

    agent_result = {"response": "ok", "confidence": "0.87", "internal_reasoning": "some reason", "_metrics": {}}

    payload = rn.normalize(agent, "llm_agent", agent_result)

    # Confidence is normalized to float by normalize_payload
    assert payload["confidence"] == 0.87
    assert payload["internal_reasoning"] == "some reason"
    assert payload["response"] == "ok"
