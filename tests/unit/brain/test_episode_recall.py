"""Unit tests for orka.brain.episode_recall — EpisodeRecaller scoring and formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orka.brain.episode import Episode
from orka.brain.episode_recall import (
    EpisodeMatch,
    EpisodeRecaller,
    WEIGHT_SEMANTIC,
    WEIGHT_RECENCY,
    WEIGHT_DOMAIN,
    WEIGHT_OUTCOME,
)


def _make_episode(
    domain: str = "test",
    success: bool = True,
    age_hours: float = 0.0,
    **kwargs,
) -> Episode:
    ts = datetime.now(UTC) - timedelta(hours=age_hours)
    return Episode(
        task_input=kwargs.get("task_input", f"Task in {domain}"),
        task_domain=domain,
        success=success,
        quality_score=kwargs.get("quality_score", 0.8 if success else 0.2),
        outcome_summary=kwargs.get("outcome_summary", "Completed"),
        what_worked=kwargs.get("what_worked", []),
        what_failed=kwargs.get("what_failed", []),
        failure_analysis=kwargs.get("failure_analysis", None),
        lessons=kwargs.get("lessons", []),
        timestamp=ts,
    )


class TestEpisodeRecallerScore:
    """Tests for the score() method."""

    def test_score_returns_episode_match(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode()
        match = recaller.score(ep, semantic_similarity=0.8, query_domain="test")
        assert isinstance(match, EpisodeMatch)
        assert match.episode is ep
        assert match.semantic_score == 0.8

    def test_recency_recent_episode_high(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(age_hours=0.5)
        match = recaller.score(ep, semantic_similarity=0.5)
        assert match.recency_score > 0.95  # Very recent

    def test_recency_old_episode_decays(self) -> None:
        recaller = EpisodeRecaller(half_life_hours=168)
        ep = _make_episode(age_hours=168)  # 1 week old
        match = recaller.score(ep, semantic_similarity=0.5)
        assert 0.45 < match.recency_score < 0.55  # ~50% after 1 half-life

    def test_domain_match_same(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(domain="analytics")
        match = recaller.score(ep, semantic_similarity=0.5, query_domain="analytics")
        assert match.domain_score == 1.0

    def test_domain_match_different(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(domain="analytics")
        match = recaller.score(ep, semantic_similarity=0.5, query_domain="engineering")
        assert match.domain_score == 0.0

    def test_domain_match_unknown(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(domain="analytics")
        match = recaller.score(ep, semantic_similarity=0.5, query_domain=None)
        assert match.domain_score == 0.5  # Neutral

    def test_outcome_failure_scores_higher(self) -> None:
        recaller = EpisodeRecaller()
        ep_fail = _make_episode(success=False)
        ep_ok = _make_episode(success=True)
        match_fail = recaller.score(ep_fail, semantic_similarity=0.5)
        match_ok = recaller.score(ep_ok, semantic_similarity=0.5)
        assert match_fail.outcome_relevance > match_ok.outcome_relevance

    def test_outcome_bonus_failure_analysis(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(success=False, failure_analysis="Schema mismatch")
        match = recaller.score(ep, semantic_similarity=0.5)
        # 0.7 (failure) + 0.2 (analysis) = 0.9
        assert abs(match.outcome_relevance - 0.9) < 1e-9

    def test_outcome_bonus_many_lessons(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(
            success=True,
            lessons=["lesson1", "lesson2", "lesson3"],
        )
        match = recaller.score(ep, semantic_similarity=0.5)
        # 0.3 (success) + 0.1 (>=3 lessons) = 0.4
        assert match.outcome_relevance == 0.4

    def test_combined_score_uses_weights(self) -> None:
        recaller = EpisodeRecaller()
        now = datetime.now(UTC)
        ep = _make_episode(domain="test", success=True, age_hours=0)
        match = recaller.score(
            ep,
            semantic_similarity=1.0,
            query_domain="test",
            now=now,
        )
        # semantic=1.0*0.5 + recency≈1.0*0.2 + domain=1.0*0.2 + outcome=0.3*0.1
        expected = 1.0 * 0.5 + 1.0 * 0.2 + 1.0 * 0.2 + 0.3 * 0.1
        assert abs(match.combined_score - expected) < 0.02

    def test_injection_text_populated(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(outcome_summary="Built parser OK")
        match = recaller.score(ep, semantic_similarity=0.8)
        assert "Built parser OK" in match.injection_text


class TestEpisodeRecallerRank:
    """Tests for rank() method."""

    def test_rank_sorts_by_combined_score(self) -> None:
        recaller = EpisodeRecaller()
        matches = [
            EpisodeMatch(episode=_make_episode(), combined_score=0.3),
            EpisodeMatch(episode=_make_episode(), combined_score=0.9),
            EpisodeMatch(episode=_make_episode(), combined_score=0.6),
        ]
        ranked = recaller.rank(matches)
        assert ranked[0].combined_score == 0.9
        assert ranked[1].combined_score == 0.6
        assert ranked[2].combined_score == 0.3

    def test_rank_filters_by_min_score(self) -> None:
        recaller = EpisodeRecaller()
        matches = [
            EpisodeMatch(episode=_make_episode(), combined_score=0.1),
            EpisodeMatch(episode=_make_episode(), combined_score=0.5),
            EpisodeMatch(episode=_make_episode(), combined_score=0.9),
        ]
        ranked = recaller.rank(matches, min_score=0.4)
        assert len(ranked) == 2
        assert all(m.combined_score >= 0.4 for m in ranked)

    def test_rank_empty_list(self) -> None:
        recaller = EpisodeRecaller()
        assert recaller.rank([]) == []


class TestEpisodeRecallerFormatForInjection:
    """Tests for format_for_injection() method."""

    def test_format_basic(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(
            outcome_summary="Parsed JSON successfully",
            domain="engineering",
        )
        match = recaller.score(ep, semantic_similarity=0.8)
        text = recaller.format_for_injection([match])
        assert "RELEVANT PAST EXPERIENCE:" in text
        assert "Parsed JSON successfully" in text

    def test_format_empty_matches(self) -> None:
        recaller = EpisodeRecaller()
        assert recaller.format_for_injection([]) == ""

    def test_format_respects_token_budget(self) -> None:
        recaller = EpisodeRecaller()
        matches = []
        for i in range(20):
            ep = _make_episode(
                outcome_summary="A" * 200,  # Long per-episode text
                lessons=[f"lesson_{j}" for j in range(5)],
            )
            match = recaller.score(ep, semantic_similarity=0.5)
            matches.append(match)

        text = recaller.format_for_injection(matches, max_tokens=100)
        # 100 tokens ≈ 400 chars; should have the header and maybe 1 episode
        assert len(text) < 800

    def test_format_includes_lessons_and_failures(self) -> None:
        recaller = EpisodeRecaller()
        ep = _make_episode(
            success=False,
            outcome_summary="Pipeline crashed",
            what_failed=["Stage 2 timeout"],
            failure_analysis="Memory overflow",
            lessons=["Increase heap size"],
        )
        match = recaller.score(ep, semantic_similarity=0.7)
        text = recaller.format_for_injection([match])
        assert "FAILED" in text
        assert "Pipeline crashed" in text
        assert "Stage 2 timeout" in text
        assert "Memory overflow" in text
        assert "Increase heap size" in text


class TestEpisodeMatchSerialization:
    """Tests for EpisodeMatch.to_dict()."""

    def test_to_dict_keys(self) -> None:
        ep = _make_episode(domain="eng", lessons=["a", "b"])
        match = EpisodeMatch(
            episode=ep,
            semantic_score=0.8,
            recency_score=0.9,
            domain_score=1.0,
            outcome_relevance=0.3,
            combined_score=0.75,
        )
        d = match.to_dict()
        assert d["episode_id"] == ep.id
        assert d["semantic_score"] == 0.8
        assert d["combined_score"] == 0.75
        assert d["task_domain"] == "eng"
        assert d["success"] is True
        assert d["lessons"] == ["a", "b"]
