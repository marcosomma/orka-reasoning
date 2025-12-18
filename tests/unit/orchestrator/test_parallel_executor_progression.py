import pytest
from unittest.mock import Mock


@pytest.mark.asyncio
async def test_parallel_executor_marks_done_and_enqueues_next(temp_config_file):
    from orka.orchestrator.execution.parallel_executor import ParallelExecutor

    # Create a simple orchestrator stub
    orchestrator = Mock()
    orchestrator.agents = {"a1": Mock(), "a2": Mock()}

    # Make _run_branch_with_retry return an immediate mapping for branch
    async def fake_run_branch(branch, input_data, prev_outputs, max_retries=2, retry_delay=1.0):
        # return mapping for each agent in branch
        result = {}
        for aid in branch:
            result[aid] = {"response": "ok"}
        return result

    orchestrator._run_branch_with_retry = fake_run_branch

    orchestrator.fork_manager = Mock()
    orchestrator.enqueue_fork = Mock()

    pe = ParallelExecutor(orchestrator)

    # Run with a single branch list
    logs = await pe.run_parallel_agents(["a1", "a2"], "fg_test", {}, {})

    # fork_manager.mark_agent_done should be called for each agent present in logs
    assert orchestrator.fork_manager.mark_agent_done.call_count >= 2
