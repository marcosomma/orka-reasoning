"""P5: episodes must record real success/failure, not a hardcoded default.

The episodic workflow now feeds an independent scorer's verdict into record_episode.
These tests prove the Brain honors a success=False outcome (so the feedback/decay loop
can learn from failure) rather than silently defaulting to success=True.
"""

from __future__ import annotations

import asyncio

import pytest

from orka.brain.brain import Brain


def _brain(fake_memory):
    return Brain(memory=fake_memory)  # no embedder needed for outcome wiring


def test_failure_outcome_records_failed_episode(fake_memory):
    brain = _brain(fake_memory)
    episode = asyncio.run(
        brain.record_episode(
            task_input="deploy the service to prod",
            context={"domain": "devops", "task": "deploy"},
            outcome={
                "success": False,
                "quality": 0.2,
                "outcome_summary": "Deployment failed: missing migration.",
                "what_failed": ["db migration not run"],
                "failure_analysis": "schema drift",
                "lessons": ["run migrations before deploy"],
            },
            execution_trace={"agents": ["task_executor"], "strategy": "sequential"},
        )
    )
    assert episode.success is False
    assert episode.quality_score == 0.2
    # It must be retrievable as a failure, not lost.
    failures = brain.episode_store.find_failures(limit=10)
    assert any(e.id == episode.id for e in failures)
    assert not any(e.id == episode.id for e in brain.episode_store.list_episodes(domain="devops") if e.success)


def test_success_outcome_records_success_episode(fake_memory):
    brain = _brain(fake_memory)
    episode = asyncio.run(
        brain.record_episode(
            task_input="add a healthcheck endpoint",
            context={"domain": "devops", "task": "feature"},
            outcome={"success": True, "quality": 0.9, "outcome_summary": "done", "lessons": ["x"]},
            execution_trace={"agents": ["task_executor"], "strategy": "sequential"},
        )
    )
    assert episode.success is True
    assert episode.id not in {e.id for e in brain.episode_store.find_failures(limit=10)}


def test_failure_and_success_are_distinguished(fake_memory):
    """The store must separate the two — proving success isn't a constant."""
    brain = _brain(fake_memory)
    ok = asyncio.run(brain.record_episode("good task", {"domain": "d"}, {"success": True, "quality": 0.8}, {}))
    bad = asyncio.run(brain.record_episode("bad task", {"domain": "d"}, {"success": False, "quality": 0.1}, {}))
    failure_ids = {e.id for e in brain.episode_store.find_failures(limit=10)}
    assert bad.id in failure_ids
    assert ok.id not in failure_ids
