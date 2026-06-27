"""P3 regression: the normalizer must not drop confidence/cost from a wrapped OrkaResponse.

Before the fix, BaseAgent.run wrapped LLM output as
    {result: {response, confidence, cost_usd, _metrics}, status, component_type: "agent", ...}
and the normalizer routed it to from_node_response (no top-level "response" key),
silently defaulting confidence to 0.0 and dropping cost_usd.
"""

from __future__ import annotations

from orka.orchestrator.execution.response_normalizer import ResponseNormalizer
from orka.response_builder import ResponseBuilder


class _FakeEngine:
    pass


def _wrapped_llm_orkaresponse():
    """Exactly what BaseAgent.run produces for an LLM agent."""
    inner = {
        "response": "the answer",
        "confidence": "0.87",
        "internal_reasoning": "because",
        "cost_usd": 0.0123,
        "token_usage": {"total_tokens": 42},
        "_metrics": {"latency_ms": 10},
    }
    return ResponseBuilder.create_success_response(
        result=inner,
        component_id="llm_agent",
        component_type="agent",
        metadata={"agent_type": "OpenAIAnswerBuilder"},
    )


def test_wrapped_orkaresponse_preserves_confidence_and_cost():
    rn = ResponseNormalizer(_FakeEngine())
    payload = rn.normalize(agent=None, agent_id="llm_agent", agent_result=_wrapped_llm_orkaresponse())

    # The fields that were previously lost:
    assert payload["confidence"] == 0.87, f"confidence lost/defaulted: {payload.get('confidence')}"
    assert payload["cost_usd"] == 0.0123, f"cost dropped: {payload.get('cost_usd')}"
    # And the actual answer + reasoning survive:
    assert payload["response"] == "the answer"
    assert payload["result"] == "the answer"
    assert payload["internal_reasoning"] == "because"
    assert payload["status"] == "success"


def test_demonstrates_old_path_would_have_dropped_them():
    """Sanity: routing the SAME object through from_node_response (the old path) loses them."""
    wrapped = _wrapped_llm_orkaresponse()
    old = ResponseBuilder.from_node_response(wrapped, "llm_agent")
    # from_node_response never extracts confidence/cost -> proves the bug existed.
    assert "confidence" not in old or old.get("confidence") in (None, 0.0)
    assert old.get("cost_usd") is None


def test_raw_legacy_dict_still_works():
    """The pre-existing raw-dict path is unchanged (no component_type -> skip new branch)."""
    rn = ResponseNormalizer(_FakeEngine())
    payload = rn.normalize(
        agent=None,
        agent_id="llm_agent",
        agent_result={"response": "ok", "confidence": "0.5", "internal_reasoning": "r", "_metrics": {}},
    )
    assert payload["confidence"] == 0.5
    assert payload["response"] == "ok"
