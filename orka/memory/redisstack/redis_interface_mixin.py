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
Redis Interface Mixin
=====================

Provides thread-safe Redis operation delegations.
"""


class RedisInterfaceMixin:
    """Mixin providing thread-safe Redis interface methods."""

    def hset(self, name: str, key: str, value: str | bytes | int | float) -> int:
        return self._get_thread_safe_client().hset(name, key, value)

    def hget(self, name: str, key: str) -> str | None:
        return self._get_thread_safe_client().hget(name, key)

    def hkeys(self, name: str) -> list[str]:
        return self._get_thread_safe_client().hkeys(name)

    def hdel(self, name: str, *keys: str) -> int:
        return self._get_thread_safe_client().hdel(name, *keys)

    def smembers(self, name: str) -> list[str]:
        members = self._get_thread_safe_client().smembers(name)
        return list(members)

    def scan(
        self, cursor: int = 0, match: str | None = None, count: int | None = None
    ) -> tuple[int, list[str]]:
        """Scan Redis keys with optional pattern matching."""
        return self._get_thread_safe_client().scan(cursor=cursor, match=match, count=count)

    def sadd(self, name: str, *values: str) -> int:
        return self._get_thread_safe_client().sadd(name, *values)

    def srem(self, name: str, *values: str) -> int:
        return self._get_thread_safe_client().srem(name, *values)

    def get(self, key: str) -> str | None:
        return self._get_thread_safe_client().get(key)

    def set(self, key: str, value: str | bytes | int | float) -> bool:
        try:
            return bool(self._get_thread_safe_client().set(key, value))
        except Exception:
            return False

    def delete(self, *keys: str) -> int:
        return self._get_thread_safe_client().delete(*keys)

