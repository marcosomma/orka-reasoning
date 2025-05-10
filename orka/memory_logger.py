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
from typing import Any, Dict, List, Optional, Union

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

    def _sanitize_for_json(self, obj: Any) -> Any:
        """
        Recursively sanitize an object for JSON serialization.

        Args:
            obj: Object to sanitize

        Returns:
            JSON-serializable version of the object
        """
        try:
            if obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, bytes):
                # Convert bytes to base64-encoded string
                import base64

                return {
                    "__type": "bytes",
                    "data": base64.b64encode(obj).decode("utf-8"),
                }
            elif isinstance(obj, (list, tuple)):
                return [self._sanitize_for_json(item) for item in obj]
            elif isinstance(obj, dict):
                return {str(k): self._sanitize_for_json(v) for k, v in obj.items()}
            elif hasattr(obj, "__dict__"):
                try:
                    # Handle custom objects by converting to dict
                    return {
                        "__type": obj.__class__.__name__,
                        "data": self._sanitize_for_json(obj.__dict__),
                    }
                except Exception as e:
                    return f"<non-serializable object: {obj.__class__.__name__}, error: {str(e)}>"
            elif hasattr(obj, "isoformat"):  # Handle datetime-like objects
                return obj.isoformat()
            else:
                # Last resort - convert to string
                return f"<non-serializable: {type(obj).__name__}>"
        except Exception as e:
            logger.warning(f"Failed to sanitize object for JSON: {str(e)}")
            return f"<sanitization-error: {str(e)}>"

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

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": safe_payload,
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
            event["previous_outputs"] = self._sanitize_for_json(previous_outputs)

        self.memory.append(event)

        try:
            # Sanitize previous outputs if present
            safe_previous_outputs = None
            if previous_outputs:
                try:
                    safe_previous_outputs = json.dumps(
                        self._sanitize_for_json(previous_outputs)
                    )
                except Exception as e:
                    logger.error(f"Failed to serialize previous_outputs: {str(e)}")
                    safe_previous_outputs = json.dumps(
                        {"error": f"Serialization error: {str(e)}"}
                    )

            # Prepare the Redis entry
            redis_entry = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": str(step or -1),
            }

            # Safely serialize the payload
            try:
                redis_entry["payload"] = json.dumps(safe_payload)
            except Exception as e:
                logger.error(f"Failed to serialize payload: {str(e)}")
                redis_entry["payload"] = json.dumps(
                    {"error": "Original payload contained non-serializable objects"}
                )

            # Only add previous_outputs if it exists and is not None
            if safe_previous_outputs:
                redis_entry["previous_outputs"] = safe_previous_outputs

            # Add the entry to Redis
            self.client.xadd(self.stream_key, redis_entry)

        except Exception as e:
            logger.error(f"Failed to log event to Redis: {str(e)}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {str(e)}"
                }
                self.client.xadd(
                    self.stream_key,
                    {
                        "agent_id": agent_id,
                        "event_type": event_type,
                        "timestamp": event["timestamp"],
                        "payload": json.dumps(simplified_payload),
                        "run_id": run_id or "default",
                        "step": str(step or -1),
                    },
                )
                logger.info("Logged simplified error payload instead")
            except Exception as inner_e:
                logger.error(
                    f"Failed to log event to Redis: {str(e)} and fallback also failed: {str(inner_e)}"
                )

    def save_to_file(self, file_path: str) -> None:
        """
        Save the logged events to a JSON file.

        Args:
            file_path: Path to the output JSON file.
        """
        try:
            # Pre-sanitize all memory entries
            sanitized_memory = self._sanitize_for_json(self.memory)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    sanitized_memory,
                    f,
                    indent=2,
                    default=lambda o: f"<non-serializable: {type(o).__name__}>",
                )
            logger.info(f"[MemoryLogger] Logs saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save logs to file: {str(e)}")
            # Try again with simplified content
            try:
                simplified_memory = [
                    {
                        "agent_id": entry.get("agent_id", "unknown"),
                        "event_type": entry.get("event_type", "unknown"),
                        "timestamp": entry.get(
                            "timestamp", datetime.utcnow().isoformat()
                        ),
                        "error": "Original entry contained non-serializable data",
                    }
                    for entry in self.memory
                ]
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(simplified_memory, f, indent=2)
                logger.info(f"[MemoryLogger] Simplified logs saved to {file_path}")
            except Exception as inner_e:
                logger.error(f"Failed to save simplified logs to file: {str(inner_e)}")

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from the Redis stream.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        try:
            results = self.client.xrevrange(self.stream_key, count=count)
            # Sanitize results for JSON serialization before returning
            return self._sanitize_for_json(results)
        except Exception as e:
            logger.error(f"Failed to retrieve events from Redis: {str(e)}")
            return []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a field in a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added.
        """
        try:
            # Convert non-string values to strings if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(self._sanitize_for_json(value))
            return self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {str(e)}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {str(e)}")
            return None

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a Redis hash.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        try:
            return self.client.hkeys(name)
        except Exception as e:
            logger.error(f"Failed to get hash keys from {name}: {str(e)}")
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a Redis hash.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Failed to delete hash fields from {name}: {str(e)}")
            return 0

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a Redis set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        try:
            return self.client.smembers(name)
        except Exception as e:
            logger.error(f"Failed to get set members from {name}: {str(e)}")
            return []


# Future stub
class KafkaMemoryLogger:
    """
    A placeholder for a future Kafka-based memory logger.
    Raises NotImplementedError as it is not yet implemented.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Kafka backend not implemented yet")
