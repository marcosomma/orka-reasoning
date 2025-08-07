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


class FakeRedisClient:
    def __init__(self):
        self.store = {}

    def get(self, key):
        result = self.store.get(key)
        if result is None:
            return None
        # Convert all values to bytes like real Redis does
        if isinstance(result, str):
            return result.encode()
        elif isinstance(result, (int, float)):
            return str(result).encode()
        else:
            return str(result).encode()

    def set(self, key, val):
        self.store[key] = val
        return True

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                count += 1
        return count

    def hset(self, key, field, val):
        if key not in self.store:
            self.store[key] = {}
            is_new = True
        else:
            is_new = field not in self.store[key]
        self.store[key][field] = val
        return 1 if is_new else 0

    def hget(self, key, field):
        result = self.store.get(key, {}).get(field)
        if result is None:
            return None
        # Convert to bytes if it's not already
        if isinstance(result, str):
            return result.encode()
        elif isinstance(result, (int, float)):
            return str(result).encode()
        else:
            return str(result).encode()

    def hkeys(self, key):
        return [k.encode() if isinstance(k, str) else k for k in self.store.get(key, {}).keys()]

    def hdel(self, key, *fields):
        if key not in self.store:
            return 0
        count = 0
        for field in fields:
            if field in self.store[key]:
                del self.store[key][field]
                count += 1
        return count

    def keys(self, pattern="*"):
        if pattern == "*":
            return [k.encode() if isinstance(k, str) else k for k in self.store.keys()]
        # Simple pattern matching for testing
        import fnmatch

        return [
            k.encode() if isinstance(k, str) else k
            for k in self.store.keys()
            if fnmatch.fnmatch(k, pattern)
        ]

    def smembers(self, key):
        members = self.store.get(key, set())
        # Return bytes like real Redis for consistency
        return {m.encode() if isinstance(m, str) else m for m in members}

    def sadd(self, key, *vals):
        if key not in self.store:
            self.store[key] = set()
        old_size = len(self.store[key])
        self.store[key].update(vals)
        return len(self.store[key]) - old_size

    def scard(self, key):
        return len(self.smembers(key))

    def srem(self, key, *vals):
        if key not in self.store or not isinstance(self.store[key], set):
            return 0
        old_size = len(self.store[key])
        self.store[key].difference_update(vals)
        return old_size - len(self.store[key])

    def xadd(self, stream, data):
        self.store.setdefault(stream, []).append(data)
        return f"{len(self.store[stream])}-0"  # Return a stream ID

    def xrevrange(self, stream, count=1):
        entries = self.store.get(stream, [])
        return list(reversed(entries[-count:]))

    def close(self):
        """Close connection (no-op for fake client)"""

    def getaddrinfo(self, *args, **kwargs):
        # Return a plausible value for socket.getaddrinfo
        return [(2, 1, 6, "", ("127.0.0.1", 6379))]

    def lrange(self, key, start, end):
        """Get list range - return decoded strings"""
        items = self.store.get(key, [])
        if start < 0:
            start = len(items) + start
        if end < 0:
            end = len(items) + end + 1
        else:
            end = end + 1
        result = items[start:end]
        return [item.decode() if isinstance(item, bytes) else item for item in result]

    def get_all_streams(self):
        """Get all stream names (custom method for testing)"""
        streams = {}
        for key, value in self.store.items():
            if isinstance(value, list):
                # Handle both string and bytes keys
                key_str = key.decode() if isinstance(key, bytes) else str(key)
                if key_str.startswith("orka:memory"):
                    streams[key] = value
        return streams

    def xrange(self, stream, start="-", end="+", count=None):
        """Get entries from stream within range"""
        entries = self.store.get(stream, [])
        if isinstance(stream, str):
            entries = self.store.get(stream.encode(), entries)

        # Simple implementation for testing - return all entries with stream IDs
        result = []
        for i, entry in enumerate(entries):
            stream_id = f"{i + 1}-0"
            result.append([stream_id.encode(), entry])

        if count:
            result = result[:count]

        return result

    def xinfo_stream(self, stream):
        """Get information about stream"""
        entries = self.store.get(stream, [])
        if isinstance(stream, str):
            entries = self.store.get(stream.encode(), entries)

        return {
            b"length": len(entries),
            b"radix-tree-keys": 1,
            b"radix-tree-nodes": 2,
            b"groups": 0,
            b"last-generated-id": f"{len(entries)}-0".encode() if entries else b"0-0",
            b"first-entry": None,
            b"last-entry": None,
        }
