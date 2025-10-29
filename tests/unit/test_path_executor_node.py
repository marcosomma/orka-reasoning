from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.nodes.path_executor_node import PathExecutorNode


class TestPathExecutorNodeInitialization:
    """Test PathExecutorNode initialization scenarios."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        node = PathExecutorNode(node_id="test_executor")

        assert node.node_id == "test_executor"
        assert node.path_source == "validated_path"
        assert node.on_agent_failure == "continue"

    def test_custom_path_source(self):
        """Test initialization with custom path_source."""
        node = PathExecutorNode(
            node_id="test_executor",
            path_source="validation_loop.response.result.graphscout_router"
        )

        assert node.path_source == "validation_loop.response.result.graphscout_router"

    def test_failure_handling_modes(self):
        """Test both failure handling modes."""
        node_continue = PathExecutorNode(
            node_id="test1",
            on_agent_failure="continue"
        )
        node_abort = PathExecutorNode(
            node_id="test2",
            on_agent_failure="abort"
        )

        assert node_continue.on_agent_failure == "continue"
        assert node_abort.on_agent_failure == "abort"

    def test_invalid_failure_mode_raises_error(self):
        """Test that invalid on_agent_failure raises ValueError."""
        with pytest.raises(ValueError, match="must be 'continue' or 'abort'"):
            PathExecutorNode(
                node_id="test",
                on_agent_failure="invalid_mode"
            )


class TestPathExtraction:
    """Test path extraction from previous_outputs."""

    def test_extract_simple_path(self):
        """Test extracting path from simple key."""
        node = PathExecutorNode(node_id="test", path_source="graphscout")
        
        context = {
            "previous_outputs": {
                "graphscout": {
                    "target": ["agent1", "agent2", "agent3"]
                }
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert error is None
        assert path == ["agent1", "agent2", "agent3"]

    def test_extract_nested_path(self):
        """Test extracting path with dot notation."""
        node = PathExecutorNode(
            node_id="test",
            path_source="validation_loop.response.result.graphscout_router"
        )
        
        context = {
            "previous_outputs": {
                "validation_loop": {
                    "response": {
                        "result": {
                            "graphscout_router": {
                                "target": ["search", "analyze", "generate"]
                            }
                        }
                    }
                }
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert error is None
        assert path == ["search", "analyze", "generate"]

    def test_extract_from_graphscout_result(self):
        """Test extracting from GraphScout decision format."""
        node = PathExecutorNode(node_id="test", path_source="graphscout_router")
        
        context = {
            "previous_outputs": {
                "graphscout_router": {
                    "decision": "agent",
                    "target": ["web_search", "analyzer", "generator"],
                    "confidence": 0.92,
                    "reasoning": "Path requires search + analysis"
                }
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert error is None
        assert path == ["web_search", "analyzer", "generator"]

    def test_extract_from_loop_result(self):
        """Test extracting from loop validation result."""
        node = PathExecutorNode(
            node_id="test",
            path_source="loop.response.result.plan_proposer"
        )
        
        context = {
            "previous_outputs": {
                "loop": {
                    "response": {
                        "result": {
                            "plan_proposer": {
                                "path": ["step1", "step2", "step3"]
                            }
                        }
                    }
                }
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert error is None
        assert path == ["step1", "step2", "step3"]

    def test_missing_path_source(self):
        """Test error when path_source key doesn't exist."""
        node = PathExecutorNode(node_id="test", path_source="nonexistent")
        
        context = {
            "previous_outputs": {
                "other_agent": {"result": "data"}
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert path == []
        assert error is not None
        assert "not found" in error

    def test_invalid_path_format(self):
        """Test error when path data is in wrong format."""
        node = PathExecutorNode(node_id="test", path_source="bad_format")
        
        context = {
            "previous_outputs": {
                "bad_format": "not_a_dict_or_list"
            }
        }
        
        path, error = node._extract_agent_path(context)
        
        assert path == []
        assert error is not None
        assert "Could not extract agent list" in error

    def test_no_previous_outputs(self):
        """Test error when previous_outputs is missing."""
        node = PathExecutorNode(node_id="test")
        
        context = {}
        
        path, error = node._extract_agent_path(context)
        
        assert path == []
        assert error == "No previous_outputs available"


class TestParseAgentList:
    """Test parsing agent lists from various formats."""

    def test_parse_direct_list(self):
        """Test parsing a direct list of agents."""
        node = PathExecutorNode(node_id="test")
        
        result = node._parse_agent_list(["agent1", "agent2"])
        
        assert result == ["agent1", "agent2"]

    def test_parse_target_field(self):
        """Test parsing from dict with 'target' field (GraphScout format)."""
        node = PathExecutorNode(node_id="test")
        
        result = node._parse_agent_list({
            "target": ["search", "analyze"],
            "confidence": 0.9
        })
        
        assert result == ["search", "analyze"]

    def test_parse_path_field(self):
        """Test parsing from dict with 'path' field (alternative format)."""
        node = PathExecutorNode(node_id="test")
        
        result = node._parse_agent_list({
            "path": ["step1", "step2"]
        })
        
        assert result == ["step1", "step2"]

    def test_parse_invalid_format(self):
        """Test parsing returns None for invalid formats."""
        node = PathExecutorNode(node_id="test")
        
        assert node._parse_agent_list("invalid") is None
        assert node._parse_agent_list(123) is None
        assert node._parse_agent_list({"no_target_or_path": True}) is None


class TestValidateExecutionContext:
    """Test validation of execution context."""

    def test_valid_context(self):
        """Test validation passes with valid context."""
        node = PathExecutorNode(node_id="test")
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock()
        
        context = {
            "orchestrator": mock_orchestrator
        }
        
        error = node._validate_execution_context(context)
        
        assert error is None

    def test_missing_orchestrator(self):
        """Test error when orchestrator is missing."""
        node = PathExecutorNode(node_id="test")
        
        context = {}
        
        error = node._validate_execution_context(context)
        
        assert error is not None
        assert "Orchestrator context is missing" in error

    def test_orchestrator_is_none(self):
        """Test error when orchestrator is None."""
        node = PathExecutorNode(node_id="test")
        
        context = {"orchestrator": None}
        
        error = node._validate_execution_context(context)
        
        assert error is not None
        assert "Orchestrator is None" in error

    def test_orchestrator_missing_method(self):
        """Test error when orchestrator lacks required method."""
        node = PathExecutorNode(node_id="test")
        
        mock_orchestrator = Mock(spec=[])  # No methods
        
        context = {"orchestrator": mock_orchestrator}
        
        error = node._validate_execution_context(context)
        
        assert error is not None
        assert "_run_agent_async" in error


@pytest.mark.asyncio
class TestAgentExecution:
    """Test agent execution functionality."""

    async def test_execute_single_agent(self):
        """Test executing a single agent."""
        node = PathExecutorNode(node_id="test")
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock(
            return_value=("agent1", {"response": "result1"})
        )
        mock_orchestrator.agents = {"agent1": Mock()}
        
        context = {
            "input": "test input",
            "orchestrator": mock_orchestrator,
            "run_id": "test_run"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1"],
            context=context
        )
        
        assert len(results) == 1
        assert "agent1" in results
        assert results["agent1"] == {"response": "result1"}
        assert len(errors) == 0
        
        mock_orchestrator._run_agent_async.assert_called_once()

    async def test_execute_multiple_agents_sequential(self):
        """Test executing multiple agents in sequence."""
        node = PathExecutorNode(node_id="test")
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock(
            side_effect=[
                ("agent1", {"response": "result1"}),
                ("agent2", {"response": "result2"}),
                ("agent3", {"response": "result3"}),
            ]
        )
        mock_orchestrator.agents = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock()
        }
        
        context = {
            "input": "test input",
            "orchestrator": mock_orchestrator,
            "run_id": "test_run"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1", "agent2", "agent3"],
            context=context
        )
        
        assert len(results) == 3
        assert len(errors) == 0
        assert results["agent1"] == {"response": "result1"}
        assert results["agent2"] == {"response": "result2"}
        assert results["agent3"] == {"response": "result3"}
        
        assert mock_orchestrator._run_agent_async.call_count == 3

    async def test_results_accumulation(self):
        """Test that results accumulate and are passed to subsequent agents."""
        node = PathExecutorNode(node_id="test")
        
        # Track what previous_outputs are passed to each agent
        call_args_list = []
        
        async def mock_run_agent(agent_id, input_data, previous_outputs, full_payload):
            call_args_list.append({
                "agent_id": agent_id,
                "previous_outputs": previous_outputs.copy()
            })
            return (agent_id, {"response": f"result_{agent_id}"})
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = mock_run_agent
        mock_orchestrator.agents = {"agent1": Mock(), "agent2": Mock()}
        
        context = {
            "input": "test",
            "orchestrator": mock_orchestrator,
            "run_id": "test"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1", "agent2"],
            context=context
        )
        
        # First agent should see empty previous_outputs
        assert call_args_list[0]["previous_outputs"] == {}
        
        # Second agent should see agent1's result
        assert "agent1" in call_args_list[1]["previous_outputs"]
        assert call_args_list[1]["previous_outputs"]["agent1"] == {"response": "result_agent1"}

    async def test_orchestrator_context_passing(self):
        """Test that orchestrator context is passed correctly."""
        node = PathExecutorNode(node_id="test")
        
        captured_payloads = []
        
        async def capture_payload(agent_id, input_data, previous_outputs, full_payload):
            captured_payloads.append(full_payload)
            return (agent_id, {"response": "ok"})
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = capture_payload
        mock_orchestrator.agents = {"agent1": Mock()}
        
        context = {
            "input": "test_input",
            "orchestrator": mock_orchestrator,
            "run_id": "run123"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1"],
            context=context
        )
        
        # Verify payload structure
        assert len(captured_payloads) == 1
        payload = captured_payloads[0]
        assert payload["input"] == "test_input"
        assert payload["orchestrator"] == mock_orchestrator
        assert payload["run_id"] == "run123"


@pytest.mark.asyncio
class TestFailureHandling:
    """Test failure handling strategies."""

    async def test_continue_on_failure(self):
        """Test that execution continues when on_agent_failure='continue'."""
        node = PathExecutorNode(
            node_id="test",
            on_agent_failure="continue"
        )
        
        # Mock orchestrator with one failing agent
        async def mock_run_agent(agent_id, input_data, previous_outputs, full_payload):
            if agent_id == "failing_agent":
                raise RuntimeError("Agent failed")
            return (agent_id, {"response": f"result_{agent_id}"})
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = mock_run_agent
        mock_orchestrator.agents = {
            "agent1": Mock(),
            "failing_agent": Mock(),
            "agent3": Mock()
        }
        
        context = {
            "input": "test",
            "orchestrator": mock_orchestrator,
            "run_id": "test"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1", "failing_agent", "agent3"],
            context=context
        )
        
        # All agents should have entries
        assert len(results) == 3
        assert "agent1" in results
        assert "failing_agent" in results
        assert "agent3" in results
        
        # Failing agent should have error
        assert "error" in results["failing_agent"]
        
        # Successful agents should have results
        assert results["agent1"] == {"response": "result_agent1"}
        assert results["agent3"] == {"response": "result_agent3"}
        
        # Errors list should contain the failure
        assert len(errors) == 1
        assert "Agent failed" in errors[0]

    async def test_abort_on_failure(self):
        """Test that execution aborts when on_agent_failure='abort'."""
        node = PathExecutorNode(
            node_id="test",
            on_agent_failure="abort"
        )
        
        # Mock orchestrator with one failing agent
        async def mock_run_agent(agent_id, input_data, previous_outputs, full_payload):
            if agent_id == "failing_agent":
                raise RuntimeError("Agent failed")
            return (agent_id, {"response": f"result_{agent_id}"})
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = mock_run_agent
        mock_orchestrator.agents = {
            "agent1": Mock(),
            "failing_agent": Mock(),
            "agent3": Mock()
        }
        
        context = {
            "input": "test",
            "orchestrator": mock_orchestrator,
            "run_id": "test"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1", "failing_agent", "agent3"],
            context=context
        )
        
        # Only agents before failure should have results
        assert len(results) == 2
        assert "agent1" in results
        assert "failing_agent" in results
        assert "agent3" not in results  # Should not execute
        
        # Error should be recorded
        assert len(errors) == 1
        assert "Agent failed" in errors[0]

    async def test_missing_agent_error(self):
        """Test handling of missing agent (not in orchestrator.agents)."""
        node = PathExecutorNode(
            node_id="test",
            on_agent_failure="continue"
        )
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock(
            return_value=("agent1", {"response": "ok"})
        )
        mock_orchestrator.agents = {"agent1": Mock()}  # Missing missing_agent
        
        context = {
            "input": "test",
            "orchestrator": mock_orchestrator,
            "run_id": "test"
        }
        
        results, errors = await node._execute_agent_sequence(
            agent_path=["agent1", "missing_agent"],
            context=context
        )
        
        # Should have results for agent1 and error for missing_agent
        assert "agent1" in results
        assert results["agent1"] == {"response": "ok"}
        assert "missing_agent" in results
        assert "error" in results["missing_agent"]
        
        assert len(errors) == 1
        assert "not found" in errors[0]


@pytest.mark.asyncio
class TestIntegration:
    """Test end-to-end integration scenarios."""

    async def test_with_validation_loop_output(self):
        """Test integration with validation loop output structure."""
        node = PathExecutorNode(
            node_id="path_executor",
            path_source="validation_loop.response.result.graphscout_router"
        )
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock(
            side_effect=[
                ("web_search", {"result": "search results"}),
                ("analyzer", {"analysis": "insights"}),
                ("generator", {"output": "final result"}),
            ]
        )
        mock_orchestrator.agents = {
            "web_search": Mock(),
            "analyzer": Mock(),
            "generator": Mock()
        }
        
        # Realistic validation loop output
        context = {
            "input": "test query",
            "previous_outputs": {
                "validation_loop": {
                    "response": {
                        "result": {
                            "graphscout_router": {
                                "decision": "agent",
                                "target": ["web_search", "analyzer", "generator"],
                                "confidence": 0.92
                            }
                        }
                    },
                    "threshold_met": True,
                    "final_score": 0.88
                }
            },
            "orchestrator": mock_orchestrator,
            "run_id": "test_run"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "success"
        assert result["executed_path"] == ["web_search", "analyzer", "generator"]
        assert len(result["results"]) == 3
        assert "web_search" in result["results"]
        assert "analyzer" in result["results"]
        assert "generator" in result["results"]

    async def test_with_graphscout_output(self):
        """Test integration with direct GraphScout output."""
        node = PathExecutorNode(
            node_id="path_executor",
            path_source="graphscout_router"
        )
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = AsyncMock(
            return_value=("test_agent", {"response": "ok"})
        )
        mock_orchestrator.agents = {"test_agent": Mock()}
        
        context = {
            "input": "test",
            "previous_outputs": {
                "graphscout_router": {
                    "decision": "agent",
                    "target": ["test_agent"],
                    "confidence": 0.95,
                    "reasoning": "Simple path"
                }
            },
            "orchestrator": mock_orchestrator,
            "run_id": "test"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "success"
        assert result["executed_path"] == ["test_agent"]
        assert "test_agent" in result["results"]

    async def test_end_to_end_execution(self):
        """Test complete end-to-end execution flow."""
        node = PathExecutorNode(
            node_id="executor",
            path_source="validated_path",
            on_agent_failure="abort"
        )
        
        # Mock orchestrator with realistic behavior
        async def realistic_run_agent(agent_id, input_data, previous_outputs, full_payload):
            await asyncio.sleep(0.01)  # Simulate async work
            return (agent_id, {
                "response": f"Result from {agent_id}",
                "processed_input": input_data
            })
        
        import asyncio
        
        mock_orchestrator = Mock()
        mock_orchestrator._run_agent_async = realistic_run_agent
        mock_orchestrator.agents = {
            "step1": Mock(),
            "step2": Mock(),
            "step3": Mock()
        }
        
        context = {
            "input": "user query",
            "previous_outputs": {
                "validated_path": ["step1", "step2", "step3"]
            },
            "orchestrator": mock_orchestrator,
            "run_id": "exec_001"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "success"
        assert len(result["executed_path"]) == 3
        assert len(result["results"]) == 3
        assert "errors" not in result
        
        # Verify all agents executed
        for agent_id in ["step1", "step2", "step3"]:
            assert agent_id in result["results"]
            assert "response" in result["results"][agent_id]

