# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Episode Model
=============

Defines the core data structure for episodic memory — recording *what happened*
during task execution rather than abstract procedures.

An Episode is an immutable fact about a past execution: the task input, what the
system produced, what worked, what failed, and actionable lessons for future tasks.
Unlike Skills (which abstract away domain details), Episodes preserve specific
context so they can provide genuinely new information to the model.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Episode:
    """A single execution record with outcome details and actionable lessons.

    Episodes are immutable facts — they don't gain or lose confidence like Skills.
    Their value comes from storing information the model cannot derive from its
    weights: what specifically happened in *this system* on *previous runs*.

    Attributes:
        id: Unique identifier (UUID).
        timestamp: When this episode occurred (UTC).
        task_input: Raw task text (may be truncated for very long inputs).
        task_domain: Domain classification (e.g. ``"data_engineering"``).
        task_type: Finer task classification (e.g. ``"etl"``, ``"code_review"``).
        agents_used: Agent IDs that participated in execution.
        strategy: Orchestration strategy (``"sequential"``, ``"parallel"``, etc.).
        model: LLM model identifier used for execution.
        context_features: Abstract context features (from ContextAnalyzer).
        success: Whether the execution succeeded.
        quality_score: Quality metric from 0.0 to 1.0.
        outcome_summary: 1–2 sentence natural-language summary.
        what_worked: Specific successes observed during execution.
        what_failed: Specific failures or issues encountered.
        failure_analysis: Root-cause analysis when ``success`` is False.
        lessons: Actionable takeaways for future similar tasks.
        tokens_used: Total tokens consumed during execution.
        latency_ms: Total execution latency in milliseconds.
        related_episode_ids: UUIDs of episodes that were recalled for this task.
        supersedes_id: If this is a retry, points to the failed episode.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Task identity
    task_input: str = ""
    task_domain: str = "general"
    task_type: str = ""

    # Execution context
    agents_used: list[str] = field(default_factory=list)
    strategy: str = "sequential"
    model: str = ""
    context_features: dict[str, Any] = field(default_factory=dict)

    # Outcome
    success: bool = True
    quality_score: float = 0.0

    # The valuable part — LLM-generated at record time
    outcome_summary: str = ""
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    failure_analysis: str | None = None
    lessons: list[str] = field(default_factory=list)

    # Resource metrics
    tokens_used: int = 0
    latency_ms: float = 0.0

    # Linking
    related_episode_ids: list[str] = field(default_factory=list)
    supersedes_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "task_input": self.task_input,
            "task_domain": self.task_domain,
            "task_type": self.task_type,
            "agents_used": self.agents_used,
            "strategy": self.strategy,
            "model": self.model,
            "context_features": self.context_features,
            "success": self.success,
            "quality_score": self.quality_score,
            "outcome_summary": self.outcome_summary,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "failure_analysis": self.failure_analysis,
            "lessons": self.lessons,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "related_episode_ids": self.related_episode_ids,
            "supersedes_id": self.supersedes_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        """Deserialize from a dictionary."""
        ts = data.get("timestamp", "")
        if isinstance(ts, str) and ts:
            timestamp = datetime.fromisoformat(ts)
        elif isinstance(ts, datetime):
            timestamp = ts
        else:
            timestamp = datetime.now(UTC)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=timestamp,
            task_input=data.get("task_input", ""),
            task_domain=data.get("task_domain", "general"),
            task_type=data.get("task_type", ""),
            agents_used=data.get("agents_used", []),
            strategy=data.get("strategy", "sequential"),
            model=data.get("model", ""),
            context_features=data.get("context_features", {}),
            success=data.get("success", True),
            quality_score=float(data.get("quality_score", 0.0)),
            outcome_summary=data.get("outcome_summary", ""),
            what_worked=data.get("what_worked", []),
            what_failed=data.get("what_failed", []),
            failure_analysis=data.get("failure_analysis"),
            lessons=data.get("lessons", []),
            tokens_used=int(data.get("tokens_used", 0)),
            latency_ms=float(data.get("latency_ms", 0.0)),
            related_episode_ids=data.get("related_episode_ids", []),
            supersedes_id=data.get("supersedes_id"),
        )

    def to_embedding_text(self) -> str:
        """Generate text for vector embedding.

        Combines domain, task input (truncated), outcome summary, and lessons
        into a single string optimised for semantic similarity search.
        """
        parts = [f"{self.task_domain}: {self.task_input[:200]}"]
        if self.outcome_summary:
            parts.append(self.outcome_summary)
        if self.lessons:
            parts.append("lessons: " + "; ".join(self.lessons))
        return " | ".join(parts)
