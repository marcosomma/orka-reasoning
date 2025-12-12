import json

import pytest

from orka.nodes.loop_node import LoopNode


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def test_create_safe_result_handles_circular_and_excludes_keys():
    node = LoopNode("test_node")

    circular: dict[str, object] = {"a": 1}
    circular["self"] = circular

    payload = {
        "ok": "value",
        "previous_outputs": {"should": "be removed"},
        "payload": {"should": "be removed"},
        "nested": circular,
    }

    safe = node._create_safe_result(payload)

    assert isinstance(safe, dict)
    assert "previous_outputs" not in safe
    assert "payload" not in safe
    assert safe["ok"] == "value"

    # Circular references must not blow up serialization
    assert "nested" in safe
    assert "<circular_reference>" in json.dumps(safe)


def test_create_safe_result_with_context_preserves_agent_response_and_past_loops():
    node = LoopNode("test_node")

    very_long = "x" * 3000
    result = {
        "past_loops": [{"loop_number": 1, "score": 0.8}],
        "progressive_agent": {"response": very_long, "confidence": 0.9, "_metrics": {"a": 1}},
        "some_other": {"payload": {"nested": "should be skipped"}, "value": 123},
    }

    safe = node._create_safe_result_with_context(result)

    assert isinstance(safe, dict)
    assert "past_loops" in safe
    assert isinstance(safe["past_loops"], list)
    assert safe["past_loops"][0]["loop_number"] == 1

    assert "progressive_agent" in safe
    assert "response" in safe["progressive_agent"]
    assert isinstance(safe["progressive_agent"]["response"], str)
    assert len(safe["progressive_agent"]["response"]) <= 2000 + len("...<truncated_for_safety>")

    # It should not carry through raw 'payload' keys.
    assert "payload" not in safe.get("some_other", {})


def test_extract_secondary_metric_supports_dict_json_python_and_regex():
    node = LoopNode("test_node")

    result = {
        "agent_dict": {"response": {"REASONING_QUALITY": 0.88}},
        "agent_json": {
            "response": json.dumps({"CONVERGENCE_TREND": "IMPROVING", "REASONING_QUALITY": 0.77})
        },
        "agent_py": {"response": "{'REASONING_QUALITY': 0.66, 'OTHER': 'x'}"},
        "agent_regex": {"response": "REASONING_QUALITY: 0.55"},
    }

    rq = node._extract_secondary_metric(result, "REASONING_QUALITY")
    assert isinstance(rq, (float, int))
    assert rq in {0.88, 0.77, 0.66, 0.55}

    trend = node._extract_secondary_metric(result, "CONVERGENCE_TREND", default="STABLE")
    assert trend == "IMPROVING"

    missing = node._extract_secondary_metric(result, "NOT_PRESENT", default="DEFAULT")
    assert missing == "DEFAULT"


def test_extract_cognitive_insights_uses_patterns_and_dedupes():
    node = LoopNode("test_node")
    node.cognitive_extraction = {
        "enabled": True,
        "extract_patterns": {
            "insights": [r"insight:\s*(.+?)(?:\n|$)"],
            "improvements": [r"improvement:\s*(.+?)(?:\n|$)"],
            "mistakes": [r"mistake:\s*(.+?)(?:\n|$)"],
        },
        "max_length_per_category": 200,
    }

    result = {
        "agent_a": {
            "response": "insight: Use caching\nimprovement: Add unit tests\nmistake: Missing edge-case"
        },
        "agent_b": {
            "response": "insight: Use caching\nimprovement: Add more docs\n"
        },
    }

    insights = node._extract_cognitive_insights(result)
    assert "Use caching" in insights["insights"]
    assert insights["insights"].count("Use caching") == 1  # de-dup
    assert "Add unit tests" in insights["improvements"]
    assert "Add more docs" in insights["improvements"]
    assert "Missing edge-case" in insights["mistakes"]


def test_create_past_loop_object_renders_metadata_templates():
    node = LoopNode("test_node")
    node.cognitive_extraction = {
        "enabled": True,
        "extract_patterns": {
            "insights": [r"insight:\s*(.+?)(?:\n|$)"],
            "improvements": [],
            "mistakes": [],
        },
    }
    node.past_loops_metadata = {
        "loop_number": "{{ loop_number }}",
        "score": "{{ '%.2f' % score }}",
        "timestamp": "{{ timestamp }}",
        "insights": "{{ insights }}",
    }

    loop_result = {"agent": {"response": "insight: Keep prompts short"}}
    past = node._create_past_loop_object(loop_number=2, score=0.8123, result=loop_result, original_input="hi")

    assert past["loop_number"] == "2"
    assert past["score"] == "0.81"
    assert "Keep prompts short" in str(past.get("insights", ""))
