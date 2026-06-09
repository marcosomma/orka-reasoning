"""Shared fixtures for brain unit tests."""

from __future__ import annotations

import pytest


class FakeMemoryWithSortedSets:
    """In-memory fake of RedisStack memory with sorted-set support for testing.

    Extends the standard FakeMemory pattern used in brain tests with
    ``zadd``, ``zrevrange``, ``zrange``, ``zrem``, and ``zcard`` operations
    required by :class:`orka.brain.episode_store.EpisodeStore`.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self._logs: list[dict] = []

    # ---- string ops ----

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> bool:
        self._store[key] = value
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
        return count

    # ---- hash ops ----

    def hset(self, name: str, key: str, value: str) -> int:
        if name not in self._hashes:
            self._hashes[name] = {}
        self._hashes[name][key] = value
        return 1

    def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    def hkeys(self, name: str) -> list[str]:
        return list(self._hashes.get(name, {}).keys())

    def hdel(self, name: str, *keys: str) -> int:
        count = 0
        h = self._hashes.get(name, {})
        for k in keys:
            if k in h:
                del h[k]
                count += 1
        return count

    # ---- set ops ----

    def sadd(self, name: str, *values: str) -> int:
        if name not in self._sets:
            self._sets[name] = set()
        count = 0
        for v in values:
            if v not in self._sets[name]:
                self._sets[name].add(v)
                count += 1
        return count

    def srem(self, name: str, *values: str) -> int:
        s = self._sets.get(name, set())
        count = 0
        for v in values:
            if v in s:
                s.discard(v)
                count += 1
        return count

    def smembers(self, name: str) -> list[str]:
        return list(self._sets.get(name, set()))

    # ---- sorted-set ops ----

    def zadd(self, name: str, mapping: dict[str, float]) -> int:
        if name not in self._sorted_sets:
            self._sorted_sets[name] = {}
        count = 0
        for member, score in mapping.items():
            if member not in self._sorted_sets[name]:
                count += 1
            self._sorted_sets[name][member] = score
        return count

    def zrem(self, name: str, *members: str) -> int:
        zs = self._sorted_sets.get(name, {})
        count = 0
        for m in members:
            if m in zs:
                del zs[m]
                count += 1
        return count

    def zcard(self, name: str) -> int:
        return len(self._sorted_sets.get(name, {}))

    def zrevrange(self, name: str, start: int, stop: int) -> list[str]:
        """Return members from highest to lowest score, inclusive range."""
        zs = self._sorted_sets.get(name, {})
        sorted_members = sorted(zs.keys(), key=lambda m: zs[m], reverse=True)
        if stop < 0:
            stop = len(sorted_members) + stop + 1
        else:
            stop = stop + 1  # Make inclusive
        return sorted_members[start:stop]

    def zrange(self, name: str, start: int, stop: int) -> list[str]:
        """Return members from lowest to highest score, inclusive range."""
        zs = self._sorted_sets.get(name, {})
        sorted_members = sorted(zs.keys(), key=lambda m: zs[m])
        if stop < 0:
            stop = len(sorted_members) + stop + 1
        else:
            stop = stop + 1  # Make inclusive
        return sorted_members[start:stop]

    # ---- logging ----

    def log(self, **kwargs) -> None:
        self._logs.append(kwargs)


@pytest.fixture
def fake_memory() -> FakeMemoryWithSortedSets:
    """Provide a fresh FakeMemory instance with sorted-set support."""
    return FakeMemoryWithSortedSets()
