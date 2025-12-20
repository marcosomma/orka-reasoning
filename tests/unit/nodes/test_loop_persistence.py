from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from orka.nodes.loop.persistence import LoopPersistence


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


@pytest.mark.asyncio
async def test_load_past_loops_trims_to_max():
    mem = Mock()
    loops = [{"loop_number": i, "score": 0.1, "timestamp": "t"} for i in range(35)]
    mem.get.return_value = json.dumps(loops)

    p = LoopPersistence(node_id="n1", memory_logger=mem)
    loaded = await p.load_past_loops(max_past_loops=20)

    assert isinstance(loaded, list)
    assert len(loaded) == 20
    assert loaded[0]["loop_number"] == 15
    assert loaded[-1]["loop_number"] == 34


@pytest.mark.asyncio
async def test_clear_loop_cache_scans_and_deletes():
    mem = Mock()
    redis = Mock()
    mem.redis = redis

    # scan returns some keys, then terminates cursor=0
    redis.scan.side_effect = [
        (0, [b"k1", b"k2"]),
        (0, []),
        (0, []),
        (0, []),
    ]

    p = LoopPersistence(node_id="node_x", memory_logger=mem)
    await p.clear_loop_cache(loop_number=3)

    assert redis.scan.called
    assert redis.delete.called


def test_store_json_and_store_hash_json_use_json_dumps():
    mem = Mock()
    p = LoopPersistence(node_id="n1", memory_logger=mem)

    p.store_json("k", {"a": 1})
    mem.set.assert_called_once()
    args, _ = mem.set.call_args
    assert args[0] == "k"
    assert json.loads(args[1]) == {"a": 1}

    p.store_hash_json("hk", "f", {"b": 2})
    mem.hset.assert_called_once()
    args, _ = mem.hset.call_args
    assert args[0] == "hk"
    assert args[1] == "f"
    assert json.loads(args[2]) == {"b": 2}


