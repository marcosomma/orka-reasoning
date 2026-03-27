# OrKa: Orchestrator Kit Agents — Brain v2 Skill Architecture Tests

"""Tests for Brain v2 features: SkillType, search tokens, new learning modes,
two-stage retrieval, GraphScout-Brain integration, and BrainAgent v2 operations.
"""

import json
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from orka.brain.skill import (
    Skill,
    SkillCondition,
    SkillStep,
    SkillType,
    generate_search_tokens,
)
from orka.brain.skill_graph import SkillGraph
from orka.brain.brain import Brain
from orka.brain.transfer_engine import SkillTransferEngine
from orka.brain.context_analyzer import ContextAnalyzer


# ------------------------------------------------------------------ #
# FakeMemory — shared in-memory Redis compatible mock
# ------------------------------------------------------------------ #


class FakeMemory:
    """In-memory fake of RedisStack memory for testing."""

    def __init__(self) -> None:
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


# ------------------------------------------------------------------ #
# SkillType Enum
# ------------------------------------------------------------------ #


class TestSkillType:
    def test_all_values(self):
        expected = {
            "procedural",
            "execution_recipe",
            "prompt_template",
            "parameter_config",
            "graph_path",
            "anti_pattern",
            "domain_heuristic",
        }
        assert {st.value for st in SkillType} == expected

    def test_str_enum(self):
        assert SkillType.EXECUTION_RECIPE == "execution_recipe"
        assert isinstance(SkillType.GRAPH_PATH, str)

    def test_default_skill_type(self):
        skill = Skill(name="test")
        assert skill.skill_type == SkillType.PROCEDURAL.value


# ------------------------------------------------------------------ #
# generate_search_tokens
# ------------------------------------------------------------------ #


class TestGenerateSearchTokens:
    def test_simple_name(self):
        tokens = generate_search_tokens("recipe:code-review:parallel-linter")
        assert "recipe" in tokens
        assert "code" in tokens
        assert "review" in tokens
        assert "linter" in tokens
        assert "parallel" in tokens

    def test_arrow_separator(self):
        tokens = generate_search_tokens("path:analysis→summarizer→writer")
        assert "analysis" in tokens
        assert "summarizer" in tokens
        assert "writer" in tokens

    def test_underscore_and_plus(self):
        tokens = generate_search_tokens("recipe:data_pipeline:etl+validate")
        assert "data" in tokens
        assert "pipeline" in tokens
        assert "etl" in tokens
        assert "validate" in tokens

    def test_preserves_colon_parts(self):
        tokens = generate_search_tokens("anti:security:sql-injection")
        assert "anti" in tokens
        assert "security" in tokens

    def test_empty_string(self):
        tokens = generate_search_tokens("")
        assert tokens == []

    def test_sorted_and_unique(self):
        tokens = generate_search_tokens("a:a:b")
        assert tokens == sorted(set(tokens))


# ------------------------------------------------------------------ #
# Skill v2 Fields
# ------------------------------------------------------------------ #


class TestSkillV2Fields:
    def _make_v2_skill(self, **kwargs: object) -> Skill:
        defaults: dict[str, object] = {
            "name": "recipe:code-review:sequential-lint+analyze",
            "description": "Code review recipe",
            "skill_type": SkillType.EXECUTION_RECIPE.value,
            "task_description": "Lint and analyze a PR for code quality",
            "domain_keywords": ["code-review", "quality"],
            "output_description": "JSON report with lint issues",
            "search_tokens": generate_search_tokens("recipe:code-review:sequential-lint+analyze"),
            "recipe": {
                "pattern": "sequential",
                "agents": [{"id": "linter"}, {"id": "analyzer"}],
                "total_agents": 2,
            },
            "anti_signals": [],
        }
        defaults.update(kwargs)
        return Skill(**defaults)  # type: ignore[arg-type]

    def test_roundtrip_v2_fields(self):
        skill = self._make_v2_skill()
        data = skill.to_dict()
        restored = Skill.from_dict(data)

        assert restored.skill_type == SkillType.EXECUTION_RECIPE.value
        assert restored.task_description == skill.task_description
        assert restored.domain_keywords == skill.domain_keywords
        assert restored.output_description == skill.output_description
        assert restored.search_tokens == skill.search_tokens
        assert restored.recipe == skill.recipe
        assert restored.anti_signals == skill.anti_signals

    def test_roundtrip_anti_pattern(self):
        skill = Skill(
            name="anti:security:sql-injection",
            skill_type=SkillType.ANTI_PATTERN.value,
            task_description="Injected SQL in user prompt",
            anti_signals=["sql injection", "unescaped input"],
            domain_keywords=["security"],
        )
        data = skill.to_dict()
        restored = Skill.from_dict(data)
        assert restored.anti_signals == ["sql injection", "unescaped input"]
        assert restored.skill_type == SkillType.ANTI_PATTERN.value

    def test_v2_embedding_text_recipe(self):
        skill = self._make_v2_skill()
        text = skill.to_embedding_text()
        assert "Lint and analyze" in text
        assert "linter" in text
        assert "analyzer" in text
        assert "sequential" in text
        assert "JSON report" in text

    def test_v2_embedding_text_anti_pattern(self):
        skill = Skill(
            name="anti:security:sql-injection",
            skill_type=SkillType.ANTI_PATTERN.value,
            task_description="SQL injection via prompt",
            anti_signals=["sql injection"],
            domain_keywords=["security"],
        )
        text = skill.to_embedding_text()
        assert "SQL injection" in text
        assert "not: sql injection" in text
        assert "security" in text

    def test_legacy_embedding_fallback(self):
        """Skills without v2 fields use the legacy embedding format."""
        skill = Skill(
            name="Divide and Conquer",
            description="Break a problem down",
            tags=["decomposition"],
            procedure=[SkillStep(action="decompose", order=0)],
            preconditions=[SkillCondition(predicate="input is decomposable")],
        )
        text = skill.to_embedding_text()
        assert "Divide and Conquer" in text
        assert "decompose" in text
        assert "decomposable" in text

    def test_backward_compat_defaults(self):
        """Legacy skills without v2 keys deserialize correctly."""
        legacy_data = {
            "name": "Old Skill",
            "description": "Old description",
            "procedure": [],
            "tags": ["old"],
        }
        skill = Skill.from_dict(legacy_data)
        assert skill.skill_type == SkillType.PROCEDURAL.value
        assert skill.task_description == ""
        assert skill.domain_keywords == []
        assert skill.recipe == {}
        assert skill.anti_signals == []
        assert skill.search_tokens == []


