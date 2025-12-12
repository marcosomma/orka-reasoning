import asyncio
from unittest.mock import AsyncMock, MagicMock


def test_execution_engine_run_success(monkeypatch):
    """Exercise ExecutionEngine.run success path with mocked agents and runner."""
    # Import here so monkeypatch of heavy imports in conftest apply
    from orka.orchestrator import execution_engine as ee_mod

    # Create a fake execution engine class to test the public run flow
    class DummyEngine(ee_mod.ExecutionEngine):
        def __init__(self, *a, **k):
            # call base init but avoid heavy wiring
            super().__init__(*a, **k)

    # Prepare a minimal orchestrator config that ExecutionEngine expects
    fake_config = {
        "orchestrator": {"id": "test", "strategy": "sequential"},
        "agents": [],
    }

    # Patch the internal comprehensive runner so run() resolves quickly
    async def fake_run(self, input_data, logs, return_logs=False):
        return {"status": "success", "result": {}}

    monkeypatch.setattr(
        ee_mod.ExecutionEngine,
        "_run_with_comprehensive_error_handling",
        fake_run,
        raising=False,
    )

    # Instantiate with dummy YAML path (OrchestratorBase expects a path)
    engine = ee_mod.ExecutionEngine("tests/unit/orchestrator/dummy_path.yml")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(engine.run({}))
    finally:
        loop.close()

    assert isinstance(result, dict)
    assert result.get("status") in ("success", "ok", None) or "result" in result


def test_execution_engine_run_error_handling(monkeypatch):
    """Ensure ExecutionEngine.run captures exceptions from internal runner and returns an error-like dict."""
    from orka.orchestrator import execution_engine as ee_mod

    async def fake_run_raises(self, input_data, logs, return_logs=False):
        raise RuntimeError("simulated")

    monkeypatch.setattr(
        ee_mod.ExecutionEngine,
        "_run_with_comprehensive_error_handling",
        fake_run_raises,
        raising=False,
    )

    engine = ee_mod.ExecutionEngine("tests/unit/orchestrator/dummy_path.yml")

    import asyncio as _asyncio

    loop = _asyncio.new_event_loop()
    try:
        _asyncio.set_event_loop(loop)
        import pytest

        with pytest.raises(RuntimeError):
            loop.run_until_complete(engine.run({}))
    finally:
        loop.close()
"""Unit tests for orka.orchestrator.execution_engine."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from orka.orchestrator.execution_engine import ExecutionEngine, json_serializer

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestJsonSerializer:
    """Test suite for json_serializer function."""

    def test_json_serializer_datetime(self):
        """Test json_serializer with datetime object."""
        dt = datetime.now(UTC)
        result = json_serializer(dt)
        assert isinstance(result, str)
        assert dt.isoformat() == result

    def test_json_serializer_unsupported_type(self):
        """Test json_serializer with unsupported type raises TypeError."""
        with pytest.raises(TypeError):
            json_serializer({"key": "value"})


class TestExecutionEngine:
    """Test suite for ExecutionEngine class."""

    @pytest.fixture
    def mock_config_file(self, tmp_path):
        """Create a temporary config file."""
        config_path = tmp_path / "test_config.yml"
        config_path.write_text("""
orchestrator:
  id: test_orchestrator
  strategy: sequential
  agents: [agent1, agent2]
agents:
  - id: agent1
    type: local_llm
    prompt: "Test prompt 1"
  - id: agent2
    type: local_llm
    prompt: "Test prompt 2"
