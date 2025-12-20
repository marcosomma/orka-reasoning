# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Classification Mixin
====================

Methods for memory classification (importance, type, category).
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ClassificationMixin:
    """Mixin providing memory classification methods."""

    # Expected from host class
    decay_config: dict[str, Any]

    def _calculate_importance_score(
        self,
        event_type: str,
        agent_id: str,
        payload: dict[str, Any],
    ) -> float:
        """
        Calculate importance score for a memory entry.

        Args:
            event_type: Type of the event
            agent_id: ID of the agent generating the event
            payload: Event payload

        Returns:
            Importance score between 0.0 and 1.0
        """
        rules = self.decay_config.get("importance_rules", {})
        score = rules.get("base_score", 0.5)

        # Apply event type boosts
        event_boost = rules.get("event_type_boosts", {}).get(event_type, 0.0)
        score += event_boost

        # Apply agent type boosts
        for agent_type, boost in rules.get("agent_type_boosts", {}).items():
            if agent_type in agent_id:
                score += boost
                break

        # Check payload for result indicators
        if isinstance(payload, dict):
            if payload.get("result") or payload.get("response"):
                score += 0.1
            if payload.get("error"):
                score -= 0.1

        # Clamp score between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _classify_memory_type(
        self,
        event_type: str,
        importance_score: float,
        category: str = "log",
    ) -> str:
        """
        Classify memory entry as short-term or long-term.

        Args:
            event_type: Type of the event
            importance_score: Calculated importance score
            category: Memory category ("stored" or "log")

        Returns:
            "short_term" or "long_term"
        """
        # CRITICAL: Only "stored" memories should be classified as long-term
        if category == "log":
            return "short_term"

        rules = self.decay_config.get("memory_type_rules", {})

        # Check explicit rules first
        if event_type in rules.get("long_term_events", []):
            return "long_term"
        if event_type in rules.get("short_term_events", []):
            return "short_term"

        # Fallback to importance score
        return "long_term" if importance_score >= 0.7 else "short_term"

    def _classify_memory_category(
        self,
        event_type: str,
        agent_id: str,
        payload: dict[str, Any],
        log_type: str = "log",
    ) -> str:
        """
        Classify memory entry category for separation between logs and stored memories.

        Args:
            event_type: Type of the event
            agent_id: ID of the agent generating the event
            payload: Event payload
            log_type: Explicit log type ("log" or "memory")

        Returns:
            "stored" for memory writer outputs, "log" for other events
        """
        # Use explicit log_type parameter first
        if log_type == "memory":
            return "stored"
        elif log_type == "log":
            return "log"

        # Fallback to legacy detection
        if event_type == "write" and (
            "memory" in agent_id.lower() or "writer" in agent_id.lower()
        ):
            return "stored"

        # Check payload for memory content indicators
        if isinstance(payload, dict):
            if payload.get("content") and payload.get("metadata"):
                return "stored"
            if payload.get("memory_object") or payload.get("memories"):
                return "stored"

        return "log"

