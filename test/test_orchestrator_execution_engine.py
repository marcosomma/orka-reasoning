"""
Tests for orka.orchestrator.execution_engine module.

This module tests the ExecutionEngine class which handles workflow execution,
agent coordination, and parallel processing.
"""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, agent_type="agent", result=None, config=None, params=None):
        self.type = agent_type
        self.config = config or {}
        self.params = params or {}
        self._result = result or {"status": "success", "output": "test output"}
        self.__class__.__name__ = f"Mock{agent_type.title()}Agent"

    def run(self, payload):
        return self._result

    async def async_run(self, payload):
        return self._result


class MockOrchestrator(ExecutionEngine):
    """Mock orchestrator that inherits from ExecutionEngine for testing."""

    def __init__(self):
        self.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        self.agents = {}
        self.memory = Mock()
        self.memory.memory = []
        self.memory.log = Mock()
        self.memory.save_to_file = Mock()
        self.memory.close = Mock()
        self.memory.hget = Mock(return_value=None)
        self.memory.hset = Mock()

        self.fork_manager = Mock()
        self.fork_manager.generate_group_id = Mock(return_value="test_group_123")
        self.fork_manager.create_group = Mock()
        self.fork_manager.delete_group = Mock()
        self.fork_manager.mark_agent_done = Mock()
        self.fork_manager.next_in_sequence = Mock(return_value=None)

        self.run_id = str(uuid4())
        self.step_index = 0
        self.queue = []

        # Error tracking
        self.error_telemetry = {
            "errors": [],
            "retry_counters": {},
            "partial_successes": [],
            "silent_degradations": [],
            "status_codes": {},
            "execution_status": "running",
            "critical_failures": [],
            "recovery_actions": [],
        }

    def build_previous_outputs(self, logs):
        """Mock implementation of build_previous_outputs."""
        return {log["agent_id"]: log.get("payload", {}).get("result") for log in logs}

    def normalize_bool(self, value):
        """Mock implementation of normalize_bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value)

    def _record_error(self, error_type, agent_id, message, exception, recovery_action):
        """Mock implementation of _record_error."""
        self.error_telemetry["errors"].append(
            {
                "type": error_type,
                "agent_id": agent_id,
                "message": message,
                "exception": str(exception),
                "recovery_action": recovery_action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _record_retry(self, agent_id):
        """Mock implementation of _record_retry."""
        if agent_id not in self.error_telemetry["retry_counters"]:
            self.error_telemetry["retry_counters"][agent_id] = 0
        self.error_telemetry["retry_counters"][agent_id] += 1

    def _record_partial_success(self, agent_id, retry_count):
        """Mock implementation of _record_partial_success."""
        self.error_telemetry["partial_successes"].append(
            {
                "agent_id": agent_id,
                "retry_count": retry_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _extract_llm_metrics(self, agent, result):
        """Mock implementation of _extract_llm_metrics."""
        if hasattr(agent, "llm_metrics"):
            return agent.llm_metrics
        return None

    def _generate_meta_report(self, logs):
        """Mock implementation of _generate_meta_report."""
        return {
            "total_duration": 1.234,
            "total_llm_calls": 5,
            "total_tokens": 1000,
            "total_cost_usd": 0.05,
            "avg_latency_ms": 250.0,
        }

    def _save_error_report(self, logs, exception):
        """Mock implementation of _save_error_report."""

    def _render_agent_prompt(self, agent, payload):
        """Mock implementation of _render_agent_prompt."""

    def _add_prompt_to_payload(self, agent, payload_out, payload):
        """Mock implementation of _add_prompt_to_payload."""
        payload_out["prompt_rendered"] = True


@pytest.fixture
def orchestrator():
    """Create a mock orchestrator for testing."""
    return MockOrchestrator()


@pytest.fixture
def sample_input_data():
    """Sample input data for testing."""
    return {"query": "test query", "context": "test context"}


class TestExecutionEngine:
    """Test cases for ExecutionEngine class."""

    @pytest.mark.asyncio
    async def test_run_success(self, orchestrator, sample_input_data):
        """Test successful execution run."""
        # Setup agents
        agent1 = MockAgent("agent", {"status": "success", "output": "result1"})
        agent2 = MockAgent("agent", {"status": "success", "output": "result2"})
        orchestrator.agents = {"agent1": agent1, "agent2": agent2}

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator.run(sample_input_data)

        assert len(result) == 2
        assert result[0]["agent_id"] == "agent1"
        assert result[1]["agent_id"] == "agent2"
        assert orchestrator.memory.log.call_count == 2
        assert orchestrator.memory.save_to_file.called
        assert orchestrator.memory.close.called

    @pytest.mark.asyncio
    async def test_run_with_exception(self, orchestrator, sample_input_data):
        """Test run with fatal exception."""
        orchestrator.orchestrator_cfg = {"agents": ["failing_agent"]}
        orchestrator.agents = {"failing_agent": MockAgent()}

        # Mock _run_with_comprehensive_error_handling to raise exception
        with patch.object(
            orchestrator,
            "_run_with_comprehensive_error_handling",
            side_effect=Exception("Fatal error"),
        ):
            with pytest.raises(Exception, match="Fatal error"):
                await orchestrator.run(sample_input_data)

        assert orchestrator.error_telemetry["execution_status"] == "failed"
        assert len(orchestrator.error_telemetry["critical_failures"]) == 1

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_success(
        self,
        orchestrator,
        sample_input_data,
    ):
        """Test comprehensive error handling with successful execution."""
        agent = MockAgent("agent", {"status": "success", "output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        assert len(result) == 1
        assert result[0]["agent_id"] == "agent1"

    @pytest.mark.asyncio
    async def test_run_with_agent_retry_logic(self, orchestrator, sample_input_data):
        """Test agent retry logic on failure."""
        # Create agent that fails twice then succeeds
        call_count = 0

        def failing_run(payload):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception(f"Failure {call_count}")
            return {"status": "success", "output": "finally worked"}

        agent = MockAgent("agent")
        agent.run = failing_run
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        assert len(result) == 1
        assert result[0]["payload"]["result"]["result"]["output"] == "finally worked"
        assert orchestrator.error_telemetry["retry_counters"]["agent1"] == 2
        assert len(orchestrator.error_telemetry["partial_successes"]) == 1

    @pytest.mark.asyncio
    async def test_run_with_max_retries_exceeded(self, orchestrator, sample_input_data):
        """Test agent that exceeds max retries."""
        agent = MockAgent("agent")
        agent.run = Mock(side_effect=Exception("Always fails"))
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        assert len(result) == 1
        assert result[0]["payload"]["result"]["status"] == "failed"
        assert orchestrator.error_telemetry["retry_counters"]["agent1"] == 4

    @pytest.mark.asyncio
    async def test_execute_single_agent_router_node(self, orchestrator, sample_input_data):
        """Test execution of router node."""
        agent = MockAgent("routernode", ["next_agent1", "next_agent2"])
        agent.params = {
            "decision_key": "should_continue",
            "routing_map": {"true": ["next_agent1"], "false": ["next_agent2"]},
        }

        payload = {
            "input": sample_input_data,
            "previous_outputs": {"should_continue": True},
        }
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "router1",
            agent,
            "routernode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["decision_value"] == "true"
        assert result["next_agents"] == "['next_agent1', 'next_agent2']"
        assert queue == ["next_agent1", "next_agent2"]

    @pytest.mark.asyncio
    async def test_execute_single_agent_fork_node(self, orchestrator, sample_input_data):
        """Test execution of fork node."""
        agent = MockAgent("forknode", {"status": "forked"})
        agent.config = {"targets": [["agent1", "agent2"], ["agent3"]], "mode": "parallel"}
        agent.run = AsyncMock(return_value={"status": "forked"})

        # Mock run_parallel_agents
        orchestrator.run_parallel_agents = AsyncMock(
            return_value=[
                {"agent_id": "agent1", "result": "result1"},
                {"agent_id": "agent2", "result": "result2"},
            ],
        )

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "fork1",
            agent,
            "forknode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["fork_group"] == "test_group_123"
        assert result["fork_targets"] == ["agent1", "agent2", "agent3"]
        assert orchestrator.fork_manager.create_group.called
        assert orchestrator.run_parallel_agents.called

    @pytest.mark.asyncio
    async def test_execute_single_agent_join_node_waiting(self, orchestrator, sample_input_data):
        """Test execution of join node in waiting state."""
        agent = MockAgent("joinnode", {"status": "waiting", "message": "waiting for agents"})
        agent.group_id = "test_group"

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "join1",
            agent,
            "joinnode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["status"] == "waiting"
        assert "join1" in queue  # Should be re-queued

    @pytest.mark.asyncio
    async def test_execute_single_agent_join_node_timeout(self, orchestrator, sample_input_data):
        """Test execution of join node with timeout."""
        agent = MockAgent("joinnode", {"status": "timeout", "message": "timeout waiting"})
        agent.group_id = "test_group"

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "join1",
            agent,
            "joinnode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["status"] == "timeout"
        assert orchestrator.fork_manager.delete_group.called

    @pytest.mark.asyncio
    async def test_execute_single_agent_join_node_done(self, orchestrator, sample_input_data):
        """Test execution of join node when done."""
        agent = MockAgent("joinnode", {"status": "done", "results": {"agent1": "result1"}})
        agent.group_id = "test_group"

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "join1",
            agent,
            "joinnode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["result"]["status"] == "done"
        assert orchestrator.fork_manager.delete_group.called

    @pytest.mark.asyncio
    async def test_execute_single_agent_memory_node(self, orchestrator, sample_input_data):
        """Test execution of memory reader node (async)."""
        agent = MockAgent("memoryreadernode", {"status": "success", "data": "memory_data"})
        agent.run = AsyncMock(return_value={"status": "success", "data": "memory_data"})

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "memory1",
            agent,
            "memoryreadernode",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["result"]["data"] == "memory_data"
        assert agent.run.called

    @pytest.mark.asyncio
    async def test_execute_single_agent_regular_agent(self, orchestrator, sample_input_data):
        """Test execution of regular synchronous agent."""
        agent = MockAgent("agent", {"status": "success", "output": "regular_output"})

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "regular1",
            agent,
            "agent",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["result"]["output"] == "regular_output"
        assert result["prompt_rendered"] is True

    @pytest.mark.asyncio
    async def test_execute_single_agent_waiting_status(self, orchestrator, sample_input_data):
        """Test agent returning waiting status."""
        agent = MockAgent("agent", {"status": "waiting", "received": "partial_input"})

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        result = await orchestrator._execute_single_agent(
            "waiting1",
            agent,
            "agent",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert result["status"] == "waiting"
        assert "waiting1" in queue

    @pytest.mark.asyncio
    async def test_run_agent_async_sync_agent(self, orchestrator, sample_input_data):
        """Test running synchronous agent asynchronously."""
        agent = MockAgent("agent", {"output": "sync_result"})
        orchestrator.agents = {"agent1": agent}

        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_pool = Mock()
            mock_executor.return_value.__enter__.return_value = mock_pool

            # Mock the event loop
            mock_loop = Mock()
            mock_loop.run_in_executor = AsyncMock(return_value={"output": "sync_result"})

            with patch("asyncio.get_event_loop", return_value=mock_loop):
                agent_id, result = await orchestrator._run_agent_async(
                    "agent1",
                    sample_input_data,
                    {},
                )

        assert agent_id == "agent1"
        assert result["output"] == "sync_result"

    @pytest.mark.asyncio
    async def test_run_agent_async_async_agent(self, orchestrator, sample_input_data):
        """Test running asynchronous agent."""
        agent = MockAgent("agent", {"output": "async_result"})
        agent.run = AsyncMock(return_value={"output": "async_result"})
        orchestrator.agents = {"agent1": agent}

        agent_id, result = await orchestrator._run_agent_async(
            "agent1",
            sample_input_data,
            {},
        )

        assert agent_id == "agent1"
        assert result["output"] == "async_result"

    @pytest.mark.asyncio
    async def test_run_agent_async_needs_orchestrator(self, orchestrator, sample_input_data):
        """Test running agent that needs orchestrator parameter."""
        agent = MockAgent("agent", {"output": "orchestrator_result"})

        # Mock run method that takes orchestrator parameter
        def run_with_orchestrator(orchestrator_param, payload):
            return {"output": "orchestrator_result"}

        agent.run = run_with_orchestrator
        orchestrator.agents = {"agent1": agent}

        agent_id, result = await orchestrator._run_agent_async(
            "agent1",
            sample_input_data,
            {},
        )

        assert agent_id == "agent1"
        assert result["output"] == "orchestrator_result"

    @pytest.mark.asyncio
    async def test_run_branch_async(self, orchestrator, sample_input_data):
        """Test running a branch of agents sequentially."""
        agent1 = MockAgent("agent", {"output": "result1"})
        agent2 = MockAgent("agent", {"output": "result2"})
        orchestrator.agents = {"agent1": agent1, "agent2": agent2}

        # Mock _run_agent_async
        async def mock_run_agent_async(agent_id, input_data, previous_outputs):
            return agent_id, orchestrator.agents[agent_id].run({})

        orchestrator._run_agent_async = mock_run_agent_async

        result = await orchestrator._run_branch_async(
            ["agent1", "agent2"],
            sample_input_data,
            {},
        )

        assert result["agent1"]["output"] == "result1"
        assert result["agent2"]["output"] == "result2"

    @pytest.mark.asyncio
    async def test_run_parallel_agents(self, orchestrator, sample_input_data):
        """Test running multiple agents in parallel."""
        # Setup fork node
        fork_node = MockAgent("forknode")
        fork_node.targets = [["agent1"], ["agent2"]]
        orchestrator.agents = {
            "fork1": fork_node,
            "agent1": MockAgent("agent", {"output": "result1"}),
            "agent2": MockAgent("agent", {"output": "result2"}),
        }

        # Mock _run_branch_async
        async def mock_run_branch_async(branch_agents, input_data, previous_outputs):
            results = {}
            for agent_id in branch_agents:
                results[agent_id] = orchestrator.agents[agent_id].run({})
            return results

        orchestrator._run_branch_async = mock_run_branch_async

        result = await orchestrator.run_parallel_agents(
            ["agent1", "agent2"],
            "fork1_123",
            sample_input_data,
            {},
        )

        assert len(result) == 2
        assert result[0]["agent_id"] == "agent1"
        assert result[1]["agent_id"] == "agent2"
        assert orchestrator.memory.hset.call_count == 2  # Results saved to Redis

    def test_enqueue_fork(self, orchestrator):
        """Test enqueuing fork agents."""
        orchestrator.queue = []
        orchestrator.enqueue_fork(["agent1", "agent2"], "group1")

        assert orchestrator.queue == ["agent1", "agent2"]

    @pytest.mark.asyncio
    async def test_router_node_missing_decision_key(self, orchestrator, sample_input_data):
        """Test router node with missing decision key."""
        agent = MockAgent("routernode", ["next_agent"])
        agent.params = {}  # Missing decision_key

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        with pytest.raises(ValueError, match="Router agent must have 'decision_key'"):
            await orchestrator._execute_single_agent(
                "router1",
                agent,
                "routernode",
                payload,
                sample_input_data,
                queue,
                logs,
            )

    @pytest.mark.asyncio
    async def test_fork_node_empty_targets(self, orchestrator, sample_input_data):
        """Test fork node with empty targets."""
        agent = MockAgent("forknode", {"status": "forked"})
        agent.config = {"targets": []}  # Empty targets
        agent.run = AsyncMock(return_value={"status": "forked"})

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        with pytest.raises(ValueError, match="ForkNode .* requires non-empty 'targets' list"):
            await orchestrator._execute_single_agent(
                "fork1",
                agent,
                "forknode",
                payload,
                sample_input_data,
                queue,
                logs,
            )

    @pytest.mark.asyncio
    async def test_join_node_missing_group_id(self, orchestrator, sample_input_data):
        """Test join node with missing group ID."""
        agent = MockAgent("joinnode", {"status": "done"})
        agent.group_id = None  # Missing group_id
        orchestrator.memory.hget.return_value = None

        payload = {"input": sample_input_data, "previous_outputs": {}}
        queue = []
        logs = []

        with pytest.raises(ValueError, match="JoinNode .* missing required group_id"):
            await orchestrator._execute_single_agent(
                "join1",
                agent,
                "joinnode",
                payload,
                sample_input_data,
                queue,
                logs,
            )

    @pytest.mark.asyncio
    async def test_memory_logging_error_handling(self, orchestrator, sample_input_data):
        """Test error handling during memory logging."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        # Make memory.log raise an exception
        orchestrator.memory.log.side_effect = Exception("Memory error")

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        # Should continue despite memory error
        assert len(result) == 1
        assert len(orchestrator.error_telemetry["errors"]) == 1
        assert orchestrator.error_telemetry["errors"][0]["type"] == "memory_logging"

    @pytest.mark.asyncio
    async def test_metrics_extraction_error_handling(self, orchestrator, sample_input_data):
        """Test error handling during metrics extraction."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        # Make _extract_llm_metrics raise an exception
        orchestrator._extract_llm_metrics = Mock(side_effect=Exception("Metrics error"))

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        # Should continue despite metrics error
        assert len(result) == 1
        assert len(orchestrator.error_telemetry["errors"]) == 1
        assert orchestrator.error_telemetry["errors"][0]["type"] == "metrics_extraction"

    @pytest.mark.asyncio
    async def test_step_execution_error_handling(self, orchestrator, sample_input_data):
        """Test error handling at step level."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent, "agent2": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1", "agent2"]}

        # Make _execute_single_agent raise an exception for first agent
        original_execute = orchestrator._execute_single_agent
        call_count = 0

        async def failing_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Step error")
            return await original_execute(*args, **kwargs)

        orchestrator._execute_single_agent = failing_execute

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        # Should continue to second agent despite first agent error
        assert len(result) == 2  # Both agents succeeded (first after retry)
        assert len(orchestrator.error_telemetry["errors"]) == 1
        assert orchestrator.error_telemetry["errors"][0]["type"] == "agent_execution"

    @pytest.mark.asyncio
    async def test_memory_close_error_handling(self, orchestrator, sample_input_data):
        """Test error handling during memory close."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        # Make memory.close raise an exception
        orchestrator.memory.close.side_effect = Exception("Close error")

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            # Should not raise exception despite close error
            result = await orchestrator._run_with_comprehensive_error_handling(
                sample_input_data,
                [],
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_log_directory_creation(self, orchestrator, sample_input_data):
        """Test log directory creation."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "custom_logs")
            with patch.dict(os.environ, {"ORKA_LOG_DIR": log_dir}):
                await orchestrator._run_with_comprehensive_error_handling(sample_input_data, [])

            assert os.path.exists(log_dir)

    @pytest.mark.asyncio
    async def test_meta_report_generation(self, orchestrator, sample_input_data):
        """Test meta report generation and storage."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.orchestrator_cfg = {"agents": ["agent1"]}

        with patch.dict(os.environ, {"ORKA_LOG_DIR": tempfile.gettempdir()}):
            await orchestrator._run_with_comprehensive_error_handling(sample_input_data, [])

        # Check that meta report was added to memory
        meta_report_entry = orchestrator.memory.memory[-1]
        assert meta_report_entry["agent_id"] == "meta_report"
        assert meta_report_entry["event_type"] == "MetaReport"
        assert "meta_report" in meta_report_entry["payload"]

    @pytest.mark.asyncio
    async def test_fork_sequence_handling(self, orchestrator, sample_input_data):
        """Test fork sequence handling with next agent."""
        agent = MockAgent("agent", {"output": "test"})
        orchestrator.agents = {"agent1": agent}
        orchestrator.fork_manager.next_in_sequence.return_value = "agent2"

        payload = {"input": {"fork_group": "test_group"}, "previous_outputs": {}}
        queue = []
        logs = []

        # Mock enqueue_fork
        orchestrator.enqueue_fork = Mock()

        await orchestrator._execute_single_agent(
            "agent1",
            agent,
            "agent",
            payload,
            sample_input_data,
            queue,
            logs,
        )

        assert orchestrator.fork_manager.mark_agent_done.called
        orchestrator.enqueue_fork.assert_called_with(["agent2"], {"fork_group": "test_group"})
