"""
Streaming types and contracts for OrKa streaming runtime.

Defines enums and TypedDict schemas used across the streaming subpackage.
This module is intentionally self-contained and has no heavy imports to
remain import-safe in limited environments and unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Literal, Optional, TypedDict


class EventType(str, Enum):
    """Canonical event types used on the streaming bus."""

    INGRESS = "ingress"
    EGRESS = "egress"
    STATE = "state"
    ALERTS = "alerts"
    TOOLS = "tools"
    HEARTBEAT = "heartbeat"
    REPLACEMENT = "replacement"


def channel_name(session_id: str, suffix: str) -> str:
    """Build a stream channel name for a given session id and suffix."""

    return f"{session_id}.{suffix}"


class MessageEnvelope(TypedDict, total=False):
    """Envelope for messages traveling on the EventBus.

    Fields are designed to be JSON-serializable and stable for audit/replay.
    Optional fields are marked with total=False.
    """

    session_id: str
    channel: str
    type: str
    payload: Dict
    timestamp_ms: int
    source: str
    state_version: int
    idempotency_key: str
    retry_count: int
    offset: str


class ReplacementEvent(TypedDict):
    executor_instance_id_old: str
    executor_instance_id_new: str
    reason: Literal[
        "cadence_tick",
        "critical_alert",
        "state_delta_threshold",
        "manual",
    ]
    state_version_before: int
    state_version_after: int
    timestamp_ms: int


class RetrievalPolicy(TypedDict, total=False):
    namespace: str
    freshness_ms: int
    max_items: int
    max_tokens: int
    conflict_behavior: Literal["last_write_wins", "reject", "merge"]
    retention_ms: int
    provenance_required: bool


class StorePolicy(TypedDict, total=False):
    namespace: str
    freshness_ms: int
    max_items: int
    max_tokens: int
    conflict_behavior: Literal["last_write_wins", "reject", "merge"]
    retention_ms: int
    provenance_required: bool


@dataclass(frozen=True)
class PromptBudgets:
    """Prompt budgets for the composer.

    total_tokens: maximum tokens across all sections (invariants excluded from trim).
    sections: per-section caps.
    """

    total_tokens: int
    sections: Dict[str, int]
