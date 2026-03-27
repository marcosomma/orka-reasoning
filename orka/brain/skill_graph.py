# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Skill Graph
===========

A knowledge graph of learned skills, stored in Redis.

Skills are connected through relationships that capture how they relate:
- **DERIVES_FROM**: Skill B is a refinement of Skill A
- **COMPOSED_OF**: Skill C is built from Skills A and B
- **SPECIALIZES**: Skill B is a domain-specific version of Skill A
- **TRANSFERRED_TO**: Skill A was successfully applied in a new context
- **CONFLICTS_WITH**: Skills A and B are mutually exclusive approaches
- **COMPLEMENTS**: Skills A and B work well together

The graph enables:
1. Finding related skills when a direct match isn't perfect
2. Composing complex skills from simpler building blocks
3. Tracing the lineage of skill evolution
4. Identifying skill clusters and gaps
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .skill import Skill

logger = logging.getLogger(__name__)

# Relationship types between skills
SKILL_RELATIONS = [
    "DERIVES_FROM",
    "COMPOSED_OF",
    "SPECIALIZES",
    "TRANSFERRED_TO",
    "CONFLICTS_WITH",
    "COMPLEMENTS",
]

# Redis key prefixes for the skill graph
_SKILL_PREFIX = "orka:brain:skill:"
_GRAPH_EDGES_PREFIX = "orka:brain:edges:"
_SKILL_INDEX = "orka:brain:skill_index"
_SKILL_TAGS_PREFIX = "orka:brain:tags:"
_SKILL_TYPE_INDEX_PREFIX = "orka:brain:type_index:"
_SKILL_DOMAIN_INDEX_PREFIX = "orka:brain:domain_index:"


