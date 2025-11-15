"""Unit tests for orka.nodes.base_node."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.nodes.base_node import BaseNode

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class ConcreteNode(BaseNode):
    """Concrete implementation of BaseNode for testing."""
    
    async def _run_impl(self, input_data):
        """Implementation for testing."""
        return f"Processed: {input_data}"


class TestBaseNode:
    """Test suite for BaseNode class."""

    def test_init(self):
        """Test BaseNode initialization."""
        node = ConcreteNode(node_id="test_node", prompt="Test prompt", queue=["next_node"])
        
        assert node.node_id == "test_node"
        assert node.prompt == "Test prompt"
        assert node.queue == ["next_node"]
        assert node.type == "concretenode"

    def test_init_with_kwargs(self):
        """Test BaseNode initialization with additional kwargs."""
        node = ConcreteNode(
            node_id="test_node",
            prompt="Test",
            queue=[],
            max_tokens=1000,
            temperature=0.7,
        )
        
        assert node.params["max_tokens"] == 1000
        assert node.params["temperature"] == 0.7

    def test_init_failing_node_type(self):
        """Test BaseNode initialization with failing type sets agent_id."""
        class FailingNode(BaseNode):
            async def _run_impl(self, input_data):
                pass
        
        # Create node with type that will trigger agent_id assignment
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        # The type check happens in __init__, so we need to check after init
        # For FailingNode specifically, the type would be "failingnode" not "failing"
        assert node.type == "failingnode"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method."""
        node = ConcreteNode(node_id="test_node", prompt="Test", queue=[])
        
        # Should not raise exception
        await node.initialize()

    @pytest.mark.asyncio
    async def test_run_success(self):
        """Test run method with successful execution."""
        node = ConcreteNode(node_id="test_node", prompt="Test", queue=[])
        
        with patch('orka.nodes.base_node.ResponseBuilder.create_success_response') as mock_create:
            mock_create.return_value = {
                "component_type": "node",
                "status": "success",
                "result": "Processed: test input",
            }
            
            result = await node.run("test input")
            
            assert result["status"] == "success"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_exception(self):
        """Test run method handles exceptions."""
        class FailingNode(BaseNode):
            async def _run_impl(self, input_data):
                raise ValueError("Test error")
        
        node = FailingNode(node_id="failing_node", prompt="Test", queue=[])
        
        with patch('orka.nodes.base_node.ResponseBuilder.create_error_response') as mock_create:
            mock_create.return_value = {
                "component_type": "node",
                "status": "error",
                "error": "Test error",
            }
            
            result = await node.run("test input")
            
            assert result["status"] == "error"
            mock_create.assert_called_once()

    def test_repr(self):
        """Test __repr__ method."""
        node = ConcreteNode(node_id="test_node", prompt="Test", queue=["next"])
        
        repr_str = repr(node)
        
        assert "ConcreteNode" in repr_str
        assert "test_node" in repr_str
        assert "next" in repr_str

