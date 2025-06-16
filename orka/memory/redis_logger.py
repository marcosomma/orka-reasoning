# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Redis Memory Logger Implementation
=================================

Redis-based memory logger that uses Redis streams for event storage.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis

from .base_logger import BaseMemoryLogger

logger = logging.getLogger(__name__)


class RedisMemoryLogger(BaseMemoryLogger):
    """
    A memory logger that uses Redis to store and retrieve orchestration events.
    Supports logging events, saving logs to files, and querying recent events.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
    ) -> None:
        """
        Initialize the Redis memory logger.

        Args:
            redis_url: URL for the Redis server. Defaults to environment variable REDIS_URL or redis service name.
            stream_key: Key for the Redis stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
        """
        super().__init__(stream_key, debug_keep_previous_outputs)
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.redis_url)

    @property
    def redis(self) -> redis.Redis:
        """
        Return the Redis client for backward compatibility.
        This property exists for compatibility with existing code.
        """
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
                        self._sanitize_for_json(previous_outputs),
                    )
                except Exception as e:
                    logger.error(f"Failed to serialize previous_outputs: {e!s}")
                    safe_previous_outputs = json.dumps(
                        {"error": f"Serialization error: {e!s}"},
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
                logger.error(f"Failed to serialize payload: {e!s}")
                redis_entry["payload"] = json.dumps(
                    {"error": "Original payload contained non-serializable objects"},
                )

            # Only add previous_outputs if it exists and is not None
            if safe_previous_outputs:
                redis_entry["previous_outputs"] = safe_previous_outputs

            # Add the entry to Redis
            self.client.xadd(self.stream_key, redis_entry)

        except Exception as e:
            logger.error(f"Failed to log event to Redis: {e!s}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {e!s}",
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
                    f"Failed to log event to Redis: {e!s} and fallback also failed: {inner_e!s}",
                )

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
            logger.error(f"Failed to retrieve events from Redis: {e!s}")
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
            logger.error(f"Failed to set hash field {key} in {name}: {e!s}")
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
            logger.error(f"Failed to get hash field {key} from {name}: {e!s}")
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
            logger.error(f"Failed to get hash keys from {name}: {e!s}")
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
            if not keys:
                logger.warning(f"hdel called with no keys for hash {name}")
                return 0
            return self.client.hdel(name, *keys)
        except Exception as e:
            # Handle WRONGTYPE errors by cleaning up the key and retrying
            if "WRONGTYPE" in str(e):
                logger.warning(f"WRONGTYPE error for key '{name}', attempting cleanup")
                if self._cleanup_redis_key(name):
                    try:
                        # Retry after cleanup
                        return self.client.hdel(name, *keys)
                    except Exception as retry_e:
                        logger.error(f"Failed to hdel after cleanup: {retry_e!s}")
                        return 0
            logger.error(f"Failed to delete hash fields from {name}: {e!s}")
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
            logger.error(f"Failed to get set members from {name}: {e!s}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """
        Add members to a Redis set.

        Args:
            name: Name of the set.
            *values: Values to add.

        Returns:
            Number of new members added.
        """
        try:
            return self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Failed to add members to set {name}: {e!s}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """
        Remove members from a Redis set.

        Args:
            name: Name of the set.
            *values: Values to remove.

        Returns:
            Number of members removed.
        """
        try:
            return self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Failed to remove members from set {name}: {e!s}")
            return 0

    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key from Redis.

        Args:
            key: The key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            result = self.client.get(key)
            return result.decode() if isinstance(result, bytes) else result
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e!s}")
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set a value by key in Redis.

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e!s}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e!s}")
            return 0

    def close(self) -> None:
        """Close the Redis client connection."""
        try:
            self.client.close()
            # Only log if logging system is still available
            try:
                logger.info("[RedisMemoryLogger] Redis client closed")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass
        except Exception as e:
            try:
                logger.error(f"Error closing Redis client: {e!s}")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            # Ignore all errors during cleanup
            pass

    def _cleanup_redis_key(self, key: str) -> bool:
        """
        Clean up a Redis key that might have the wrong type.

        This method deletes a key to resolve WRONGTYPE errors.

        Args:
            key: The Redis key to clean up

        Returns:
            True if key was cleaned up, False if cleanup failed
        """
        try:
            self.client.delete(key)
            logger.warning(f"Cleaned up Redis key '{key}' due to type conflict")
            return True
        except Exception as e:
            logger.error(f"Failed to clean up Redis key '{key}': {e!s}")
            return False
