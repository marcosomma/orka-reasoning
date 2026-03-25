# OrKa: Orchestrator Kit Agents — Brain Skill Graph Tests

"""Tests for the SkillGraph knowledge graph."""

import json
import pytest
from unittest.mock import MagicMock

from orka.brain.skill import Skill, SkillStep
from orka.brain.skill_graph import SkillGraph, SKILL_RELATIONS


class FakeMemory:
    """In-memory fake of RedisStack memory for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    def hset(self, name: str, key: str, value: str) -> int:
        if name not in self._hashes:
            self._hashes[name] = {}
        self._hashes[name][key] = value
        return 1

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    def hkeys(self, name: str) -> list[str]:
        return list(self._hashes.get(name, {}).keys())

    def hdel(self, name: str, *keys: str) -> int:
        count = 0
        h = self._hashes.get(name, {})
        for k in keys:
            if k in h:
                del h[k]
                count += 1
        return count

    def sadd(self, name: str, *values: str) -> int:
        if name not in self._sets:
            self._sets[name] = set()
        count = 0
        for v in values:
            if v not in self._sets[name]:
                self._sets[name].add(v)
                count += 1
        return count

    def srem(self, name: str, *values: str) -> int:
        s = self._sets.get(name, set())
        count = 0
        for v in values:
            if v in s:
                s.discard(v)
                count += 1
        return count

    def smembers(self, name: str) -> list[str]:
        return list(self._sets.get(name, set()))


def _make_skill(name: str = "Test Skill", tags: list[str] | None = None) -> Skill:
    return Skill(
        name=name,
        description=f"Description of {name}",
        procedure=[SkillStep(action="do stuff", order=0)],
        tags=tags or ["test"],
        source_context={"task_structures": ["sequential"]},
    )


class TestSkillGraph:
    def setup_method(self):
        self.memory = FakeMemory()
        self.graph = SkillGraph(memory=self.memory)

    def test_save_and_retrieve(self):
        skill = _make_skill("Alpha")
        self.graph.save_skill(skill)

        retrieved = self.graph.get_skill(skill.id)
        assert retrieved is not None
        assert retrieved.name == "Alpha"
        assert retrieved.id == skill.id

    def test_get_nonexistent(self):
        assert self.graph.get_skill("nonexistent") is None

    def test_list_skills(self):
        s1 = _make_skill("Skill A")
        s2 = _make_skill("Skill B")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)

        skills = self.graph.list_skills()
        names = {s.name for s in skills}
        assert names == {"Skill A", "Skill B"}

    def test_list_skills_empty(self):
        assert self.graph.list_skills() == []

    def test_find_by_tag(self):
        s1 = _make_skill("Tagged A", tags=["analysis"])
        s2 = _make_skill("Tagged B", tags=["generation"])
        s3 = _make_skill("Tagged C", tags=["analysis", "generation"])
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)
        self.graph.save_skill(s3)

        analysis_skills = self.graph.find_by_tag("analysis")
        names = {s.name for s in analysis_skills}
        assert "Tagged A" in names
        assert "Tagged C" in names
        assert "Tagged B" not in names

    def test_delete_skill(self):
        skill = _make_skill("Deletable")
        self.graph.save_skill(skill)
        assert self.graph.get_skill(skill.id) is not None

        result = self.graph.delete_skill(skill.id)
        assert result is True
        assert self.graph.get_skill(skill.id) is None

    def test_delete_nonexistent(self):
        assert self.graph.delete_skill("nope") is False

    def test_add_and_get_edges(self):
        s1 = _make_skill("Source")
        s2 = _make_skill("Target")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)

        self.graph.add_edge(s1.id, "DERIVES_FROM", s2.id, {"reason": "refinement"})

        edges = self.graph.get_edges(s1.id)
        assert len(edges) == 1
        assert edges[0]["relation"] == "DERIVES_FROM"
        assert edges[0]["target"] == s2.id

    def test_get_edges_filtered(self):
        s1 = _make_skill("A")
        s2 = _make_skill("B")
        s3 = _make_skill("C")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)
        self.graph.save_skill(s3)

        self.graph.add_edge(s1.id, "DERIVES_FROM", s2.id)
        self.graph.add_edge(s1.id, "COMPLEMENTS", s3.id)

        derives = self.graph.get_edges(s1.id, "DERIVES_FROM")
        assert len(derives) == 1
        all_edges = self.graph.get_edges(s1.id)
        assert len(all_edges) == 2

    def test_add_edge_invalid_relation(self):
        with pytest.raises(ValueError, match="Unknown relation"):
            self.graph.add_edge("a", "INVALID", "b")

    def test_reverse_edges_created(self):
        s1 = _make_skill("Source")
        s2 = _make_skill("Target")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)

        self.graph.add_edge(s1.id, "DERIVES_FROM", s2.id)

        # Target should have reverse edge
        reverse_edges = self.graph.get_edges(s2.id)
        assert len(reverse_edges) == 1
        assert reverse_edges[0]["relation"] == "REVERSE_DERIVES_FROM"
        assert reverse_edges[0]["target"] == s1.id

    def test_get_related_skills(self):
        s1 = _make_skill("Root")
        s2 = _make_skill("Child")
        s3 = _make_skill("Grandchild")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)
        self.graph.save_skill(s3)

        self.graph.add_edge(s1.id, "DERIVES_FROM", s2.id)
        self.graph.add_edge(s2.id, "DERIVES_FROM", s3.id)

        # Depth 1 — only direct neighbors
        related = self.graph.get_related_skills(s1.id, max_depth=1)
        names = {s.name for s in related}
        assert "Child" in names
        assert "Grandchild" not in names

        # Depth 2 — includes grandchild (via reverse edges)
        related_deep = self.graph.get_related_skills(s1.id, max_depth=2)
        names_deep = {s.name for s in related_deep}
        assert "Child" in names_deep

    def test_get_related_skills_with_filter(self):
        s1 = _make_skill("A")
        s2 = _make_skill("B")
        s3 = _make_skill("C")
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)
        self.graph.save_skill(s3)

        self.graph.add_edge(s1.id, "DERIVES_FROM", s2.id)
        self.graph.add_edge(s1.id, "COMPLEMENTS", s3.id)

        related = self.graph.get_related_skills(s1.id, relation="DERIVES_FROM")
        names = {s.name for s in related}
        assert "B" in names
        assert "C" not in names

    def test_update_skill(self):
        skill = _make_skill("Original")
        self.graph.save_skill(skill)

        skill.name = "Updated"
        skill.confidence = 0.9
        self.graph.save_skill(skill)

        retrieved = self.graph.get_skill(skill.id)
        assert retrieved is not None
        assert retrieved.name == "Updated"
        assert retrieved.confidence == 0.9


class TestSkillGraphTTL:
    def setup_method(self):
        self.memory = FakeMemory()
        self.graph = SkillGraph(memory=self.memory)

    def test_list_skills_excludes_expired(self):
        from datetime import UTC, datetime, timedelta

        active = _make_skill("Active")
        active.renew_ttl()
        self.graph.save_skill(active)

        expired = _make_skill("Expired")
        expired.expires_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.graph.save_skill(expired)

        skills = self.graph.list_skills()
        names = {s.name for s in skills}
        assert "Active" in names
        assert "Expired" not in names

    def test_list_skills_includes_no_expiry(self):
        """Skills without expires_at (legacy) are always included."""
        legacy = _make_skill("Legacy")
        assert legacy.expires_at == ""
        self.graph.save_skill(legacy)

        skills = self.graph.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "Legacy"

    def test_cleanup_expired_skills(self):
        from datetime import UTC, datetime, timedelta

        active = _make_skill("Active")
        active.renew_ttl()
        self.graph.save_skill(active)

        expired = _make_skill("Expired")
        expired.expires_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.graph.save_skill(expired)

        result = self.graph.cleanup_expired_skills()
        assert result["deleted"] == 1
        assert result["checked"] == 2

        # Verify active is still there, expired is gone
        assert self.graph.get_skill(active.id) is not None
        assert self.graph.get_skill(expired.id) is None

    def test_cleanup_no_expired(self):
        active = _make_skill("Active")
        active.renew_ttl()
        self.graph.save_skill(active)

        result = self.graph.cleanup_expired_skills()
        assert result["deleted"] == 0
        assert result["checked"] == 1

    def test_save_skill_sets_redis_ttl_when_expire_method_exists(self):
        """When memory has .expire(), save_skill should call it."""
        self.memory.expire = MagicMock()
        skill = _make_skill("With TTL")
        skill.renew_ttl()
        self.graph.save_skill(skill)

        self.memory.expire.assert_called_once()
        key, ttl = self.memory.expire.call_args[0]
        assert key == f"orka:brain:skill:{skill.id}"
        assert ttl > 0
