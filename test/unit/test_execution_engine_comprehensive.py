"""
Comprehensive unit tests for the execution_engine.py module.
Tests the ExecutionEngine class and all its complex orchestration capabilities.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the execution engine to ensure it's loaded for coverage
from orka.orchestrator.execution_engine import ExecutionEngine


class TestExecutionEngine:
    """Test suite for the ExecutionEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock execution engine with required attributes
        self.engine = ExecutionEngine()

        # Mock required attributes
        self.engine.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        self.engine.agents = {
            "agent1": Mock(type="openai", run=Mock(return_value={"result": "test1"})),
            "agent2": Mock(type="completion", run=Mock(return_value={"result": "test2"})),
        }
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

        # Mock helper methods
        self.engine.build_previous_outputs = Mock(return_value={})
        self.engine._record_error = Mock()
        self.engine._save_error_report = Mock()
        self.engine._generate_meta_report = Mock(
            return_value={
                "total_duration": 1.234,
                "total_llm_calls": 2,
                "total_tokens": 150,
                "total_cost_usd": 0.001,
                "avg_latency_ms": 250.5,
            },
        )
        self.engine.normalize_bool = Mock(return_value=True)
        self.engine._add_prompt_to_payload = Mock()
        self.engine._render_agent_prompt = Mock()

    @pytest.mark.asyncio
    async def test_run_success(self):
        """Test successful run execution."""
        input_data = {"test": "data"}
        expected_logs = [{"agent_id": "agent1", "result": "test1"}]

        with patch.object(
            self.engine,
            "_run_with_comprehensive_error_handling",
            new_callable=AsyncMock,
            return_value=expected_logs,
        ) as mock_run:
            result = await self.engine.run(input_data)

            mock_run.assert_called_once_with(input_data, [])
            assert result == expected_logs

    @pytest.mark.asyncio
    async def test_run_with_fatal_error(self):
        """Test run with fatal error handling."""
        input_data = {"test": "data"}
        test_error = Exception("Fatal execution error")

        with patch.object(
            self.engine,
            "_run_with_comprehensive_error_handling",
            new_callable=AsyncMock,
            side_effect=test_error,
        ):
            with pytest.raises(Exception, match="Fatal execution error"):
                await self.engine.run(input_data)

            # Verify error handling was called
            self.engine._record_error.assert_called_once()
            self.engine._save_error_report.assert_called_once()
            assert self.engine.error_telemetry["execution_status"] == "failed"
            assert len(self.engine.error_telemetry["critical_failures"]) == 1

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_success(self):
        """Test successful comprehensive error handling execution."""
        input_data = {"test": "data"}
        logs = []

        # Set up orchestrator config with actual agents
        self.engine.orchestrator_cfg = {"agents": ["agent1"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="TestAgent"),
                run=Mock(return_value={"result": "success"}),
            ),
        }

        with patch.object(
            self.engine,
            "_execute_single_agent",
            new_callable=AsyncMock,
            return_value={"result": "success"},
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch(
                    "orka.orchestrator.execution_engine.os.path.join",
                    return_value="test_log.json",
                ):
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

            assert isinstance(result, list)
            self.engine.memory.save_to_file.assert_called_once()
            self.engine.memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_memory_close_error(self):
        """Test comprehensive error handling when memory close fails."""
        input_data = {"test": "data"}
        logs = []

        # Mock memory close to raise an exception
        self.engine.memory.close.side_effect = Exception("Close failed")

        with patch.object(self.engine, "_execute_single_agent", new_callable=AsyncMock):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    with patch("builtins.print") as mock_print:
                        result = await self.engine._run_with_comprehensive_error_handling(
                            input_data,
                            logs,
                        )

                        # Should continue execution despite close error
                        assert isinstance(result, list)
                        # Should print warning about close failure
                        mock_print.assert_any_call(
                            "Warning: Failed to cleanly close memory backend: Close failed",
                        )

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_full_execution(self):
        """Test full execution loop with multiple agents."""
        input_data = {"test": "data"}
        logs = []

        # Set up orchestrator config with multiple agents
        self.engine.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="Agent1"),
                run=Mock(return_value={"result": "result1"}),
            ),
            "agent2": Mock(
                type="completion",
                __class__=Mock(__name__="Agent2"),
                run=Mock(return_value={"result": "result2"}),
            ),
        }

        # Mock the queue behavior
        self.engine.queue = ["agent1", "agent2"]

        with patch.object(
            self.engine,
            "_execute_single_agent",
            new_callable=AsyncMock,
            side_effect=[
                {"result": "result1"},
                {"result": "result2"},
            ],
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

            assert isinstance(result, list)
            assert len(result) >= 2  # Should have processed both agents

    @pytest.mark.asyncio
    async def test_execute_single_agent_routernode(self):
        """Test executing a router node agent."""
        agent_id = "router1"
        agent = Mock(type="routernode", run=Mock(return_value=["next_agent1", "next_agent2"]))
        agent.params = {
            "decision_key": "classification",
            "routing_map": {"true": "path1", "false": "path2"},
        }

        payload = {
            "input": "test",
            "previous_outputs": {"classification": "positive"},
        }
        queue = ["agent2", "agent3"]
        logs = []

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "routernode",
            payload,
            "test",
            queue,
            logs,
        )

        # Verify router behavior
        agent.run.assert_called_once_with(payload)
        assert queue == ["next_agent1", "next_agent2"]  # Queue should be updated
        assert "next_agents" in result
        self.engine.normalize_bool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_routernode_missing_decision_key(self):
        """Test router node with missing decision_key."""
        agent_id = "router1"
        agent = Mock(type="routernode")
        agent.params = {"routing_map": {"true": "path1"}}  # Missing decision_key

        payload = {"input": "test", "previous_outputs": {}}

        with pytest.raises(ValueError, match="Router agent must have 'decision_key' in params"):
            await self.engine._execute_single_agent(
                agent_id,
                agent,
                "routernode",
                payload,
                "test",
                [],
                [],
            )

    @pytest.mark.asyncio
    async def test_execute_single_agent_forknode(self):
        """Test executing a fork node agent."""
        agent_id = "fork1"
        agent = Mock(type="forknode", run=AsyncMock(return_value={"result": "fork_result"}))
        agent.config = {"targets": [["agent1", "agent2"], ["agent3"]], "mode": "parallel"}

        payload = {"input": "test", "previous_outputs": {}}
        queue = []
        logs = []

        with patch.object(
            self.engine,
            "run_parallel_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await self.engine._execute_single_agent(
                agent_id,
                agent,
                "forknode",
                payload,
                "test",
                queue,
                logs,
            )

        # Verify fork behavior
        agent.run.assert_called_once_with(self.engine, payload)
        assert "fork_targets" in result
        self.engine.fork_manager.create_group.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_forknode_empty_targets(self):
        """Test fork node with empty targets."""
        agent_id = "fork1"
        agent = Mock(type="forknode", run=AsyncMock(return_value={"result": "fork_result"}))
        agent.config = {"targets": []}

        payload = {"input": "test", "previous_outputs": {}}

        with pytest.raises(ValueError, match="ForkNode 'fork1' requires non-empty 'targets' list"):
            await self.engine._execute_single_agent(
                agent_id,
                agent,
                "forknode",
                payload,
                "test",
                [],
                [],
            )

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_waiting(self):
        """Test join node in waiting state."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id="fork_group_123")
        agent.run = Mock(return_value={"status": "waiting", "message": "Waiting for fork group"})

        payload = {"input": "test", "previous_outputs": {}}
        queue = []

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            queue,
            [],
        )

        assert result["status"] == "waiting"
        assert agent_id in queue  # Should be re-queued
        self.engine.memory.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_timeout(self):
        """Test join node with timeout."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id="fork_group_123")
        agent.run = Mock(return_value={"status": "timeout", "message": "Timeout waiting"})

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            [],
            [],
        )

        assert result["status"] == "timeout"
        self.engine.memory.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_done(self):
        """Test join node completion."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id="fork_group_123")
        agent.run = Mock(return_value={"status": "done", "result": "joined_result"})

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            [],
            [],
        )

        assert "result" in result
        self.engine.fork_manager.delete_group.assert_called_once_with("fork_group_123")

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_missing_group_id(self):
        """Test join node with missing group_id."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id=None)
        agent.run = Mock(return_value={"status": "complete"})

        self.engine.memory.hget.return_value = None  # No group mapping

        with pytest.raises(ValueError, match="JoinNode 'join1' missing required group_id"):
            await self.engine._execute_single_agent(
                agent_id,
                agent,
                "joinnode",
                {},
                "test",
                [],
                [],
            )

    @pytest.mark.asyncio
    async def test_execute_single_agent_memory_nodes(self):
        """Test executing memory reader and writer nodes."""
        # Test memory reader node
        agent_id = "memory_reader"
        agent = Mock(
            type="memoryreadernode",
            run=AsyncMock(return_value={"memories": ["mem1", "mem2"]}),
        )

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "memoryreadernode",
            payload,
            "test",
            [],
            [],
        )

        agent.run.assert_called_once_with(payload)
        assert "result" in result

        # Test memory writer node
        agent_id = "memory_writer"
        agent = Mock(type="memorywriternode", run=AsyncMock(return_value={"status": "written"}))

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "memorywriternode",
            payload,
            "test",
            [],
            [],
        )

        agent.run.assert_called_once_with(payload)
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_single_agent_failover_node(self):
        """Test executing failover node."""
        agent_id = "failover1"
        agent = Mock(type="failovernode", run=AsyncMock(return_value={"result": "failover_result"}))

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "failovernode",
            payload,
            "test",
            [],
            [],
        )

        agent.run.assert_called_once_with(payload)
        assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_single_agent_waiting_status(self):
        """Test agent returning waiting status."""
        agent_id = "waiting_agent"
        agent = Mock(
            type="openai",
            run=Mock(return_value={"status": "waiting", "received": "partial_input"}),
        )

        payload = {"input": "test", "previous_outputs": {}}
        queue = []

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "openai",
            payload,
            "test",
            queue,
            [],
        )

        assert result["status"] == "waiting"
        assert agent_id in queue  # Should be re-queued

    @pytest.mark.asyncio
    async def test_execute_single_agent_normal_agent(self):
        """Test executing normal agent."""
        agent_id = "normal_agent"
        agent = Mock(type="openai", run=Mock(return_value={"result": "normal_result"}))

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "openai",
            payload,
            "test",
            [],
            [],
        )

        agent.run.assert_called_once_with(payload)
        assert "result" in result
        self.engine._render_agent_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_async_needs_orchestrator(self):
        """Test running agent that needs orchestrator."""
        agent_id = "orchestrator_agent"
        agent = Mock()
        agent.run = Mock(return_value={"result": "orchestrator_result"})

        # Add the agent to the engine's agents dict
        self.engine.agents[agent_id] = agent

        # Mock signature to indicate it needs orchestrator (more than 1 parameter)
        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"self": None, "orchestrator": None, "payload": None}

            result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "orchestrator_result"})
        agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_async_async_agent(self):
        """Test running async agent."""
        agent_id = "async_agent"
        agent = Mock()
        agent.run = AsyncMock(return_value={"result": "async_result"})

        # Add the agent to the engine's agents dict
        self.engine.agents[agent_id] = agent

        # Mock signature and coroutine function
        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"self": None, "payload": None}

            with patch(
                "orka.orchestrator.execution_engine.inspect.iscoroutinefunction",
                return_value=True,
            ):
                result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "async_result"})
        agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_agent_async_sync_agent(self):
        """Test running synchronous agent in thread pool."""
        agent_id = "sync_agent"
        agent = Mock()
        agent.run = Mock(return_value={"result": "sync_result"})

        # Add the agent to the engine's agents dict
        self.engine.agents[agent_id] = agent

        # Mock signature and synchronous function
        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"self": None, "payload": None}

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

                        result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "sync_result"})

    @pytest.mark.asyncio
    async def test_run_branch_async(self):
        """Test running a branch of agents asynchronously."""
        branch_agents = ["agent1", "agent2"]
        input_data = {"test": "data"}
        previous_outputs = {"context": "test"}

        with patch.object(
            self.engine,
            "_run_agent_async",
            new_callable=AsyncMock,
            side_effect=[
                ("agent1", {"result": "result1"}),
                ("agent2", {"result": "result2"}),
            ],
        ):
            result = await self.engine._run_branch_async(
                branch_agents,
                input_data,
                previous_outputs,
            )

        assert result == {"agent1": {"result": "result1"}, "agent2": {"result": "result2"}}

    @pytest.mark.asyncio
    async def test_run_parallel_agents_comprehensive(self):
        """Test comprehensive parallel agent execution."""
        agent_ids = ["agent1", "agent2"]
        fork_group_id = "fork_node_123_456"
        input_data = {"test": "data"}
        previous_outputs = {"context": "test"}

        # Set up fork node
        self.engine.agents["fork_node_123"] = Mock(
            type="forknode",
            targets=[["agent1"], ["agent2"]],
        )

        with patch.object(
            self.engine,
            "_run_branch_async",
            new_callable=AsyncMock,
            side_effect=[
                {"agent1": {"result": "result1"}},
                {"agent2": {"result": "result2"}},
            ],
        ):
            with patch.object(
                self.engine,
                "_ensure_complete_context",
                return_value=previous_outputs,
            ):
                with patch("orka.orchestrator.execution_engine.json.dumps", return_value="{}"):
                    result = await self.engine.run_parallel_agents(
                        agent_ids,
                        fork_group_id,
                        input_data,
                        previous_outputs,
                    )

        assert isinstance(result, list)
        assert len(result) == 2
        # Verify Redis operations
        assert self.engine.memory.hset.call_count == 2

    @pytest.mark.asyncio
    async def test_run_parallel_agents_with_coroutine_result(self):
        """Test parallel agents with coroutine results."""
        agent_ids = ["agent1"]
        fork_group_id = "fork_node_123_456"
        input_data = {"test": "data"}
        previous_outputs = {"context": "test"}

        # Set up fork node
        self.engine.agents["fork_node_123"] = Mock(
            type="forknode",
            targets=[["agent1"]],
        )

        # Create a coroutine result
        async def async_result():
            return {"result": "async_result"}

        with patch.object(
            self.engine,
            "_run_branch_async",
            new_callable=AsyncMock,
            return_value={"agent1": async_result()},
        ):
            with patch.object(
                self.engine,
                "_ensure_complete_context",
                return_value=previous_outputs,
            ):
                with patch("orka.orchestrator.execution_engine.json.dumps", return_value="{}"):
                    result = await self.engine.run_parallel_agents(
                        agent_ids,
                        fork_group_id,
                        input_data,
                        previous_outputs,
                    )

        assert isinstance(result, list)
        assert len(result) == 1

    def test_ensure_complete_context_direct_memories(self):
        """Test context enhancement with direct memories."""
        previous_outputs = {
            "agent1": {"memories": ["mem1", "mem2"], "other": "data"},
            "agent2": {"result": "simple_result"},
        }

        result = self.engine._ensure_complete_context(previous_outputs)

        assert "agent1" in result
        assert "memories" in result["agent1"]
        assert result["agent1"]["memories"] == ["mem1", "mem2"]

    def test_ensure_complete_context_nested_memories(self):
        """Test context enhancement with nested memories."""
        previous_outputs = {
            "agent1": {
                "result": {"memories": ["mem1", "mem2"], "response": "test_response"},
                "other": "data",
            },
        }

        result = self.engine._ensure_complete_context(previous_outputs)

        assert "agent1" in result
        assert "memories" in result["agent1"]
        assert result["agent1"]["memories"] == ["mem1", "mem2"]
        assert "response" in result["agent1"]
        assert result["agent1"]["response"] == "test_response"

    def test_ensure_complete_context_nested_response(self):
        """Test context enhancement with nested response."""
        previous_outputs = {
            "agent1": {
                "result": {"response": "test_response", "other": "data"},
                "original": "value",
            },
        }

        result = self.engine._ensure_complete_context(previous_outputs)

        assert "agent1" in result
        assert "response" in result["agent1"]
        assert result["agent1"]["response"] == "test_response"
        assert result["agent1"]["original"] == "value"

    def test_ensure_complete_context_non_dict_result(self):
        """Test context enhancement with non-dict results."""
        previous_outputs = {
            "agent1": "simple_string",
            "agent2": 42,
            "agent3": ["list", "data"],
        }

        result = self.engine._ensure_complete_context(previous_outputs)

        assert result["agent1"] == "simple_string"
        assert result["agent2"] == 42
        assert result["agent3"] == ["list", "data"]

    def test_enqueue_fork(self):
        """Test enqueue fork functionality."""
        agent_ids = ["agent1", "agent2", "agent3"]
        fork_group_id = "fork_123"

        self.engine.enqueue_fork(agent_ids, fork_group_id)

        assert self.engine.queue == ["agent1", "agent2", "agent3"]

    @pytest.mark.asyncio
    async def test_comprehensive_error_handling_with_agent_step_error(self):
        """Test comprehensive error handling when an agent step fails."""
        input_data = {"test": "data"}
        logs = []

        # Mock agent execution to raise an exception
        with patch.object(
            self.engine,
            "_execute_single_agent",
            new_callable=AsyncMock,
            side_effect=Exception("Agent step failed"),
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

                    # Should continue execution despite step error
                    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execution_with_retry_logic(self):
        """Test execution with retry logic for failed agents."""
        input_data = {"test": "data"}
        logs = []

        # Create a more detailed mock for testing retry logic
        self.engine.orchestrator_cfg = {"agents": ["failing_agent"]}
        self.engine.agents = {
            "failing_agent": Mock(
                type="openai",
                __class__=Mock(__name__="TestAgent"),
            ),
        }

        # Mock execute_single_agent to fail then succeed
        call_count = 0

        async def mock_execute_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {"result": "success_after_retry"}

        with patch.object(
            self.engine,
            "_execute_single_agent",
            new_callable=AsyncMock,
            side_effect=mock_execute_with_retry,
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

                    # Should succeed after retry
                    assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_single_agent_with_fork_group_handling(self):
        """Test agent execution with fork group handling."""
        agent_id = "fork_agent"
        agent = Mock(type="openai", run=Mock(return_value={"result": "fork_result"}))

        payload = {
            "input": {"fork_group": "fork_123"},
            "previous_outputs": {},
        }

        # Mock fork manager methods
        self.engine.fork_manager.next_in_sequence.return_value = "next_agent"

        with patch("builtins.print") as mock_print:
            result = await self.engine._execute_single_agent(
                agent_id,
                agent,
                "openai",
                payload,
                "test",
                [],
                [],
            )

        # Verify fork group handling
        self.engine.fork_manager.mark_agent_done.assert_called_once_with(
            {"fork_group": "fork_123"},
            agent_id,
        )
        self.engine.fork_manager.next_in_sequence.assert_called_once_with(
            {"fork_group": "fork_123"},
            agent_id,
        )
        mock_print.assert_called()  # Should print next agent message

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_queue_processing(self):
        """Test comprehensive error handling with queue processing."""
        input_data = {"test": "data"}
        logs = []

        # Set up orchestrator config
        self.engine.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="Agent1"),
                run=Mock(return_value={"result": "result1"}),
            ),
            "agent2": Mock(
                type="completion",
                __class__=Mock(__name__="Agent2"),
                run=Mock(return_value={"result": "result2"}),
            ),
        }

        # Mock queue processing with different scenarios
        queue_states = [
            ["agent1", "agent2"],  # Initial queue
            ["agent2"],  # After processing agent1
            [],  # After processing agent2
        ]

        call_count = 0

        def mock_queue_side_effect():
            nonlocal call_count
            if call_count < len(queue_states):
                self.engine.queue = queue_states[call_count].copy()
                call_count += 1
            else:
                self.engine.queue = []

        with patch.object(
            self.engine,
            "_execute_single_agent",
            new_callable=AsyncMock,
            side_effect=lambda *args, **kwargs: (
                mock_queue_side_effect(),
                {"result": f"result_{args[0]}"},
            )[1],
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_run_agent_async_with_awaitable_result(self):
        """Test running agent with awaitable result."""
        agent_id = "awaitable_agent"
        agent = Mock()

        # Create a coroutine result
        async def async_result():
            return {"result": "awaitable_result"}

        agent.run = Mock(return_value=async_result())

        # Add the agent to the engine's agents dict
        self.engine.agents[agent_id] = agent

        # Mock signature
        with patch("orka.orchestrator.execution_engine.inspect.signature") as mock_sig:
            mock_sig.return_value.parameters = {"self": None, "payload": None}

            with patch(
                "orka.orchestrator.execution_engine.inspect.iscoroutinefunction",
                return_value=False,
            ):
                with patch(
                    "orka.orchestrator.execution_engine.asyncio.iscoroutine",
                    return_value=True,
                ):
                    result = await self.engine._run_agent_async(agent_id, {"test": "data"}, {})

        assert result == (agent_id, {"result": "awaitable_result"})

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_with_hget_result(self):
        """Test join node with hget returning group ID."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id="original_group")
        agent.run = Mock(return_value={"status": "done", "result": "joined_result"})

        # Mock hget to return a group ID
        self.engine.memory.hget.return_value = b"mapped_group_123"

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            [],
            [],
        )

        assert "result" in result
        assert "fork_group_id" in result
        assert result["fork_group_id"] == "mapped_group_123"

    @pytest.mark.asyncio
    async def test_execute_single_agent_joinnode_with_string_hget_result(self):
        """Test join node with hget returning string group ID."""
        agent_id = "join1"
        agent = Mock(type="joinnode", group_id="original_group")
        agent.run = Mock(return_value={"status": "done", "result": "joined_result"})

        # Mock hget to return a string group ID
        self.engine.memory.hget.return_value = "mapped_group_123"

        payload = {"input": "test", "previous_outputs": {}}

        result = await self.engine._execute_single_agent(
            agent_id,
            agent,
            "joinnode",
            payload,
            "test",
            [],
            [],
        )

        assert "result" in result
        assert "fork_group_id" in result
        assert result["fork_group_id"] == "mapped_group_123"

    @pytest.mark.asyncio
    async def test_execute_single_agent_forknode_with_nested_targets(self):
        """Test fork node with nested branch targets."""
        agent_id = "fork1"
        agent = Mock(type="forknode", run=AsyncMock(return_value={"result": "fork_result"}))
        agent.config = {
            "targets": [["agent1", "agent2"], "agent3", ["agent4"]],
            "mode": "parallel",
        }

        payload = {"input": "test", "previous_outputs": {}}
        queue = []
        logs = []

        with patch.object(
            self.engine,
            "run_parallel_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await self.engine._execute_single_agent(
                agent_id,
                agent,
                "forknode",
                payload,
                "test",
                queue,
                logs,
            )

        # Verify fork behavior with flattened targets
        assert "fork_targets" in result
        # Should flatten nested targets: ["agent1", "agent2", "agent3", "agent4"]
        expected_targets = ["agent1", "agent2", "agent3", "agent4"]
        assert result["fork_targets"] == expected_targets

    @pytest.mark.asyncio
    async def test_run_parallel_agents_with_debug_logging(self):
        """Test parallel agents with debug logging enabled."""
        agent_ids = ["agent1"]
        fork_group_id = "fork_node_123_456"
        input_data = {"test": "data"}
        previous_outputs = {
            "agent1": {
                "memories": ["mem1", "mem2"],
                "result": {"response": "test_response"},
            },
        }

        # Set up fork node
        self.engine.agents["fork_node_123"] = Mock(
            type="forknode",
            targets=[["agent1"]],
        )

        # Enable debug logging
        with patch("orka.orchestrator.execution_engine.logger") as mock_logger:
            mock_logger.isEnabledFor.return_value = True

            with patch.object(
                self.engine,
                "_run_branch_async",
                new_callable=AsyncMock,
                return_value={"agent1": {"result": "result1"}},
            ):
                with patch.object(
                    self.engine,
                    "_ensure_complete_context",
                    return_value=previous_outputs,
                ):
                    with patch("orka.orchestrator.execution_engine.json.dumps", return_value="{}"):
                        result = await self.engine.run_parallel_agents(
                            agent_ids,
                            fork_group_id,
                            input_data,
                            previous_outputs,
                        )

        # Verify debug logging was called
        mock_logger.debug.assert_called()
        assert isinstance(result, list)
