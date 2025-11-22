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

    @pytest.mark.asyncio
    async def test_run_impl_child_with_prompt(self):
        """Test _run_impl with child that has prompt template."""
        child = Mock()
        child.run = AsyncMock(return_value={"result": "success"})
        child.agent_id = "child1"
        child.prompt = "Process: {{ input }}"
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child],
            queue=[]
        )
        
        input_data = {"input": "test_data"}
        
        result = await node._run_impl(input_data)
        
        assert result["successful_child"] == "child1"
        # Verify formatted_prompt was added to payload
        call_args = child.run.call_args[0][0]
        assert "formatted_prompt" in call_args

    @pytest.mark.asyncio
    async def test_run_impl_prompt_rendering_fails(self):
        """Test _run_impl when prompt rendering fails but continues."""
        child = Mock()
        child.run = AsyncMock(return_value={"result": "success"})
        child.agent_id = "child1"
        child.prompt = "{{ undefined_variable }}"  # Will cause Jinja2 error
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        # Should still succeed with fallback prompt
        assert result["successful_child"] == "child1"
        call_args = child.run.call_args[0][0]
        assert "formatted_prompt" in call_args

    @pytest.mark.asyncio
    async def test_run_impl_child_without_run_method(self):
        """Test _run_impl with child that has no run method."""
        child1 = Mock(spec=[])  # No run method
        child1.agent_id = "broken_child"
        
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
        
        # Should skip child1 and succeed with child2
        assert result["successful_child"] == "child2"

    @pytest.mark.asyncio
    async def test_run_impl_sync_child_run_method(self):
        """Test _run_impl with synchronous child run method."""
        child = Mock()
        child.run = Mock(return_value={"result": "sync_success"})  # Sync method
        child.agent_id = "sync_child"
        child.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert result["successful_child"] == "sync_child"
        assert result["result"] == {"result": "sync_success"}

    @pytest.mark.asyncio
    async def test_run_impl_empty_result(self):
        """Test _run_impl when child returns empty result."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=None)  # Empty result
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
        
        # Should skip child1 (empty) and use child2
        assert result["successful_child"] == "child2"

    @pytest.mark.asyncio
    async def test_run_impl_rate_limit_error(self):
        """Test _run_impl handles rate limit errors with delay."""
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("RateLimit exceeded"))
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
        
        # Should detect rate limit and continue
        assert result["successful_child"] == "child2"

    def test_is_valid_result_status_error(self):
        """Test _is_valid_result rejects status=error."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result({"status": "error"}) is False

    def test_is_valid_result_none_response(self):
        """Test _is_valid_result rejects None/NONE responses."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result({"response": None}) is False
        assert node._is_valid_result({"response": "NONE"}) is False
        assert node._is_valid_result({"response": ""}) is False

    def test_is_valid_result_html_response(self):
        """Test _is_valid_result rejects HTML content."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result({"response": "<html>tag content</html>"}) is False

    def test_is_valid_result_nested_result_none(self):
        """Test _is_valid_result rejects nested None response."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result({
            "result": {"response": None}
        }) is False

    def test_is_valid_result_nested_html(self):
        """Test _is_valid_result rejects nested HTML."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result({
            "result": {"response": "<div>HTML tag</div>"}
        }) is False

    def test_is_valid_result_empty_list(self):
        """Test _is_valid_result rejects empty list."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result([]) is False

    def test_is_valid_result_list_with_error(self):
        """Test _is_valid_result rejects list with error messages."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result(["Result failed to process"]) is False
        assert node._is_valid_result(["Error occurred"]) is False
        assert node._is_valid_result(["Rate limit exceeded"]) is False
        assert node._is_valid_result(["Connection timeout"]) is False
        assert node._is_valid_result(["404 Not Found"]) is False

    def test_is_valid_result_list_with_html(self):
        """Test _is_valid_result rejects list with HTML content."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        # Must have HTML tags (<>) AND HTML indicators
        assert node._is_valid_result(["<input> tag element"]) is False
        assert node._is_valid_result(["<form> HTML attribute"]) is False
        assert node._is_valid_result(["<div> javascript code</div>"]) is False

    def test_is_valid_result_list_valid(self):
        """Test _is_valid_result accepts valid list."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result(["valid data", "more data"]) is True

    def test_is_valid_result_string_none(self):
        """Test _is_valid_result rejects NONE string."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result("NONE") is False

    def test_is_valid_result_string_error(self):
        """Test _is_valid_result rejects error strings."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result("Request failed") is False
        assert node._is_valid_result("Error processing") is False
        assert node._is_valid_result("503 Service Unavailable") is False

    def test_is_valid_result_string_html(self):
        """Test _is_valid_result rejects HTML strings."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result("<html>tag</html>") is False

    def test_is_valid_result_string_valid(self):
        """Test _is_valid_result accepts valid string."""
        node = FailoverNode(node_id="test", children=[], queue=[])
        
        assert node._is_valid_result("Valid response data") is True

    @pytest.mark.asyncio
    async def test_run_impl_child_with_node_id_fallback(self):
        """Test _run_impl uses node_id when agent_id not available."""
        child = Mock(spec=['run', 'node_id', 'prompt'])
        child.run = AsyncMock(return_value={"result": "success"})
        child.node_id = "child_node"
        child.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert result["successful_child"] == "child_node"

    @pytest.mark.asyncio
    async def test_run_impl_child_unknown_id(self):
        """Test _run_impl with child having neither agent_id nor node_id."""
        child = Mock(spec=['run', 'prompt'])
        child.run = AsyncMock(return_value={"result": "success"})
        child.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        # Should use unknown_child_0 as fallback
        assert "unknown_child_0" in result["successful_child"]

    @pytest.mark.asyncio
    async def test_run_impl_all_fail_no_error(self):
        """Test _run_impl all children fail without exception."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=None)  # Invalid result
        child1.agent_id = "child1"
        child1.prompt = None
        
        child2 = Mock()
        child2.run = AsyncMock(return_value={})  # Empty dict
        child2.agent_id = "child2"
        child2.prompt = None
        
        node = FailoverNode(
            node_id="failover_node",
            children=[child1, child2],
            queue=[]
        )
        
        input_data = {"input": "test"}
        
        result = await node._run_impl(input_data)
        
        assert result["status"] == "failed"
        assert result["successful_child"] is None
        assert "error" in result