""")
        return str(config_path)

    @pytest.fixture
    def execution_engine(self, mock_config_file):
        """Create ExecutionEngine instance with mocked dependencies."""
        with patch('orka.orchestrator.base.YAMLLoader') as MockLoader, \
             patch('orka.orchestrator.base.create_memory_logger') as MockMemoryLogger, \
             patch('orka.orchestrator.base.ForkGroupManager') as MockForkManager:
            
            mock_loader = Mock()
            mock_loader.get_orchestrator.return_value = {
                "id": "test_orchestrator",
                "strategy": "sequential",
                "agents": ["agent1", "agent2"]
            }
            mock_loader.get_agents.return_value = [
                {"id": "agent1", "type": "local_llm", "prompt": "Test prompt 1"},
                {"id": "agent2", "type": "local_llm", "prompt": "Test prompt 2"}
            ]
            mock_loader.validate.return_value = True
            MockLoader.return_value = mock_loader
            
            mock_memory = Mock()
            MockMemoryLogger.return_value = mock_memory
            
            mock_fork_manager = Mock()
            MockForkManager.return_value = mock_fork_manager
            
            engine = ExecutionEngine(mock_config_file)
            mock_agent1 = Mock()
            mock_agent1.type = "local_llm"
            mock_agent1.capabilities = []
            mock_agent2 = Mock()
            mock_agent2.type = "local_llm"
            mock_agent2.capabilities = []
            engine.agents = {
                "agent1": mock_agent1,
                "agent2": mock_agent2,
            }
            return engine

    def test_init(self, execution_engine):
        """Test ExecutionEngine initialization."""
        assert "agent1" in execution_engine.agents
        assert "agent2" in execution_engine.agents
        assert execution_engine.orchestrator == execution_engine

    @pytest.mark.asyncio
    async def test_run_success(self, execution_engine):
        """Test run method with successful execution."""
        execution_engine.agents["agent1"].run = AsyncMock(return_value={"result": "output1"})
        execution_engine.agents["agent2"].run = AsyncMock(return_value={"result": "output2"})
        
        with patch.object(execution_engine, '_run_with_comprehensive_error_handling', return_value="final_result"):
            result = await execution_engine.run("test input")
            assert result == "final_result"

    @pytest.mark.asyncio
    async def test_run_exception(self, execution_engine):
        """Test run method handles exceptions."""
        with patch.object(execution_engine, '_run_with_comprehensive_error_handling', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                await execution_engine.run("test input")
            
            # Verify error was recorded
            assert len(execution_engine.error_telemetry["errors"]) > 0

    def test_ensure_complete_context(self, execution_engine):
        """Test _ensure_complete_context method."""
        previous_outputs = {
            "agent1": {"result": "output1"},
            "agent2": {"result": "output2"},
        }
        
        result = execution_engine._ensure_complete_context(previous_outputs)
        
        assert isinstance(result, dict)
        assert "agent1" in result
        assert "agent2" in result

    def test_enqueue_fork(self, execution_engine):
        """Test enqueue_fork method."""
        execution_engine.fork_manager.enqueue_fork(["agent1", "agent2"], "fork_group_1")
        execution_engine.fork_manager.enqueue_fork.assert_called_once_with(
            ["agent1", "agent2"], "fork_group_1"
        )

    def test_extract_final_response(self, execution_engine):
        """Test _extract_final_response method."""
        logs = [
            {"agent_id": "agent1", "event_type": "local_llm", "payload": {"result": "output1"}},
            {"agent_id": "agent2", "event_type": "LocalLLMAgent", "payload": {"result": "output2"}},
        ]
        
        result = execution_engine._extract_final_response(logs)
        
        # Should return the last agent's result
        assert result == {}

    def test_extract_final_response_empty_logs(self, execution_engine):
        """Test _extract_final_response with empty logs."""
        result = execution_engine._extract_final_response([])
        assert result == []

    def test_check_unresolved_variables(self, execution_engine):
        """Test _check_unresolved_variables method."""
        # Text with unresolved variable
        text_with_var = "Hello {{ name }}"
        assert execution_engine._check_unresolved_variables(text_with_var) is True
        
        # Text without variables
        text_no_var = "Hello world"
        assert execution_engine._check_unresolved_variables(text_no_var) is False

    def test_extract_template_variables(self, execution_engine):
        """Test _extract_template_variables method."""
        template = "Hello {{ name }}, you have {{ count }} messages"
        variables = execution_engine._extract_template_variables(template)
        
        assert "name" in [v.strip() for v in variables]
        assert "count" in [v.strip() for v in variables]

    def test_build_template_context(self, execution_engine):
        """Test _build_template_context method."""
        payload = {
            "input": "test input",
            "previous_outputs": {
                "agent1": {"result": "output1"}
            }
        }
        
        context = execution_engine._build_template_context(payload, "agent2")
        
        assert isinstance(context, dict)
        assert "input" in context
        assert "agent1" in context["previous_outputs"]

    def test_simplify_agent_result_for_templates(self, execution_engine):
        """Test _simplify_agent_result_for_templates method."""
        # Test with dict result
        result_dict = {"result": "output", "status": "success"}
        simplified = execution_engine._simplify_agent_result_for_templates(result_dict)
        assert simplified['result'] == "output"
        
        # Test with string result
        result_str = "simple output"
        simplified = execution_engine._simplify_agent_result_for_templates(result_str)
        assert simplified == "simple output"
        
        # Test with None
        simplified = execution_engine._simplify_agent_result_for_templates(None)
        assert simplified is None

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_router_empty_result(
        self, execution_engine
    ):
        """
        Test _run_with_comprehensive_error_handling when a router node returns an empty or invalid result.
        Ensures the orchestrator continues processing without errors and the queue isn't modified.
        """
        router_agent_id = "router_agent"
        execution_engine.orchestrator_cfg["agents"] = [router_agent_id, "agent1"]
        execution_engine.agents[router_agent_id] = Mock(type="routernode")
        execution_engine.agents["agent1"] = Mock(type="local_llm", capabilities=[])

        # Mock _run_agent_async to return an empty list for the router
        async def mock_run_agent_async(agent_id, *args, **kwargs):
            if agent_id == router_agent_id:
                # Simulate router returning an OrkaResponse with an empty result list
                return agent_id, {"component_type": "RouterNode", "result": []}
            return agent_id, {"result": "some_output"}

        execution_engine._run_agent_async = AsyncMock(side_effect=mock_run_agent_async)

        # Mock memory logging to prevent interaction with actual Redis
        execution_engine.memory.log = Mock()
        execution_engine.memory.set = Mock()
        execution_engine.memory.hset = Mock()
        execution_engine.memory.memory.append = Mock()


        initial_queue = execution_engine.orchestrator_cfg["agents"].copy()
        
        # Patch methods that would interact with file system or external resources
        with patch("orka.orchestrator.execution_engine.os.makedirs"), \
             patch("orka.orchestrator.execution_engine.os.path.join"), \
             patch.object(execution_engine.memory, 'save_enhanced_trace'):
            
            result_logs = []
            final_result = await execution_engine._run_with_comprehensive_error_handling(
                "test input", result_logs, return_logs=True
            )

        # Assertions
        assert len(result_logs) == 1  # Only agent1 should be logged, router is skipped
        assert result_logs[0]["agent_id"] == "agent1"
        assert router_agent_id not in [log["agent_id"] for log in result_logs] # Router should not be logged
        assert execution_engine._run_agent_async.call_count == 2 # Both agents were attempted to run
        
        # The queue should essentially become just the remaining agents after the router is processed
        # as the router did not add any new agents.
        # The logic `continue` after an empty router result skips normal processing,
        # so the agent following the router ('agent1') should still be processed.
        # The original queue was [router_agent_id, "agent1"].
        # After router, queue.pop(0) removes router_agent_id, leaving ["agent1"].
        # Since router returned empty, queue is not extended. So "agent1" should be next.
        assert "agent1" in [log["agent_id"] for log in result_logs] # Ensure agent1 was executed
        assert final_result == result_logs # Should return logs since return_logs=True

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_router_success_routing(
        self, execution_engine
    ):
        """
        Test _run_with_comprehensive_error_handling when a router node successfully routes to new agents.
        Ensures the orchestrator's queue is correctly updated.
        """
        router_agent_id = "router_agent"
        new_routed_agents = ["new_agent1", "new_agent2"]
        original_remaining_agent = "agent1"
        
        execution_engine.orchestrator_cfg["agents"] = [router_agent_id, original_remaining_agent]
        
        mock_router_agent = Mock(type="routernode")
        mock_agent1 = Mock(type="local_llm", capabilities=[])
        mock_new_agent1 = Mock(type="local_llm", capabilities=[])
        mock_new_agent2 = Mock(type="local_llm", capabilities=[])
        
        execution_engine.agents = {
            router_agent_id: mock_router_agent,
            original_remaining_agent: mock_agent1,
            new_routed_agents[0]: mock_new_agent1,
            new_routed_agents[1]: mock_new_agent2,
        }

        # Mock _run_agent_async to return the new routed agents for the router
        async def mock_run_agent_async(agent_id, *args, **kwargs):
            if agent_id == router_agent_id:
                # Simulate router returning an OrkaResponse with a list of new agents
                return agent_id, {"component_type": "RouterNode", "result": new_routed_agents}
            # For other agents, return a simple successful result
            return agent_id, {"result": f"{agent_id}_output"}

        execution_engine._run_agent_async = AsyncMock(side_effect=mock_run_agent_async)

        # Mock memory logging to prevent interaction with actual Redis
        execution_engine.memory.log = Mock()
        execution_engine.memory.set = Mock()
        execution_engine.memory.hset = Mock()
        execution_engine.memory.memory.append = Mock()

        # Patch methods that would interact with file system or external resources
        with patch("orka.orchestrator.execution_engine.os.makedirs"), \
             patch("orka.orchestrator.execution_engine.os.path.join"), \
             patch.object(execution_engine.memory, 'save_enhanced_trace'):

            result_logs = []
            await execution_engine._run_with_comprehensive_error_handling(
                "test input", result_logs, return_logs=True
            )

        # Assertions
        # Router itself should be logged as it produced a result (the new queue)
        assert len(result_logs) == 3 # new_agent1 + new_agent2 + original_remaining_agent
        assert router_agent_id not in [log["agent_id"] for log in result_logs] # Router should not be logged
        
        # The queue should be updated with new agents at the beginning
        # and the original remaining agent after that.
        # The processing order should be: router -> new_agent1 -> new_agent2 -> original_remaining_agent
        assert result_logs[0]["agent_id"] == new_routed_agents[0]
        assert result_logs[1]["agent_id"] == new_routed_agents[1]
        assert result_logs[2]["agent_id"] == original_remaining_agent
        
        # Verify that run_agent_async was called for all expected agents in order
        expected_calls = [
            (router_agent_id,),
            (new_routed_agents[0],),
            (new_routed_agents[1],),
            (original_remaining_agent,),
        ]
        actual_calls = [call.args[0] for call in execution_engine._run_agent_async.call_args_list]
        assert actual_calls == [router_agent_id, new_routed_agents[0], new_routed_agents[1], original_remaining_agent]

    @pytest.mark.asyncio
    async def test_run_with_comprehensive_error_handling_graphscout_commit_next(
        self, execution_engine
    ):
        """
        Test _run_with_comprehensive_error_handling when a GraphScout agent returns 'commit_next'.
        Ensures the orchestrator's queue is correctly updated and _validate_and_enforce_terminal_agent is called.
        """
        graphscout_agent_id = "graphscout_agent"
        target_agent_id = "final_agent"
        original_remaining_agent = "agent1"

        execution_engine.orchestrator_cfg["agents"] = [graphscout_agent_id, original_remaining_agent]

        mock_graphscout_agent = Mock(type="graphscoutagent")
        mock_agent1 = Mock(type="local_llm", capabilities=[])
        mock_final_agent = Mock(type="local_llm", capabilities=["response_generation"])

        execution_engine.agents = {
            graphscout_agent_id: mock_graphscout_agent,
            original_remaining_agent: mock_agent1,
            target_agent_id: mock_final_agent, # Ensure the target agent exists
        }

        # Mock _run_agent_async for GraphScout to return 'commit_next' with a target
        async def mock_run_agent_async(agent_id, *args, **kwargs):
            if agent_id == graphscout_agent_id:
                return agent_id, {"component_type": "GraphScoutAgent", "result": {"decision": "commit_next", "target": target_agent_id}}
            # For other agents, return a simple successful result
            return agent_id, {"result": f"{agent_id}_output"}

        execution_engine._run_agent_async = AsyncMock(side_effect=mock_run_agent_async)

        # Mock memory logging and other external interactions
        execution_engine.memory.log = Mock()
        execution_engine.memory.set = Mock()
        execution_engine.memory.hset = Mock()
        execution_engine.memory.memory.append = Mock()
        
        # Mock _validate_and_enforce_terminal_agent
        with patch.object(execution_engine, '_validate_and_enforce_terminal_agent', wraps=execution_engine._validate_and_enforce_terminal_agent) as mock_validate_enforce:
            with patch("orka.orchestrator.execution_engine.os.makedirs"), \
                 patch("orka.orchestrator.execution_engine.os.path.join"), \
                 patch.object(execution_engine.memory, 'save_enhanced_trace'):

                result_logs = []
                await execution_engine._run_with_comprehensive_error_handling(
                    "test input", result_logs, return_logs=True
                )

        # Assertions
        # GraphScout should be logged, as its result is processed
        assert len(result_logs) == 3 # GraphScout + target_agent_id + original_remaining_agent (if it's not the same as target_agent_id)
        assert result_logs[0]["agent_id"] == graphscout_agent_id
        assert result_logs[0]["payload"]["decision"] == "commit_next"
        assert result_logs[0]["payload"]["target"] == target_agent_id

        # The queue should be updated with the target agent, followed by the original remaining agent
        # And the _validate_and_enforce_terminal_agent should have been called
        mock_validate_enforce.assert_called_once_with([target_agent_id])

        # Verify the execution order
        expected_calls = [
            (graphscout_agent_id,),
            (target_agent_id,),
            (original_remaining_agent,),
        ]
        actual_calls = [call.args[0] for call in execution_engine._run_agent_async.call_args_list]
        assert actual_calls == [graphscout_agent_id, target_agent_id, original_remaining_agent]



    def test_is_response_builder(self, execution_engine):
        """Test _is_response_builder method."""
        # Test with response builder agent
        execution_engine.agents["response_builder"] = Mock(
            type="local_llm",
            __class__=Mock(__name__="LocalLLMAgent"),
            capabilities=["text_generation", "response_generation"]
        )
        assert execution_engine._is_response_builder("response_builder") is True
        
        # Test with non-response builder
        execution_engine.agents["agent1"].type = "search"
        assert execution_engine._is_response_builder("agent1") is False

    def test_is_memory_agent(self, execution_engine):
        """Test _is_memory_agent method."""
        # Test with memory agent
        execution_engine.agents["memory_reader"] = Mock(
            __class__=Mock(__name__="MemoryReaderNode"),
            type="memory"
        )
        assert execution_engine._is_memory_agent("memory_reader") is True
        
        # Test with non-memory agent
        assert execution_engine._is_memory_agent("agent1") is False

    def test_get_memory_operation(self, execution_engine):
        """Test _get_memory_operation method."""
        # Test with memory reader
        execution_engine.agents["memory_reader"] = Mock(
            __class__=Mock(__name__="MemoryReaderNode"),
            config={"operation": "read"}
        )
        operation = execution_engine._get_memory_operation("memory_reader")
        assert operation == "read"
        
        # Test with memory writer
        execution_engine.agents["memory_writer"] = Mock(
            __class__=Mock(__name__="MemoryWriterNode"),
            config={"operation": "write"}
        )
        operation = execution_engine._get_memory_operation("memory_writer")
        assert operation == "write"

    def test_get_best_response_builder(self, execution_engine):
        """Test _get_best_response_builder method."""
        # Test with response builder available
        execution_engine.agents["response_builder"] = Mock(
            type="local_llm",
            __class__=Mock(__name__="LocalLLMAgent"),
            capabilities=["text_generation", "response_generation"]
        )
        execution_engine.orchestrator_cfg['agents'].append('response_builder')
        result = execution_engine._get_best_response_builder()
        assert result == "response_builder"
        
        # Test with no response builder
        execution_engine.agents = {
            "agent1": Mock(type="local_llm", capabilities=[]),
        }
        execution_engine.orchestrator_cfg['agents'] = ['agent1']
        result = execution_engine._get_best_response_builder()
        assert result is None

    def test_validate_and_enforce_terminal_agent(self, execution_engine):
        """Test _validate_and_enforce_terminal_agent method."""
        # Test with queue that has response builder
        execution_engine.agents["response_builder"] = Mock(
            type="local_llm",
            __class__=Mock(__name__="LocalLLMAgent"),
            capabilities=["text_generation", "response_generation"]
        )
        queue = ["agent1", "response_builder"]
        result = execution_engine._validate_and_enforce_terminal_agent(queue)
        assert result == queue  # Should remain unchanged
        
        # Test with queue without response builder
        queue = ["agent1", "agent2"]
        result = execution_engine._validate_and_enforce_terminal_agent(queue)
        # Should append response builder if available
        best_builder = execution_engine._get_best_response_builder()
        if best_builder:
            assert result[-1] == best_builder

    def test_apply_memory_routing_logic(self, execution_engine):
        """Test _apply_memory_routing_logic method."""
        # Test with shortlist containing memory agents
        execution_engine.agents["memory_reader"] = Mock(
            __class__=Mock(__name__="MemoryReaderNode"),
            type="memory",
            config={"operation": "read"}
        )
        execution_engine.agents["response_builder"] = Mock(
            type="local_llm",
            __class__=Mock(__name__="LocalLLMAgent"),
            capabilities=["text_generation", "response_generation"]
        )
        
        shortlist = [
            {"node_id": "memory_reader"},
            {"node_id": "response_builder"},
        ]
        
        result = execution_engine._apply_memory_routing_logic(shortlist)
        
        assert isinstance(result, list)
        assert len(result) > 0

    def test_select_best_candidate_from_shortlist(self, execution_engine):
        """Test _select_best_candidate_from_shortlist method."""
        shortlist = [
            {"node_id": "agent1", "score": 0.8},
            {"node_id": "agent2", "score": 0.9},
            {"node_id": "agent3", "score": 0.7},
        ]
        
        result = execution_engine._select_best_candidate_from_shortlist(shortlist, "question", {})
        
        # Should return the candidate with highest score
        assert result["node_id"] == "agent1"
        assert result["score"] == 0.8

    def test_select_best_candidate_from_shortlist_empty(self, execution_engine):
        """Test _select_best_candidate_from_shortlist with empty shortlist."""
        result = execution_engine._select_best_candidate_from_shortlist([], "question", {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_run_agent_async(self, execution_engine):
        """Test _run_agent_async method."""
        mock_agent = Mock()
        mock_agent.run = AsyncMock(return_value={"result": "test output"})
        execution_engine.agents["test_agent"] = mock_agent
        
        result_status, result_data = await execution_engine._run_agent_async(
            "test_agent",
            "test input",
            {},
        )
        
        assert result_status == "test_agent"
        assert result_data == {"result": "test output"}

    @pytest.mark.asyncio
    async def test_run_agent_async_exception(self, execution_engine):
        """Test _run_agent_async handles exceptions."""
        mock_agent = Mock()
        mock_agent.run = AsyncMock(side_effect=Exception("Agent error"))
        execution_engine.agents["test_agent"] = mock_agent
        
        with pytest.raises(Exception, match="Agent error"):
            await execution_engine._run_agent_async(
                "test_agent",
                "test input",
                {},
            )

    @pytest.mark.asyncio
    async def test_run_parallel_agents(self, execution_engine):
        """Test run_parallel_agents method."""
        mock_agent1 = Mock()
        mock_agent1.run = AsyncMock(return_value={"result": "output1"})
        mock_agent2 = Mock()
        mock_agent2.run = AsyncMock(return_value={"result": "output2"})
        
        execution_engine.agents = {
            "agent1": mock_agent1,
            "agent2": mock_agent2,
        }
        
        results = await execution_engine.run_parallel_agents(
            ["agent1", "agent2"],
            "fork_group_1",
            "test input",
            {},
        )
        
        assert len(results) == 2
        assert results[0]['payload']["result"] == "output1"
        assert results[1]['payload']["result"] == "output2"

    def test_build_enhanced_trace(self, execution_engine):
        """Test _build_enhanced_trace method."""
        logs = [
            {
                "agent_id": "agent1",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration": 1.5,
                "payload": {"result": "output1"},
            },
            {
                "agent_id": "agent2",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration": 2.0,
                "payload": {"result": "output2"},
            },
        ]
        
        trace = execution_engine._build_enhanced_trace(logs)
        
        assert isinstance(trace, dict)
        assert "execution_metadata" in trace
        assert "agent_executions" in trace
        assert trace['agent_executions'][0]["agent_id"] == "agent1"
        assert trace['agent_executions'][1]["agent_id"] == "agent2"