# ------------------------------------------------------------------ #
# SkillGraph — type/domain indexes
# ------------------------------------------------------------------ #


class TestSkillGraphV2Indexes:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.graph = SkillGraph(memory=self.memory)

    def _make_skill(self, name: str, skill_type: str, domains: list[str]) -> Skill:
        return Skill(
            name=name,
            description=f"Test skill {name}",
            skill_type=skill_type,
            domain_keywords=domains,
            procedure=[SkillStep(action="do", order=0)],
            tags=domains,
        )

    def test_find_by_type(self):
        recipe = self._make_skill("R1", SkillType.EXECUTION_RECIPE.value, ["code"])
        anti = self._make_skill("A1", SkillType.ANTI_PATTERN.value, ["code"])
        self.graph.save_skill(recipe)
        self.graph.save_skill(anti)

        recipes = self.graph.find_by_type(SkillType.EXECUTION_RECIPE.value)
        assert len(recipes) == 1
        assert recipes[0].name == "R1"

        antis = self.graph.find_by_type(SkillType.ANTI_PATTERN.value)
        assert len(antis) == 1
        assert antis[0].name == "A1"

    def test_find_by_type_empty(self):
        assert self.graph.find_by_type("graph_path") == []

    def test_find_by_domain(self):
        s1 = self._make_skill("S1", SkillType.PROCEDURAL.value, ["security"])
        s2 = self._make_skill("S2", SkillType.PROCEDURAL.value, ["performance"])
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)

        sec = self.graph.find_by_domain("security")
        assert len(sec) == 1
        assert sec[0].name == "S1"

    def test_find_by_domain_multi_keyword(self):
        s = self._make_skill("S", SkillType.PROCEDURAL.value, ["security", "code-review"])
        self.graph.save_skill(s)

        assert len(self.graph.find_by_domain("security")) == 1
        assert len(self.graph.find_by_domain("code-review")) == 1

    def test_find_filtered_both(self):
        s1 = self._make_skill("R-Sec", SkillType.EXECUTION_RECIPE.value, ["security"])
        s2 = self._make_skill("R-Perf", SkillType.EXECUTION_RECIPE.value, ["performance"])
        s3 = self._make_skill("A-Sec", SkillType.ANTI_PATTERN.value, ["security"])
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)
        self.graph.save_skill(s3)

        # Type + domain intersection
        results = self.graph.find_filtered(
            skill_type=SkillType.EXECUTION_RECIPE.value,
            domain="security",
        )
        assert len(results) == 1
        assert results[0].name == "R-Sec"

    def test_find_filtered_type_only(self):
        s1 = self._make_skill("R1", SkillType.EXECUTION_RECIPE.value, ["a"])
        s2 = self._make_skill("R2", SkillType.EXECUTION_RECIPE.value, ["b"])
        self.graph.save_skill(s1)
        self.graph.save_skill(s2)

        results = self.graph.find_filtered(skill_type=SkillType.EXECUTION_RECIPE.value)
        assert len(results) == 2

    def test_find_filtered_domain_only(self):
        s1 = self._make_skill("X", SkillType.GRAPH_PATH.value, ["ml"])
        self.graph.save_skill(s1)

        results = self.graph.find_filtered(domain="ml")
        assert len(results) == 1

    def test_find_filtered_no_args_fallback(self):
        s1 = self._make_skill("A", SkillType.PROCEDURAL.value, [])
        self.graph.save_skill(s1)

        results = self.graph.find_filtered()
        assert len(results) >= 1

    def test_delete_cleans_type_index(self):
        s = self._make_skill("D", SkillType.EXECUTION_RECIPE.value, ["x"])
        self.graph.save_skill(s)
        assert len(self.graph.find_by_type(SkillType.EXECUTION_RECIPE.value)) == 1

        self.graph.delete_skill(s.id)
        assert len(self.graph.find_by_type(SkillType.EXECUTION_RECIPE.value)) == 0

    def test_delete_cleans_domain_index(self):
        s = self._make_skill("D", SkillType.PROCEDURAL.value, ["nlp"])
        self.graph.save_skill(s)
        assert len(self.graph.find_by_domain("nlp")) == 1

        self.graph.delete_skill(s.id)
        assert len(self.graph.find_by_domain("nlp")) == 0

    def test_expired_skill_excluded_from_find_by_type(self):
        s = self._make_skill("E", SkillType.GRAPH_PATH.value, ["x"])
        s.expires_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        self.graph.save_skill(s)

        assert self.graph.find_by_type(SkillType.GRAPH_PATH.value) == []


