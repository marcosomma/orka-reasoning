# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)


class RedisMemoryLogger:
    """
    A memory logger that uses Redis to store and retrieve orchestration events.
    Supports logging events, saving logs to files, and querying recent events.
    """

    def __init__(
        self, redis_url: Optional[str] = None, stream_key: str = "orka:memory"
    ) -> None:
        """
        Initialize the Redis memory logger.

        Args:
            redis_url: URL for the Redis server. Defaults to environment variable REDIS_URL or redis service name.
            stream_key: Key for the Redis stream. Defaults to "orka:memory".
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.stream_key = stream_key
        self.client = redis.from_url(self.redis_url)
        self.memory: List[
            Dict[str, Any]
        ] = []  # Local memory buffer for in-memory storage

    @property
    def redis(self) -> redis.Redis:
        """Return the Redis client instance."""
        return self.client

    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: Dict[str, Any],
        step: Optional[int] = None,
        run_id: Optional[str] = None,
        fork_group: Optional[str] = None,
        parent: Optional[str] = None,
        previous_outputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an event to Redis and local memory.

        Args:
            agent_id: ID of the agent generating the event.
            event_type: Type of the event.
            payload: Event payload.
            step: Step number in the orchestration.
            run_id: ID of the orchestration run.
            fork_group: ID of the fork group.
            parent: ID of the parent event.
            previous_outputs: Previous outputs from agents.

        Raises:
            ValueError: If agent_id is missing.
            Exception: If Redis operation fails.
        """
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = previous_outputs

        self.memory.append(event)

        try:
            self.client.xadd(
                self.stream_key,
                {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "timestamp": event["timestamp"],
                    "payload": json.dumps(payload),
                    "run_id": run_id or "default",
                    "step": str(step or -1),
                },
            )
        except Exception as e:
            raise Exception(f"Failed to log event to Redis: {str(e)}")

    def save_to_file(self, file_path: str) -> None:
        """
        Save the logged events to a JSON file.

        Args:
            file_path: Path to the output JSON file.
        """
        with open(file_path, "w") as f:
            json.dump(self.memory, f, indent=2)
        logger.info(f"[MemoryLogger] Logs saved to {file_path}")

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from the Redis stream.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        return self.client.xrevrange(self.stream_key, count=count)

    def hset(self, name: str, key: str, value: str) -> int:
        """
        Set a field in a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added.
        """
        return self.client.hset(name, key, value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        return self.client.hget(name, key)

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a Redis hash.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        return self.client.hkeys(name)

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a Redis hash.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        return self.client.hdel(name, *keys)

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a Redis set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        return self.client.smembers(name)


# Future stub
class KafkaMemoryLogger:
    """
    A placeholder for a future Kafka-based memory logger.
    Raises NotImplementedError as it is not yet implemented.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Kafka backend not implemented yet")
