from unittest.mock import AsyncMock, Mock

import pytest

from orka.nodes.loop.runner import LoopRunnerDeps, run_loop


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


@pytest.mark.asyncio
async def test_run_loop_does_not_load_or_persist_past_loops_when_persist_disabled():
    deps = LoopRunnerDeps(
        execute_internal_workflow=AsyncMock(return_value={"agent_x": {"response": "ok"}}),
        extract_score=AsyncMock(return_value=0.0),
        load_past_loops=AsyncMock(return_value=[{"loop_number": 999}]),
        clear_loop_cache=AsyncMock(),
        build_past_loop_object=lambda loop_number, score, result: {
            "loop_number": str(loop_number),
            "score": str(score),
            "timestamp": "t",
            "insights": "",
            "improvements": "",
            "mistakes": "",
        },
        store_json=Mock(),
        store_hash_json=Mock(),
        create_safe_result=lambda v: v,
    )

    result = await run_loop(
        node_id="loop_node",
        original_input="x",
        original_previous_outputs={},
        max_loops=1,
        score_threshold=1.0,
        persist_across_runs=False,
        deps=deps,
    )

    assert isinstance(result, dict)
    assert "past_loops" in result
    assert len(result["past_loops"]) == 1

    deps.load_past_loops.assert_not_called()
    # Ensure we didn't write the cross-run past_loops key
    assert not any("past_loops:loop_node" in str(call) for call in deps.store_json.call_args_list)


@pytest.mark.asyncio
async def test_run_loop_loads_and_persists_past_loops_when_enabled():
    deps = LoopRunnerDeps(
        execute_internal_workflow=AsyncMock(return_value={"agent_x": {"response": "ok"}}),
        extract_score=AsyncMock(return_value=0.0),
        load_past_loops=AsyncMock(return_value=[{"loop_number": "1", "score": "0.1", "timestamp": "t"}]),
        clear_loop_cache=AsyncMock(),
        build_past_loop_object=lambda loop_number, score, result: {
            "loop_number": str(loop_number),
            "score": str(score),
            "timestamp": "t",
            "insights": "",
            "improvements": "",
            "mistakes": "",
        },
        store_json=Mock(),
        store_hash_json=Mock(),
        create_safe_result=lambda v: v,
    )

    result = await run_loop(
        node_id="loop_node",
        original_input="x",
        original_previous_outputs={},
        max_loops=1,
        score_threshold=1.0,
        persist_across_runs=True,
        deps=deps,
    )

    assert isinstance(result, dict)
    assert len(result["past_loops"]) == 2  # loaded 1 + appended 1
    deps.load_past_loops.assert_called_once()
    assert any("past_loops:loop_node" in str(call) for call in deps.store_json.call_args_list)


