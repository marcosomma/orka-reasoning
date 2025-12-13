"""Additional unit tests for MemoryWriterNode template helper functions.

This file targets the helper functions returned by MemoryWriterNode._get_template_helper_functions,
which contain many branches and are easy to exercise deterministically.

These tests avoid external services (Redis/LLM) and validate real behaviors to prevent
"mocking the test into passing".
"""

from unittest.mock import Mock

import pytest

from orka.nodes.memory_writer_node import MemoryWriterNode


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _make_node() -> MemoryWriterNode:
    return MemoryWriterNode(
        node_id="memory_writer",
        prompt="Test",
        queue=[],
        memory_logger=Mock(),
    )


def test_template_helpers_basic_input_and_loop_helpers():
    node = _make_node()

    payload = {
        "input": {"input": "hello", "loop_number": 3, "previous_outputs": {"past_loops": []}},
        "previous_outputs": {},
    }

    helpers = node._get_template_helper_functions(payload)

    assert helpers["get_input"]() == "hello"
    assert helpers["get_current_topic"]() == "hello"
    assert helpers["get_loop_number"]() == 3
    assert helpers["has_past_loops"]() is False
    assert helpers["get_past_loops"]() == []
    assert helpers["get_round_info"]() == "3"


def test_template_helpers_past_loops_insights_and_evolution():
    node = _make_node()

    payload = {
        "input": {
            "input": "topic",
            "loop_number": 2,
            "previous_outputs": {
                "past_loops": [
                    {"round": "1", "synthesis_insights": "insight1", "agreement_score": "0.4"},
                    {"round": "2", "synthesis_insights": "insight2", "agreement_score": "0.7"},
                ]
            },
        },
        "previous_outputs": {},
    }

    helpers = node._get_template_helper_functions(payload)

    assert helpers["has_past_loops"]() is True
    assert helpers["get_past_insights"]() == "insight2"
    assert helpers["get_past_loop_data"]("round") == "2"
    # With past loops, round info should come from last loop
    assert helpers["get_round_info"]() == "2"
    assert "Round 1" in helpers["get_debate_evolution"]()


def test_template_helpers_agent_response_and_safe_get_response():
    node = _make_node()

    payload = {
        "input": "x",
        "previous_outputs": {
            "agent_a": {"response": "A"},
            "agent_b": {"result": "B"},
        },
    }

    helpers = node._get_template_helper_functions(payload)

    assert helpers["get_agent_response"]("agent_a") == "A"
    assert helpers["safe_get_response"]("agent_a") == "A"
    # Note: get_agent_response uses the wording "No response from ..." for missing agents,
    # and safe_get_response only switches to fallback when the string starts with
    # "No response found".
    assert helpers["safe_get_response"]("missing_agent", fallback="F") == "No response from missing_agent"


def test_template_helpers_joined_results_and_fork_responses_multiple_shapes():
    node = _make_node()

    payload = {
        "input": "x",
        "previous_outputs": {
            "join_agent": {"joined_results": ["r1", "r2"]},
            "fork_group": {
                "agent1": {"response": "v1"},
                "result": {"agent2": {"response": "v2"}},
                "results": {"agent3": {"response": "v3"}},
            },
        },
    }

    helpers = node._get_template_helper_functions(payload)

    assert helpers["joined_results"]() == ["r1", "r2"]

    fork_responses = helpers["get_fork_responses"]("fork_group")
    assert fork_responses == {"agent1": "v1", "agent2": "v2", "agent3": "v3"}


def test_template_helpers_memory_context_helpers_filtering():
    node = _make_node()

    payload = {
        "input": "x",
        "previous_outputs": {
            "memory_reader": {"memories": ["note:abc", "decision:def"]},
            "some_agent": {"response": "decision text"},
        },
    }

    helpers = node._get_template_helper_functions(payload)

    assert "note:abc" in helpers["get_my_past_memory"](agent_type="note")
    assert helpers["get_my_past_decisions"]("some_agent") == "decision text"

    context = helpers["get_agent_memory_context"]("note", "some_agent")
    assert "Past Memory" in context
    assert "Past Decisions" in context
