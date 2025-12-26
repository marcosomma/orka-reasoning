import asyncio
import pytest

from orka.streaming.event_bus import EventBus


@pytest.mark.asyncio
async def test_in_memory_publish_read_ack():
    bus = EventBus()
    ch = "sess1.ingress"
    env = {
        "session_id": "sess1",
        "channel": ch,
        "type": "ingress",
        "payload": {"text": "hello"},
        "source": "test",
    }
    mid = await bus.publish(ch, env)
    assert isinstance(mid, str)

    msgs = await bus.read([ch], count=1, block_ms=50)
    assert len(msgs) == 1
    item = msgs[0]
    assert item["channel"] == ch
    assert item["envelope"]["payload"]["text"] == "hello"

    await bus.ack("default", ch, item["message_id"])  # should not raise


@pytest.mark.asyncio
async def test_idempotency_drop():
    bus = EventBus()
    ch = "sess2.ingress"
    env = {
        "session_id": "sess2",
        "channel": ch,
        "type": "ingress",
        "payload": {"text": "x"},
        "source": "test",
        "idempotency_key": "k1",
    }
    id1 = await bus.publish(ch, dict(env))
    id2 = await bus.publish(ch, dict(env))
    assert id1 != "DUP-0"
    assert id2 == "DUP-0"
