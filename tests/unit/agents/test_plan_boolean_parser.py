"""POC ③: behavioral tests for the plan-validator boolean parser.

Covers the real parse paths: JSON, JSON-in-code-fence, value coercion, the
text-regex fallback, and malformed input (must not crash; returns a usable structure).
"""

from __future__ import annotations

import json

from orka.agents.plan_validator.boolean_parser import (
    parse_boolean_evaluation,
    _normalize_boolean_value,
)


def test_json_structure_with_two_dimensions():
    resp = json.dumps({
        "completeness": {"has_all_required_steps": True, "handles_edge_cases": False},
        "safety": {"validates_inputs": "yes", "has_timeout_protection": 0},
    })
    out = parse_boolean_evaluation(resp)
    assert out["completeness"]["has_all_required_steps"] is True
    assert out["completeness"]["handles_edge_cases"] is False
    # value coercion: "yes" -> True, 0 -> False
    assert out["safety"]["validates_inputs"] is True
    assert out["safety"]["has_timeout_protection"] is False


def test_json_in_code_fence_with_prose_around_it():
    resp = (
        "Here is my evaluation:\n```json\n"
        + json.dumps({"completeness": {"a": True}, "efficiency": {"b": True}})
        + "\n```\nHope that helps."
    )
    out = parse_boolean_evaluation(resp)
    assert out["completeness"]["a"] is True
    assert out["efficiency"]["b"] is True


def test_text_fallback_extracts_criterion_booleans():
    # No valid JSON -> regex fallback over "criterion: true/false" pairs.
    resp = "validates_inputs: true\nhandles_edge_cases: false\noptimizes_cost: yes"
    out = parse_boolean_evaluation(resp)
    # Fallback returns the canonical dimension buckets.
    assert set(out.keys()) == {"completeness", "efficiency", "safety", "coherence"}
    flat = {k: v for dim in out.values() for k, v in dim.items()}
    assert flat.get("validates_inputs") is True
    assert flat.get("handles_edge_cases") is False
    assert flat.get("optimizes_cost") is True


def test_malformed_input_does_not_crash():
    for junk in ["", "completely unstructured nonsense", "{not json at all", "12345"]:
        out = parse_boolean_evaluation(junk)
        assert isinstance(out, dict)
        # always returns the canonical buckets (possibly empty), never raises
        assert set(out.keys()) >= {"completeness", "efficiency", "safety", "coherence"} or out


def test_normalize_boolean_value_variants():
    assert _normalize_boolean_value(True) is True
    assert _normalize_boolean_value(False) is False
    for truthy in ("true", "YES", "1", "pass", "passed", "Y"):
        assert _normalize_boolean_value(truthy) is True, truthy
    for falsy in ("false", "no", "0", "maybe", ""):
        assert _normalize_boolean_value(falsy) is False, falsy
    assert _normalize_boolean_value(1) is True
    assert _normalize_boolean_value(0) is False
    assert _normalize_boolean_value(None) is False
