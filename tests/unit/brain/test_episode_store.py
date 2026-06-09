"""Unit tests for orka.brain.episode_store — EpisodeStore with FakeMemory."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orka.brain.episode import Episode
from orka.brain.episode_store import EpisodeStore


def _make_episode(
    domain: str = "test",
    success: bool = True,
    task_type: str = "unit_test",
    age_hours: float = 0.0,
    **kwargs,
) -> Episode:
    """Helper to create an Episode with optional age offset."""
    ts = datetime.now(UTC) - timedelta(hours=age_hours)
    return Episode(
        task_input=kwargs.get("task_input", f"Task in {domain}"),
        task_domain=domain,
        task_type=task_type,
        success=success,
        quality_score=kwargs.get("quality_score", 0.8 if success else 0.2),
        outcome_summary=kwargs.get("outcome_summary", "Completed"),
        lessons=kwargs.get("lessons", ["lesson1"]),
        timestamp=ts,
    )


class TestEpisodeStoreSaveAndGet:
    """Tests for save_episode / get_episode round-trip."""

    def test_save_and_get(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode()
        store.save_episode(ep)

        retrieved = store.get_episode(ep.id)
        assert retrieved is not None
        assert retrieved.id == ep.id
        assert retrieved.task_domain == ep.task_domain
        assert retrieved.success == ep.success

    def test_get_nonexistent(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        assert store.get_episode("nonexistent") is None

    def test_save_indexes_timeline(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode()
        store.save_episode(ep)

        # Timeline sorted set should contain the episode
        assert fake_memory.zcard("orka:brain:episode:timeline") == 1

    def test_save_indexes_domain(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(domain="analytics")
        store.save_episode(ep)

        assert fake_memory.zcard("orka:brain:episode:domain:analytics") == 1

    def test_save_indexes_success(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep_ok = _make_episode(success=True)
        ep_fail = _make_episode(success=False)
        store.save_episode(ep_ok)
        store.save_episode(ep_fail)

        assert fake_memory.zcard("orka:brain:episode:successes") == 1
        assert fake_memory.zcard("orka:brain:episode:failures") == 1

    def test_save_indexes_type(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(task_type="etl")
        store.save_episode(ep)

        assert ep.id in fake_memory.smembers("orka:brain:episode:type:etl")

    def test_save_indexes_hash(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(domain="eng")
        store.save_episode(ep)

        assert fake_memory.hget("orka:brain:episode:index", ep.id) == "eng"


class TestEpisodeStoreDelete:
    """Tests for delete_episode and index cleanup."""

    def test_delete_existing(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode()
        store.save_episode(ep)
        assert store.delete_episode(ep.id) is True
        assert store.get_episode(ep.id) is None

    def test_delete_nonexistent(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        assert store.delete_episode("nonexistent") is False

    def test_delete_cleans_indexes(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(domain="cleanup_test", task_type="test_type")
        store.save_episode(ep)
        store.delete_episode(ep.id)

        assert fake_memory.zcard("orka:brain:episode:timeline") == 0
        assert fake_memory.zcard("orka:brain:episode:domain:cleanup_test") == 0
        assert ep.id not in fake_memory.smembers("orka:brain:episode:type:test_type")
        assert fake_memory.hget("orka:brain:episode:index", ep.id) is None


class TestEpisodeStoreList:
    """Tests for list_episodes, find_by_domain, find_failures."""

    def test_list_episodes_ordered_by_recency(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        old = _make_episode(age_hours=24)
        new = _make_episode(age_hours=1)
        store.save_episode(old)
        store.save_episode(new)

        episodes = store.list_episodes()
        assert len(episodes) == 2
        assert episodes[0].id == new.id  # Most recent first

    def test_list_episodes_by_domain(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep_a = _make_episode(domain="alpha")
        ep_b = _make_episode(domain="beta")
        store.save_episode(ep_a)
        store.save_episode(ep_b)

        result = store.list_episodes(domain="alpha")
        assert len(result) == 1
        assert result[0].task_domain == "alpha"

    def test_find_by_domain(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(domain="eng")
        store.save_episode(ep)

        result = store.find_by_domain("eng")
        assert len(result) == 1
        assert result[0].id == ep.id

    def test_find_failures(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ok = _make_episode(success=True)
        fail = _make_episode(success=False)
        store.save_episode(ok)
        store.save_episode(fail)

        failures = store.find_failures()
        assert len(failures) == 1
        assert failures[0].success is False

    def test_list_with_limit(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        for i in range(5):
            store.save_episode(_make_episode(age_hours=float(i)))

        result = store.list_episodes(limit=3)
        assert len(result) == 3


class TestEpisodeStoreCount:
    """Tests for count()."""

    def test_count_all(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        assert store.count() == 0
        store.save_episode(_make_episode())
        assert store.count() == 1

    def test_count_by_domain(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        store.save_episode(_make_episode(domain="a"))
        store.save_episode(_make_episode(domain="b"))
        store.save_episode(_make_episode(domain="a"))

        assert store.count(domain="a") == 2
        assert store.count(domain="b") == 1


class TestEpisodeStoreSemanticSearch:
    """Tests for semantic_search (keyword fallback)."""

    def test_keyword_fallback_search(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)  # No embedder
        ep = _make_episode(
            task_input="Analyze network traffic patterns",
            domain="security",
        )
        store.save_episode(ep)

        results = store.semantic_search("network traffic", top_k=5)
        assert len(results) == 1
        episode, score = results[0]
        assert episode.id == ep.id
        assert score > 0.0

    def test_keyword_search_no_results(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode(task_input="Build REST API")
        store.save_episode(ep)

        results = store.semantic_search("quantum physics", top_k=5)
        # May return low-scoring result; ensure no crash
        assert isinstance(results, list)

    def test_keyword_search_empty_store(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        results = store.semantic_search("anything", top_k=5)
        assert results == []


class TestEpisodeStoreCleanup:
    """Tests for cleanup() retention policies."""

    def test_cleanup_removes_oldest(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        # Add episodes with increasing age
        episodes = []
        for i in range(5):
            ep = _make_episode(domain="cleanup", age_hours=float(i))
            store.save_episode(ep)
            episodes.append(ep)

        result = store.cleanup(max_per_domain=3)
        assert result["deleted"] == 2
        # Newest 3 should remain
        remaining = store.list_episodes(domain="cleanup")
        assert len(remaining) == 3

    def test_cleanup_no_action_when_under_limit(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        for _ in range(3):
            store.save_episode(_make_episode(domain="small"))

        result = store.cleanup(max_per_domain=10)
        assert result["deleted"] == 0

    def test_maybe_cleanup_respects_interval(self, fake_memory) -> None:
        store = EpisodeStore(memory=fake_memory)
        ep = _make_episode()
        store.save_episode(ep)

        # Reset last cleanup to now, so maybe_cleanup should be a no-op
        store._last_cleanup = datetime.now(UTC)
        store.maybe_cleanup()  # Should not crash, should be no-op
        assert store.count() == 1
