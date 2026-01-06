"""Compliance scoring tests for PathScorer.

Validates that PathScorer can optionally include a compliance component that
penalizes paths missing required agents when a policy is provided in context
and a weight is configured.
"""

from unittest.mock import Mock

import pytest

from orka.orchestrator.path_scoring import PathScorer

pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _config_with_compliance() -> Mock:
    cfg = Mock()
    cfg.score_weights = {
        # Keep weights simple to make compliance impact visible
        "llm": 0.0,
        "heuristics": 0.0,
        "prior": 0.0,
        "cost": 0.0,
        "latency": 0.0,
        "compliance": 1.0,
    }
    cfg.scoring_mode = "numeric"
    cfg.k_beam = 3
    # Other attributes referenced by PathScorer
    cfg.max_reasonable_cost = 0.10
    cfg.path_length_penalty = 0.10
    cfg.keyword_match_boost = 0.30
    cfg.default_neutral_score = 0.50
    cfg.optimal_path_length = (2, 3)
    cfg.min_readiness_score = 0.30
    cfg.no_requirements_score = 0.90
    cfg.risky_capabilities = {"file_write", "code_execution", "external_api"}
    cfg.safety_markers = {"sandboxed", "read_only", "validated"}
    cfg.safe_default_score = 0.70
    # Also surface boolean guard flag through config
    cfg.require_critical = True
    return cfg


@pytest.mark.asyncio
async def test_compliance_penalty_applied_when_required_missing():
    scorer = PathScorer(_config_with_compliance())

    candidates = [
        {"node_id": "a", "path": ["search", "analysis", "answer"]},
        {"node_id": "b", "path": ["search", "answer"]},  # missing analysis
    ]

    policy = {"require_critical": True, "required_agents": ["analysis"]}
    context = {"graph_scout_policy": policy}

    # Make non-compliance clearly visible: neutralize other components
    async def fake_score_candidate(c, q, ctx):
        return {"llm": 0.0, "heuristics": 0.0, "prior": 0.0, "cost": 1.0, "latency": 1.0, "compliance": scorer._score_compliance(c, ctx)}  # type: ignore[attr-defined]

    scorer._score_candidate = fake_score_candidate  # type: ignore[method-assign]

    ranked = await scorer.score_candidates(candidates, question="q", context=context)

    assert ranked[0]["path"] == ["search", "analysis", "answer"]
    assert ranked[0]["score"] == 1.0
    # Non-compliant paths get near-zero score (0.01) as a hard filter
    assert ranked[1]["score"] == 0.01


@pytest.mark.asyncio
async def test_no_penalty_when_policy_absent():
    scorer = PathScorer(_config_with_compliance())

    candidates = [
        {"node_id": "a", "path": ["x", "y"]},
        {"node_id": "b", "path": ["y"]},
    ]

    # No policy in context -> compliance component treated as neutral (1.0)
    async def fake_score_candidate(c, q, ctx):
        comp = scorer._score_compliance(c, ctx)  # type: ignore[attr-defined]
        return {"llm": 0.0, "heuristics": 0.0, "prior": 0.0, "cost": 1.0, "latency": 1.0, "compliance": comp}

    scorer._score_candidate = fake_score_candidate  # type: ignore[method-assign]

    ranked = await scorer.score_candidates(candidates, question="q", context={})

    # With identical components and compliance=1.0, ordering preserved
    assert len(ranked) == 2
    assert ranked[0]["score"] == ranked[1]["score"] == 1.0
