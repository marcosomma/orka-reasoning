"""Additional unit tests for orka.orchestrator.path_scoring.

The existing suite covers the happy-path, but a few branches remain under-tested.
These tests aim to exercise:
- LLM relevance fallback scoring (keyword boost + path penalty)
- Input readiness scoring using required_inputs
- Safety fit scoring with risky capabilities and safety tags
- Numeric candidate scoring ordering + beam limiting
"""

from unittest.mock import Mock

import pytest

from orka.orchestrator.path_scoring import PathScorer


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _config() -> Mock:
    config = Mock()
    # IMPORTANT: match actual component keys used by PathScorer
    config.score_weights = {
        "llm": 0.3,
        "heuristics": 0.2,
        "prior": 0.2,
        "cost": 0.15,
        "latency": 0.15,
    }
    config.scoring_mode = "numeric"
    config.k_beam = 2

    config.max_reasonable_cost = 0.10
    config.path_length_penalty = 0.10
    config.keyword_match_boost = 0.30
    config.default_neutral_score = 0.50
    config.optimal_path_length = (2, 3)

    config.min_readiness_score = 0.30
    config.no_requirements_score = 0.90

    config.risky_capabilities = {"file_write", "code_execution", "external_api"}
    config.safety_markers = {"sandboxed", "read_only", "validated"}
    config.safe_default_score = 0.70
    return config


@pytest.mark.asyncio
async def test_score_llm_relevance_fallback_keyword_boost_and_path_penalty():
    scorer = PathScorer(_config())

    candidate = {"node_id": "search_agent", "path": ["a", "b", "c", "d"]}
    score = await scorer._score_llm_relevance(candidate, question="please search this", context={})

    # Keyword boost (+0.30) and long path penalty (-0.10)
    assert 0.0 <= score <= 1.0
    assert score >= 0.6


def test_check_input_readiness_required_inputs_present_and_missing():
    scorer = PathScorer(_config())

    agent = Mock()
    agent.required_inputs = ["a", "b"]

    orchestrator = Mock()
    orchestrator.agents = {"agent1": agent}

    # Both available
    context_ok = {"orchestrator": orchestrator, "previous_outputs": {"a": 1, "b": 2}}
    readiness_ok = scorer._check_input_readiness({"node_id": "agent1"}, context_ok)
    assert readiness_ok == 1.0

    # One missing -> partial readiness, but clamped to min_readiness_score
    context_partial = {"orchestrator": orchestrator, "previous_outputs": {"a": 1}}
    readiness_partial = scorer._check_input_readiness({"node_id": "agent1"}, context_partial)
    assert scorer.min_readiness_score <= readiness_partial < 1.0


def test_check_safety_fit_risky_capability_with_and_without_safety_tag():
    scorer = PathScorer(_config())

    risky_agent_safe = Mock()
    risky_agent_safe.capabilities = ["code_execution"]
    risky_agent_safe.safety_tags = ["sandboxed"]

    risky_agent_unsafe = Mock()
    risky_agent_unsafe.capabilities = ["code_execution"]
    risky_agent_unsafe.safety_tags = []

    orchestrator = Mock()
    orchestrator.agents = {
        "safe_agent": risky_agent_safe,
        "unsafe_agent": risky_agent_unsafe,
    }

    context = {"orchestrator": orchestrator}

    s1 = scorer._check_safety_fit({"node_id": "safe_agent"}, context)
    s2 = scorer._check_safety_fit({"node_id": "unsafe_agent"}, context)

    assert s1 > s2
    assert 0.0 <= s1 <= 1.0
    assert 0.0 <= s2 <= 1.0


@pytest.mark.asyncio
async def test_score_candidates_numeric_orders_and_applies_k_beam():
    scorer = PathScorer(_config())

    # Make heuristics/prior deterministic without mocking the whole function away
    async def score_candidate(candidate, question, context):
        # Force different final scores based on node_id
        base = 0.9 if candidate["node_id"] == "best" else 0.2
        return {"llm": base, "heuristics": base, "prior": base, "cost": base, "latency": base}

    scorer._score_candidate = score_candidate  # type: ignore[method-assign]

    candidates = [
        {"node_id": "worst", "path": ["worst"], "estimated_cost": 0.05, "estimated_latency": 5000},
        {"node_id": "best", "path": ["best"], "estimated_cost": 0.001, "estimated_latency": 200},
        {"node_id": "mid", "path": ["mid"], "estimated_cost": 0.01, "estimated_latency": 1000},
    ]

    ranked = await scorer.score_candidates(candidates, question="q", context={})

    # Beam width keeps top 2
    assert len(ranked) == 2
    assert ranked[0]["node_id"] == "best"
    assert ranked[0]["score"] >= ranked[1]["score"]