class SkillGraph:
    """Knowledge graph of skills backed by Redis.

    Provides CRUD operations on skills plus graph traversal for finding
    related, composed, and derivative skills.

    The graph uses Redis hashes for skill storage, sets for adjacency lists,
    and a hash index for fast lookups by name or tag.

    Args:
        memory: A memory logger instance (RedisStackMemoryLogger or compatible)
            that provides Redis primitive operations (hset, hget, etc.).
    """

    def __init__(self, memory: Any) -> None:
        self._memory = memory

    # ========== Skill CRUD ==========

    def save_skill(self, skill: Skill) -> str:
        """Save or update a skill in the graph.

        Args:
            skill: The skill to persist.

        Returns:
            The skill's ID.
        """
        key = f"{_SKILL_PREFIX}{skill.id}"
        data = json.dumps(skill.to_dict())
        self._memory.set(key, data)

        # Set Redis native TTL for automatic eviction
        if skill.expires_at:
            try:
                expires_dt = datetime.fromisoformat(skill.expires_at)
                ttl_seconds = int((expires_dt - datetime.now(UTC)).total_seconds())
                if ttl_seconds > 0 and hasattr(self._memory, "expire"):
                    self._memory.expire(key, ttl_seconds)
            except (ValueError, TypeError):
                pass

        # Index by name for fast lookup
        self._memory.hset(_SKILL_INDEX, skill.id, skill.name)

        # Index by tags
        for tag in skill.tags:
            self._memory.sadd(f"{_SKILL_TAGS_PREFIX}{tag}", skill.id)

        # Index by skill type for two-stage retrieval
        if skill.skill_type:
            self._memory.sadd(f"{_SKILL_TYPE_INDEX_PREFIX}{skill.skill_type}", skill.id)

        # Index by domain keywords for fast domain filtering
        for domain in skill.domain_keywords:
            self._memory.sadd(f"{_SKILL_DOMAIN_INDEX_PREFIX}{domain}", skill.id)

        logger.debug(f"Saved skill '{skill.name}' ({skill.id})")
        return skill.id

    def get_skill(self, skill_id: str) -> Skill | None:
        """Retrieve a skill by ID.

        Args:
            skill_id: The skill's unique identifier.

        Returns:
            The Skill object, or None if not found.
        """
        key = f"{_SKILL_PREFIX}{skill_id}"
        raw = self._memory.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        return Skill.from_dict(data)

    def delete_skill(self, skill_id: str) -> bool:
        """Remove a skill and its edges from the graph.

        Args:
            skill_id: The skill to remove.

        Returns:
            True if the skill was found and removed.
        """
        skill = self.get_skill(skill_id)
        if skill is None:
            return False

        # Remove from tag indexes
        for tag in skill.tags:
            self._memory.srem(f"{_SKILL_TAGS_PREFIX}{tag}", skill_id)

        # Remove from type and domain indexes
        if skill.skill_type:
            self._memory.srem(f"{_SKILL_TYPE_INDEX_PREFIX}{skill.skill_type}", skill_id)
        for domain in skill.domain_keywords:
            self._memory.srem(f"{_SKILL_DOMAIN_INDEX_PREFIX}{domain}", skill_id)

        # Remove from name index
        self._memory.hdel(_SKILL_INDEX, skill_id)

        # Remove edges (both directions)
        edge_key = f"{_GRAPH_EDGES_PREFIX}{skill_id}"
        edges_raw = self._memory.smembers(edge_key)
        for edge_data in edges_raw:
            edge = json.loads(edge_data) if isinstance(edge_data, str) else edge_data
            target_id = edge.get("target")
            if target_id:
                # Remove reverse edge
                reverse_key = f"{_GRAPH_EDGES_PREFIX}{target_id}"
                reverse_edges = self._memory.smembers(reverse_key)
                for rev in reverse_edges:
                    rev_parsed = json.loads(rev) if isinstance(rev, str) else rev
                    if rev_parsed.get("target") == skill_id:
                        self._memory.srem(reverse_key, rev if isinstance(rev, str) else json.dumps(rev))

        self._memory.delete(edge_key)
        self._memory.delete(f"{_SKILL_PREFIX}{skill_id}")

        logger.debug(f"Deleted skill {skill_id}")
        return True

    def list_skills(self) -> list[Skill]:
        """List all skills in the graph.

        Returns:
            List of all stored, non-expired skills.
        """
        skill_ids = self._memory.hkeys(_SKILL_INDEX)
        skills = []
        for sid in skill_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode("utf-8")
            skill = self.get_skill(sid_str)
            if skill and not skill.is_expired:
                skills.append(skill)
        return skills

    def find_by_tag(self, tag: str) -> list[Skill]:
        """Find skills that have a specific tag.

        Args:
            tag: The tag to search for.

        Returns:
            List of matching skills.
        """
        skill_ids = self._memory.smembers(f"{_SKILL_TAGS_PREFIX}{tag}")
        skills = []
        for sid in skill_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode("utf-8")
            skill = self.get_skill(sid_str)
            if skill:
                skills.append(skill)
        return skills

    def find_by_type(self, skill_type: str) -> list[Skill]:
        """Find skills of a given type (e.g. ``execution_recipe``).

        Args:
            skill_type: The :class:`SkillType` value to filter on.

        Returns:
            Non-expired skills matching *skill_type*.
        """
        skill_ids = self._memory.smembers(f"{_SKILL_TYPE_INDEX_PREFIX}{skill_type}")
        skills = []
        for sid in skill_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode("utf-8")
            skill = self.get_skill(sid_str)
            if skill and not skill.is_expired:
                skills.append(skill)
        return skills

    def find_by_domain(self, domain: str) -> list[Skill]:
        """Find skills indexed under a domain keyword.

        Args:
            domain: A domain keyword (e.g. ``"security"``, ``"code-review"``).

        Returns:
            Non-expired skills matching *domain*.
        """
        skill_ids = self._memory.smembers(f"{_SKILL_DOMAIN_INDEX_PREFIX}{domain}")
        skills = []
        for sid in skill_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode("utf-8")
            skill = self.get_skill(sid_str)
            if skill and not skill.is_expired:
                skills.append(skill)
        return skills

    def find_filtered(
        self,
        skill_type: str | None = None,
        domain: str | None = None,
    ) -> list[Skill]:
        """Two-stage retrieval: narrow by type/domain indexes, then return.

        When both *skill_type* and *domain* are provided the result is the
        intersection of both index sets.  Falls back to ``list_skills()``
        when neither filter is given.

        Args:
            skill_type: Optional skill type filter.
            domain: Optional domain keyword filter.

        Returns:
            Non-expired skills matching the provided filters.
        """
        candidate_ids: set[str] | None = None

        if skill_type:
            raw = self._memory.smembers(f"{_SKILL_TYPE_INDEX_PREFIX}{skill_type}")
            type_ids = {s if isinstance(s, str) else s.decode("utf-8") for s in raw}
            candidate_ids = type_ids

        if domain:
            raw = self._memory.smembers(f"{_SKILL_DOMAIN_INDEX_PREFIX}{domain}")
            domain_ids = {s if isinstance(s, str) else s.decode("utf-8") for s in raw}
            candidate_ids = candidate_ids & domain_ids if candidate_ids is not None else domain_ids

        if candidate_ids is None:
            return self.list_skills()

        skills: list[Skill] = []
        for sid in candidate_ids:
            skill = self.get_skill(sid)
            if skill and not skill.is_expired:
                skills.append(skill)
        return skills

    def cleanup_expired_skills(self) -> dict[str, int]:
        """Delete all expired skills from the graph.

        Returns:
            Dict with 'deleted' and 'checked' counts.
        """
        skill_ids = self._memory.hkeys(_SKILL_INDEX)
        deleted = 0
        checked = 0
        for sid in skill_ids:
            sid_str = sid if isinstance(sid, str) else sid.decode("utf-8")
            checked += 1
            skill = self.get_skill(sid_str)
            if skill and skill.is_expired:
                self.delete_skill(sid_str)
                deleted += 1
                logger.debug(f"Cleaned up expired skill '{skill.name}' ({sid_str})")
        if deleted:
            logger.info(f"Expired skill cleanup: {deleted}/{checked} removed")
        return {"deleted": deleted, "checked": checked}

    # ========== Graph Edges ==========

    def add_edge(
        self, source_id: str, relation: str, target_id: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """Create a directed edge between two skills.

        Args:
            source_id: ID of the source skill.
            relation: Type of relationship (must be in SKILL_RELATIONS).
            target_id: ID of the target skill.
            metadata: Optional edge metadata.

        Raises:
            ValueError: If the relation type is not recognized.
        """
        if relation not in SKILL_RELATIONS:
            raise ValueError(f"Unknown relation '{relation}'. Must be one of {SKILL_RELATIONS}")

        edge = json.dumps({
            "target": target_id,
            "relation": relation,
            "metadata": metadata or {},
        })
        self._memory.sadd(f"{_GRAPH_EDGES_PREFIX}{source_id}", edge)

        # Store reverse edge for bidirectional traversal
        reverse_edge = json.dumps({
            "target": source_id,
            "relation": f"REVERSE_{relation}",
            "metadata": metadata or {},
        })
        self._memory.sadd(f"{_GRAPH_EDGES_PREFIX}{target_id}", reverse_edge)

    def get_edges(self, skill_id: str, relation: str | None = None) -> list[dict[str, Any]]:
        """Get all edges from a skill, optionally filtered by relation.

        Args:
            skill_id: The source skill's ID.
            relation: Optional filter for edge type.

        Returns:
            List of edge dictionaries with 'target', 'relation', 'metadata'.
        """
        raw_edges = self._memory.smembers(f"{_GRAPH_EDGES_PREFIX}{skill_id}")
        edges = []
        for raw in raw_edges:
            edge = json.loads(raw) if isinstance(raw, str) else raw
            if relation is None or edge.get("relation") == relation:
                edges.append(edge)
        return edges

    def get_related_skills(
        self, skill_id: str, relation: str | None = None, max_depth: int = 1
    ) -> list[Skill]:
        """Find skills connected to a given skill through the graph.

        Performs BFS traversal up to max_depth hops.

        Args:
            skill_id: Starting skill.
            relation: Optional filter for edge type.
            max_depth: Maximum traversal depth.

        Returns:
            List of related skills (excluding the starting skill).
        """
        visited: set[str] = {skill_id}
        frontier: list[str] = [skill_id]
        results: list[Skill] = []

        for _depth in range(max_depth):
            next_frontier: list[str] = []
            for sid in frontier:
                edges = self.get_edges(sid, relation)
                for edge in edges:
                    target = edge["target"]
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
                        skill = self.get_skill(target)
                        if skill:
                            results.append(skill)
            frontier = next_frontier
            if not frontier:
                break

        return results
