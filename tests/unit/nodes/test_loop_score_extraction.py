"""POC ② stabilization: behavioral tests for loop score extraction.

The score extractor was previously tested mostly by stubbing. These tests exercise
the real strategy ladder (pattern / direct_key / no-match) and pin down the new
opt-in `agreement_fallback` behavior that replaced the demo-specific agent-name magic.
"""

from __future__ import annotations

import asyncio

import pytest

from orka.nodes.loop.score_extractor import LoopScoreExtractor


def _extractor(score_extraction_config, high_priority_agents=None):
    return LoopScoreExtractor(
        node_id="t",
        score_calculator=None,  # skip boolean path; exercise legacy strategies
        scoring_preset=None,
        score_extraction_config=score_extraction_config,
        high_priority_agents=high_priority_agents or [],
    )


def test_pattern_strategy_extracts_score_from_response():
    ex = _extractor({"strategies": [{"type": "pattern", "patterns": [r"SCORE:\s*([0-9.]+)"]}]})
    result = {"scorer": {"response": "Analysis complete. SCORE: 0.75 — good."}}
    assert asyncio.run(ex.extract_score(result)) == 0.75


def test_direct_key_strategy():
    ex = _extractor({"strategies": [{"type": "direct_key", "key": "score"}]})
    result = {"score": 0.6, "agent": {"response": "whatever"}}
    assert asyncio.run(ex.extract_score(result)) == 0.6


def test_no_match_returns_zero():
    ex = _extractor({"strategies": [{"type": "pattern", "patterns": [r"SCORE:\s*([0-9.]+)"]}]})
    result = {"a": {"response": "no numeric score present here"}}
    assert asyncio.run(ex.extract_score(result)) == 0.0


def test_agreement_fallback_off_by_default_returns_zero():
    """Generic agents + no flag + no match -> 0.0 (NOT an agreement score)."""
    ex = _extractor({"strategies": []})
    result = {"agent_one": {"response": "x"}, "agent_two": {"response": "y"}}
    assert asyncio.run(ex.extract_score(result)) == 0.0


def test_agreement_fallback_opt_in_triggers_agreement(monkeypatch):
    ex = _extractor({"strategies": [], "agreement_fallback": True})

    async def fake_agreement(_result):
        return 0.42

    monkeypatch.setattr(ex, "_compute_agreement_score", fake_agreement)
    result = {"agent_one": {"response": "x"}, "agent_two": {"response": "y"}}
    assert asyncio.run(ex.extract_score(result)) == 0.42


def test_agent_names_no_longer_trigger_agreement(monkeypatch):
    """The hardcoded agent-name magic is removed: perspective-named agents must NOT
    trigger the agreement fallback unless agreement_fallback is explicitly set."""
    ex = _extractor({"strategies": []})  # no agreement_fallback flag

    async def fake_agreement(_result):
        return 0.55  # must NOT be reached

    monkeypatch.setattr(ex, "_compute_agreement_score", fake_agreement)
    result = {"progressive": {"response": "a"}, "conservative": {"response": "b"}}
    assert asyncio.run(ex.extract_score(result)) == 0.0  # name-magic gone -> no agreement
