"""
Event bus for OrKa streaming runtime.

Provides a minimal, asyncio-friendly publish/read/ack interface with an
in-memory fallback for offline unit tests. A Redis client can be plugged
in later without changing the public API.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    # Lazy import; tests can run without redis installed
    from redis.asyncio import Redis  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore

from .types import MessageEnvelope


@dataclass
class EventBusConfig:
    base_backoff_ms: int = 200
    max_retries: int = 5
    dlq_suffix: str = ".dlq"


class EventBus:
    """Typed event bus abstraction with optional Redis backend.

    Public methods are designed to be stable and easily unit-testable.
    """

    def __init__(
        self,
        redis_client: Optional["Redis"] = None,
        config: Optional[EventBusConfig] = None,
    ) -> None:
        self._redis = redis_client
        self._config = config or EventBusConfig()
        self._in_memory_streams: Dict[str, asyncio.Queue[Tuple[str, MessageEnvelope]]] = {}
        self._in_memory_offsets: Dict[str, int] = {}
        self._seen_idempotency: Dict[str, float] = {}
        self._idempotency_ttl = 600.0  # seconds

    # Internal helpers
    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _get_queue(self, channel: str) -> asyncio.Queue[Tuple[str, MessageEnvelope]]:
        if channel not in self._in_memory_streams:
            self._in_memory_streams[channel] = asyncio.Queue()
            self._in_memory_offsets[channel] = 0
        return self._in_memory_streams[channel]

    def _next_id(self, channel: str) -> str:
        self._in_memory_offsets[channel] = self._in_memory_offsets.get(channel, 0) + 1
        return f"{self._in_memory_offsets[channel]}-0"

    def _dedupe(self) -> None:
        cutoff = time.time() - self._idempotency_ttl
        for k, ts in list(self._seen_idempotency.items()):
            if ts < cutoff:
                del self._seen_idempotency[k]

    async def publish(self, channel: str, envelope: Dict[str, Any]) -> str:
        """Publish a message envelope on a channel.

        Returns a backend-specific message id as string.
        """
        if "timestamp_ms" not in envelope:
            envelope["timestamp_ms"] = self._now_ms()

        idem = envelope.get("idempotency_key")
        if idem:
            self._dedupe()
            if idem in self._seen_idempotency:
                # Already seen, return a synthetic id to indicate drop
                return "DUP-0"
            self._seen_idempotency[idem] = time.time()

        if self._redis is not None:
            # Store as JSON string
            payload = json.dumps(envelope)
            msg_id = await self._redis.xadd(channel, {"data": payload})  # type: ignore[attr-defined]
            return str(msg_id)

        # In-memory fallback
        msg_id = self._next_id(channel)
        await self._get_queue(channel).put((msg_id, envelope))  # type: ignore[arg-type]
        return msg_id

    async def read(self, channels: List[str], count: int, block_ms: int) -> List[Dict[str, Any]]:
        """Read up to count messages from channels, blocking up to block_ms.

        Returns list of {"channel", "message_id", "envelope"} dicts.
        """
        if self._redis is not None:
            streams = {ch: ">" for ch in channels}
            # XREAD with BLOCK
            resp = await self._redis.xread(streams=streams, count=count, block=block_ms)  # type: ignore[attr-defined]
            results: List[Dict[str, Any]] = []
            for ch, entries in resp:
                for message_id, data in entries:
                    try:
                        raw = data.get(b"data") or data.get("data")
                        envelope = json.loads(raw)
                    except Exception:
                        envelope = {"raw": data}
                    results.append(
                        {"channel": ch.decode() if isinstance(ch, bytes) else ch, "message_id": str(message_id), "envelope": envelope}
                    )
            return results

        # In-memory: poll queues fairly
        end = time.time() + (block_ms / 1000.0)
        in_mem_results: List[Dict[str, Any]] = []
        while len(in_mem_results) < count and time.time() < end:
            made_progress = False
            for ch in channels:
                q = self._get_queue(ch)
                if q.empty():
                    continue
                msg_id, env = await q.get()
                in_mem_results.append({"channel": ch, "message_id": msg_id, "envelope": env})
                made_progress = True
                if len(in_mem_results) >= count:
                    break
            if not made_progress:
                await asyncio.sleep(0.001)
        return in_mem_results

    async def ack(self, group: str, channel: str, message_id: str) -> None:  # noqa: ARG002
        """Acknowledge a message. No-op for in-memory backend."""
        if self._redis is not None:
            try:
                await self._redis.xack(channel, group, message_id)  # type: ignore[attr-defined]
            except Exception:
                # Best-effort ack; swallow errors for robustness
                return

    async def to_dlq(self, channel: str, envelope: Dict[str, Any], reason: str) -> None:
        """Send an envelope to the per-session DLQ stream."""
        dlq_channel = f"{channel}{self._config.dlq_suffix}"
        env = dict(envelope)
        env["dlq_reason"] = reason
        await self.publish(dlq_channel, env)
