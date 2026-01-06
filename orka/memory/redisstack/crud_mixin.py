# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory CRUD Operations Mixin
============================

Provides Create, Read, Update, Delete operations for memory entries.
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MemoryCRUDMixin:
    """Mixin providing CRUD operations for Redis memory entries."""

    def _safe_get_redis_value(
        self, memory_data: dict, key: str, default: Any = None
    ) -> Any:
        """Safely get value from Redis hash data that might have bytes or string keys."""
        value = memory_data.get(key, memory_data.get(key.encode("utf-8"), default))
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return default
        return value

    def get_all_memories(self, trace_id: str | None = None) -> list[dict[str, Any]]:
        """Get all memories, optionally filtered by trace_id."""
        try:
            pattern = "orka_memory:*"
            keys = self._get_thread_safe_client().keys(pattern)

            memories = []
            for key in keys:
                try:
                    memory_data = self._get_thread_safe_client().hgetall(key)
                    if not memory_data:
                        continue

                    if (
                        trace_id
                        and self._safe_get_redis_value(memory_data, "trace_id")
                        != trace_id
                    ):
                        continue

                    if self._is_expired(memory_data):
                        continue

                    try:
                        metadata_value = self._safe_get_redis_value(
                            memory_data, "metadata", "{}"
                        )
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                    memory = {
                        "content": self._safe_get_redis_value(memory_data, "content", ""),
                        "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                        "trace_id": self._safe_get_redis_value(
                            memory_data, "trace_id", ""
                        ),
                        "importance_score": float(
                            self._safe_get_redis_value(
                                memory_data, "importance_score", "0"
                            )
                        ),
                        "memory_type": self._safe_get_redis_value(
                            memory_data, "memory_type", ""
                        ),
                        "timestamp": int(
                            self._safe_get_redis_value(memory_data, "timestamp", "0")
                        ),
                        "metadata": metadata,
                        "key": key.decode() if isinstance(key, bytes) else key,
                    }
                    memories.append(memory)

                except Exception as e:
                    logger.warning(f"Error processing memory {key}: {e}")
                    continue

            memories.sort(key=lambda x: x["timestamp"], reverse=True)
            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []

    def delete_memory(self, key: str) -> bool:
        """Delete a specific memory entry."""
        try:
            result = self._get_thread_safe_client().delete(key)
            logger.debug(f"Deleted memory key: {key}")
            return bool(result > 0)
        except Exception as e:
            logger.error(f"Failed to delete memory {key}: {e}")
            return False

    def clear_all_memories(self) -> None:
        """Clear all memories from the RedisStack storage."""
        try:
            pattern = "orka_memory:*"
            keys = self._get_thread_safe_client().keys(pattern)
            if keys:
                deleted = self._get_thread_safe_client().delete(*keys)
                logger.info(f"Cleared {deleted} memories from RedisStack")
            else:
                logger.info("No memories to clear")
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")

    def get_recent_stored_memories(self, count: int = 5) -> list[dict[str, Any]]:
        """Get recent stored memories (log_type='memory' only), sorted by timestamp."""
        try:
            client = self._get_thread_safe_client()
            pattern = "orka_memory:*"
            keys = client.keys(pattern)

            stored_memories = []
            current_time_ms = int(time.time() * 1000)

            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if not memory_data:
                        continue

                    if self._is_expired(memory_data):
                        continue

                    try:
                        metadata_value = self._safe_get_redis_value(
                            memory_data, "metadata", "{}"
                        )
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                    memory_log_type = metadata.get("log_type", "log")
                    memory_category = metadata.get("category", "log")

                    if memory_log_type != "memory" and memory_category != "stored":
                        continue

                    expiry_info = self._get_ttl_info(key, memory_data, current_time_ms)
                    if not expiry_info:
                        continue

                    memory = {
                        "content": self._safe_get_redis_value(memory_data, "content", ""),
                        "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                        "trace_id": self._safe_get_redis_value(
                            memory_data, "trace_id", ""
                        ),
                        "importance_score": float(
                            self._safe_get_redis_value(
                                memory_data, "importance_score", "0"
                            )
                        ),
                        "memory_type": self._safe_get_redis_value(
                            memory_data, "memory_type", ""
                        ),
                        "timestamp": int(
                            self._safe_get_redis_value(memory_data, "timestamp", "0")
                        ),
                        "metadata": metadata,
                        "key": key.decode() if isinstance(key, bytes) else key,
                        **expiry_info,
                    }
                    stored_memories.append(memory)

                except Exception as e:
                    logger.warning(f"Error processing memory {key}: {e}")
                    continue

            stored_memories.sort(key=lambda x: x["timestamp"], reverse=True)
            return stored_memories[:count]

        except Exception as e:
            logger.error(f"Failed to get recent stored memories: {e}")
            return []

    def tail(self, count: int = 10) -> list[dict[str, Any]]:
        """Get recent memory entries."""
        try:
            memories = self.get_all_memories()
            memories.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return memories[:count]
        except Exception as e:
            logger.error(f"Error in tail operation: {e}")
            return []

