import json
import pytest
from unittest.mock import Mock

from orka.orchestrator.execution.parallel_executor import ParallelExecutor


@pytest.mark.asyncio
async def test_parallel_executor_writes_group_results(temp_config_file):
    orchestrator = Mock()
    orchestrator.agents = {"a1": Mock()}

    # Simulate branch runner returning a normal result with response/confidence
    async def fake_run_branch(branch, input_data, prev_outputs, max_retries=2, retry_delay=1.0):
        return {"a1": {"response": "ok", "confidence": "0.95"}}

    orchestrator._run_branch_with_retry = fake_run_branch
    orchestrator.memory = Mock()

    pe = ParallelExecutor(orchestrator)

    result_logs = await pe.run_parallel_agents(["a1"], "fg_test", {}, {})

    # Check that memory.hset was called for the join state key and the group key
    hset_calls = [c for c in orchestrator.memory.hset.call_args_list]
    assert any("waitfor:fg_test:inputs" in str(c) for c in hset_calls)
    assert any("fork_group_results:fg_test" in str(c) for c in hset_calls)

    # Expect that direct agent_result key was set
    set_calls = [c for c in orchestrator.memory.set.call_args_list]
    assert any("agent_result:fg_test:a1" in str(c) for c in set_calls)

    # And logs should contain the branch event
    assert any(r.get("agent_id") == "a1" or r.get("agent_id", "").startswith("branch_") for r in result_logs)
