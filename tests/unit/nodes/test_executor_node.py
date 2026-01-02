"""Unit tests for orka.nodes.executor_node (StreamingExecutorNode)."""

import pytest

from orka.nodes.executor_node import StreamingExecutorNode

pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestStreamingExecutorNode:
    """Test suite for StreamingExecutorNode class."""

    def test_init(self):
        """Test StreamingExecutorNode initialization."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        assert node.node_id == "executor"
        assert node.prompt == "Execute"
        assert node.type == "streamingexecutornode"

    @pytest.mark.asyncio
    async def test_run_impl_with_sections_dict(self):
        """Test _run_impl with proper composer output containing sections."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = {
            "sections": {
                "system": "System prompt",
                "context": "Context info",
                "task": "Task description"
            },
            "total_tokens": 150
        }
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert "used_sections" in result
        assert set(result["used_sections"]) == {"system", "context", "task"}
        assert result["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_run_impl_with_sections_no_total_tokens(self):
        """Test _run_impl with sections but missing total_tokens."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = {
            "sections": {
                "system": "System prompt"
            }
        }
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert result["used_sections"] == ["system"]
        assert result["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_run_impl_with_empty_sections(self):
        """Test _run_impl with empty sections dict."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = {
            "sections": {},
            "total_tokens": 0
        }
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert result["used_sections"] == []
        assert result["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_run_impl_with_non_dict_input(self):
        """Test _run_impl with non-dict input (fallback echo)."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = "plain string input"
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert result["echo"] == "plain string input"

    @pytest.mark.asyncio
    async def test_run_impl_with_dict_missing_sections(self):
        """Test _run_impl with dict input but no 'sections' key (fallback echo)."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = {
            "other_field": "value",
            "total_tokens": 100
        }
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert "echo" in result
        assert "other_field" in result["echo"]

    @pytest.mark.asyncio
    async def test_run_impl_with_list_input(self):
        """Test _run_impl with list input (fallback echo)."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = ["item1", "item2", "item3"]
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert "echo" in result
        assert "item1" in result["echo"]

    @pytest.mark.asyncio
    async def test_run_impl_with_none_input(self):
        """Test _run_impl with None input (fallback echo)."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = None
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert result["echo"] == "None"

    @pytest.mark.asyncio
    async def test_run_impl_with_numeric_input(self):
        """Test _run_impl with numeric input (fallback echo)."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = 42
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "ok"
        assert result["echo"] == "42"

    @pytest.mark.asyncio
    async def test_run_method_calls_run_impl(self):
        """Test that run() method properly invokes _run_impl()."""
        node = StreamingExecutorNode(node_id="executor", prompt="Execute", queue=[])
        
        input_data = {
            "sections": {"main": "content"},
            "total_tokens": 50
        }
        
        # Call the public run method instead of _run_impl
        result = await node.run(input_data)
        
        # The run method returns OrkaResponse with "success" status
        assert result["status"] == "success"
        assert "result" in result
        assert result["result"]["status"] == "ok"
        assert "used_sections" in result["result"]
        assert result["result"]["used_sections"] == ["main"]

    def test_init_with_kwargs(self):
        """Test StreamingExecutorNode initialization with additional kwargs."""
        node = StreamingExecutorNode(
            node_id="executor",
            prompt="Execute",
            queue=["next_node"],
            custom_param="custom_value"
        )
        
        assert node.node_id == "executor"
        assert node.queue == ["next_node"]
        assert node.params.get("custom_param") == "custom_value"
