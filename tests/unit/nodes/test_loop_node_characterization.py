"""Characterization tests for LoopNode.

These tests lock down key invariants and edge-case behaviors so we can safely
refactor `orka/nodes/loop_node.py` into smaller components without accidentally
changing runtime semantics.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.nodes.loop_node import LoopNode


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


@pytest.mark.asyncio
async def test_run_impl_trims_past_loops_to_20_in_final_result():
    """If past_loops grows beyond 20, final output should be trimmed to last 20."""
    node = LoopNode(node_id="loop_node", max_loops=1, score_threshold=1.0, persist_across_runs=True)

    # Simulate persisted past_loops larger than allowed.
    persisted = [{"loop_number": i, "score": 0.1, "timestamp": "t"} for i in range(25)]

    with patch.object(node, "_load_past_loops_from_redis", new=AsyncMock(return_value=persisted)), patch.object(
        node, "_execute_internal_workflow", new=AsyncMock(return_value={"agent_x": {"response": "score: 1.0"}})
    ), patch.object(node, "_extract_score", new=AsyncMock(return_value=0.0)):
        result = await node._run_impl({"input": "x", "previous_outputs": {}})

    assert isinstance(result, dict)
    assert "past_loops" in result
    assert isinstance(result["past_loops"], list)
    assert len(result["past_loops"]) <= 20


def test_create_safe_result_removes_previous_outputs_and_payload_keys():
    node = LoopNode("loop_node")

    raw = {
        "agent": {
            "response": "ok",
            "previous_outputs": {"a": 1},
            "payload": {"b": 2},
        },
        "previous_outputs": {"x": "y"},
        "payload": {"p": "q"},
    }

    safe = node._create_safe_result(raw)
    assert isinstance(safe, dict)
    # Keys are filtered out at any dict level by implementation.
    assert "previous_outputs" not in safe
    assert "payload" not in safe
    assert "agent" in safe and isinstance(safe["agent"], dict)
    assert "previous_outputs" not in safe["agent"]
    assert "payload" not in safe["agent"]


@pytest.mark.asyncio
async def test_load_past_loops_from_redis_trims_to_20():
    mock_memory = Mock()
    loops = [{"loop_number": i, "score": 0.1, "timestamp": "t"} for i in range(35)]
    mock_memory.get.return_value = json.dumps(loops)

    node = LoopNode(node_id="loop_node", memory_logger=mock_memory, persist_across_runs=True)

    loaded = await node._load_past_loops_from_redis()
    assert isinstance(loaded, list)
    assert len(loaded) == 20
    # Should keep the most recent N entries
    assert loaded[0]["loop_number"] == 15
    assert loaded[-1]["loop_number"] == 34


