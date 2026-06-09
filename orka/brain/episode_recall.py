# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Episode Recall
==============

Scoring, ranking, and prompt formatting for episodic memory retrieval.

The recaller scores candidate episodes on four dimensions:

- **Semantic similarity** (50%): Embedding-based similarity between query and episode.
- **Recency** (20%): Exponential decay — recent episodes are more relevant.
- **Domain match** (20%): Same domain gets a boost.
- **Outcome relevance** (10%): Failure episodes score higher when the task
  has risk indicators.

The ``format_for_injection`` method produces structured text ready for
prompt injection, giving the model concrete past experience to act on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .episode import Episode

# Scoring weights
WEIGHT_SEMANTIC = 0.50
WEIGHT_RECENCY = 0.20
WEIGHT_DOMAIN = 0.20
WEIGHT_OUTCOME = 0.10

# Recency half-life in hours: episode is 50% relevant after this period
RECENCY_HALF_LIFE_HOURS = 168.0  # 1 week


@dataclass
class EpisodeMatch:
    """A scored episode match from recall.

    Attributes:
        episode: The matched episode.
        semantic_score: Embedding similarity to the query (0.0–1.0).
        recency_score: Exponential decay based on age (0.0–1.0).
        domain_score: Domain match quality (0.0, 0.5, or 1.0).
        outcome_relevance: Higher for failures when task has risk indicators.
        combined_score: Weighted sum of all scores.
        injection_text: Pre-formatted text ready for prompt injection.
    """

    episode: Episode
    semantic_score: float = 0.0
    recency_score: float = 0.0
    domain_score: float = 0.0
    outcome_relevance: float = 0.0
    combined_score: float = 0.0
    injection_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "episode_id": self.episode.id,
            "semantic_score": round(self.semantic_score, 4),
            "recency_score": round(self.recency_score, 4),
            "domain_score": round(self.domain_score, 4),
            "outcome_relevance": round(self.outcome_relevance, 4),
            "combined_score": round(self.combined_score, 4),
            "task_domain": self.episode.task_domain,
            "success": self.episode.success,
            "lessons": self.episode.lessons,
        }


class EpisodeRecaller:
    """Scores and ranks episodes for recall, then formats them for prompt injection.

    Args:
        half_life_hours: Recency decay half-life in hours.
    """

    def __init__(self, half_life_hours: float = RECENCY_HALF_LIFE_HOURS) -> None:
        self._half_life = half_life_hours

    def score(
        self,
        episode: Episode,
        semantic_similarity: float,
        query_domain: str | None = None,
        now: datetime | None = None,
    ) -> EpisodeMatch:
        """Score a single episode against a query.

        Args:
            episode: The candidate episode.
            semantic_similarity: Pre-computed semantic similarity (0.0–1.0).
            query_domain: The domain of the current task.
            now: Current time (defaults to UTC now).

        Returns:
            An ``EpisodeMatch`` with all scores computed.
        """
        if now is None:
            now = datetime.now(UTC)

        # Recency: exponential decay
        age_hours = max(0.0, (now - episode.timestamp).total_seconds() / 3600.0)
        recency = math.exp(-age_hours * math.log(2) / self._half_life)

        # Domain match
        if query_domain and episode.task_domain:
            domain_score = 1.0 if episode.task_domain == query_domain else 0.0
        else:
            domain_score = 0.5  # Unknown domain — neutral

        # Outcome relevance: failures are more informative
        outcome = 0.7 if not episode.success else 0.3
        # Bonus if the episode has failure analysis or many lessons
        if episode.failure_analysis:
            outcome = min(1.0, outcome + 0.2)
        if len(episode.lessons) >= 3:
            outcome = min(1.0, outcome + 0.1)

        combined = (
            WEIGHT_SEMANTIC * semantic_similarity
            + WEIGHT_RECENCY * recency
            + WEIGHT_DOMAIN * domain_score
            + WEIGHT_OUTCOME * outcome
        )

        injection = self._format_single(episode, now)

        return EpisodeMatch(
            episode=episode,
            semantic_score=semantic_similarity,
            recency_score=recency,
            domain_score=domain_score,
            outcome_relevance=outcome,
            combined_score=combined,
            injection_text=injection,
        )

    def rank(
        self,
        matches: list[EpisodeMatch],
        min_score: float = 0.0,
    ) -> list[EpisodeMatch]:
        """Sort matches by combined score and apply minimum threshold.

        Args:
            matches: List of scored episode matches.
            min_score: Minimum combined score to include.

        Returns:
            Filtered and sorted list of matches.
        """
        filtered = [m for m in matches if m.combined_score >= min_score]
        filtered.sort(key=lambda m: m.combined_score, reverse=True)
        return filtered

    def format_for_injection(
        self,
        matches: list[EpisodeMatch],
        max_tokens: int = 500,
    ) -> str:
        """Format top episodes as structured text for prompt injection.

        Args:
            matches: Ranked episode matches (should be pre-sorted).
            max_tokens: Approximate token budget (1 token ≈ 4 chars).

        Returns:
            Formatted string ready for prompt injection, or empty string
            if no matches.
        """
        if not matches:
            return ""

        max_chars = max_tokens * 4
        lines = ["RELEVANT PAST EXPERIENCE:"]
        total_chars = len(lines[0])

        for match in matches:
            block = match.injection_text
            if total_chars + len(block) > max_chars:
                break
            lines.append(block)
            total_chars += len(block)

        if len(lines) == 1:
            return ""  # Only header, no episodes fit

        return "\n".join(lines)

    @staticmethod
    def _format_single(episode: Episode, now: datetime | None = None) -> str:
        """Format a single episode for prompt injection."""
        if now is None:
            now = datetime.now(UTC)

        age_hours = max(0.0, (now - episode.timestamp).total_seconds() / 3600.0)
        if age_hours < 1:
            age_str = "just now"
        elif age_hours < 24:
            age_str = f"{int(age_hours)} hours ago"
        elif age_hours < 720:  # 30 days
            age_str = f"{int(age_hours / 24)} days ago"
        else:
            age_str = f"{int(age_hours / 720)} months ago"

        status = "SUCCESS" if episode.success else "FAILED"
        parts = [f"\n- [{age_str}, {episode.task_domain}] {status}: {episode.outcome_summary}"]

        if episode.lessons:
            parts.append(f"  Lessons: {'; '.join(episode.lessons)}")

        if episode.what_failed:
            parts.append(f"  What failed: {'; '.join(episode.what_failed)}")

        if episode.failure_analysis:
            parts.append(f"  Root cause: {episode.failure_analysis}")

        if episode.what_worked:
            parts.append(f"  What worked: {'; '.join(episode.what_worked)}")

        return "\n".join(parts)
