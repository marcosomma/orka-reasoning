# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Episode Store
=============

Redis-backed storage for episodic memories, parallel to :mod:`orka.brain.skill_graph`.

Episodes are indexed by:
- **Timeline**: Sorted set with timestamp scores for recency queries.
- **Domain**: Sorted set per domain for domain-scoped retrieval.
- **Outcome**: Separate sorted sets for successes and failures.
- **Task type**: Regular sets for categorical lookup.

Retention is count-based (sliding window per domain), not TTL-based.
Failure episodes get 2× retention because they carry more information.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime
from typing import Any

from .episode import Episode

logger = logging.getLogger(__name__)

# Redis key prefixes
_EPISODE_PREFIX = "orka:brain:episode:"
_EPISODE_INDEX = "orka:brain:episode:index"
_TIMELINE_KEY = "orka:brain:episode:timeline"
_DOMAIN_PREFIX = "orka:brain:episode:domain:"
_FAILURES_KEY = "orka:brain:episode:failures"
_SUCCESSES_KEY = "orka:brain:episode:successes"
_TYPE_PREFIX = "orka:brain:episode:type:"

_CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
_DEFAULT_MAX_PER_DOMAIN = 200
_FAILURE_RETENTION_FACTOR = 2


class EpisodeStore:
    """Redis-backed episode storage with sorted-set indexing.

    Args:
        memory: A memory logger instance (RedisStackMemoryLogger or compatible)
            that provides Redis primitive operations.
        embedder: Optional sentence embedding model for semantic search.
    """

    def __init__(self, memory: Any, embedder: Any | None = None) -> None:
        self._memory = memory
        self._embedder = embedder
        self._last_cleanup: datetime = datetime.now(UTC)

    # ========== Storage ==========

    def save_episode(self, episode: Episode) -> str:
        """Persist an episode and update all indexes.

        Args:
            episode: The episode to store.

        Returns:
            The episode's ID.
        """
        key = f"{_EPISODE_PREFIX}{episode.id}"
        data = json.dumps(episode.to_dict())
        self._memory.set(key, data)

        # Timeline index (score = timestamp in ms)
        ts_ms = episode.timestamp.timestamp() * 1000
        self._memory.zadd(_TIMELINE_KEY, {episode.id: ts_ms})

        # Domain index
        if episode.task_domain:
            self._memory.zadd(
                f"{_DOMAIN_PREFIX}{episode.task_domain}",
                {episode.id: ts_ms},
            )

        # Outcome indexes
        if episode.success:
            self._memory.zadd(_SUCCESSES_KEY, {episode.id: ts_ms})
        else:
            self._memory.zadd(_FAILURES_KEY, {episode.id: ts_ms})

        # Task type index
        if episode.task_type:
            self._memory.sadd(f"{_TYPE_PREFIX}{episode.task_type}", episode.id)

        # Name index for fast enumeration
        self._memory.hset(_EPISODE_INDEX, episode.id, episode.task_domain)

        logger.debug(
            "Saved episode '%s' (domain=%s, success=%s)",
            episode.id,
            episode.task_domain,
            episode.success,
        )
        return episode.id

    def get_episode(self, episode_id: str) -> Episode | None:
        """Retrieve an episode by ID.

        Args:
            episode_id: The episode's unique identifier.

        Returns:
            The Episode object, or ``None`` if not found.
        """
        key = f"{_EPISODE_PREFIX}{episode_id}"
        raw = self._memory.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return Episode.from_dict(data)

    def delete_episode(self, episode_id: str) -> bool:
        """Remove an episode and clean up all indexes.

        Args:
            episode_id: The episode to remove.

        Returns:
            ``True`` if the episode was found and removed.
        """
        episode = self.get_episode(episode_id)
        if episode is None:
            return False

        # Remove from all indexes
        self._memory.zrem(_TIMELINE_KEY, episode_id)
        if episode.task_domain:
            self._memory.zrem(f"{_DOMAIN_PREFIX}{episode.task_domain}", episode_id)
        if episode.success:
            self._memory.zrem(_SUCCESSES_KEY, episode_id)
        else:
            self._memory.zrem(_FAILURES_KEY, episode_id)
        if episode.task_type:
            self._memory.srem(f"{_TYPE_PREFIX}{episode.task_type}", episode_id)
        self._memory.hdel(_EPISODE_INDEX, episode_id)

        # Remove the episode data
        self._memory.delete(f"{_EPISODE_PREFIX}{episode_id}")

        logger.debug("Deleted episode %s", episode_id)
        return True

    # ========== Retrieval ==========

    def list_episodes(
        self,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[Episode]:
        """List episodes ordered by recency.

        Args:
            domain: If provided, restrict to this domain.
            limit: Maximum number of episodes to return.

        Returns:
            List of episodes, most recent first.
        """
        if domain:
            ids = self._memory.zrevrange(f"{_DOMAIN_PREFIX}{domain}", 0, limit - 1)
        else:
            ids = self._memory.zrevrange(_TIMELINE_KEY, 0, limit - 1)

        episodes = []
        for eid in ids:
            eid_str = eid if isinstance(eid, str) else eid.decode("utf-8")
            ep = self.get_episode(eid_str)
            if ep is not None:
                episodes.append(ep)
        return episodes

    def find_by_domain(self, domain: str, limit: int = 50) -> list[Episode]:
        """Find episodes in a specific domain, newest first.

        Args:
            domain: The domain to filter by.
            limit: Maximum number of results.

        Returns:
            List of episodes in the given domain.
        """
        return self.list_episodes(domain=domain, limit=limit)

    def find_failures(self, limit: int = 50) -> list[Episode]:
        """Find failed episodes, newest first.

        Args:
            limit: Maximum number of results.

        Returns:
            List of failed episodes.
        """
        ids = self._memory.zrevrange(_FAILURES_KEY, 0, limit - 1)
        episodes = []
        for eid in ids:
            eid_str = eid if isinstance(eid, str) else eid.decode("utf-8")
            ep = self.get_episode(eid_str)
            if ep is not None:
                episodes.append(ep)
        return episodes

    def count(self, domain: str | None = None) -> int:
        """Count stored episodes.

        Args:
            domain: If provided, count only episodes in this domain.

        Returns:
            Number of episodes.
        """
        if domain:
            return self._memory.zcard(f"{_DOMAIN_PREFIX}{domain}")
        return self._memory.zcard(_TIMELINE_KEY)

    # ========== Semantic Search ==========

    def semantic_search(
        self,
        query_text: str,
        top_k: int = 5,
        domain: str | None = None,
    ) -> list[tuple[Episode, float]]:
        """Find semantically similar episodes using embeddings.

        Falls back to keyword overlap when no embedder is available.

        Args:
            query_text: The query to match against.
            top_k: Maximum number of results.
            domain: Optional domain filter.

        Returns:
            List of ``(episode, similarity_score)`` tuples, sorted by score.
        """
        # Get candidate episodes
        candidates = self.list_episodes(domain=domain, limit=200)
        if not candidates:
            return []

        if self._embedder is not None:
            return self._vector_search(query_text, candidates, top_k)
        return self._keyword_search(query_text, candidates, top_k)

    def _vector_search(
        self,
        query_text: str,
        candidates: list[Episode],
        top_k: int,
    ) -> list[tuple[Episode, float]]:
        """Semantic search via sentence embeddings."""
        if self._embedder is None:
            return self._keyword_search(query_text, candidates, top_k)
        try:
            query_vec = self._embedder.encode(query_text)
        except Exception:
            logger.warning("Embedder failed, falling back to keyword search")
            return self._keyword_search(query_text, candidates, top_k)

        scored: list[tuple[Episode, float]] = []
        for ep in candidates:
            try:
                ep_vec = self._embedder.encode(ep.to_embedding_text())
                # Cosine similarity
                dot = sum(a * b for a, b in zip(query_vec, ep_vec))
                norm_q = math.sqrt(sum(a * a for a in query_vec))
                norm_e = math.sqrt(sum(b * b for b in ep_vec))
                if norm_q > 0 and norm_e > 0:
                    sim = (dot / (norm_q * norm_e) + 1) / 2  # Normalize to [0, 1]
                else:
                    sim = 0.0
                scored.append((ep, sim))
            except Exception:
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _keyword_search(
        self,
        query_text: str,
        candidates: list[Episode],
        top_k: int,
    ) -> list[tuple[Episode, float]]:
        """Fallback search using keyword overlap (Jaccard similarity)."""
        query_tokens = set(query_text.lower().split())
        if not query_tokens:
            return []

        scored: list[tuple[Episode, float]] = []
        for ep in candidates:
            ep_tokens = set(ep.to_embedding_text().lower().split())
            if not ep_tokens:
                continue
            intersection = query_tokens & ep_tokens
            union = query_tokens | ep_tokens
            sim = len(intersection) / len(union) if union else 0.0
            scored.append((ep, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ========== Maintenance ==========

    def cleanup(
        self,
        max_per_domain: int = _DEFAULT_MAX_PER_DOMAIN,
    ) -> dict[str, int]:
        """Enforce sliding-window retention per domain.

        Keeps the most recent ``max_per_domain`` episodes per domain.
        Failure episodes get ``2×`` the retention limit.

        Args:
            max_per_domain: Maximum episodes to keep per domain.

        Returns:
            Dictionary with ``deleted`` and ``checked`` counts.
        """
        deleted = 0
        checked = 0

        # Gather all domains from the index
        domain_map: dict[str, list[str]] = {}
        all_entries = self._memory.hkeys(_EPISODE_INDEX)
        for eid in all_entries:
            eid_str = eid if isinstance(eid, str) else eid.decode("utf-8")
            domain_raw = self._memory.hget(_EPISODE_INDEX, eid_str)
            domain = (
                domain_raw if isinstance(domain_raw, str) else domain_raw.decode("utf-8") if domain_raw else "general"
            )
            domain_map.setdefault(domain, []).append(eid_str)
            checked += 1

        for domain, episode_ids in domain_map.items():
            domain_key = f"{_DOMAIN_PREFIX}{domain}"
            # Get all episodes in this domain sorted by timestamp (oldest first)
            all_ids = self._memory.zrange(domain_key, 0, -1)
            if len(all_ids) <= max_per_domain:
                continue

            # Keep the newest max_per_domain; delete the rest
            to_delete = all_ids[: len(all_ids) - max_per_domain]
            for eid in to_delete:
                eid_str = eid if isinstance(eid, str) else eid.decode("utf-8")
                # Check if it's a failure — failures get 2x retention
                ep = self.get_episode(eid_str)
                if ep and not ep.success:
                    # Count failures in this domain
                    failure_count = self._memory.zcard(_FAILURES_KEY)
                    if failure_count <= max_per_domain * _FAILURE_RETENTION_FACTOR:
                        continue  # Keep this failure
                self.delete_episode(eid_str)
                deleted += 1

        logger.info("Episode cleanup: checked=%d, deleted=%d", checked, deleted)
        return {"deleted": deleted, "checked": checked}

    def maybe_cleanup(self, max_per_domain: int = _DEFAULT_MAX_PER_DOMAIN) -> None:
        """Run cleanup at most once per hour (lazy)."""
        now = datetime.now(UTC)
        if (now - self._last_cleanup).total_seconds() >= _CLEANUP_INTERVAL_SECONDS:
            self.cleanup(max_per_domain=max_per_domain)
            self._last_cleanup = now
