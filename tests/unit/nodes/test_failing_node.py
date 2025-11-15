"""Unit tests for orka.nodes.failing_node."""

import asyncio
from unittest.mock import Mock, patch

import pytest

from orka.nodes.failing_node import FailingNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestFailingNode:
    """Test suite for FailingNode class."""

    def test_init(self):
        """Test FailingNode initialization."""
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        
        assert node.node_id == "failing_node"
        assert node.type == "failingnode"

    def test_id_property(self):
        """Test id property."""
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        
        # Should return node_id or agent_id
        assert node.id == "failing_node"

    def test_id_property_with_agent_id(self):
        """Test id property when agent_id is set."""
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        node.agent_id = "agent_123"
        
        assert node.id == "agent_123"

    @pytest.mark.asyncio
    async def test_run_impl_raises_error(self):
        """Test _run_impl raises RuntimeError."""
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(RuntimeError, match="failed intentionally"):
                await node._run_impl("test input")

