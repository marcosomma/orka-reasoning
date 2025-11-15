"""Unit tests for orka.nodes.failover_node."""

from unittest.mock import Mock, AsyncMock

import pytest

from orka.nodes.failover_node import FailoverNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestFailoverNode:
    """Test suite for FailoverNode class."""

    def test_init(self):
        """Test FailoverNode initialization."""
        child1 = Mock()
        child2 = Mock()
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child1, child2],
            queue=[],
            prompt="Test"
        )
        
        assert node.node_id == "failover_node"
        assert len(node.children) == 2
        assert node.agent_id == "failover_node"

    def test_init_no_children(self):
        """Test FailoverNode initialization with no children."""
        node = FailoverNode(
            node_id="failover_node",
            children=None,
            queue=[]
        )
        
        assert node.children == []

    @pytest.mark.asyncio
    async def test_run_impl_first_child_succeeds(self):
        """Test _run_impl when first child succeeds."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"result": "success"})
        child1.agent_id = "child1"
        child1.prompt = None
        
        child2 = Mock()
        child2.agent_id = "child2"
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child1, child2],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert result["result"] == {"result": "success"}
        assert result["successful_child"] == "child1"
        child1.run.assert_called_once()
        # child2 should not be called
        assert not hasattr(child2, 'run') or not child2.run.called

    @pytest.mark.asyncio
    async def test_run_impl_second_child_succeeds(self):
        """Test _run_impl when first child fails, second succeeds."""
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("Child1 failed"))
        child1.agent_id = "child1"
        child1.prompt = None
        
        child2 = Mock()
        child2.run = AsyncMock(return_value={"result": "success"})
        child2.agent_id = "child2"
        child2.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child1, child2],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert result["result"] == {"result": "success"}
        assert result["successful_child"] == "child2"
        child1.run.assert_called_once()
        child2.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impl_all_fail(self):
        """Test _run_impl when all children fail."""
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("Child1 failed"))
        child1.agent_id = "child1"
        child1.prompt = None
        
        child2 = Mock()
        child2.run = AsyncMock(side_effect=Exception("Child2 failed"))
        child2.agent_id = "child2"
        child2.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child1, child2],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert "error" in result["result"].lower() or "failed" in result["result"].lower()

    def test_is_valid_result(self):
        """Test _is_valid_result method."""
        node = FailoverNode(
            node_id="failover_node",
            children=[],
            queue=[]
        )
        
        assert node._is_valid_result({"result": "data"}) is True
        assert node._is_valid_result(None) is False
        assert node._is_valid_result("") is False
        assert node._is_valid_result({}) is False

