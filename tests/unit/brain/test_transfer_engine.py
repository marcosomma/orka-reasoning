# OrKa: Orchestrator Kit Agents — Brain Transfer Engine Tests

"""Tests for the SkillTransferEngine."""

import pytest

from orka.brain.context_analyzer import ContextAnalyzer, ContextFeatures
from orka.brain.skill import Skill, SkillStep, SkillTransferRecord
from orka.brain.skill_graph import SkillGraph
from orka.brain.transfer_engine import SkillTransferEngine, TransferCandidate


class FakeMemory:
    """In-memory fake for testing (same as in test_skill_graph)."""

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


def _make_skill(name: str, structures: list[str], patterns: list[str], **kwargs) -> Skill:
    defaults = {
        "name": name,
        "description": f"Skill: {name}",
        "procedure": [SkillStep(action=f"step for {name}", order=0)],
        "source_context": {
            "task_structures": structures,
            "cognitive_patterns": patterns,
            "input_shape": kwargs.get("input_shape", "single_text"),
            "output_shape": kwargs.get("output_shape", "text"),
        },
        "tags": structures + patterns,
        "confidence": kwargs.get("confidence", 0.6),
    }
    return Skill(**defaults)


class TestSkillTransferEngine:
    def setup_method(self):
        self.memory = FakeMemory()
        self.graph = SkillGraph(memory=self.memory)
        self.analyzer = ContextAnalyzer()
        self.engine = SkillTransferEngine(
            skill_graph=self.graph,
            context_analyzer=self.analyzer,
        )

    def test_find_no_skills(self):
        candidates = self.engine.find_transferable_skills(
            {"task": "do something"}
        )
        assert candidates == []

    def test_find_matching_skill(self):
        # Create a skill learned in text analysis domain
        skill = _make_skill(
            "Text Decomposer",
            structures=["decomposition", "sequential"],
            patterns=["analysis"],
        )
        self.graph.save_skill(skill)

        # Search in a different domain but with similar structure
        candidates = self.engine.find_transferable_skills(
            {"task": "Break down the codebase into modules and analyze each one"},
            min_score=0.0,
        )
        assert len(candidates) >= 1
        assert candidates[0].skill.name == "Text Decomposer"
        assert candidates[0].structural_score > 0.0

    def test_ranking_by_relevance(self):
        # High-relevance skill (matches structure and patterns)
        good_skill = _make_skill(
            "Analyzer",
            structures=["decomposition", "sequential"],
            patterns=["analysis", "extraction"],
            confidence=0.8,
        )
        # Low-relevance skill (different structure entirely)
        bad_skill = _make_skill(
            "Router",
            structures=["routing"],
            patterns=["classification"],
            confidence=0.8,
        )
        self.graph.save_skill(good_skill)
        self.graph.save_skill(bad_skill)

        # Context that should match the analyzer
        candidates = self.engine.find_transferable_skills(
            {"task": "Analyze and break down the input, then extract key points"},
            min_score=0.0,
        )
        assert len(candidates) == 2
        # Analyzer should rank higher
        assert candidates[0].skill.name == "Analyzer"

    def test_min_score_filters(self):
        skill = _make_skill(
            "Weak Match",
            structures=["routing"],
            patterns=["classification"],
            confidence=0.3,
        )
        self.graph.save_skill(skill)

        # Context that doesn't match at all
        candidates = self.engine.find_transferable_skills(
            {"task": "Generate a creative poem"},
            min_score=0.8,
        )
        assert len(candidates) == 0

    def test_top_k_limits(self):
        for i in range(10):
            skill = _make_skill(
                f"Skill_{i}",
                structures=["sequential"],
                patterns=["analysis"],
            )
            self.graph.save_skill(skill)

        candidates = self.engine.find_transferable_skills(
            {"task": "Analyze step by step"},
            top_k=3,
            min_score=0.0,
        )
        assert len(candidates) <= 3

    def test_transfer_history_boosts_score(self):
        # Skill with successful transfer history
        proven_skill = _make_skill(
            "Proven",
            structures=["decomposition"],
            patterns=["analysis"],
            confidence=0.6,
        )
        proven_skill.record_transfer(
            SkillTransferRecord(target_context={}, success=True, confidence=0.7)
        )
        proven_skill.record_transfer(
            SkillTransferRecord(target_context={}, success=True, confidence=0.8)
        )

        # Same skill but no transfer history
        unproven = _make_skill(
            "Unproven",
            structures=["decomposition"],
            patterns=["analysis"],
            confidence=0.6,
        )

        self.graph.save_skill(proven_skill)
        self.graph.save_skill(unproven)

        candidates = self.engine.find_transferable_skills(
            {"task": "Break down and analyze"},
            min_score=0.0,
        )
        # Proven skill should rank higher due to transfer history
        proven_candidate = next(c for c in candidates if c.skill.name == "Proven")
        unproven_candidate = next(c for c in candidates if c.skill.name == "Unproven")
        assert proven_candidate.transfer_score > unproven_candidate.transfer_score

    def test_adaptations_suggested(self):
        skill = _make_skill(
            "Text Skill",
            structures=["decomposition"],
            patterns=["analysis"],
            input_shape="single_text",
            output_shape="text",
        )
        self.graph.save_skill(skill)

        # Target has different shapes
        candidates = self.engine.find_transferable_skills(
            {
                "task": "Break down the data and analyze",
                "input": {"key": "value"},
                "output_format": "json",
            },
            min_score=0.0,
        )
        assert len(candidates) >= 1
        candidate = candidates[0]
        # Should suggest input and output adaptations
        assert "input_adaptation" in candidate.adaptations or "output_adaptation" in candidate.adaptations

    def test_reasoning_generated(self):
        skill = _make_skill(
            "Named Skill",
            structures=["decomposition"],
            patterns=["analysis"],
        )
        self.graph.save_skill(skill)

        candidates = self.engine.find_transferable_skills(
            {"task": "Break down input and analyze"},
            min_score=0.0,
        )
        assert len(candidates) >= 1
        assert "Named Skill" in candidates[0].reasoning

    def test_keyword_similarity_fallback(self):
        # Without embedder, should use keyword overlap
        skill = _make_skill(
            "Keyword Skill",
            structures=["validation"],
            patterns=["evaluation"],
        )
        self.graph.save_skill(skill)

        candidates = self.engine.find_transferable_skills(
            {"task": "Validate and evaluate the results"},
            min_score=0.0,
        )
        assert len(candidates) >= 1
        # Should have some semantic score from keyword overlap
        assert candidates[0].semantic_score >= 0.0