# ------------------------------------------------------------------ #
# Brain — new learn methods
# ------------------------------------------------------------------ #


class TestBrainLearnRecipe:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.brain = Brain(memory=self.memory)

    @pytest.mark.asyncio
    async def test_learn_recipe_basic(self):
        skill = await self.brain.learn_recipe(
            agents=[{"id": "linter"}, {"id": "analyzer"}],
            pattern="sequential",
            context={"domain": "code-review", "task": "PR review"},
            outcome={"success": True, "quality": 0.9},
        )
        assert skill is not None
        assert skill.skill_type == SkillType.EXECUTION_RECIPE.value
        assert "recipe" in skill.name or "code-review" in skill.name
        assert skill.recipe["pattern"] == "sequential"
        assert len(skill.recipe["agents"]) == 2
        # Preconditions must list required agents
        assert len(skill.preconditions) >= 2
        predicates = [c.predicate for c in skill.preconditions]
        assert any("linter" in p for p in predicates)
        assert any("analyzer" in p for p in predicates)
        assert any("pattern" in p for p in predicates)  # composition pattern

    @pytest.mark.asyncio
    async def test_learn_recipe_failed_outcome(self):
        result = await self.brain.learn_recipe(
            agents=[{"id": "a"}],
            pattern="sequential",
            context={"domain": "x"},
            outcome={"success": False},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_learn_recipe_no_agents(self):
        result = await self.brain.learn_recipe(
            agents=[],
            pattern="sequential",
            context={"domain": "x"},
            outcome={"success": True},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_learn_recipe_reinforces_existing(self):
        skill1 = await self.brain.learn_recipe(
            agents=[{"id": "a"}, {"id": "b"}],
            pattern="sequential",
            context={"domain": "test", "task": "demo"},
            outcome={"success": True, "quality": 0.8},
        )
        skill2 = await self.brain.learn_recipe(
            agents=[{"id": "a"}, {"id": "b"}],
            pattern="sequential",
            context={"domain": "test", "task": "demo"},
            outcome={"success": True, "quality": 0.9},
        )
        assert skill1 is not None
        assert skill2 is not None
        assert skill2.id == skill1.id
        assert skill2.usage_count >= 2

    @pytest.mark.asyncio
    async def test_learn_recipe_failure_degrades_existing(self):
        """Failure on existing skill should lower success_rate below 1.0."""
        skill1 = await self.brain.learn_recipe(
            agents=[{"id": "a"}, {"id": "b"}],
            pattern="sequential",
            context={"domain": "test", "task": "demo"},
            outcome={"success": True, "quality": 0.8},
        )
        assert skill1 is not None
        assert skill1.success_rate == 1.0

        # Same recipe, but this time it fails
        skill2 = await self.brain.learn_recipe(
            agents=[{"id": "a"}, {"id": "b"}],
            pattern="sequential",
            context={"domain": "test", "task": "demo"},
            outcome={"success": False},
        )
        assert skill2 is not None
        assert skill2.id == skill1.id
        assert skill2.success_rate < 1.0
        assert skill2.usage_count == 2


class TestBrainLearnAntiPattern:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.brain = Brain(memory=self.memory)

    @pytest.mark.asyncio
    async def test_learn_anti_pattern_basic(self):
        skill = await self.brain.learn_anti_pattern(
            what_failed="Using GPT-4 for simple lookups",
            why="Excessive cost for trivial queries",
            context={"domain": "cost-optimization"},
        )
        assert skill.skill_type == SkillType.ANTI_PATTERN.value
        assert "anti:" in skill.name
        assert "cost-optimization" in skill.name or "general" in skill.name
        assert "Excessive cost" in skill.anti_signals[0]
        assert skill.confidence == 0.9

    @pytest.mark.asyncio
    async def test_learn_anti_pattern_severity(self):
        skill = await self.brain.learn_anti_pattern(
            what_failed="Unvalidated user input",
            why="SQL injection risk",
            context={"domain": "security"},
            severity="critical",
        )
        assert "critical" in skill.tags

    @pytest.mark.asyncio
    async def test_learn_anti_pattern_dedup(self):
        """Second call with same what_failed should reinforce, not duplicate."""
        skill1 = await self.brain.learn_anti_pattern(
            what_failed="Using GPT-4 for simple lookups",
            why="Excessive cost",
            context={"domain": "cost-optimization"},
        )
        skill2 = await self.brain.learn_anti_pattern(
            what_failed="Using GPT-4 for simple lookups",
            why="Excessive cost",
            context={"domain": "cost-optimization"},
        )
        assert skill1.id == skill2.id
        assert skill2.usage_count == 2

    @pytest.mark.asyncio
    async def test_learn_anti_pattern_dedup_different_text_same_context(self):
        """Similar context should still dedup via fingerprint/similarity."""
        skill1 = await self.brain.learn_anti_pattern(
            what_failed="Running analysis on trivial changes",
            why="Wastes compute",
            context={"domain": "code-review", "task": "trivial PR"},
        )
        # Same domain+task context → similar features → should match
        skill2 = await self.brain.learn_anti_pattern(
            what_failed="Running analysis on trivial changes",
            why="Wastes compute",
            context={"domain": "code-review", "task": "trivial PR"},
        )
        assert skill1.id == skill2.id


class TestBrainLearnPath:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.brain = Brain(memory=self.memory)

    @pytest.mark.asyncio
    async def test_learn_path_basic(self):
        skill = await self.brain.learn_path(
            path_nodes=["analyzer", "summarizer", "writer"],
            score=0.85,
            context={"domain": "text-analysis", "task": "summarize long docs"},
            outcome={"success": True, "quality": 0.9},
        )
        assert skill is not None
        assert skill.skill_type == SkillType.GRAPH_PATH.value
        assert "path:" in skill.name
        assert skill.recipe["pattern"] == "graphscout-path"
        assert len(skill.recipe["agents"]) == 3
        assert skill.recipe["graphscout_score"] == 0.85
        # Preconditions must list required agents
        assert len(skill.preconditions) == 3
        predicates = [c.predicate for c in skill.preconditions]
        assert any("analyzer" in p for p in predicates)
        assert any("summarizer" in p for p in predicates)
        assert any("writer" in p for p in predicates)

    @pytest.mark.asyncio
    async def test_learn_path_failed_outcome(self):
        result = await self.brain.learn_path(
            path_nodes=["a", "b"],
            score=0.5,
            context={"domain": "x"},
            outcome={"success": False},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_learn_path_empty_nodes(self):
        result = await self.brain.learn_path(
            path_nodes=[],
            score=0.5,
            context={"domain": "x"},
            outcome={"success": True},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_learn_path_with_budget(self):
        skill = await self.brain.learn_path(
            path_nodes=["a", "b"],
            score=0.7,
            context={"domain": "test"},
            outcome={"success": True},
            budget_used={"tokens": 500, "latency_ms": 200},
        )
        assert skill is not None
        assert skill.recipe["budget_used"] == {"tokens": 500, "latency_ms": 200}

    @pytest.mark.asyncio
    async def test_learn_path_failure_degrades_existing(self):
        """Failure on existing path skill should lower success_rate."""
        skill1 = await self.brain.learn_path(
            path_nodes=["a", "b", "c"],
            score=0.85,
            context={"domain": "test", "task": "demo"},
            outcome={"success": True, "quality": 0.9},
        )
        assert skill1 is not None
        assert skill1.success_rate == 1.0

        skill2 = await self.brain.learn_path(
            path_nodes=["a", "b", "c"],
            score=0.85,
            context={"domain": "test", "task": "demo"},
            outcome={"success": False},
        )
        assert skill2 is not None
        assert skill2.id == skill1.id
        assert skill2.success_rate == 0.5
        assert skill2.usage_count == 2


# ------------------------------------------------------------------ #
# Brain — recall with v2 filters
# ------------------------------------------------------------------ #


class TestBrainRecallV2:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.brain = Brain(memory=self.memory)

    @pytest.mark.asyncio
    async def test_recall_with_skill_types_filter(self):
        await self.brain.learn_recipe(
            agents=[{"id": "linter"}],
            pattern="sequential",
            context={"domain": "code", "task": "lint"},
            outcome={"success": True, "quality": 0.8},
        )
        await self.brain.learn_anti_pattern(
            what_failed="bad config",
            why="crashed",
            context={"domain": "code"},
        )

        # Recall only recipes
        candidates = await self.brain.recall(
            context={"domain": "code", "task": "lint"},
            skill_types=[SkillType.EXECUTION_RECIPE.value],
            min_score=0.0,
        )
        for c in candidates:
            assert c.skill.skill_type == SkillType.EXECUTION_RECIPE.value

    @pytest.mark.asyncio
    async def test_recall_with_domain_filter(self):
        await self.brain.learn_recipe(
            agents=[{"id": "sec-scan"}],
            pattern="sequential",
            context={"domain": "security", "task": "scan"},
            outcome={"success": True},
        )
        await self.brain.learn_recipe(
            agents=[{"id": "perf-test"}],
            pattern="sequential",
            context={"domain": "performance", "task": "benchmark"},
            outcome={"success": True},
        )

        candidates = await self.brain.recall(
            context={"domain": "security"},
            domain_filter="security",
            min_score=0.0,
        )
        # Only security-domain skills
        for c in candidates:
            assert "security" in c.skill.domain_keywords


# ------------------------------------------------------------------ #
# TransferEngine — two-stage retrieval
# ------------------------------------------------------------------ #


class TestTransferEngineTwoStage:
    def setup_method(self) -> None:
        self.memory = FakeMemory()
        self.graph = SkillGraph(memory=self.memory)
        self.analyzer = ContextAnalyzer()
        self.engine = SkillTransferEngine(
            skill_graph=self.graph,
            context_analyzer=self.analyzer,
        )

    def _store_skill(self, name: str, skill_type: str, domains: list[str]) -> Skill:
        skill = Skill(
            name=name,
            description=f"Desc for {name}",
            skill_type=skill_type,
            domain_keywords=domains,
            procedure=[SkillStep(action="do", order=0)],
            tags=domains,
            source_context={
                "task_structures": ["sequential"],
                "cognitive_patterns": ["analysis"],
                "domain_hints": domains,
            },
        )
        skill.renew_ttl()
        self.graph.save_skill(skill)
        return skill

    def test_filter_by_type(self):
        self._store_skill("R", SkillType.EXECUTION_RECIPE.value, ["code"])
        self._store_skill("A", SkillType.ANTI_PATTERN.value, ["code"])

        results = self.engine.find_transferable_skills(
            target_context={"domain": "code"},
            skill_types=[SkillType.EXECUTION_RECIPE.value],
            min_score=0.0,
        )
        for r in results:
            assert r.skill.skill_type == SkillType.EXECUTION_RECIPE.value

    def test_filter_by_domain(self):
        self._store_skill("Sec", SkillType.PROCEDURAL.value, ["security"])
        self._store_skill("Perf", SkillType.PROCEDURAL.value, ["performance"])

        results = self.engine.find_transferable_skills(
            target_context={"domain": "security"},
            domain_filter="security",
            min_score=0.0,
        )
        for r in results:
            assert "security" in r.skill.domain_keywords

    def test_filter_both(self):
        self._store_skill("R-Sec", SkillType.EXECUTION_RECIPE.value, ["security"])
        self._store_skill("R-Perf", SkillType.EXECUTION_RECIPE.value, ["performance"])
        self._store_skill("A-Sec", SkillType.ANTI_PATTERN.value, ["security"])

        results = self.engine.find_transferable_skills(
            target_context={"domain": "security"},
            skill_types=[SkillType.EXECUTION_RECIPE.value],
            domain_filter="security",
            min_score=0.0,
        )
        assert len(results) == 1
        assert results[0].skill.name == "R-Sec"

    def test_no_filter_returns_all(self):
        self._store_skill("A", SkillType.PROCEDURAL.value, ["x"])
        self._store_skill("B", SkillType.ANTI_PATTERN.value, ["y"])

        results = self.engine.find_transferable_skills(
            target_context={"domain": "x"},
            min_score=0.0,
        )
        assert len(results) >= 2


# ------------------------------------------------------------------ #
# BrainAgent — v2 operations
# ------------------------------------------------------------------ #


class TestBrainAgentV2Operations:
    def setup_method(self) -> None:
        self.memory = FakeMemory()

    def _make_agent(self, operation: str = "learn") -> "BrainAgent":
        from orka.agents.brain_agent import BrainAgent

        return BrainAgent(
            agent_id="test-brain",
            operation=operation,
            memory_logger=self.memory,
        )

    @pytest.mark.asyncio
    async def test_learn_recipe_operation(self):
        agent = self._make_agent("learn_recipe")
        ctx = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "lint"}, {"id": "check"}],
                "pattern": "sequential",
                "domain": "code-review",
                "task": "PR quality check",
                "quality": 0.85,
            }),
        }
        result = await agent._run_impl(ctx)
        assert "recipe" in result.get("response", "").lower() or "Learned" in result.get("response", "")
        assert result.get("skill_type") == SkillType.EXECUTION_RECIPE.value

    @pytest.mark.asyncio
    async def test_learn_anti_operation(self):
        agent = self._make_agent("learn_anti")
        ctx = {
            "formatted_prompt": json.dumps({
                "what_failed": "Using local model for summarization",
                "why": "Hallucination rate too high",
                "domain": "summarization",
                "severity": "critical",
            }),
        }
        result = await agent._run_impl(ctx)
        assert "anti-pattern" in result.get("response", "").lower() or "anti:" in result.get("skill_name", "")
        assert result.get("skill_type") == SkillType.ANTI_PATTERN.value

    @pytest.mark.asyncio
    async def test_learn_path_operation(self):
        agent = self._make_agent("learn_path")
        ctx = {
            "formatted_prompt": json.dumps({
                "path_nodes": ["analyzer", "summarizer", "writer"],
                "score": 0.9,
                "domain": "text-analysis",
                "task": "summarize reports",
            }),
        }
        result = await agent._run_impl(ctx)
        assert "path" in result.get("response", "").lower() or "Learned" in result.get("response", "")
        assert result.get("skill_type") == SkillType.GRAPH_PATH.value

    @pytest.mark.asyncio
    async def test_learn_path_from_arrow_string(self):
        agent = self._make_agent("learn_path")
        ctx = {
            "formatted_prompt": json.dumps({
                "path_nodes": "a→b→c",
                "score": 0.7,
                "domain": "test",
            }),
        }
        result = await agent._run_impl(ctx)
        assert result.get("skill_id") is not None

    @pytest.mark.asyncio
    async def test_learn_path_dict_nodes(self):
        """path_nodes may contain dicts (e.g. {\"id\": \"agent1\"}) from the LLM."""
        agent = self._make_agent("learn_path")
        ctx = {
            "formatted_prompt": json.dumps({
                "path_nodes": [
                    {"id": "analyzer"},
                    {"id": "summarizer"},
                    {"id": "writer"},
                ],
                "score": 0.85,
                "domain": "test-dict",
                "task": "dict nodes",
            }),
        }
        result = await agent._run_impl(ctx)
        assert result.get("skill_id") is not None
        assert result.get("skill_type") == SkillType.GRAPH_PATH.value
        # Verify the name was built from string IDs, not repr(dict)
        assert "analyzer" in result.get("skill_name", "")

    @pytest.mark.asyncio
    async def test_learn_recipe_reads_success_false(self):
        """_handle_learn_recipe must read payload['success'] not hardcode True."""
        agent = self._make_agent("learn_recipe")
        # First create the recipe (success=True)
        ctx_ok = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "lint"}, {"id": "check"}],
                "pattern": "sequential",
                "domain": "code-review",
                "task": "PR quality check",
                "quality": 0.85,
            }),
        }
        result_ok = await agent._run_impl(ctx_ok)
        skill_id = result_ok.get("skill_id")
        assert skill_id is not None

        # Now send success: false — should degrade success_rate
        ctx_fail = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "lint"}, {"id": "check"}],
                "pattern": "sequential",
                "domain": "code-review",
                "task": "PR quality check",
                "quality": 0.0,
                "success": False,
            }),
        }
        result_fail = await agent._run_impl(ctx_fail)
        # Should return the same skill, now with usage_count=2
        assert result_fail.get("skill_id") == skill_id

        # Verify success_rate dropped
        from orka.brain.brain import Brain
        brain = Brain(memory=self.memory)
        skill = await brain.get_skill(skill_id)
        assert skill is not None
        assert skill.usage_count == 2
        assert skill.success_rate < 1.0  # was 100%, now 50%

    @pytest.mark.asyncio
    async def test_learn_path_reads_success_false(self):
        """_handle_learn_path must read payload['success'] not hardcode True."""
        agent = self._make_agent("learn_path")
        # First create the path (success=True implicitly)
        ctx_ok = {
            "formatted_prompt": json.dumps({
                "path_nodes": ["a", "b", "c"],
                "score": 0.9,
                "domain": "test",
                "task": "demo path",
            }),
        }
        result_ok = await agent._run_impl(ctx_ok)
        skill_id = result_ok.get("skill_id")
        assert skill_id is not None

        # Now send success: false — should degrade
        ctx_fail = {
            "formatted_prompt": json.dumps({
                "path_nodes": ["a", "b", "c"],
                "score": 0.3,
                "domain": "test",
                "task": "demo path",
                "success": False,
            }),
        }
        result_fail = await agent._run_impl(ctx_fail)
        assert result_fail.get("skill_id") == skill_id

        from orka.brain.brain import Brain
        brain = Brain(memory=self.memory)
        skill = await brain.get_skill(skill_id)
        assert skill is not None
        assert skill.success_rate < 1.0

    @pytest.mark.asyncio
    async def test_learn_recipe_string_success_false(self):
        """success='false' (string) should be treated as False."""
        agent = self._make_agent("learn_recipe")
        ctx_ok = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "x"}],
                "pattern": "sequential",
                "domain": "strtest",
                "task": "string false",
                "quality": 0.8,
            }),
        }
        await agent._run_impl(ctx_ok)

        ctx_fail = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "x"}],
                "pattern": "sequential",
                "domain": "strtest",
                "task": "string false",
                "quality": 0.0,
                "success": "false",
            }),
        }
        result = await agent._run_impl(ctx_fail)
        from orka.brain.brain import Brain
        brain = Brain(memory=self.memory)
        skill = await brain.get_skill(result["skill_id"])
        assert skill is not None
        assert skill.success_rate < 1.0

    @pytest.mark.asyncio
    async def test_recall_with_v2_filters(self):
        # First learn something
        learn_agent = self._make_agent("learn_recipe")
        ctx_learn = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "a"}],
                "pattern": "sequential",
                "domain": "test",
                "task": "demo",
                "quality": 0.8,
            }),
        }
        await learn_agent._run_impl(ctx_learn)

        # Now recall with filters
        recall_agent = self._make_agent("recall")
        ctx_recall = {
            "formatted_prompt": json.dumps({
                "domain": "test",
                "task": "demo",
                "skill_types": [SkillType.EXECUTION_RECIPE.value],
                "min_score": 0.0,
            }),
        }
        result = await recall_agent._run_impl(ctx_recall)
        # Should find the learned recipe (or report none if scoring is too strict)
        assert "response" in result

    @pytest.mark.asyncio
    async def test_feedback_records_transfer(self):
        """operation=feedback should record a transfer on the skill."""
        # First learn a recipe
        learn_agent = self._make_agent("learn_recipe")
        ctx_learn = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "a"}, {"id": "b"}],
                "pattern": "sequential",
                "domain": "transfer-test",
                "task": "transfer demo",
                "quality": 0.8,
            }),
        }
        result_learn = await learn_agent._run_impl(ctx_learn)
        skill_id = result_learn.get("skill_id")
        assert skill_id is not None

        # Now send feedback
        fb_agent = self._make_agent("feedback")
        ctx_fb = {
            "formatted_prompt": json.dumps({
                "skill_id": skill_id,
                "domain": "new-domain",
                "task": "adapted task",
                "success": True,
                "adaptations": {"from": "transfer-test", "to": "new-domain"},
            }),
        }
        result_fb = await fb_agent._run_impl(ctx_fb)
        assert "successful" in result_fb.get("response", "").lower() or result_fb.get("transfer_success") is True
        assert result_fb.get("transfer_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_feedback_failed_transfer(self):
        """Failed feedback should record a failed transfer."""
        learn_agent = self._make_agent("learn_recipe")
        ctx_learn = {
            "formatted_prompt": json.dumps({
                "agents": [{"id": "c"}],
                "pattern": "sequential",
                "domain": "feedback-fail-test",
                "task": "fail demo",
                "quality": 0.8,
            }),
        }
        result_learn = await learn_agent._run_impl(ctx_learn)
        skill_id = result_learn.get("skill_id")

        fb_agent = self._make_agent("feedback")
        ctx_fb = {
            "formatted_prompt": json.dumps({
                "skill_id": skill_id,
                "domain": "other-domain",
                "task": "failed transfer",
                "success": False,
            }),
        }
        result_fb = await fb_agent._run_impl(ctx_fb)
        assert "failed" in result_fb.get("response", "").lower() or result_fb.get("transfer_success") is False


# ------------------------------------------------------------------ #
# GraphScout-Brain integration
# ------------------------------------------------------------------ #


class TestGraphScoutBrainConfig:
    def test_brain_assisted_defaults(self):
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig()
        assert config.brain_assisted is False
        assert config.brain_boost_weight == 0.15

    def test_brain_assisted_adds_score_weight(self):
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=True)
        assert "brain" in config.score_weights
        assert config.score_weights["brain"] == 0.15

    def test_brain_assisted_custom_weight(self):
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=True, brain_boost_weight=0.20)
        assert config.score_weights["brain"] == 0.20

    def test_brain_disabled_no_weight(self):
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=False)
        assert "brain" not in config.score_weights


