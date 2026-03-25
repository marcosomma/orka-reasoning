# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Skill Model
===========

Defines the core data structures for representing learned skills.

A Skill is a context-free abstraction of a capability that the Brain has learned.
It captures *what* was done (procedure), *when* it applies (preconditions),
and *what it achieves* (postconditions) — all described abstractly so the skill
can transfer across domains.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

DEFAULT_SKILL_TTL_HOURS: float = 168.0


@dataclass
class SkillStep:
    """A single abstract step in a skill's procedure.

    Steps are described in domain-agnostic terms so they can be
    re-interpreted in different contexts.

    Attributes:
        action: What to do, described abstractly (e.g., "decompose input into parts").
        description: Longer explanation of the step's purpose.
        order: Position in the procedure sequence.
        parameters: Named parameters the step expects.
        is_optional: Whether the step can be skipped.
    """

    action: str
    description: str = ""
    order: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    is_optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "description": self.description,
            "order": self.order,
            "parameters": self.parameters,
            "is_optional": self.is_optional,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillStep:
        return cls(
            action=data["action"],
            description=data.get("description", ""),
            order=data.get("order", 0),
            parameters=data.get("parameters", {}),
            is_optional=data.get("is_optional", False),
        )


@dataclass
class SkillCondition:
    """A precondition or postcondition for a skill.

    Conditions are expressed as abstract predicates that can be
    evaluated against any context.

    Attributes:
        predicate: Abstract condition (e.g., "input is decomposable").
        description: Human-readable explanation.
        required: Whether this condition is mandatory.
    """

    predicate: str
    description: str = ""
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "description": self.description,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillCondition:
        return cls(
            predicate=data["predicate"],
            description=data.get("description", ""),
            required=data.get("required", True),
        )


@dataclass
class SkillTransferRecord:
    """Records a skill being applied in a new context.

    Tracks the history of cross-context transfers so the Brain can
    learn which skills transfer well and which don't.

    Attributes:
        target_context: Abstract features of the context where the skill was applied.
        success: Whether the transfer produced a good outcome.
        confidence: How confident the Brain was in the transfer (0.0-1.0).
        adaptations: What modifications were made to the procedure.
        timestamp: When the transfer occurred.
    """

    target_context: dict[str, Any]
    success: bool
    confidence: float
    adaptations: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_context": self.target_context,
            "success": self.success,
            "confidence": self.confidence,
            "adaptations": self.adaptations,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillTransferRecord:
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.now(UTC)
        return cls(
            target_context=data["target_context"],
            success=data["success"],
            confidence=data.get("confidence", 0.0),
            adaptations=data.get("adaptations", {}),
            timestamp=ts,
        )


@dataclass
class Skill:
    """A learned, transferable capability.

    Skills are the core knowledge unit of the Brain. They represent
    abstract capabilities that can be recognized and applied across
    entirely different domains.

    The key insight is that many problem-solving patterns are domain-agnostic:
    "divide and conquer", "validate then act", "gather evidence then conclude",
    "prioritize by impact" — these work everywhere.

    Attributes:
        id: Unique identifier.
        name: Human-readable skill name.
        description: What this skill does, abstractly.
        procedure: Ordered list of abstract steps.
        preconditions: What must be true for this skill to apply.
        postconditions: What is true after successful application.
        source_context: Abstract features of the context where the skill was learned.
        transfer_history: Record of cross-context applications.
        confidence: Overall reliability score (0.0-1.0).
        usage_count: How many times this skill has been applied.
        success_rate: Fraction of successful applications.
        tags: Semantic tags for categorization.
        created_at: When the skill was first learned.
        updated_at: When the skill was last modified.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    procedure: list[SkillStep] = field(default_factory=list)
    preconditions: list[SkillCondition] = field(default_factory=list)
    postconditions: list[SkillCondition] = field(default_factory=list)
    source_context: dict[str, Any] = field(default_factory=dict)
    transfer_history: list[SkillTransferRecord] = field(default_factory=list)
    confidence: float = 0.5
    usage_count: int = 0
    success_rate: float = 0.0
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: str = ""

    @property
    def ttl_hours(self) -> float:
        """Effective TTL in hours, scaled by usage and confidence."""
        return DEFAULT_SKILL_TTL_HOURS * (
            1 + math.log2(max(1, self.usage_count))
        ) * (0.5 + self.confidence)

    @property
    def is_expired(self) -> bool:
        """Whether this skill has passed its expiry time."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) >= datetime.fromisoformat(self.expires_at)

    def renew_ttl(self) -> None:
        """Recalculate and set the expiry timestamp."""
        self.expires_at = (
            datetime.now(UTC) + timedelta(hours=self.ttl_hours)
        ).isoformat()
        self.updated_at = datetime.now(UTC)

    def record_usage(self, success: bool) -> None:
        """Update usage statistics after an application."""
        self.usage_count += 1
        total_successes = self.success_rate * (self.usage_count - 1)
        if success:
            total_successes += 1
        self.success_rate = total_successes / self.usage_count
        # Confidence grows with successful usage, decays with failures
        if success:
            self.confidence = min(1.0, self.confidence + 0.05 * (1.0 - self.confidence))
        else:
            self.confidence = max(0.0, self.confidence - 0.1 * self.confidence)
        self.updated_at = datetime.now(UTC)
        if success:
            self.renew_ttl()

    def record_transfer(self, record: SkillTransferRecord) -> None:
        """Record a cross-context transfer attempt."""
        self.transfer_history.append(record)
        self.record_usage(record.success)

    @property
    def transfer_success_rate(self) -> float:
        """Success rate specifically for cross-context transfers."""
        if not self.transfer_history:
            return 0.0
        successes = sum(1 for t in self.transfer_history if t.success)
        return successes / len(self.transfer_history)

    @property
    def is_transferable(self) -> bool:
        """Whether this skill has demonstrated cross-context applicability."""
        return len(self.transfer_history) >= 1 and self.transfer_success_rate >= 0.5

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "procedure": [s.to_dict() for s in self.procedure],
            "preconditions": [c.to_dict() for c in self.preconditions],
            "postconditions": [c.to_dict() for c in self.postconditions],
            "source_context": self.source_context,
            "transfer_history": [t.to_dict() for t in self.transfer_history],
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skill:
        """Deserialize from dictionary."""
        created = data.get("created_at")
        updated = data.get("updated_at")
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            procedure=[SkillStep.from_dict(s) for s in data.get("procedure", [])],
            preconditions=[SkillCondition.from_dict(c) for c in data.get("preconditions", [])],
            postconditions=[SkillCondition.from_dict(c) for c in data.get("postconditions", [])],
            source_context=data.get("source_context", {}),
            transfer_history=[
                SkillTransferRecord.from_dict(t) for t in data.get("transfer_history", [])
            ],
            confidence=data.get("confidence", 0.5),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 0.0),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(created) if isinstance(created, str) else datetime.now(UTC),
            updated_at=datetime.fromisoformat(updated) if isinstance(updated, str) else datetime.now(UTC),
            expires_at=data.get("expires_at", ""),
        )

    def to_embedding_text(self) -> str:
        """Generate text representation for vector embedding.

        Combines name, description, tags, and procedure actions into a single
        string optimized for semantic similarity search.
        """
        parts = [self.name, self.description]
        parts.extend(self.tags)
        parts.extend(step.action for step in self.procedure)
        parts.extend(c.predicate for c in self.preconditions)
        return " | ".join(part for part in parts if part)
