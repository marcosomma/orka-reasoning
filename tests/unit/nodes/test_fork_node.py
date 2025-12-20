"""Unit tests for orka.nodes.fork_node."""

import json
from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.fork_node import ForkNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestForkNode:
    """Test suite for ForkNode class."""

    def test_init(self):
        """Test ForkNode initialization."""
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1", "agent2"], ["agent3"]]
        )
        
        assert node.node_id == "fork_node"
        assert node.targets == [["agent1", "agent2"], ["agent3"]]
        assert node.mode == "sequential"  # Default

    def test_init_parallel_mode(self):
        """Test ForkNode initialization with parallel mode."""
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1"], ["agent2"]],
            mode="parallel"
        )
        
        assert node.mode == "parallel"

    @pytest.mark.asyncio
    async def test_run_impl(self):
        """Test _run_impl method."""
        mock_orchestrator = Mock()
        mock_fork_manager = Mock()
        mock_fork_manager.generate_group_id.return_value = "fork_group_123"
        mock_orchestrator.fork_manager = mock_fork_manager
        mock_orchestrator.enqueue_fork = Mock()
        
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1", "agent2"]]
        )
        
        context = {
            "orchestrator": mock_orchestrator,
            "input": "test"
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "forked"
        assert "fork_group" in result
        mock_fork_manager.create_group.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impl_no_targets(self):
        """Test _run_impl raises ValueError when no targets."""
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[]
        )
        
        context = {
            "orchestrator": Mock(),
        }
        
        with pytest.raises(ValueError, match="requires non-empty 'targets' list"):
            await node._run_impl(context)

    @pytest.mark.asyncio
    async def test_run_impl_no_orchestrator(self):
        """Test _run_impl raises ValueError when orchestrator missing."""
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1"]]
        )
        
        context = {}
        
        with pytest.raises(ValueError, match="requires orchestrator in context"):
            await node._run_impl(context)

    @pytest.mark.asyncio
    async def test_run_impl_sequential_mode(self):
        """Test _run_impl in sequential mode."""
        mock_orchestrator = Mock()
        mock_fork_manager = Mock()
        mock_fork_manager.generate_group_id.return_value = "fork_group_123"
        mock_orchestrator.fork_manager = mock_fork_manager
        mock_orchestrator.enqueue_fork = Mock()
        
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1", "agent2"]],
            mode="sequential"
        )
        
        context = {
            "orchestrator": mock_orchestrator,
        }
        
        result = await node._run_impl(context)
        
        # In sequential mode, should only queue first agent
        assert result["status"] == "forked"
        mock_fork_manager.track_branch_sequence.assert_called_once()
        # The orchestrator should be requested to enqueue the first branch agent
        mock_orchestrator.enqueue_fork.assert_called_once_with(["agent1"], "fork_group_123")

    @pytest.mark.asyncio
    async def test_run_impl_with_memory_logger(self):
        """Test _run_impl with memory logger."""
        mock_orchestrator = Mock()
        mock_fork_manager = Mock()
        mock_fork_manager.generate_group_id.return_value = "fork_group_123"
        mock_orchestrator.fork_manager = mock_fork_manager
        mock_orchestrator.enqueue_fork = Mock()
        
        mock_memory = Mock()
        mock_memory.hset = Mock()
        mock_memory.sadd = Mock()
        mock_memory.set = Mock()
        
        node = ForkNode(
            node_id="fork_node",
            prompt="Test",
            queue=[],
            targets=[["agent1"]],
            memory_logger=mock_memory
        )
        
        context = {
            "orchestrator": mock_orchestrator,
        }
        
        result = await node._run_impl(context)
        
        assert result["status"] == "forked"
        mock_memory.hset.assert_called()
        mock_memory.sadd.assert_called()

