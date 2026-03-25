# OrKa: Orchestrator Kit Agents — Brain Skill Tests

"""Tests for the Skill data model."""

import pytest
from datetime import UTC, datetime

from orka.brain.skill import Skill, SkillStep, SkillCondition, SkillTransferRecord


class TestSkillStep:
    def test_create_basic(self):
        step = SkillStep(action="decompose input", description="Break into parts", order=0)
        assert step.action == "decompose input"
        assert step.order == 0
        assert step.is_optional is False

    def test_roundtrip(self):
        step = SkillStep(
            action="aggregate",
            description="Combine results",
            order=2,
            parameters={"method": "concat"},
            is_optional=True,
        )
        data = step.to_dict()
        restored = SkillStep.from_dict(data)
        assert restored.action == step.action
        assert restored.order == step.order
        assert restored.parameters == step.parameters
        assert restored.is_optional is True


class TestSkillCondition:
    def test_create_basic(self):
        cond = SkillCondition(predicate="input is text", required=True)
        assert cond.predicate == "input is text"
        assert cond.required is True

    def test_roundtrip(self):
        cond = SkillCondition(
            predicate="task supports decomposition",
            description="Must be decomposable",
            required=False,
        )
        data = cond.to_dict()
        restored = SkillCondition.from_dict(data)
        assert restored.predicate == cond.predicate
        assert restored.required is False


class TestSkillTransferRecord:
    def test_create_basic(self):
        record = SkillTransferRecord(
            target_context={"domain": "code_review"},
            success=True,
            confidence=0.8,
        )
        assert record.success is True
        assert record.confidence == 0.8

    def test_roundtrip(self):
        record = SkillTransferRecord(
            target_context={"domain": "data_pipeline", "task": "etl"},
            success=False,
            confidence=0.6,
            adaptations={"input_adaptation": "changed shape"},
        )
        data = record.to_dict()
        restored = SkillTransferRecord.from_dict(data)
        assert restored.target_context == record.target_context
        assert restored.success is False
        assert restored.adaptations == record.adaptations


class TestSkill:
    def _make_skill(self, **kwargs):
        defaults = {
            "name": "Divide and Conquer",
            "description": "Break a complex problem into sub-problems",
            "procedure": [
                SkillStep(action="decompose", order=0),
                SkillStep(action="solve parts", order=1),
                SkillStep(action="aggregate", order=2),
            ],
            "preconditions": [SkillCondition(predicate="input is decomposable")],
            "postconditions": [SkillCondition(predicate="output is complete")],
            "source_context": {
                "task_structures": ["decomposition", "aggregation"],
                "cognitive_patterns": ["analysis"],
            },
            "tags": ["decomposition", "divide-and-conquer"],
        }
        defaults.update(kwargs)
        return Skill(**defaults)

    def test_create(self):
        skill = self._make_skill()
        assert skill.name == "Divide and Conquer"
        assert len(skill.procedure) == 3
        assert skill.confidence == 0.5
        assert skill.usage_count == 0

    def test_record_usage_success(self):
        skill = self._make_skill(confidence=0.5)
        skill.record_usage(success=True)
        assert skill.usage_count == 1
        assert skill.success_rate == 1.0
        assert skill.confidence > 0.5

    def test_record_usage_failure(self):
        skill = self._make_skill(confidence=0.5)
        skill.record_usage(success=False)
        assert skill.usage_count == 1
        assert skill.success_rate == 0.0
        assert skill.confidence < 0.5

    def test_record_usage_mixed(self):
        skill = self._make_skill(confidence=0.5, usage_count=0, success_rate=0.0)
        skill.record_usage(success=True)
        skill.record_usage(success=True)
        skill.record_usage(success=False)
        assert skill.usage_count == 3
        # 2 successes out of 3
        assert abs(skill.success_rate - 2 / 3) < 0.01

    def test_record_transfer(self):
        skill = self._make_skill()
        record = SkillTransferRecord(
            target_context={"domain": "new_domain"},
            success=True,
            confidence=0.7,
        )
        skill.record_transfer(record)
        assert len(skill.transfer_history) == 1
        assert skill.usage_count == 1

    def test_transfer_success_rate(self):
        skill = self._make_skill()
        skill.record_transfer(
            SkillTransferRecord(target_context={}, success=True, confidence=0.5)
        )
        skill.record_transfer(
            SkillTransferRecord(target_context={}, success=False, confidence=0.5)
        )
        assert skill.transfer_success_rate == 0.5

    def test_transfer_success_rate_empty(self):
        skill = self._make_skill()
        assert skill.transfer_success_rate == 0.0

    def test_is_transferable(self):
        skill = self._make_skill()
        assert skill.is_transferable is False

        skill.record_transfer(
            SkillTransferRecord(target_context={}, success=True, confidence=0.5)
        )
        assert skill.is_transferable is True

    def test_is_not_transferable_low_rate(self):
        skill = self._make_skill()
        skill.record_transfer(
            SkillTransferRecord(target_context={}, success=False, confidence=0.5)
        )
        assert skill.is_transferable is False

    def test_roundtrip(self):
        skill = self._make_skill()
        skill.record_transfer(
            SkillTransferRecord(
                target_context={"domain": "test"},
                success=True,
                confidence=0.7,
            )
        )
        data = skill.to_dict()
        restored = Skill.from_dict(data)

        assert restored.id == skill.id
        assert restored.name == skill.name
        assert len(restored.procedure) == len(skill.procedure)
        assert len(restored.transfer_history) == 1
        assert restored.tags == skill.tags

    def test_to_embedding_text(self):
        skill = self._make_skill()
        text = skill.to_embedding_text()
        assert "Divide and Conquer" in text
        assert "decompose" in text
        assert "decomposable" in text

    def test_confidence_bounded(self):
        skill = self._make_skill(confidence=0.99)
        for _ in range(100):
            skill.record_usage(success=True)
        assert skill.confidence <= 1.0

        skill2 = self._make_skill(confidence=0.01)
        for _ in range(100):
            skill2.record_usage(success=False)
        assert skill2.confidence >= 0.0
