from __future__ import annotations

import pytest

from orka.nodes.loop.log_result_extractor import extract_agent_results_from_logs


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def test_extract_payload_result_strategy():
    logs = [
        {"agent_id": "a1", "payload": {"result": {"response": "ok"}}},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert executed == ["a1"]
    assert res["a1"]["response"] == "ok"
    assert stats.successful_extractions == 1


def test_extract_orchestrator_payload_result_strategy_records_method():
    logs = [
        {"agent_id": "a1", "event_type": "LocalLLMAgent", "payload": {"result": {"response": "ok"}}},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert executed == ["a1"]
    assert res["a1"]["response"] == "ok"
    assert stats.extraction_methods.get("orchestrator.payload.result") == 1


def test_extract_orchestrator_payload_response_strategy_wraps_response():
    logs = [
        {"agent_id": "a1", "event_type": "LocalLLMAgent", "payload": {"response": "hello"}},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert executed == ["a1"]
    assert res["a1"]["response"] == "hello"
    assert stats.extraction_methods.get("orchestrator.payload.response") == 1


def test_extract_orchestrator_payload_result_preserves_nested_shape():
    nested = {"result": {"response": "ok"}}
    logs = [
        {"agent_id": "a1", "event_type": "SomeNode", "payload": {"result": nested}},
    ]
    res, _, _ = extract_agent_results_from_logs(logs)
    assert res["a1"] == nested


def test_extract_direct_result_strategy():
    logs = [
        {"agent_id": "a1", "result": {"response": "ok"}},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert res["a1"]["response"] == "ok"
    assert stats.extraction_methods.get("direct_result") == 1


def test_skips_meta_report_entries():
    logs = [
        {"event_type": "MetaReport", "agent_id": "a1", "payload": {"result": {"response": "x"}}},
        {"agent_id": "a1", "payload": {"result": {"response": "ok"}}},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert res["a1"]["response"] == "ok"
    assert stats.agent_entries == 1


def test_response_pattern_strategy():
    logs = [
        {"agent_id": "a1", "content": "hello"},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs)
    assert res["a1"]["response"] == "hello"
    assert stats.extraction_methods.get("response_pattern") == 1


def test_legacy_fallback_can_be_disabled_for_content_search():
    # This log entry would previously be captured by the loose "content_search" heuristic.
    logs = [
        {"agent_id": "a1", "message": "AGREEMENT_SCORE: 0.9"},
    ]
    res, executed, stats = extract_agent_results_from_logs(logs, legacy_fallback=False)
    assert executed == ["a1"]
    assert "a1" not in res
    assert stats.successful_extractions == 0


