# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Orchestration Logging Mixin
===========================

Provides orchestration event logging functionality for memory operations.
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OrchestrationLoggingMixin:
    """Mixin providing orchestration event logging for memory storage."""

    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: dict[str, Any],
        step: int | None = None,
        run_id: str | None = None,
        fork_group: str | None = None,
        parent: str | None = None,
        previous_outputs: dict[str, Any] | None = None,
        agent_decay_config: dict[str, Any] | None = None,
        log_type: str = "log",
    ) -> None:
        """Log an orchestration event as a memory entry."""
        try:
            content = self._extract_content_from_payload(payload, event_type)

            importance_score = self._calculate_importance_score(
                event_type, agent_id, payload
            )
            memory_type = self._determine_memory_type(event_type, importance_score)

            expiry_hours = self._calculate_expiry_hours(
                memory_type,
                importance_score,
                agent_decay_config,
            )

            if log_type == "log":
                expiry_hours = 0.2  # 12 minutes for orchestration logs

            self.log_memory(
                content=content,
                node_id=agent_id,
                trace_id=run_id or "default",
                metadata={
                    "event_type": event_type,
                    "step": step,
                    "fork_group": fork_group,
                    "parent": parent,
                    **(
                        {"previous_outputs": previous_outputs}
                        if self.debug_keep_previous_outputs and previous_outputs
                        else {}
                    ),
                    "agent_decay_config": agent_decay_config,
                    "log_type": log_type,
                    "category": self._classify_memory_category(
                        event_type,
                        agent_id,
                        payload,
                        log_type,
                    ),
                },
                importance_score=importance_score,
                memory_type=memory_type,
                expiry_hours=expiry_hours,
            )

            trace_entry = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": int(time.time() * 1000),
                "payload": payload,
                "step": step,
                "run_id": run_id,
                "fork_group": fork_group,
                "parent": parent,
            }
            if self.debug_keep_previous_outputs and previous_outputs:
                trace_entry["previous_outputs"] = previous_outputs
            self.memory.append(trace_entry)

        except Exception as e:
            logger.error(f"Failed to log orchestration event: {e}")

    def _extract_content_from_payload(
        self, payload: dict[str, Any], event_type: str
    ) -> str:
        """Extract meaningful content from payload for memory storage."""
        content_parts = []

        if "component_type" in payload:
            if payload.get("result"):
                content_parts.append(str(payload["result"]))
            if payload.get("internal_reasoning"):
                content_parts.append(f"Reasoning: {payload['internal_reasoning']}")
            if payload.get("formatted_prompt"):
                content_parts.append(f"Prompt: {payload['formatted_prompt']}")
            if payload.get("error"):
                content_parts.append(f"Error: {payload['error']}")
        else:
            for field in [
                "content",
                "message",
                "response",
                "result",
                "output",
                "text",
                "formatted_prompt",
            ]:
                if payload.get(field):
                    content_parts.append(str(payload[field]))

        content_parts.append(f"Event: {event_type}")

        if len(content_parts) == 1:
            content_parts.append(json.dumps(payload, default=str))

        return " ".join(content_parts)

    def _calculate_importance_score(
        self, event_type: str, agent_id: str, payload: dict[str, Any]
    ) -> float:
        """Calculate importance score based on event type and payload."""
        importance_map = {
            "agent.start": 0.7,
            "agent.end": 0.8,
            "agent.error": 0.9,
            "orchestrator.start": 0.8,
            "orchestrator.end": 0.9,
            "memory.store": 0.6,
            "memory.retrieve": 0.4,
            "llm.query": 0.5,
            "llm.response": 0.6,
        }

        base_importance = importance_map.get(event_type, 0.5)

        if isinstance(payload, dict):
            if "error" in payload or "exception" in payload:
                base_importance = min(1.0, base_importance + 0.3)
            if "result" in payload and payload.get("result"):
                base_importance = min(1.0, base_importance + 0.2)

        return base_importance

    def _determine_memory_type(self, event_type: str, importance_score: float) -> str:
        """Determine memory type based on event type and importance."""
        long_term_events = {"orchestrator.end", "agent.error", "orchestrator.start"}

        if event_type in long_term_events or importance_score >= 0.8:
            return "long_term"
        return "short_term"

