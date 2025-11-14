"""Unit tests for orka.nodes.join_node."""

import json
from unittest.mock import Mock, AsyncMock

import pytest

from orka.nodes.join_node import JoinNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestJoinNode:
    """Test suite for JoinNode class."""

    def test_init(self):
        """Test JoinNode initialization."""
        mock_memory = Mock()
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        assert node.node_id == "join_node"
        assert node.group_id == "fork_group_123"
        assert node.max_retries == 30  # Default

    def test_init_custom_max_retries(self):
        """Test JoinNode initialization with custom max_retries."""
        mock_memory = Mock()
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            max_retries=50
        )
        
        assert node.max_retries == 50

    @pytest.mark.asyncio
    async def test_run_impl_all_complete(self):
        """Test _run_impl when all agents have completed."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"  # retry count
        mock_memory.hkeys.return_value = ["agent1", "agent2"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        # Mock _complete method
        node._complete = Mock(return_value={"status": "complete", "results": {}})
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "complete"
        mock_memory.hdel.assert_called()

    @pytest.mark.asyncio
    async def test_run_impl_waiting(self):
        """Test _run_impl when agents are still pending."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "0"  # retry count
        mock_memory.hkeys.return_value = ["agent1"]  # Only one received
        mock_memory.smembers.return_value = ["agent1", "agent2"]  # Two expected
        mock_memory.hset = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123"
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "waiting"
        assert "pending" in result
        assert "agent2" in result["pending"]

    @pytest.mark.asyncio
    async def test_run_impl_timeout(self):
        """Test _run_impl when max retries exceeded."""
        mock_memory = Mock()
        mock_memory.hget.return_value = "30"  # At max retries
        mock_memory.hkeys.return_value = ["agent1"]
        mock_memory.smembers.return_value = ["agent1", "agent2"]
        mock_memory.hdel = Mock()
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory,
            group="fork_group_123",
            max_retries=30
        )
        
        input_data = {"fork_group_id": "fork_group_123"}
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "timeout"
        assert "pending" in result

    def test_complete(self):
        """Test _complete method."""
        mock_memory = Mock()
        mock_memory.hget.return_value = json.dumps({
            "response": "result1",
            "status": "success"
        })
        
        node = JoinNode(
            node_id="join_node",
            prompt="Test",
            queue=[],
            memory_logger=mock_memory
        )
        
        fork_targets = ["agent1", "agent2"]
        state_key = "waitfor:join_parallel_checks:inputs"
        
        result = node._complete(fork_targets, state_key)
        
        assert isinstance(result, dict)
        assert "agent1" in result
        assert "agent2" in result