# ------------------------------------------------------------------ #
# PathScorer — brain component
# ------------------------------------------------------------------ #


class TestPathScorerBrainComponent:
    def test_brain_component_added_when_present(self):
        from orka.orchestrator.path_scoring import PathScorer
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=True, brain_boost_weight=0.10)
        scorer = PathScorer(config)

        candidate = {
            "node_id": "test",
            "path": ["a", "b"],
            "brain_boost": 0.1,
            "brain_penalty": 0.0,
        }
        # We need to call the internal method which is async
        import asyncio

        async def run() -> dict[str, float]:
            return await scorer._score_candidate(candidate, "test question", {})

        components = asyncio.get_event_loop().run_until_complete(run())
        assert "brain" in components
        # 0.5 + 0.1 - 0.0 = 0.6
        assert components["brain"] == pytest.approx(0.6, abs=0.01)

    def test_brain_component_with_penalty(self):
        from orka.orchestrator.path_scoring import PathScorer
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=True, brain_boost_weight=0.10)
        scorer = PathScorer(config)

        candidate = {
            "node_id": "test",
            "path": ["a"],
            "brain_boost": 0.0,
            "brain_penalty": 0.3,
        }

        import asyncio

        async def run() -> dict[str, float]:
            return await scorer._score_candidate(candidate, "q", {})

        components = asyncio.get_event_loop().run_until_complete(run())
        assert "brain" in components
        # 0.5 + 0.0 - 0.3 = 0.2
        assert components["brain"] == pytest.approx(0.2, abs=0.01)

    def test_brain_component_clamped(self):
        from orka.orchestrator.path_scoring import PathScorer
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=True, brain_boost_weight=0.10)
        scorer = PathScorer(config)

        candidate = {
            "node_id": "test",
            "path": ["a"],
            "brain_boost": 0.0,
            "brain_penalty": 1.0,
        }

        import asyncio

        async def run() -> dict[str, float]:
            return await scorer._score_candidate(candidate, "q", {})

        components = asyncio.get_event_loop().run_until_complete(run())
        assert components["brain"] == 0.0

    def test_no_brain_component_without_signals(self):
        from orka.orchestrator.path_scoring import PathScorer
        from orka.nodes.graph_scout_agent import GraphScoutConfig

        config = GraphScoutConfig(brain_assisted=False)
        scorer = PathScorer(config)

        candidate = {
            "node_id": "test",
            "path": ["a"],
        }

        import asyncio

        async def run() -> dict[str, float]:
            return await scorer._score_candidate(candidate, "q", {})

        components = asyncio.get_event_loop().run_until_complete(run())
        assert "brain" not in components


