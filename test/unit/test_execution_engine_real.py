"""
Real execution tests for the execution_engine.py module.
Tests that exercise actual code paths rather than mocking everything.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine


class TestExecutionEngineReal:
    """Test suite for real execution engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ExecutionEngine()

        # Set up minimal required attributes
        self.engine.orchestrator_cfg = {"agents": []}
        self.engine.agents = {}
        self.engine.step_index = 0
        self.engine.run_id = "test_run_123"
        self.engine.queue = []
        self.engine.error_telemetry = {
            "execution_status": "running",
            "critical_failures": [],
        }

        # Mock memory system
        self.engine.memory = Mock()
        self.engine.memory.memory = []
        self.engine.memory.log = Mock()
        self.engine.memory.save_to_file = Mock()
        self.engine.memory.close = Mock()
        self.engine.memory.hget = Mock(return_value=None)
        self.engine.memory.hset = Mock()

        # Mock fork manager
        self.engine.fork_manager = Mock()
        self.engine.fork_manager.generate_group_id = Mock(return_value="fork_123")
        self.engine.fork_manager.create_group = Mock()
        self.engine.fork_manager.delete_group = Mock()
        self.engine.fork_manager.mark_agent_done = Mock()
        self.engine.fork_manager.next_in_sequence = Mock(return_value=None)

        # Mock helper methods that we don't want to test
        self.engine.build_previous_outputs = Mock(return_value={})
        self.engine._record_error = Mock()
        self.engine._save_error_report = Mock()
        self.engine._generate_meta_report = Mock(
            return_value={
                "total_duration": 1.0,
                "total_llm_calls": 1,
                "total_tokens": 100,
                "total_cost_usd": 0.01,
                "avg_latency_ms": 100.0,
            },
        )
        self.engine.normalize_bool = Mock(return_value=True)
        self.engine._add_prompt_to_payload = Mock()
        self.engine._render_agent_prompt = Mock()

    def test_ensure_complete_context_real(self):
        """Test the real _ensure_complete_context method."""
        previous_outputs = {
            "agent1": {"memories": ["mem1", "mem2"], "other": "data"},
            "agent2": {"result": {"memories": ["mem3"], "response": "test"}},
            "agent3": "simple_string",
        }

        # Call the real method
        result = self.engine._ensure_complete_context(previous_outputs)

        # Verify it processes the data correctly
        assert "agent1" in result
        assert result["agent1"]["memories"] == ["mem1", "mem2"]
        assert result["agent1"]["other"] == "data"

        assert "agent2" in result
        assert result["agent2"]["memories"] == ["mem3"]
        assert result["agent2"]["response"] == "test"

        assert result["agent3"] == "simple_string"

    def test_enqueue_fork_real(self):
        """Test the real enqueue_fork method."""
        agent_ids = ["agent1", "agent2", "agent3"]
        fork_group_id = "fork_123"

        # Call the real method
        self.engine.enqueue_fork(agent_ids, fork_group_id)

        # Verify it updates the queue
        assert self.engine.queue == ["agent1", "agent2", "agent3"]

    @pytest.mark.asyncio
    async def test_run_agent_async_real_sync_agent(self):
        """Test _run_agent_async with a real synchronous agent."""
        # Create a real agent
        agent = Mock()
        agent.run = Mock(return_value={"result": "sync_result"})

        agent_id = "sync_agent"
        self.engine.agents[agent_id] = agent

        # Mock the threading components
        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"payload": None}

            with patch(
                "orka.orchestrator.execution_engine.inspect.iscoroutinefunction",
                return_value=False,
            ):
                with patch(
                    "orka.orchestrator.execution_engine.ThreadPoolExecutor",
                ) as mock_executor:
                    mock_executor.return_value.__enter__.return_value = Mock()

                    with patch("asyncio.get_event_loop") as mock_loop:
                        mock_loop.return_value.run_in_executor = AsyncMock(
                            return_value={"result": "sync_result"},
                        )

                        # Call the real method
                        result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "sync_result"})

    @pytest.mark.asyncio
    async def test_run_agent_async_real_async_agent(self):
        """Test _run_agent_async with a real async agent."""
        # Create a real async agent
        agent = Mock()
        agent.run = AsyncMock(return_value={"result": "async_result"})

        agent_id = "async_agent"
        self.engine.agents[agent_id] = agent

        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"payload": None}

            with patch(
                "orka.orchestrator.execution_engine.inspect.iscoroutinefunction",
                return_value=True,
            ):
                # Call the real method
                result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "async_result"})
        agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_branch_async_real(self):
        """Test _run_branch_async with real agents."""
        # Create real agents
        agent1 = Mock()
        agent1.run = Mock(return_value={"result": "result1"})
        agent2 = Mock()
        agent2.run = Mock(return_value={"result": "result2"})

        self.engine.agents["agent1"] = agent1
        self.engine.agents["agent2"] = agent2

        branch_agents = ["agent1", "agent2"]
        input_data = {"test": "data"}
        previous_outputs = {"context": "test"}

        # Mock the async execution
        with patch.object(self.engine, "_run_agent_async") as mock_run:
            mock_run.side_effect = [
                ("agent1", {"result": "result1"}),
                ("agent2", {"result": "result2"}),
            ]

            # Call the real method
            result = await self.engine._run_branch_async(
                branch_agents,
                input_data,
                previous_outputs,
            )

        assert result == {"agent1": {"result": "result1"}, "agent2": {"result": "result2"}}
        assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_router(self):
        """Test _execute_single_agent with real router node."""
        # Create a real router agent
        agent = Mock()
        agent.run = Mock(return_value=["next_agent1", "next_agent2"])
        agent.params = {
            "decision_key": "classification",
            "routing_map": {"true": "path1", "false": "path2"},
        }

        agent_id = "router1"
        payload = {
            "input": "test",
            "previous_outputs": {"classification": "positive"},
        }
        queue = ["agent2", "agent3"]
        logs = []

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "routernode",
            payload,
            "test",
            queue,
            logs,
        )

        # Verify real behavior
        agent.run.assert_called_once_with(payload)
        assert queue == ["next_agent1", "next_agent2"]  # Queue should be updated
        assert "next_agents" in result
        self.engine.normalize_bool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_normal_agent(self):
        """Test _execute_single_agent with real normal agent."""
        # Create a real normal agent
        agent = Mock()
        agent.run = Mock(return_value={"result": "normal_result"})

        agent_id = "normal_agent"
        payload = {"input": "test", "previous_outputs": {}}

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "openai",
            payload,
            "test",
            [],
            [],
        )

        # Verify real behavior
        agent.run.assert_called_once_with(payload)
        assert "result" in result
        assert result["result"] == {"result": "normal_result"}
        self.engine._render_agent_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_memory_reader(self):
        """Test _execute_single_agent with real memory reader node."""
        # Create a real memory reader agent
        agent = Mock()
        agent.run = AsyncMock(return_value={"memories": ["mem1", "mem2"]})

        agent_id = "memory_reader"
        payload = {"input": "test", "previous_outputs": {}}

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "memoryreadernode",
            payload,
            "test",
            [],
            [],
        )

        # Verify real behavior
        agent.run.assert_called_once_with(payload)
        assert "result" in result
        assert result["result"] == {"memories": ["mem1", "mem2"]}

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_waiting_agent(self):
        """Test _execute_single_agent with agent returning waiting status."""
        # Create a real waiting agent
        agent = Mock()
        agent.run = Mock(return_value={"status": "waiting", "received": "partial_input"})

        agent_id = "waiting_agent"
        payload = {"input": "test", "previous_outputs": {}}
        queue = []

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "openai",
            payload,
            "test",
            queue,
            [],
        )

        # Verify real behavior
        agent.run.assert_called_once_with(payload)
        assert result["status"] == "waiting"
        assert agent_id in queue  # Should be re-queued

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_join_node_waiting(self):
        """Test _execute_single_agent with join node in waiting state."""
        # Create a real join node
        agent = Mock()
        agent.run = Mock(return_value={"status": "waiting", "message": "Waiting for fork group"})
        agent.group_id = "fork_group_123"

        agent_id = "join1"
        payload = {"input": "test", "previous_outputs": {}}
        queue = []

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            queue,
            [],
        )

        # Verify real behavior
        agent.run.assert_called_once()
        assert result["status"] == "waiting"
        assert agent_id in queue  # Should be re-queued
        self.engine.memory.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_real_join_node_done(self):
        """Test _execute_single_agent with join node completion."""
        # Create a real join node
        agent = Mock()
        agent.run = Mock(return_value={"status": "done", "result": "joined_result"})
        agent.group_id = "fork_group_123"

        agent_id = "join1"
        payload = {"input": "test", "previous_outputs": {}}

        # Call the real method
        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            [],
            [],
        )

        # Verify real behavior
        agent.run.assert_called_once()
        assert "result" in result
        self.engine.fork_manager.delete_group.assert_called_once_with("fork_group_123")

    @pytest.mark.asyncio
    async def test_run_parallel_agents_real(self):
        """Test run_parallel_agents with real fork node structure."""
        agent_ids = ["agent1", "agent2"]
        fork_group_id = "fork_node_123_456"
        input_data = {"test": "data"}
        previous_outputs = {"context": "test"}

        # Create real fork node
        fork_node = Mock()
        fork_node.targets = [["agent1"], ["agent2"]]
        self.engine.agents["fork_node_123"] = fork_node

        # Create real agents
        agent1 = Mock()
        agent1.run = Mock(return_value={"result": "result1"})
        agent2 = Mock()
        agent2.run = Mock(return_value={"result": "result2"})

        self.engine.agents["agent1"] = agent1
        self.engine.agents["agent2"] = agent2

        # Mock the branch execution
        with patch.object(self.engine, "_run_branch_async") as mock_branch:
            mock_branch.side_effect = [
                {"agent1": {"result": "result1"}},
                {"agent2": {"result": "result2"}},
            ]

            with patch("orka.orchestrator.execution_engine.json.dumps", return_value="{}"):
                # Call the real method
                result = await self.engine.run_parallel_agents(
                    agent_ids,
                    fork_group_id,
                    input_data,
                    previous_outputs,
                )

        # Verify real behavior
        assert isinstance(result, list)
        assert len(result) == 2
        assert self.engine.memory.hset.call_count == 2

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_real_simple(self):
        """Test _run_with_comprehensive_error_handling with real simple execution."""
        input_data = {"test": "data"}
        logs = []

        # Set up real orchestrator config
        self.engine.orchestrator_cfg = {"agents": ["agent1"]}

        # Create real agent
        agent = Mock()
        agent.run = Mock(return_value={"result": "success"})
        agent.__class__ = Mock(__name__="TestAgent")
        self.engine.agents["agent1"] = agent

        # Mock file operations
        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch(
                "orka.orchestrator.execution_engine.os.path.join",
                return_value="test_log.json",
            ):
                # Call the real method
                result = await self.engine._run_with_comprehensive_error_handling(input_data, logs)

        # Verify real behavior
        assert isinstance(result, list)
        self.engine.memory.save_to_file.assert_called_once()
        self.engine.memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_real_success(self):
        """Test the real run method with successful execution."""
        input_data = {"test": "data"}

        # Mock the comprehensive error handling
        with patch.object(self.engine, "_run_with_comprehensive_error_handling") as mock_run:
            mock_run.return_value = [{"agent_id": "agent1", "result": "success"}]

            # Call the real method
            result = await self.engine.run(input_data)

        # Verify real behavior
        mock_run.assert_called_once_with(input_data, [])
        assert result == [{"agent_id": "agent1", "result": "success"}]

    @pytest.mark.asyncio
    async def test_run_real_with_error(self):
        """Test the real run method with error handling."""
        input_data = {"test": "data"}
        test_error = Exception("Test error")

        # Mock the comprehensive error handling to raise an error
        with patch.object(self.engine, "_run_with_comprehensive_error_handling") as mock_run:
            mock_run.side_effect = test_error

            # Call the real method and expect exception
            with pytest.raises(Exception, match="Test error"):
                await self.engine.run(input_data)

        # Verify error handling was called
        self.engine._record_error.assert_called_once()
        self.engine._save_error_report.assert_called_once()
        assert self.engine.error_telemetry["execution_status"] == "failed"
        assert len(self.engine.error_telemetry["critical_failures"]) == 1
