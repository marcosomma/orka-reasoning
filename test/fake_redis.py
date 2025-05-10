# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning


class FakeRedisClient:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, val):
        self.store[key] = val

    def delete(self, key):
        self.store.pop(key, None)

    def hset(self, key, field, val):
        self.store.setdefault(key, {})[field] = val

    def hget(self, key, field):
        return self.store.get(key, {}).get(field)

    def hkeys(self, key):
        return list(self.store.get(key, {}).keys())

    def smembers(self, key):
        return self.store.get(key, set())

    def sadd(self, key, *vals):
        self.store.setdefault(key, set()).update(vals)

    def scard(self, key):
        return len(self.smembers(key))

    def srem(self, key, *vals):  # NEW
        if key in self.store and isinstance(self.store[key], set):
            self.store[key].difference_update(vals)

    def xadd(self, stream, data):
        self.store.setdefault(stream, []).append(data)

    def xrevrange(self, stream, count=1):
        entries = self.store.get(stream, [])
        return list(reversed(entries[-count:]))

    def getaddrinfo(self, *args, **kwargs):
        # Return a plausible value for socket.getaddrinfo
        return [(2, 1, 6, "", ("127.0.0.1", 6379))]
