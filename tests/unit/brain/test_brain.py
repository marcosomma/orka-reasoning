# OrKa: Orchestrator Kit Agents — Brain Tests

"""Tests for the Brain (top-level learning engine)."""

import pytest
import pytest_asyncio

from orka.brain.brain import Brain
from orka.brain.skill import Skill


class FakeMemory:
    """In-memory fake for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}
        self.logged_events: list[dict] = []

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

    def log(self, agent_id, event_type, payload, **kwargs):
        self.logged_events.append({
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": payload,
        })


@pytest.fixture
def brain():
    memory = FakeMemory()
    return Brain(memory=memory)


@pytest.fixture
def brain_with_memory():
    memory = FakeMemory()
    return Brain(memory=memory), memory


class TestBrainLearn:
    @pytest.mark.asyncio
    async def test_learn_from_successful_execution(self, brain):
        skill = await brain.learn(
            execution_trace={
                "steps": [
                    {"action": "decompose input into sections"},
                    {"action": "analyze each section independently"},
                    {"action": "combine analysis results"},
                ],
            },
            context={
                "domain": "text_analysis",
                "task": "Document summarization with decomposition",
            },
            outcome={"success": True, "quality": 0.9},
        )
        assert skill is not None
        assert len(skill.procedure) == 3
        assert skill.confidence > 0.0
        assert skill.usage_count == 1

    @pytest.mark.asyncio
    async def test_learn_ignores_failures(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "do stuff"}]},
            context={"domain": "test"},
            outcome={"success": False, "error": "something broke"},
        )
        assert skill is None

    @pytest.mark.asyncio
    async def test_learn_extracts_from_agents_list(self, brain):
        skill = await brain.learn(
            execution_trace={
                "agents": ["parser", "validator", "formatter"],
                "strategy": "sequential",
            },
            context={"domain": "data_pipeline", "task": "ETL processing"},
            outcome={"success": True, "quality": 0.85},
        )
        assert skill is not None
        assert len(skill.procedure) == 3
        assert any("parser" in s.action for s in skill.procedure)

    @pytest.mark.asyncio
    async def test_learn_no_procedure_returns_none(self, brain):
        skill = await brain.learn(
            execution_trace={},
            context={"domain": "test"},
            outcome={"success": True},
        )
        assert skill is None

    @pytest.mark.asyncio
    async def test_learn_reinforces_existing(self, brain):
        # Learn the same pattern twice
        context = {
            "domain": "text",
            "task": "First analyze, then validate the results",
        }
        trace = {"steps": [{"action": "analyze"}, {"action": "validate"}]}
        outcome = {"success": True, "quality": 0.8}

        skill1 = await brain.learn(
            execution_trace=trace, context=context, outcome=outcome
        )
        skill2 = await brain.learn(
            execution_trace=trace, context=context, outcome=outcome
        )

        assert skill1 is not None
        assert skill2 is not None
        # Should return the same skill, reinforced
        assert skill1.id == skill2.id
        assert skill2.usage_count == 2

    @pytest.mark.asyncio
    async def test_learn_logs_event(self, brain_with_memory):
        brain, memory = brain_with_memory
        await brain.learn(
            execution_trace={"steps": [{"action": "test step"}]},
            context={"domain": "test_domain", "task": "test learning"},
            outcome={"success": True},
        )
        assert len(memory.logged_events) == 1
        assert memory.logged_events[0]["event_type"] == "skill_learned"
        assert memory.logged_events[0]["agent_id"] == "orka_brain"

    @pytest.mark.asyncio
    async def test_learn_generates_tags(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "analyze"}]},
            context={"domain": "nlp", "task": "Analyze text step by step"},
            outcome={"success": True},
        )
        assert skill is not None
        assert len(skill.tags) > 0

    @pytest.mark.asyncio
    async def test_learn_custom_name(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "do"}]},
            context={"task": "stuff"},
            outcome={"success": True},
            skill_name="My Custom Skill",
        )
        assert skill is not None
        assert skill.name == "My Custom Skill"


class TestBrainRecall:
    @pytest.mark.asyncio
    async def test_recall_empty_brain(self, brain):
        candidates = await brain.recall(
            context={"task": "anything"}
        )
        assert candidates == []

    @pytest.mark.asyncio
    async def test_recall_finds_relevant_skill(self, brain):
        # Learn a skill
        await brain.learn(
            execution_trace={
                "steps": [
                    {"action": "decompose input"},
                    {"action": "process parts"},
                    {"action": "aggregate results"},
                ],
            },
            context={
                "domain": "text_analysis",
                "task": "Break down document and analyze parts",
            },
            outcome={"success": True, "quality": 0.9},
        )

        # Recall in a different domain with similar structure
        candidates = await brain.recall(
            context={
                "domain": "code_review",
                "task": "Break down the PR into files and analyze each change",
            },
            min_score=0.0,
        )
        assert len(candidates) >= 1

    @pytest.mark.asyncio
    async def test_recall_respects_min_score(self, brain):
        await brain.learn(
            execution_trace={"steps": [{"action": "route"}]},
            context={"task": "Route requests to different handlers"},
            outcome={"success": True},
        )

        candidates = await brain.recall(
            context={"task": "Generate a creative poem from scratch"},
            min_score=0.99,
        )
        assert len(candidates) == 0


class TestBrainFeedback:
    @pytest.mark.asyncio
    async def test_feedback_success(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "analyze"}]},
            context={"task": "Analyze data"},
            outcome={"success": True},
        )
        assert skill is not None
        initial_confidence = skill.confidence

        await brain.feedback(
            skill_id=skill.id,
            context={"domain": "new_domain", "task": "Analyze code"},
            success=True,
        )

        updated = await brain.get_skill(skill.id)
        assert updated is not None
        assert len(updated.transfer_history) == 1
        assert updated.transfer_history[0].success is True
        assert updated.confidence >= initial_confidence

    @pytest.mark.asyncio
    async def test_feedback_failure(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "analyze"}]},
            context={"task": "Analyze data"},
            outcome={"success": True},
        )
        assert skill is not None
        initial_confidence = skill.confidence

        await brain.feedback(
            skill_id=skill.id,
            context={"domain": "unrelated", "task": "cook dinner"},
            success=False,
        )

        updated = await brain.get_skill(skill.id)
        assert updated is not None
        assert len(updated.transfer_history) == 1
        assert updated.transfer_history[0].success is False
        assert updated.confidence <= initial_confidence

    @pytest.mark.asyncio
    async def test_feedback_nonexistent_skill(self, brain):
        # Should not raise, just log warning
        await brain.feedback(
            skill_id="nonexistent",
            context={"domain": "test"},
            success=True,
        )


class TestBrainIntrospection:
    @pytest.mark.asyncio
    async def test_get_skills_empty(self, brain):
        skills = await brain.get_skills()
        assert skills == []

    @pytest.mark.asyncio
    async def test_get_skills(self, brain):
        await brain.learn(
            execution_trace={"steps": [{"action": "a"}]},
            context={"task": "First, analyze data"},
            outcome={"success": True},
        )
        await brain.learn(
            execution_trace={"steps": [{"action": "b"}]},
            context={"task": "Then, generate a report"},
            outcome={"success": True},
        )
        skills = await brain.get_skills()
        assert len(skills) == 2

    @pytest.mark.asyncio
    async def test_get_skill_summary_empty(self, brain):
        summary = await brain.get_skill_summary()
        assert summary["total_skills"] == 0
        assert summary["avg_confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_get_skill_summary(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "analyze"}]},
            context={"task": "Analyze and break down data"},
            outcome={"success": True, "quality": 0.9},
        )
        assert skill is not None

        await brain.feedback(
            skill_id=skill.id,
            context={"domain": "other"},
            success=True,
        )

        summary = await brain.get_skill_summary()
        assert summary["total_skills"] == 1
        assert summary["total_transfers"] == 1
        assert summary["avg_confidence"] > 0.0
        assert len(summary["top_skills"]) == 1


class TestBrainCrossContextTransfer:
    """Integration-style tests demonstrating the core value: cross-context transfer."""

    @pytest.mark.asyncio
    async def test_text_to_code_transfer(self, brain):
        """Learn a decompose-analyze-aggregate pattern from text analysis,
        then successfully recall it for code review."""

        # Step 1: Learn from text analysis
        skill = await brain.learn(
            execution_trace={
                "steps": [
                    {"action": "decompose input into parts"},
                    {"action": "analyze each part independently"},
                    {"action": "aggregate analysis into summary"},
                ],
            },
            context={
                "domain": "text_analysis",
                "task": "Break down a long document and summarize each section",
            },
            outcome={"success": True, "quality": 0.92},
        )
        assert skill is not None

        # Step 2: Recall for code review (different domain, similar structure)
        candidates = await brain.recall(
            context={
                "domain": "code_review",
                "task": "Break down a PR into files and analyze each change, then summarize",
            },
            min_score=0.0,
        )
        assert len(candidates) >= 1
        top = candidates[0]
        assert top.structural_score > 0.0

        # Step 3: Record successful transfer
        await brain.feedback(
            skill_id=top.skill.id,
            context={"domain": "code_review"},
            success=True,
        )

        # Step 4: Verify skill is now recognized as transferable
        updated = await brain.get_skill(top.skill.id)
        assert updated is not None
        assert updated.is_transferable is True

    @pytest.mark.asyncio
    async def test_validation_pattern_transfers(self, brain):
        """Learn a validate-then-act pattern from data validation,
        then recall it for content moderation."""

        await brain.learn(
            execution_trace={
                "steps": [
                    {"action": "validate input format"},
                    {"action": "check against rules"},
                    {"action": "route to handler based on validation result"},
                ],
            },
            context={
                "domain": "data_validation",
                "task": "Validate incoming data then route to appropriate handler",
            },
            outcome={"success": True, "quality": 0.88},
        )

        candidates = await brain.recall(
            context={
                "domain": "content_moderation",
                "task": "Check content against policy rules then decide to approve or reject",
            },
            min_score=0.0,
        )
        assert len(candidates) >= 1
        # Should have picked up on the validation + routing patterns
        top = candidates[0]
        assert any(
            s in top.skill.tags
            for s in ["validation", "routing"]
        )


class TestSkillTTL:
    """Tests for Skill TTL (time-to-live) features."""

    def test_ttl_hours_formula(self):
        """Verify TTL formula: base × (1 + log2(usage)) × (0.5 + confidence)."""
        import math

        from orka.brain.skill import DEFAULT_SKILL_TTL_HOURS

        skill = Skill(usage_count=1, confidence=0.5)
        expected = DEFAULT_SKILL_TTL_HOURS * (1 + math.log2(1)) * (0.5 + 0.5)
        assert abs(skill.ttl_hours - expected) < 0.01
        assert skill.ttl_hours == DEFAULT_SKILL_TTL_HOURS  # 168 × 1 × 1.0

    def test_ttl_hours_scales_with_usage(self):
        skill_low = Skill(usage_count=1, confidence=0.5)
        skill_high = Skill(usage_count=8, confidence=0.5)
        assert skill_high.ttl_hours > skill_low.ttl_hours

    def test_ttl_hours_scales_with_confidence(self):
        skill_low = Skill(usage_count=1, confidence=0.1)
        skill_high = Skill(usage_count=1, confidence=0.9)
        assert skill_high.ttl_hours > skill_low.ttl_hours

    def test_renew_ttl_sets_expires_at(self):
        skill = Skill(usage_count=1, confidence=0.5)
        assert skill.expires_at == ""
        skill.renew_ttl()
        assert skill.expires_at != ""
        from datetime import UTC, datetime

        expires = datetime.fromisoformat(skill.expires_at)
        assert expires > datetime.now(UTC)

    def test_is_expired_false_when_no_expiry(self):
        skill = Skill()
        assert skill.is_expired is False

    def test_is_expired_false_when_future(self):
        skill = Skill(usage_count=1, confidence=0.5)
        skill.renew_ttl()
        assert skill.is_expired is False

    def test_is_expired_true_when_past(self):
        from datetime import UTC, datetime, timedelta

        skill = Skill()
        skill.expires_at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        assert skill.is_expired is True

    def test_record_usage_success_renews_ttl(self):
        skill = Skill(usage_count=1, confidence=0.5, success_rate=1.0)
        assert skill.expires_at == ""
        skill.record_usage(success=True)
        assert skill.expires_at != ""

    def test_record_usage_failure_does_not_renew_ttl(self):
        skill = Skill(usage_count=1, confidence=0.5, success_rate=1.0)
        assert skill.expires_at == ""
        skill.record_usage(success=False)
        assert skill.expires_at == ""

    def test_to_dict_includes_expires_at(self):
        skill = Skill()
        skill.renew_ttl()
        d = skill.to_dict()
        assert "expires_at" in d
        assert d["expires_at"] == skill.expires_at

    def test_from_dict_restores_expires_at(self):
        skill = Skill()
        skill.renew_ttl()
        d = skill.to_dict()
        restored = Skill.from_dict(d)
        assert restored.expires_at == skill.expires_at

    def test_from_dict_without_expires_at_defaults_empty(self):
        """Backward compat: old skills without expires_at don't crash."""
        d = {
            "id": "old-skill",
            "name": "Legacy",
            "procedure": [],
            "confidence": 0.5,
            "usage_count": 1,
        }
        skill = Skill.from_dict(d)
        assert skill.expires_at == ""
        assert skill.is_expired is False


class TestBrainLearnTTL:
    @pytest.mark.asyncio
    async def test_learn_sets_initial_ttl(self, brain):
        skill = await brain.learn(
            execution_trace={"steps": [{"action": "analyze"}]},
            context={"task": "Analyze data"},
            outcome={"success": True},
        )
        assert skill is not None
        assert skill.expires_at != ""

    @pytest.mark.asyncio
    async def test_learn_reinforcement_renews_ttl(self, brain):
        context = {"task": "First analyze, then validate data"}
        trace = {"steps": [{"action": "analyze"}, {"action": "validate"}]}
        outcome = {"success": True, "quality": 0.8}

        skill1 = await brain.learn(
            execution_trace=trace, context=context, outcome=outcome
        )
        assert skill1 is not None
        first_expiry = skill1.expires_at

        skill2 = await brain.learn(
            execution_trace=trace, context=context, outcome=outcome
        )
        assert skill2 is not None
        assert skill2.id == skill1.id
        # Reinforcement calls record_usage(True) → renew_ttl()
        assert skill2.expires_at >= first_expiry
