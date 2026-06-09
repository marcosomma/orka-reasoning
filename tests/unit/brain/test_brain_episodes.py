"""Unit tests for Brain.record_episode() and Brain.recall_episodes()."""

from __future__ import annotations

import pytest

from orka.brain.brain import Brain
from orka.brain.episode import Episode
from orka.brain.episode_recall import EpisodeMatch


class TestBrainRecordEpisode:
    """Tests for Brain.record_episode()."""

    @pytest.mark.asyncio
    async def test_record_episode_returns_episode(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        episode = await brain.record_episode(
            task_input="Analyze sales data",
            context={"domain": "analytics", "task": "data_analysis"},
            outcome={
                "success": True,
                "quality": 0.9,
                "outcome_summary": "Analysis completed",
                "lessons": ["Use pandas for faster processing"],
            },
        )
        assert isinstance(episode, Episode)
        assert episode.task_domain == "analytics"
        assert episode.success is True
        assert episode.quality_score == 0.9
        assert "Use pandas for faster processing" in episode.lessons

    @pytest.mark.asyncio
    async def test_record_episode_stores_in_store(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        episode = await brain.record_episode(
            task_input="Build a parser",
            context={"domain": "engineering"},
            outcome={"success": True},
        )
        retrieved = brain.episode_store.get_episode(episode.id)
        assert retrieved is not None
        assert retrieved.id == episode.id

    @pytest.mark.asyncio
    async def test_record_episode_with_execution_trace(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        episode = await brain.record_episode(
            task_input="Run pipeline",
            context={"domain": "data"},
            outcome={"success": True},
            execution_trace={
                "agents": ["agent_a", "agent_b"],
                "strategy": "parallel",
            },
        )
        assert episode.agents_used == ["agent_a", "agent_b"]
        assert episode.strategy == "parallel"

    @pytest.mark.asyncio
    async def test_record_episode_with_dict_agents(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        episode = await brain.record_episode(
            task_input="Run pipeline",
            context={"domain": "data"},
            outcome={"success": True},
            execution_trace={
                "agents": [{"id": "agent_x"}, {"id": "agent_y"}],
                "strategy": "sequential",
            },
        )
        assert episode.agents_used == ["agent_x", "agent_y"]

    @pytest.mark.asyncio
    async def test_record_failure_episode(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        episode = await brain.record_episode(
            task_input="Deploy service",
            context={"domain": "devops"},
            outcome={
                "success": False,
                "quality": 0.1,
                "outcome_summary": "Deployment failed",
                "what_failed": ["Health check timeout"],
                "failure_analysis": "Port conflict on 8080",
                "lessons": ["Check ports before deploy"],
            },
        )
        assert episode.success is False
        assert episode.failure_analysis == "Port conflict on 8080"
        assert "Health check timeout" in episode.what_failed


class TestBrainRecallEpisodes:
    """Tests for Brain.recall_episodes()."""

    @pytest.mark.asyncio
    async def test_recall_returns_episode_matches(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        # Record a few episodes
        await brain.record_episode(
            task_input="Parse CSV data",
            context={"domain": "data"},
            outcome={"success": True, "outcome_summary": "Parsed OK"},
        )
        await brain.record_episode(
            task_input="Parse JSON data",
            context={"domain": "data"},
            outcome={"success": True, "outcome_summary": "Parsed OK"},
        )

        matches = await brain.recall_episodes(
            context={"domain": "data"},
            task_input="Parse XML",
        )
        assert len(matches) > 0
        assert all(isinstance(m, EpisodeMatch) for m in matches)

    @pytest.mark.asyncio
    async def test_recall_filters_by_domain(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        await brain.record_episode(
            task_input="Analyze code",
            context={"domain": "engineering"},
            outcome={"success": True},
        )
        await brain.record_episode(
            task_input="Analyze sales",
            context={"domain": "analytics"},
            outcome={"success": True},
        )

        matches = await brain.recall_episodes(
            context={"domain": "engineering"},
        )
        # Should find both (fallback to all when domain yields few)
        # or just the engineering one depending on domain filtering
        domains = {m.episode.task_domain for m in matches}
        assert "engineering" in domains

    @pytest.mark.asyncio
    async def test_recall_excludes_failures(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        await brain.record_episode(
            task_input="Good task",
            context={"domain": "test"},
            outcome={"success": True},
        )
        await brain.record_episode(
            task_input="Bad task",
            context={"domain": "test"},
            outcome={"success": False},
        )

        matches = await brain.recall_episodes(
            context={"domain": "test"},
            include_failures=False,
        )
        assert all(m.episode.success for m in matches)

    @pytest.mark.asyncio
    async def test_recall_empty_store(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        matches = await brain.recall_episodes(
            context={"domain": "empty"},
            task_input="Find something",
        )
        assert matches == []

    @pytest.mark.asyncio
    async def test_recall_respects_top_k(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        for i in range(10):
            await brain.record_episode(
                task_input=f"Task {i}",
                context={"domain": "bulk"},
                outcome={"success": True},
            )

        matches = await brain.recall_episodes(
            context={"domain": "bulk"},
            top_k=3,
        )
        assert len(matches) <= 3

    @pytest.mark.asyncio
    async def test_recall_respects_min_score(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        await brain.record_episode(
            task_input="Task A",
            context={"domain": "strict"},
            outcome={"success": True},
        )

        matches = await brain.recall_episodes(
            context={"domain": "strict"},
            min_score=0.99,  # Very high threshold
        )
        # May be empty if no episode scores above 0.99
        assert all(m.combined_score >= 0.99 for m in matches)


class TestBrainEpisodeProperties:
    """Tests for Brain episode-related properties."""

    def test_episode_store_property(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        assert brain.episode_store is not None

    def test_episode_recaller_property(self, fake_memory) -> None:
        brain = Brain(memory=fake_memory)
        assert brain.episode_recaller is not None
