"""P6 regression tests for the two streaming repairs.

1. Satellites now receive accumulated conversation history (context-loss fix):
   previously each satellite prompt used only the current intent/summary.
2. EventBus actually uses an injected redis client (the --redis flag was ignored).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from orka.streaming.event_bus import EventBus
from orka.streaming.prompt_composer import PromptComposer
from orka.streaming.runtime import RefreshConfig, StreamingOrchestrator
from orka.streaming.types import PromptBudgets

pytestmark = [pytest.mark.unit]


def _composer():
    return PromptComposer(budgets=PromptBudgets(total_tokens=1000, sections={"context": 500}))


@pytest.mark.asyncio
async def test_satellites_receive_conversation_history(monkeypatch):
    """The satellite prompt must include prior-turn history, not just current intent."""
    captured: dict[str, str] = {}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def complete(self, model, system, user):
            captured["user"] = user
            return "ok"

    monkeypatch.setattr("orka.streaming.runtime.OpenAICompatClient", _FakeClient)

    orch = StreamingOrchestrator(
        session_id="s1",
        bus=EventBus(),
        composer=_composer(),
        refresh=RefreshConfig(),
        satellites={
            "roles": ["summarizer"],
            "defs": [{"role": "summarizer", "provider": "p", "model": "m", "base_url": "http://x"}],
        },
    )
    # Simulate two prior turns of conversation.
    orch._append_history_line("User: my name is Marco")
    orch._append_history_line("Assistant: nice to meet you, Marco")
    orch._append_history_line("User: what is my name?")

    await orch._run_satellites()

    assert "user" in captured, "satellite client was never called"
    # The fix: prior-turn content (the name) must be in the satellite prompt.
    assert "Marco" in captured["user"], f"history not fed to satellite: {captured['user']!r}"
    assert "what is my name" in captured["user"]


@pytest.mark.asyncio
async def test_eventbus_uses_injected_redis_client():
    """When a redis client is provided, publish must route to Redis (xadd), not memory."""
    fake_redis = AsyncMock()
    fake_redis.xadd = AsyncMock(return_value=b"1-0")

    bus = EventBus(redis_client=fake_redis)
    msg_id = await bus.publish("sess.egress", {"type": "egress", "payload": {"x": 1}})

    fake_redis.xadd.assert_awaited_once()
    args, _ = fake_redis.xadd.call_args
    assert args[0] == "sess.egress"  # channel — proves the redis path was taken
    assert msg_id  # a (stringified) stream id was returned, not the in-memory id


@pytest.mark.asyncio
async def test_eventbus_falls_back_to_memory_without_redis():
    """No redis client -> in-memory path still works (no regression)."""
    bus = EventBus()  # redis_client=None
    msg_id = await bus.publish("sess.egress", {"type": "egress", "payload": {"x": 1}})
    assert msg_id  # got an in-memory id, no exception
