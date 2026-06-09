"""Unit tests for orka.brain.episode — Episode dataclass."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from orka.brain.episode import Episode


class TestEpisodeCreation:
    """Tests for Episode construction and defaults."""

    def test_default_fields(self) -> None:
        ep = Episode()
        assert ep.id  # UUID generated
        assert isinstance(ep.timestamp, datetime)
        assert ep.task_domain == "general"
        assert ep.success is True
        assert ep.quality_score == 0.0
        assert ep.agents_used == []
        assert ep.lessons == []
        assert ep.failure_analysis is None

    def test_custom_fields(self) -> None:
        ep = Episode(
            task_input="Analyze sales data",
            task_domain="analytics",
            task_type="etl",
            agents_used=["agent_a", "agent_b"],
            strategy="parallel",
            model="gpt-4",
            success=False,
            quality_score=0.3,
            outcome_summary="Pipeline failed at stage 2",
            what_worked=["Data ingestion"],
            what_failed=["Transformation step"],
            failure_analysis="Schema mismatch",
            lessons=["Validate schema before transform"],
            tokens_used=1500,
            latency_ms=250.0,
        )
        assert ep.task_domain == "analytics"
        assert ep.task_type == "etl"
        assert ep.success is False
        assert ep.quality_score == 0.3
        assert len(ep.agents_used) == 2
        assert ep.failure_analysis == "Schema mismatch"

    def test_unique_ids(self) -> None:
        ep1 = Episode()
        ep2 = Episode()
        assert ep1.id != ep2.id


class TestEpisodeSerialization:
    """Tests for to_dict / from_dict round-trip."""

    def _make_episode(self) -> Episode:
        return Episode(
            id="test-id-123",
            task_input="Build a parser",
            task_domain="engineering",
            task_type="code_gen",
            agents_used=["coder", "reviewer"],
            strategy="sequential",
            model="llama-3",
            context_features={"complexity": "medium"},
            success=True,
            quality_score=0.85,
            outcome_summary="Parser built successfully",
            what_worked=["Template generation"],
            what_failed=[],
            failure_analysis=None,
            lessons=["Use AST for robustness"],
            tokens_used=2000,
            latency_ms=500.0,
            related_episode_ids=["prev-001"],
            supersedes_id="old-attempt",
        )

    def test_to_dict_keys(self) -> None:
        ep = self._make_episode()
        d = ep.to_dict()
        assert d["id"] == "test-id-123"
        assert d["task_domain"] == "engineering"
        assert d["success"] is True
        assert d["quality_score"] == 0.85
        assert d["related_episode_ids"] == ["prev-001"]
        assert d["supersedes_id"] == "old-attempt"

    def test_roundtrip(self) -> None:
        original = self._make_episode()
        d = original.to_dict()
        restored = Episode.from_dict(d)

        assert restored.id == original.id
        assert restored.task_input == original.task_input
        assert restored.task_domain == original.task_domain
        assert restored.task_type == original.task_type
        assert restored.agents_used == original.agents_used
        assert restored.strategy == original.strategy
        assert restored.model == original.model
        assert restored.success == original.success
        assert restored.quality_score == original.quality_score
        assert restored.outcome_summary == original.outcome_summary
        assert restored.what_worked == original.what_worked
        assert restored.what_failed == original.what_failed
        assert restored.failure_analysis == original.failure_analysis
        assert restored.lessons == original.lessons
        assert restored.tokens_used == original.tokens_used
        assert restored.latency_ms == original.latency_ms
        assert restored.related_episode_ids == original.related_episode_ids
        assert restored.supersedes_id == original.supersedes_id

    def test_json_serializable(self) -> None:
        ep = self._make_episode()
        d = ep.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        restored = Episode.from_dict(deserialized)
        assert restored.id == ep.id

    def test_from_dict_missing_fields(self) -> None:
        ep = Episode.from_dict({"task_input": "Hello"})
        assert ep.task_input == "Hello"
        assert ep.task_domain == "general"
        assert ep.success is True
        assert ep.lessons == []

    def test_from_dict_with_datetime_object(self) -> None:
        now = datetime.now(UTC)
        ep = Episode.from_dict({"timestamp": now})
        assert ep.timestamp == now


class TestEpisodeEmbeddingText:
    """Tests for to_embedding_text()."""

    def test_basic_embedding_text(self) -> None:
        ep = Episode(
            task_input="Summarize the report",
            task_domain="text_analysis",
            outcome_summary="Report summarized successfully",
            lessons=["Use bullet points", "Check grammar"],
        )
        text = ep.to_embedding_text()
        assert "text_analysis" in text
        assert "Summarize the report" in text
        assert "Report summarized successfully" in text
        assert "lessons:" in text
        assert "Use bullet points" in text

    def test_embedding_text_no_lessons(self) -> None:
        ep = Episode(
            task_input="Short task",
            task_domain="general",
        )
        text = ep.to_embedding_text()
        assert "general:" in text
        assert "Short task" in text
        assert "lessons" not in text

    def test_embedding_text_truncates_input(self) -> None:
        ep = Episode(
            task_input="x" * 500,
            task_domain="test",
        )
        text = ep.to_embedding_text()
        # Should truncate to 200 chars of input
        assert len(text) < 500
