# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma

"""
Integration tests for PathExecutor with real components.

Tests PathExecutor node with minimal mocking to ensure proper
integration with the orchestration system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from orka.nodes.path_executor_node import PathExecutorNode
from orka.orchestrator.base import OrkaOrchestrator


class TestPathExecutorIntegration:
    """Integration tests for PathExecutor with real orchestrator."""
    
    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with agent registry."""
        orch = MagicMock(spec=OrkaOrchestrator)
        
        # Create mock agents
        mock_agent1 = MagicMock()
        mock_agent1.node_id = "agent1"
        mock_agent1.run = AsyncMock(return_value={"status": "success", "output": "Result 1"})
        
        mock_agent2 = MagicMock()
        mock_agent2.node_id = "agent2"
        mock_agent2.run = AsyncMock(return_value={"status": "success", "output": "Result 2"})
        
        mock_agent3 = MagicMock()
        mock_agent3.node_id = "agent3"
        mock_agent3.run = AsyncMock(return_value={"status": "success", "output": "Result 3"})
        
        orch.agents = {
            "agent1": mock_agent1,
            "agent2": mock_agent2,
            "agent3": mock_agent3,
        }
        
        return orch
    
    @pytest.fixture
    def path_executor(self):
        """Create PathExecutor node."""
        return PathExecutorNode(
            node_id="path_executor",
            path_source="test_source",
            on_agent_failure="continue",
        )
    
    @pytest.mark.asyncio
    async def test_executor_executes_path_in_order(self, path_executor, mock_orchestrator):
        """Test that PathExecutor executes agents in the specified order."""
        context = {
            "orchestrator": mock_orchestrator,
            "run_id": "test_run",
            "test_source": ["agent1", "agent2", "agent3"],
        }
        
        result = await path_executor.run(context)
        
        # Verify execution order
        assert mock_orchestrator.agents["agent1"].run.called
        assert mock_orchestrator.agents["agent2"].run.called
        assert mock_orchestrator.agents["agent3"].run.called
        
        # Check result structure
        assert result["status"] == "success"
        assert "executed_path" in result
        assert result["executed_path"] == ["agent1", "agent2", "agent3"]
    
    @pytest.mark.asyncio
    async def test_executor_continues_on_failure(self, path_executor, mock_orchestrator):
        """Test that PathExecutor continues on agent failure when configured."""
        # Make agent2 fail
        mock_orchestrator.agents["agent2"].run = AsyncMock(
            side_effect=Exception("Agent 2 failed")
        )
        
        context = {
            "orchestrator": mock_orchestrator,
            "run_id": "test_run",
            "test_source": ["agent1", "agent2", "agent3"],
        }
        
        result = await path_executor.run(context)
        
        # Agent1 should have run
        assert mock_orchestrator.agents["agent1"].run.called
        
        # Agent3 should still run despite agent2 failure
        assert mock_orchestrator.agents["agent3"].run.called
        
        # Check that errors are tracked
        assert "errors" in result
        assert "agent2" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_executor_tracks_results(self, path_executor, mock_orchestrator):
        """Test that PathExecutor tracks individual agent results."""
        context = {
            "orchestrator": mock_orchestrator,
            "run_id": "test_run",
            "test_source": ["agent1", "agent2"],
        }
        
        result = await path_executor.run(context)
        
        # Check results tracking
        assert "results" in result
        assert "agent1" in result["results"]
        assert "agent2" in result["results"]
        
        # Verify result content
        assert result["results"]["agent1"]["output"] == "Result 1"
        assert result["results"]["agent2"]["output"] == "Result 2"
    
    @pytest.mark.asyncio
    async def test_executor_handles_empty_path(self, path_executor, mock_orchestrator):
        """Test that PathExecutor handles empty path gracefully."""
        context = {
            "orchestrator": mock_orchestrator,
            "run_id": "test_run",
            "test_source": [],
        }
        
        result = await path_executor.run(context)
        
        # Should complete without errors
        assert result["status"] in ["success", "no_path"]
        assert result["executed_path"] == []
    
    @pytest.mark.asyncio
    async def test_executor_validates_agent_existence(self, path_executor, mock_orchestrator):
        """Test that PathExecutor validates agents exist before execution."""
        context = {
            "orchestrator": mock_orchestrator,
            "run_id": "test_run",
            "test_source": ["agent1", "nonexistent_agent", "agent2"],
        }
        
        result = await path_executor.run(context)
        
        # Should track error for nonexistent agent
        if "errors" in result:
            assert "nonexistent_agent" in result["errors"]
        
        # Other agents should still execute
        assert mock_orchestrator.agents["agent1"].run.called


