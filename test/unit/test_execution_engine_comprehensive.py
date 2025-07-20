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

            # The actual implementation calls with input_data, logs, return_logs
            mock_run.assert_called_once_with(input_data, [], False)
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
            # Note: _save_error_report is not called in the run method, only _record_error

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

        self.engine.orchestrator_cfg = {"agents": ["agent1"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="TestAgent"),
                run=AsyncMock(return_value={"result": "success"}),
            ),
        }

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch(
                "orka.orchestrator.execution_engine.os.path.join",
                return_value="test_log.json",
            ):
                result = await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                    return_logs=True,  # Request logs to be returned
                )

        assert isinstance(result, list)
        self.engine.agents["agent1"].run.assert_called_once()
        self.engine.memory.save_to_file.assert_called_once()
        self.engine.memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_memory_close_error(self):
        """Test comprehensive error handling when memory close fails."""
        input_data = {"test": "data"}
        logs = []

        # Mock memory close to raise an exception
        self.engine.memory.close.side_effect = Exception("Close failed")

        self.engine.orchestrator_cfg = {"agents": ["agent1"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="TestAgent"),
                run=AsyncMock(return_value={"result": "success"}),
            ),
        }

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                with patch("builtins.print") as mock_print:
                    result = await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                        return_logs=True,  # Request logs to be returned
                    )

                    # Should continue execution despite close error
                    assert isinstance(result, list)
                    # Should print warning about close failure
                    mock_print.assert_any_call(
                        "Warning: Failed to cleanly close memory backend: Close failed",
                    )
        self.engine.agents["agent1"].run.assert_called_once()

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

        # Set up orchestrator config with multiple agents
        self.engine.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        self.engine.agents = {
            "agent1": Mock(
                type="openai",
                __class__=Mock(__name__="Agent1"),
                run=AsyncMock(return_value={"result": "result1"}),
            ),
            "agent2": Mock(
                type="completion",
                __class__=Mock(__name__="Agent2"),
                run=AsyncMock(return_value={"result": "result2"}),
            ),
        }

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                result = await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                    return_logs=True,  # Request logs to be returned
                )

        assert isinstance(result, list)
        assert len(result) >= 2  # Should have processed both agents
        self.engine.agents["agent1"].run.assert_called_once()
        self.engine.agents["agent2"].run.assert_called_once()

    @pytest.mark.asyncio
    async def test_routernode_execution(self):
        """Test executing a router node agent within the comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        # Mock a router agent and its run method
        router_agent = Mock(
            type="routernode",
            __class__=Mock(__name__="RouterAgent"),
            run=Mock(return_value=["next_agent1", "next_agent2"]),
        )
        router_agent.params = {
            "decision_key": "classification",
            "routing_map": {"true": "path1", "false": "path2"},
        }
        self.engine.agents = {"router1": router_agent}
        self.engine.orchestrator_cfg = {"agents": ["router1"]}

        # Mock the queue to observe changes
        self.engine.queue = ["agent2", "agent3"]

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        # Verify router behavior
        router_agent.run.assert_called_once()
        assert self.engine.queue == ["next_agent1", "next_agent2", "agent2", "agent3"]  # Queue should be updated
        # The result of the router node is handled internally by _run_with_comprehensive_error_handling
        # so we assert on the queue state and agent's run call.
        self.engine.normalize_bool.assert_called_once()

    @pytest.mark.asyncio
    async def test_routernode_missing_decision_key_error(self):
        """Test router node with missing decision_key raises ValueError."""
        input_data = {"test": "data"}
        logs = []

        agent = Mock(type="routernode")
        agent.params = {"routing_map": {"true": "path1"}}  # Missing decision_key
        self.engine.agents = {"router1": agent}
        self.engine.orchestrator_cfg = {"agents": ["router1"]}

        with pytest.raises(ValueError, match="Router agent must have 'decision_key' in params"):
            await self.engine._run_with_comprehensive_error_handling(
                input_data,
                logs,
            )

    @pytest.mark.asyncio
    async def test_forknode_execution(self):
        """Test executing a fork node agent within the comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        fork_agent = Mock(
            type="forknode",
            __class__=Mock(__name__="ForkAgent"),
            run=AsyncMock(return_value={}),  # ForkNode run method doesn't return a result directly
        )
        fork_agent.config = {"targets": [["agent1", "agent2"]], "mode": "parallel"}
        self.engine.agents = {"fork1": fork_agent}
        self.engine.orchestrator_cfg = {"agents": ["fork1"]}

        with patch.object(
            self.engine,
            "run_parallel_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

        # Verify fork behavior
        fork_agent.run.assert_called_once()
        self.engine.fork_manager.create_group.assert_called_once()

    @pytest.mark.asyncio
    async def test_forknode_empty_targets_error(self):
        """Test fork node with empty targets raises ValueError."""
        input_data = {"test": "data"}
        logs = []

        agent = Mock(type="forknode")
        agent.config = {"targets": []}
        self.engine.agents = {"fork1": agent}
        self.engine.orchestrator_cfg = {"agents": ["fork1"]}

        with pytest.raises(ValueError, match="ForkNode 'fork1' requires non-empty 'targets' list"):
            await self.engine._run_with_comprehensive_error_handling(
                input_data,
                logs,
            )

    @pytest.mark.asyncio
    async def test_joinnode_waiting_state(self):
        """Test join node in waiting state within the comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        join_agent = Mock(type="joinnode", group_id="fork_group_123")
        join_agent.run = Mock(return_value={"status": "waiting", "message": "Waiting for fork group"})
        self.engine.agents = {"join1": join_agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        # Mock the queue to observe re-queuing
        self.engine.queue = []

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert join_agent.run.called_once()
        assert "join1" in self.engine.queue  # Should be re-queued
        self.engine.memory.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_joinnode_timeout_state(self):
        """Test join node with timeout within the comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        join_agent = Mock(type="joinnode", group_id="fork_group_123")
        join_agent.run = Mock(return_value={"status": "timeout", "message": "Timeout waiting"})
        self.engine.agents = {"join1": join_agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert join_agent.run.called_once()
        self.engine.memory.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_joinnode_done_state(self):
        """Test join node completion within the comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        join_agent = Mock(type="joinnode", group_id="fork_group_123")
        join_agent.run = Mock(return_value={"status": "done", "result": "joined_result"})
        self.engine.agents = {"join1": join_agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert join_agent.run.called_once()
        self.engine.fork_manager.delete_group.assert_called_once_with("fork_group_123")

    @pytest.mark.asyncio
    async def test_joinnode_missing_group_id_error(self):
        """Test join node with missing group_id raises ValueError."""
        input_data = {"test": "data"}
        logs = []

        agent = Mock(type="joinnode", group_id=None)
        agent.run = Mock(return_value={"status": "complete"})
        self.engine.agents = {"join1": agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        self.engine.memory.hget.return_value = None  # No group mapping

        with pytest.raises(ValueError, match="JoinNode 'join1' missing required group_id"):
            await self.engine._run_with_comprehensive_error_handling(
                input_data,
                logs,
            )

    @pytest.mark.asyncio
    async def test_memory_nodes_execution(self):
        """Test executing memory reader and writer nodes within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        # Test memory reader node
        memory_reader_agent = Mock(
            type="memoryreadernode",
            __class__=Mock(__name__="MemoryReaderAgent"),
            run=AsyncMock(return_value={"memories": ["mem1", "mem2"]}),
        )
        self.engine.agents = {"memory_reader": memory_reader_agent}
        self.engine.orchestrator_cfg = {"agents": ["memory_reader"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        memory_reader_agent.run.assert_called_once()

        # Test memory writer node
        logs = []  # Reset logs for next test
        memory_writer_agent = Mock(
            type="memorywriternode",
            __class__=Mock(__name__="MemoryWriterAgent"),
            run=AsyncMock(return_value={"status": "written"}),
        )
        self.engine.agents = {"memory_writer": memory_writer_agent}
        self.engine.orchestrator_cfg = {"agents": ["memory_writer"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        memory_writer_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_failover_node_execution(self):
        """Test executing failover node within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        failover_agent = Mock(
            type="failovernode",
            __class__=Mock(__name__="FailoverAgent"),
            run=AsyncMock(return_value={"result": "failover_result"}),
        )
        self.engine.agents = {"failover1": failover_agent}
        self.engine.orchestrator_cfg = {"agents": ["failover1"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        failover_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_waiting_status_handling(self):
        """Test agent returning waiting status within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        waiting_agent = Mock(
            type="openai",
            __class__=Mock(__name__="WaitingAgent"),
            run=Mock(return_value={"status": "waiting", "received": "partial_input"}),
        )
        self.engine.agents = {"waiting_agent": waiting_agent}
        self.engine.orchestrator_cfg = {"agents": ["waiting_agent"]}

        # Mock the queue to observe re-queuing
        self.engine.queue = []

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert waiting_agent.run.called_once()
        assert "waiting_agent" in self.engine.queue  # Should be re-queued

    @pytest.mark.asyncio
    async def test_normal_agent_execution(self):
        """Test executing a normal agent within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        normal_agent = Mock(
            type="openai",
            __class__=Mock(__name__="NormalAgent"),
            run=Mock(return_value={"result": "normal_result"}),
        )
        self.engine.agents = {"normal_agent": normal_agent}
        self.engine.orchestrator_cfg = {"agents": ["normal_agent"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        normal_agent.run.assert_called_once()
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
        failing_agent = Mock(
            type="openai",
            __class__=Mock(__name__="FailingAgent"),
            run=AsyncMock(side_effect=Exception("Agent step failed")),
        )
        self.engine.agents = {"failing_agent": failing_agent}
        self.engine.orchestrator_cfg = {"agents": ["failing_agent"]}

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                result = await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

                # Should continue execution despite step error
                assert isinstance(result, list)
        failing_agent.run.assert_called_once()

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

        @pytest.mark.asyncio
    async def test_execution_with_retry_logic(self):
        """Test execution with retry logic for failed agents."""
        input_data = {"test": "data"}
        logs = []

        # Create a more detailed mock for testing retry logic
        self.engine.orchestrator_cfg = {"agents": ["failing_agent"]}
        failing_agent_mock = Mock(
            type="openai",
            __class__=Mock(__name__="TestAgent"),
        )
        self.engine.agents = {"failing_agent": failing_agent_mock}

        # Mock the agent's run method to fail then succeed
        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return {"result": "success_after_retry"}

        failing_agent_mock.run = AsyncMock(side_effect=mock_run_side_effect)

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                result = await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

                # Should succeed after retry
                assert isinstance(result, list)
        assert failing_agent_mock.run.call_count == 2  # One failure, one success

    @pytest.mark.asyncio
    async def test_agent_with_fork_group_handling(self):
        """Test agent execution with fork group handling within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        fork_agent = Mock(
            type="openai",
            __class__=Mock(__name__="ForkAgent"),
            run=Mock(return_value={"result": "fork_result"}),
        )
        self.engine.agents = {"fork_agent": fork_agent}
        self.engine.orchestrator_cfg = {"agents": ["fork_agent"]}

        # Mock fork manager methods
        self.engine.fork_manager.next_in_sequence.return_value = "next_agent"

        with patch("builtins.print") as mock_print:
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

        # Verify fork group handling
        self.engine.fork_manager.mark_agent_done.assert_called_once()
        self.engine.fork_manager.next_in_sequence.assert_called_once()
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
                run=AsyncMock(return_value={"result": "result1"}),
            ),
            "agent2": Mock(
                type="completion",
                __class__=Mock(__name__="Agent2"),
                run=AsyncMock(return_value={"result": "result2"}),
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

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                result = await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                    return_logs=True,  # Request logs to be returned
                )

        assert isinstance(result, list)
        self.engine.agents["agent1"].run.assert_called_once()
        self.engine.agents["agent2"].run.assert_called_once()

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
    async def test_joinnode_with_hget_result(self):
        """Test join node with hget returning group ID within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        join_agent = Mock(type="joinnode", group_id="original_group")
        join_agent.run = Mock(return_value={"status": "done", "result": "joined_result"})
        self.engine.agents = {"join1": join_agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        # Mock hget to return a group ID
        self.engine.memory.hget.return_value = b"mapped_group_123"

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert join_agent.run.called_once()
        # Verify that the fork_group_id was correctly processed and logged
        # This requires inspecting the logs, which are returned by _run_with_comprehensive_error_handling
        assert any(
            "fork_group_id" in log["payload"] and log["payload"]["fork_group_id"] == "mapped_group_123"
            for log in logs
            if log["agent_id"] == "join1"
        )

    @pytest.mark.asyncio
    async def test_joinnode_with_string_hget_result(self):
        """Test join node with hget returning string group ID within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        join_agent = Mock(type="joinnode", group_id="original_group")
        join_agent.run = Mock(return_value={"status": "done", "result": "joined_result"})
        self.engine.agents = {"join1": join_agent}
        self.engine.orchestrator_cfg = {"agents": ["join1"]}

        # Mock hget to return a string group ID
        self.engine.memory.hget.return_value = "mapped_group_123"

        with patch("orka.orchestrator.execution_engine.os.makedirs"):
            with patch("orka.orchestrator.execution_engine.os.path.join"):
                await self.engine._run_with_comprehensive_error_handling(
                    input_data,
                    logs,
                )

        assert join_agent.run.called_once()
        # Verify that the fork_group_id was correctly processed and logged
        assert any(
            "fork_group_id" in log["payload"] and log["payload"]["fork_group_id"] == "mapped_group_123"
            for log in logs
            if log["agent_id"] == "join1"
        )

    @pytest.mark.asyncio
    async def test_forknode_with_nested_targets(self):
        """Test fork node with nested branch targets within comprehensive error handling."""
        input_data = {"test": "data"}
        logs = []

        fork_agent = Mock(
            type="forknode",
            __class__=Mock(__name__="ForkAgent"),
            run=AsyncMock(return_value={}),
        )
        fork_agent.config = {
            "targets": [["agent1", "agent2"], "agent3", ["agent4"]],
            "mode": "parallel",
        }
        self.engine.agents = {"fork1": fork_agent}
        self.engine.orchestrator_cfg = {"agents": ["fork1"]}

        with patch.object(
            self.engine,
            "run_parallel_agents",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch("orka.orchestrator.execution_engine.os.makedirs"):
                with patch("orka.orchestrator.execution_engine.os.path.join"):
                    await self.engine._run_with_comprehensive_error_handling(
                        input_data,
                        logs,
                    )

        # Verify fork behavior with flattened targets
        # The run_parallel_agents mock handles the actual execution, so we check its call
        self.engine.run_parallel_agents.assert_called_once()

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
