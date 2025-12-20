# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Memory Processing Mixin
=======================

Methods for building previous outputs from execution logs.
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class MemoryProcessingMixin:
    """Mixin providing previous outputs building from logs."""

    def _build_previous_outputs(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build a dictionary of previous agent outputs from the execution logs.
        """
        outputs = {}

        # First, try to get results from Redis
        try:
            group_key = "agent_results"
            result_keys = self.hkeys(group_key)
            for agent_id in result_keys:
                result_str = self.hget(group_key, agent_id)
                if result_str:
                    result = json.loads(result_str)
                    outputs[agent_id] = result
                    logger.debug(f"- Loaded result for agent {agent_id} from Redis")
        except Exception as e:
            logger.warning(f"Failed to load results from Redis: {e}")

        # Then process logs
        for log in logs:
            agent_id = str(log.get("agent_id"))
            if not agent_id:
                continue
            payload = log.get("payload", {})

            if "result" in payload:
                outputs[agent_id] = payload["result"]

            if "result" in payload and isinstance(payload["result"], dict):
                merged = payload["result"].get("merged")
                if isinstance(merged, dict):
                    outputs.update(merged)

            if "response" in payload:
                outputs[agent_id] = {
                    "response": payload["response"],
                    "confidence": payload.get("confidence", "0.0"),
                    "internal_reasoning": payload.get("internal_reasoning", ""),
                    "_metrics": payload.get("_metrics", {}),
                    "formatted_prompt": payload.get("formatted_prompt", ""),
                }

            if "memories" in payload:
                outputs[agent_id] = {
                    "memories": payload["memories"],
                    "query": payload.get("query", ""),
                    "backend": payload.get("backend", ""),
                    "search_type": payload.get("search_type", ""),
                    "num_results": payload.get("num_results", 0),
                }

            # Store the result in Redis
            try:
                result_key = f"agent_result:{agent_id}"
                self.set(result_key, json.dumps(outputs[agent_id], default=json_serializer))
                logger.debug(f"- Stored result for agent {agent_id}")
            except Exception as e:
                logger.warning(f"Failed to store result in Redis: {e}")

            try:
                group_key = "agent_results"
                self.hset(
                    group_key, agent_id, json.dumps(outputs[agent_id], default=json_serializer)
                )
                logger.debug(f"- Stored result in group for agent {agent_id}")
            except Exception as e:
                logger.warning(f"Failed to store result in Redis: {e}")

        return outputs

    # Stubs for Redis methods - provided by concrete implementations
    def hkeys(self, name: str) -> list[str]:
        """Get all keys in a hash structure."""
        raise NotImplementedError

    def hget(self, name: str, key: str) -> str | None:
        """Get a field from a hash structure."""
        raise NotImplementedError

    def hset(self, name: str, key: str, value: str | bytes | int | float) -> int:
        """Set a field in a hash structure."""
        raise NotImplementedError

    def set(self, key: str, value: str | bytes | int | float) -> bool:
        """Set a value by key."""
        raise NotImplementedError