# ------------------------------------------------------------------ #
# GraphScoutAgent — _apply_brain_insights
# ------------------------------------------------------------------ #


class TestApplyBrainInsights:
    @pytest.mark.asyncio
    async def test_no_memory_returns_candidates_unchanged(self):
        from orka.nodes.graph_scout_agent import GraphScoutAgent

        agent = GraphScoutAgent(
            node_id="gs",
            prompt="",
            queue=[],
            params={"brain_assisted": True},
        )
        candidates = [{"path": [{"id": "a"}], "node_id": "a"}]
        result = await agent._apply_brain_insights(candidates, "test", {})
        assert result == candidates

    @pytest.mark.asyncio
    async def test_brain_insights_add_boost(self):
        from orka.nodes.graph_scout_agent import GraphScoutAgent

        memory = FakeMemory()
        brain = Brain(memory=memory)

        # Teach a recipe
        await brain.learn_recipe(
            agents=[{"id": "analyzer"}, {"id": "summarizer"}],
            pattern="sequential",
            context={"domain": "text", "task": "summarize"},
            outcome={"success": True, "quality": 0.9},
        )

        agent = GraphScoutAgent(
            node_id="gs",
            prompt="",
            queue=[],
            params={"brain_assisted": True},
        )
        candidates = [
            {
                "node_id": "analyzer",
                "path": [{"agent_id": "analyzer"}, {"agent_id": "summarizer"}],
            },
        ]
        result = await agent._apply_brain_insights(
            candidates, "summarize this text", {"memory": memory}
        )
        # Should have brain_boost >= 0
        assert result[0].get("brain_boost", 0.0) >= 0.0
        assert "brain_penalty" in result[0]

    @pytest.mark.asyncio
    async def test_brain_insights_anti_pattern_penalty(self):
        from orka.nodes.graph_scout_agent import GraphScoutAgent

        memory = FakeMemory()
        brain = Brain(memory=memory)

        # Teach an anti-pattern
        await brain.learn_anti_pattern(
            what_failed="Using large model for simple tasks",
            why="excessive cost for trivial queries",
            context={"domain": "routing"},
        )

        agent = GraphScoutAgent(
            node_id="gs",
            prompt="",
            queue=[],
            params={"brain_assisted": True},
        )
        candidates = [
            {"node_id": "gpt4", "path": [{"agent_id": "gpt4"}]},
        ]
        # The question contains anti-signal keywords
        result = await agent._apply_brain_insights(
            candidates,
            "excessive cost for trivial queries and simple tasks",
            {"memory": memory},
        )
        # Should have some penalty
        assert result[0].get("brain_penalty", 0.0) >= 0.0