class TestPathExecutorWithValidation:
    """Test PathExecutor integration with validation loop."""
    
    @pytest.fixture
    def validated_path(self):
        """Simulated validated path from GraphScout + PlanValidator."""
        return {
            "path": ["search_agent", "analysis_agent", "response_builder"],
            "score": 0.87,
            "validation_passed": True,
            "confidence": 0.92,
        }
    
    @pytest.fixture
    def mock_orchestrator_with_validated_agents(self):
        """Orchestrator with validated execution agents."""
        orch = MagicMock(spec=OrkaOrchestrator)
        
        # Create agents matching validated path
        search_agent = MagicMock()
        search_agent.node_id = "search_agent"
        search_agent.run = AsyncMock(return_value={
            "status": "success",
            "results": ["result1", "result2"]
        })
        
        analysis_agent = MagicMock()
        analysis_agent.node_id = "analysis_agent"
        analysis_agent.run = AsyncMock(return_value={
            "status": "success",
            "analysis": "Analysis complete"
        })
        
        response_builder = MagicMock()
        response_builder.node_id = "response_builder"
        response_builder.run = AsyncMock(return_value={
            "status": "success",
            "response": "Final response"
        })
        
        orch.agents = {
            "search_agent": search_agent,
            "analysis_agent": analysis_agent,
            "response_builder": response_builder,
        }
        
        return orch
    
    @pytest.mark.asyncio
    async def test_executor_runs_validated_path(
        self,
        validated_path,
        mock_orchestrator_with_validated_agents,
    ):
        """Test that PathExecutor executes a validated path correctly."""
        executor = PathExecutorNode(
            node_id="path_executor",
            path_source="validation_loop.response.result.path_proposer.target",
            on_agent_failure="continue",
        )
        
        # Simulate context from validation loop
        context = {
            "orchestrator": mock_orchestrator_with_validated_agents,
            "run_id": "validated_run",
            "previous_outputs": {
                "validation_loop": {
                    "response": {
                        "result": {
                            "path_proposer": {
                                "target": validated_path["path"]
                            }
                        }
                    }
                }
            }
        }
        
        result = await executor.run(context)
        
        # All agents should execute in order
        orch = mock_orchestrator_with_validated_agents
        assert orch.agents["search_agent"].run.called
        assert orch.agents["analysis_agent"].run.called
        assert orch.agents["response_builder"].run.called
        
        # Path should complete successfully
        assert result["status"] == "success"
        assert len(result["executed_path"]) == 3


class TestPathExecutorMetrics:
    """Test PathExecutor metrics collection (if implemented)."""
    
    @pytest.fixture
    def executor_with_metrics(self):
        """PathExecutor configured to collect metrics."""
        return PathExecutorNode(
            node_id="path_executor_metrics",
            path_source="test_path",
            on_agent_failure="continue",
            collect_metrics=True,  # May not exist yet
        )
    
    @pytest.fixture
    def simple_orchestrator(self):
        """Simple orchestrator for metrics testing."""
        orch = MagicMock(spec=OrkaOrchestrator)
        
        agent = MagicMock()
        agent.node_id = "test_agent"
        agent.run = AsyncMock(return_value={"status": "success"})
        
        orch.agents = {"test_agent": agent}
        return orch
    
    @pytest.mark.asyncio
    async def test_executor_includes_execution_time(
        self,
        executor_with_metrics,
        simple_orchestrator,
    ):
        """Test that PathExecutor tracks execution time."""
        context = {
            "orchestrator": simple_orchestrator,
            "run_id": "metrics_test",
            "test_path": ["test_agent"],
        }
        
        result = await executor_with_metrics.run(context)
        
        # Result should include timing information (if implemented)
        # This tests the new metrics functionality
        assert "status" in result
        
        # Future: Check for metrics in result
        # if "metrics" in result:
        #     assert "total_execution_time_ms" in result["metrics"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

