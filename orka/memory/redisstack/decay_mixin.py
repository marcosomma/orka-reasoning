# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory Decay Mixin for RedisStack
=================================

Memory expiry, TTL management, and cleanup operations.

Features
--------
- Memory expiration checking
- TTL calculation and formatting
- Expired memory cleanup with dry-run support
- Configurable decay rules

Usage
-----
This mixin is intended to be used with RedisStackMemoryLogger:

```python
class RedisStackMemoryLogger(BaseMemoryLogger, MemoryDecayMixin):
    pass
```
"""

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)


class MemoryDecayMixin:
    """
    Mixin providing memory decay and TTL management functionality.

    Requires the host class to provide:
    - `_get_thread_safe_client()` method
    - `_safe_get_redis_value()` method
    - `memory_decay_config` attribute
    - `_connection_pool` attribute (optional, for cleanup checks)
    """

    # Type hints for attributes provided by the host class
    memory_decay_config: dict[str, Any] | None

    # Methods expected from host class:
    # - _get_thread_safe_client() -> redis.Redis
    # - _safe_get_redis_value(memory_data, key, default) -> Any

    def _is_expired(self, memory_data: dict[str, Any]) -> bool:
        """Check if memory entry has expired."""
        expiry_time = self._safe_get_redis_value(memory_data, "orka_expire_time")
        if expiry_time:
            try:
                return int(float(expiry_time)) <= int(time.time() * 1000)
            except (ValueError, TypeError):
                return False
        return False

    def _get_ttl_info(
        self, key: bytes, memory_data: dict[str, Any], current_time_ms: int
    ) -> dict[str, Any] | None:
        """Calculate TTL information for a memory entry."""
        ttl_seconds = -1
        expires_at = None
        expires_at_formatted = "N/A"
        has_expiry = False

        # Check for Redis TTL
        try:
            client = self._get_thread_safe_client()
            redis_ttl = client.ttl(key)
            if redis_ttl > 0:
                ttl_seconds = redis_ttl
                expires_at = current_time_ms + (ttl_seconds * 1000)
                expires_at_formatted = time.strftime(
                    "%Y-%m-%d %H:%M:%S UTC", time.gmtime(expires_at / 1000)
                )
                has_expiry = True
        except Exception as e:
            key_str = key.decode() if isinstance(key, bytes) else str(key)
            logger.debug(f"Error getting Redis TTL for {key_str}: {e}")

        # Check for orka_expire_time field if Redis TTL is not set
        if not has_expiry:
            orka_expire_time = self._safe_get_redis_value(
                memory_data, "orka_expire_time"
            )
            if orka_expire_time:
                try:
                    orka_expire_time_int = int(float(orka_expire_time))
                    if orka_expire_time_int > current_time_ms:
                        ttl_seconds = int((orka_expire_time_int - current_time_ms) / 1000)
                        expires_at = orka_expire_time_int
                        expires_at_formatted = time.strftime(
                            "%Y-%m-%d %H:%M:%S UTC", time.gmtime(expires_at / 1000)
                        )
                        has_expiry = True
                    else:
                        # Already expired
                        ttl_seconds = 0
                        expires_at = orka_expire_time_int
                        expires_at_formatted = time.strftime(
                            "%Y-%m-%d %H:%M:%S UTC", time.gmtime(expires_at / 1000)
                        )
                        has_expiry = True
                except (ValueError, TypeError):
                    pass

        ttl_formatted = "N/A"
        if ttl_seconds >= 0:
            if ttl_seconds < 60:
                ttl_formatted = f"{ttl_seconds}s"
            elif ttl_seconds < 3600:
                ttl_formatted = f"{ttl_seconds // 60}m {ttl_seconds % 60}s"
            elif ttl_seconds < 86400:
                ttl_formatted = f"{ttl_seconds // 3600}h {(ttl_seconds % 3600) // 60}m"
            else:
                ttl_formatted = f"{ttl_seconds // 86400}d"

        return {
            "ttl_seconds": ttl_seconds,
            "ttl_formatted": ttl_formatted,
            "expires_at": expires_at,
            "expires_at_formatted": expires_at_formatted,
            "has_expiry": has_expiry,
        }

    def _calculate_expiry_hours(
        self,
        memory_type: str,
        importance_score: float,
        agent_decay_config: dict[str, Any] | None,
    ) -> float | None:
        """Calculate expiry hours based on memory type and importance."""
        # Use agent-specific config if available, otherwise use default
        decay_config = agent_decay_config or self.memory_decay_config

        if decay_config is None or not decay_config.get("enabled", True):
            return None

        # Base expiry times
        if memory_type == "long_term":
            base_hours = decay_config.get("long_term_hours", 168.0)  # 7 days
        else:
            base_hours = decay_config.get("short_term_hours", 2.0)  # 2 hours

        # Adjust based on importance
        importance_multiplier = 1.0 + importance_score
        adjusted_hours = base_hours * importance_multiplier

        return adjusted_hours

    def cleanup_expired_memories(self, dry_run: bool = False) -> dict[str, Any]:
        """Clean up expired memories using connection pool."""
        cleaned = 0
        total_checked = 0
        errors: list[str] = []

        try:
            # Check if connection pool is initialized
            if not hasattr(self, "_connection_pool") or self._connection_pool is None:
                logger.debug(
                    "RedisStack connection pool not yet initialized, skipping cleanup"
                )
                return {
                    "cleaned": 0,
                    "total_checked": 0,
                    "expired_found": 0,
                    "dry_run": dry_run,
                    "cleanup_type": "redisstack_not_ready",
                    "errors": ["Connection pool not yet initialized"],
                }

            # Get a client from the pool
            try:
                client = self._get_thread_safe_client()
            except Exception as e:
                logger.error(f"Failed to get Redis client for cleanup: {e}")
                return {
                    "cleaned": 0,
                    "total_checked": 0,
                    "expired_found": 0,
                    "dry_run": dry_run,
                    "cleanup_type": "redisstack_connection_failed",
                    "errors": [f"Connection failed: {e}"],
                }

            pattern = "orka_memory:*"
            keys = client.keys(pattern)
            total_checked = len(keys)

            expired_keys = []
            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if self._is_expired(memory_data):
                        expired_keys.append(key)
                except Exception as e:
                    errors.append(f"Error checking {key}: {e}")

            if not dry_run and expired_keys:
                # Delete expired keys in batches
                batch_size = 100
                for i in range(0, len(expired_keys), batch_size):
                    batch = expired_keys[i : i + batch_size]
                    try:
                        deleted_count = client.delete(*batch)
                        cleaned += deleted_count
                        logger.debug(f"Deleted batch of {deleted_count} expired memories")
                    except Exception as e:
                        errors.append(f"Batch deletion error: {e}")

            result = {
                "cleaned": cleaned,
                "total_checked": total_checked,
                "expired_found": len(expired_keys),
                "dry_run": dry_run,
                "cleanup_type": "redisstack",
                "errors": errors,
            }

            if cleaned > 0:
                logger.info(f"Cleanup completed: {cleaned} expired memories removed")

            return result

        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return {
                "error": str(e),
                "cleaned": 0,
                "total_checked": total_checked,
                "cleanup_type": "redisstack_failed",
                "errors": errors + [str(e)],
            }

