import json
import pytest
from unittest.mock import Mock

from orka.orchestrator.execution.parallel_executor import ParallelExecutor


@pytest.mark.asyncio
async def test_parallel_executor_logs_empty_branch(temp_config_file, caplog):
    orchestrator = Mock()
    orchestrator.agents = {"a1": Mock()}

    # Simulate branch runner returning an empty result (no response/confidence)
    async def fake_run_branch(branch, input_data, prev_outputs, max_retries=2, retry_delay=1.0):
        return {"a1": {"result": None}}

    orchestrator._run_branch_with_retry = fake_run_branch
    orchestrator.memory = Mock()

    pe = ParallelExecutor(orchestrator)

    caplog.clear()
    result_logs = await pe.run_parallel_agents(["a1"], "fg_empty", {}, {})

    # Expect a warning about empty/low-confidence result
    assert any("returned empty/low-confidence result" in r.message for r in caplog.records)
    # And result logs should contain at least one entry for the branch
    assert any(r.get("agent_id") for r in result_logs)
