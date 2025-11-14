"""Unit tests for orka.tools.base_tool."""

from unittest.mock import Mock, patch

import pytest

from orka.tools.base_tool import BaseTool

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class ConcreteTool(BaseTool):
    """Concrete implementation of BaseTool for testing."""
    
    def _run_impl(self, input_data):
        """Implementation for testing."""
        return f"Processed: {input_data}"


class TestBaseTool:
    """Test suite for BaseTool class."""

    def test_init(self):
        """Test BaseTool initialization."""
        tool = ConcreteTool(tool_id="test_tool", prompt="Test prompt", queue=["next_tool"])
        
        assert tool.tool_id == "test_tool"
        assert tool.prompt == "Test prompt"
        assert tool.queue == ["next_tool"]
        assert tool.type == "concretetool"

    def test_init_with_kwargs(self):
        """Test BaseTool initialization with additional kwargs."""
        tool = ConcreteTool(
            tool_id="test_tool",
            prompt="Test",
            queue=[],
            max_results=5,
            timeout=10,
        )
        
        assert tool.params["max_results"] == 5
        assert tool.params["timeout"] == 10

    def test_run_success(self):
        """Test run method with successful execution."""
        tool = ConcreteTool(tool_id="test_tool", prompt="Test", queue=[])
        
        with patch('orka.tools.base_tool.ResponseBuilder.create_success_response') as mock_create:
            mock_create.return_value = {
                "component_type": "tool",
                "status": "success",
                "result": "Processed: test input",
            }
            
            result = tool.run("test input")
            
            assert result["status"] == "success"
            mock_create.assert_called_once()

    def test_run_exception(self):
        """Test run method handles exceptions."""
        class FailingTool(BaseTool):
            def _run_impl(self, input_data):
                raise ValueError("Test error")
        
        tool = FailingTool(tool_id="failing_tool", prompt="Test", queue=[])
        
        with patch('orka.tools.base_tool.ResponseBuilder.create_error_response') as mock_create:
            mock_create.return_value = {
                "component_type": "tool",
                "status": "error",
                "error": "Test error",
            }
            
            result = tool.run("test input")
            
            assert result["status"] == "error"
            mock_create.assert_called_once()

    def test_repr(self):
        """Test __repr__ method."""
        tool = ConcreteTool(tool_id="test_tool", prompt="Test", queue=[])
        
        repr_str = repr(tool)
        
        assert "ConcreteTool" in repr_str
        assert "test_tool" in repr_str

