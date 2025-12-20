from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, List

from .types import PastLoopMetadata

logger = logging.getLogger(__name__)


@dataclass
class LoopPersistence:
    """Redis persistence and cache-eviction logic for LoopNode.

    This is an extraction of the existing LoopNode methods:
    - _load_past_loops_from_redis
    - _store_in_redis
    - _store_in_redis_hash
    - _clear_loop_cache

    Key formats are intentionally kept identical to preserve backward compatibility.
    """

    node_id: str
    memory_logger: Any = None

    async def clear_loop_cache(self, loop_number: int) -> None:
        if self.memory_logger is None:
            return

        try:
            cache_patterns = [
                f"loop_cache:{self.node_id}:{loop_number}",
                f"loop_cache:{self.node_id}:*",
                f"agent_cache:{self.node_id}:{loop_number}:*",
                f"response_cache:{self.node_id}:{loop_number}:*",
            ]

            redis = getattr(self.memory_logger, "redis", None)
            if redis is None:
                return

            for pattern in cache_patterns:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = redis.scan(cursor, match=pattern, count=100)
                        if keys:
                            redis.delete(*keys)
                            logger.debug("Cleared %s cache keys matching %s", len(keys), pattern)
                        if cursor == 0:
                            break
                except Exception as e:
                    logger.warning("Failed to clear cache pattern %s: %s", pattern, e)
        except Exception as e:
            logger.warning("Failed to clear loop cache for loop %s: %s", loop_number, e)

    async def load_past_loops(self, max_past_loops: int = 20) -> List[PastLoopMetadata]:
        past_loops: List[PastLoopMetadata] = []
        if self.memory_logger is None:
            return past_loops

        try:
            past_loops_key = f"past_loops:{self.node_id}"
            stored_data = self.memory_logger.get(past_loops_key)
            if not stored_data:
                logger.debug("No past loops found in Redis for node %s", self.node_id)
                return past_loops

            loaded_loops = json.loads(stored_data)
            if not isinstance(loaded_loops, list):
                logger.warning("Invalid past loops data format in Redis for node %s", self.node_id)
                return past_loops

            if len(loaded_loops) > max_past_loops:
                past_loops = loaded_loops[-max_past_loops:]
                logger.warning(
                    "Loaded %s past loops from Redis, trimmed to most recent %s to prevent bloat",
                    len(loaded_loops),
                    max_past_loops,
                )
            else:
                past_loops = loaded_loops
                logger.info("Loaded %s past loops from Redis for node %s", len(past_loops), self.node_id)

            return past_loops
        except Exception as e:
            logger.error("Failed to load past loops from Redis: %s", e)
            return past_loops

    def store_json(self, key: str, value: Any) -> None:
        if self.memory_logger is None:
            return
        try:
            self.memory_logger.set(key, json.dumps(value))
            logger.debug("- Stored in Redis: %s", key)
        except Exception as e:
            logger.error("Failed to store in Redis: %s", e)

    def store_hash_json(self, hash_key: str, field: str, value: Any) -> None:
        if self.memory_logger is None:
            return
        try:
            self.memory_logger.hset(hash_key, field, json.dumps(value))
            logger.debug("- Stored in Redis hash: %s[%s]", hash_key, field)
        except Exception as e:
            logger.error("Failed to store in Redis hash: %s", e)


