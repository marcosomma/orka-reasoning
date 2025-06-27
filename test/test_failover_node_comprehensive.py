"""
Comprehensive tests for OrKa FailoverNode to achieve high coverage.
This file targets the uncovered functions and error paths in failover_node.py.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.nodes.failover_node import FailoverNode


class TestFailoverNodeInitialization:
    """Test failover node initialization scenarios."""

    def test_init_with_children_list(self):
        """Test initialization with a list of children."""
        child1 = Mock()
        child1.node_id = "child1"
        child1.agent_id = "child1"
        child2 = Mock()
        child2.node_id = "child2"
        child2.agent_id = "child2"
        children = [child1, child2]

        node = FailoverNode(
            node_id="failover_test",
            children=children,
            queue=["agent1", "agent2"],
            prompt="Test failover node",
        )

        assert node.node_id == "failover_test"
        assert node.children == children
        assert len(node.children) == 2
        assert node.agent_id == "failover_test"

    def test_init_with_no_children(self):
        """Test initialization with no children provided."""
        node = FailoverNode(node_id="empty_failover")

        assert node.node_id == "empty_failover"
        assert node.children == []
        assert node.agent_id == "empty_failover"

    def test_init_with_additional_kwargs(self):
        """Test initialization with additional keyword arguments."""
        node = FailoverNode(
            node_id="failover_kwargs",
            children=[],
            custom_param="test_value",
            retry_count=3,
        )

        assert node.node_id == "failover_kwargs"
        assert "custom_param" in node.params
        assert node.params["custom_param"] == "test_value"
        assert node.params["retry_count"] == 3


class TestFailoverNodeAsyncExecution:
    """Test async execution and child handling."""

    @pytest.mark.asyncio
    async def test_successful_first_child(self):
        """Test successful execution with first child."""
        # Create mock children
        child1 = Mock()
        child1.run = AsyncMock(return_value={"result": "success", "data": "test"})
        child1.node_id = "child1"
        child1.agent_id = "child1"

        child2 = Mock()
        child2.run = AsyncMock()  # Should not be called
        child2.agent_id = "child2"

        node = FailoverNode(
            node_id="failover_success",
            children=[child1, child2],
        )

        result = await node.run({"input": "test"})

        # Verify result structure
        assert result["result"] == {"result": "success", "data": "test"}
        assert result["successful_child"] == "child1"
        assert result["child1"] == {"result": "success", "data": "test"}

        # Verify only first child was called (includes formatted_prompt)
        child1.run.assert_called_once()
        args, kwargs = child1.run.call_args
        assert args[0]["input"] == "test"
        assert "formatted_prompt" in args[0]
        child2.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_failover_to_second_child(self):
        """Test failover when first child fails."""
        # Create mock children
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("Child 1 failed"))
        child1.node_id = "child1"
        child1.agent_id = "child1"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"result": "success from child2"})
        child2.node_id = "child2"
        child2.agent_id = "child2"

        node = FailoverNode(
            node_id="failover_test",
            children=[child1, child2],
        )

        result = await node.run({"input": "test"})

        # Verify second child's result was returned
        assert result["result"] == {"result": "success from child2"}
        assert result["successful_child"] == "child2"
        assert result["child2"] == {"result": "success from child2"}

        # Verify both children were called
        child1.run.assert_called_once()
        child2.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_children_fail(self):
        """Test when all children fail."""
        # Create mock children that all fail
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("Child 1 failed"))
        child1.node_id = "child1"
        child1.agent_id = "child1"

        child2 = Mock()
        child2.run = AsyncMock(side_effect=Exception("Child 2 failed"))
        child2.node_id = "child2"
        child2.agent_id = "child2"

        node = FailoverNode(
            node_id="failover_all_fail",
            children=[child1, child2],
        )

        result = await node.run({"input": "test"})

        # Verify error result structure
        assert result["status"] == "failed"
        assert result["successful_child"] is None
        assert "All fallback agents failed" in result["result"]
        assert "Child 2 failed" in result["error"]

        # Verify both children were called
        child1.run.assert_called_once()
        child2.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit detection and delay."""
        # Create child that fails with rate limit error
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("Rate limit exceeded"))
        child1.node_id = "child1"
        child1.agent_id = "child1"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"result": "success after delay"})
        child2.node_id = "child2"
        child2.agent_id = "child2"

        node = FailoverNode(
            node_id="failover_ratelimit",
            children=[child1, child2],
        )

        with patch("asyncio.sleep") as mock_sleep:
            result = await node.run({"input": "test"})

        # Verify rate limit delay was triggered
        mock_sleep.assert_called_once_with(2)

        # Verify successful result from second child
        assert result["successful_child"] == "child2"

    @pytest.mark.asyncio
    async def test_sync_child_execution(self):
        """Test execution with synchronous child methods."""
        # Create child with synchronous run method
        child1 = Mock()
        child1.run = Mock(return_value={"result": "sync success"})
        child1.node_id = "sync_child"
        child1.agent_id = "sync_child"

        node = FailoverNode(
            node_id="failover_sync",
            children=[child1],
        )

        result = await node.run({"input": "test"})

        # Verify sync method was called and result returned
        assert result["result"] == {"result": "sync success"}
        assert result["successful_child"] == "sync_child"
        child1.run.assert_called_once()
        args, kwargs = child1.run.call_args
        assert args[0]["input"] == "test"
        assert "formatted_prompt" in args[0]

    @pytest.mark.asyncio
    async def test_child_without_run_method(self):
        """Test handling of child without run method."""
        # Create child without run method
        child1 = Mock(spec=[])  # spec=[] means no methods
        child1.node_id = "invalid_child"
        child1.agent_id = "invalid_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"result": "backup success"})
        child2.node_id = "backup_child"
        child2.agent_id = "backup_child"

        node = FailoverNode(
            node_id="failover_invalid",
            children=[child1, child2],
        )

        result = await node.run({"input": "test"})

        # Should skip invalid child and use backup
        assert result["successful_child"] == "backup_child"

    @pytest.mark.asyncio
    async def test_child_without_node_id(self):
        """Test handling of child without node_id attribute."""
        # Create child without node_id/agent_id using spec=[] to prevent auto-attribute creation
        child1 = Mock(spec=["run"])
        child1.run = AsyncMock(return_value={"result": "success"})
        # Don't set node_id or agent_id attribute

        node = FailoverNode(
            node_id="failover_no_id",
            children=[child1],
        )

        result = await node.run({"input": "test"})

        # Should still work with generated child ID
        assert result["result"] == {"result": "success"}
        assert "unknown_child_0" in str(result["successful_child"])


class TestFailoverNodeResultValidation:
    """Test result validation logic."""

    @pytest.mark.asyncio
    async def test_valid_dict_result(self):
        """Test validation of valid dictionary result."""
        child = Mock()
        child.run = AsyncMock(return_value={"response": "valid content", "status": "success"})
        child.node_id = "valid_child"
        child.agent_id = "valid_child"

        node = FailoverNode(node_id="test", children=[child])
        result = await node.run({})

        assert result["result"] == {"response": "valid content", "status": "success"}
        assert result["successful_child"] == "valid_child"

    @pytest.mark.asyncio
    async def test_invalid_empty_response(self):
        """Test rejection of empty response."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"response": ""})
        child1.node_id = "empty_child"
        child1.agent_id = "empty_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"response": "valid content"})
        child2.node_id = "valid_child"
        child2.agent_id = "valid_child"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "valid_child"

    @pytest.mark.asyncio
    async def test_invalid_none_response(self):
        """Test rejection of None response."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"response": None})
        child1.node_id = "none_child"
        child1.agent_id = "none_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"response": "valid content"})
        child2.node_id = "valid_child"
        child2.agent_id = "valid_child"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "valid_child"

    @pytest.mark.asyncio
    async def test_invalid_html_content(self):
        """Test rejection of HTML content."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"response": "<html>Some HTML tag content</html>"})
        child1.node_id = "html_child"
        child1.agent_id = "html_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"response": "Clean text content"})
        child2.node_id = "clean_child"
        child2.agent_id = "clean_child"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "clean_child"

    @pytest.mark.asyncio
    async def test_invalid_error_status(self):
        """Test rejection of error status."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"status": "error", "message": "Something went wrong"})
        child1.node_id = "error_child"
        child1.agent_id = "error_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"status": "success", "data": "Good result"})
        child2.node_id = "success_child"
        child2.agent_id = "success_child"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "success_child"

    @pytest.mark.asyncio
    async def test_invalid_nested_empty_response(self):
        """Test rejection of nested empty response."""
        child1 = Mock()
        child1.run = AsyncMock(return_value={"result": {"response": "NONE"}})
        child1.node_id = "nested_empty"
        child1.agent_id = "nested_empty"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"result": {"response": "Valid nested content"}})
        child2.node_id = "nested_valid"
        child2.agent_id = "nested_valid"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "nested_valid"

    @pytest.mark.asyncio
    async def test_invalid_list_with_error_messages(self):
        """Test rejection of list containing error messages."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=["Connection failed", "Timeout occurred"])
        child1.node_id = "error_list"
        child1.agent_id = "error_list"

        child2 = Mock()
        child2.run = AsyncMock(return_value=["Valid result", "Success message"])
        child2.node_id = "valid_list"
        child2.agent_id = "valid_list"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "valid_list"

    @pytest.mark.asyncio
    async def test_invalid_string_with_error_indicators(self):
        """Test rejection of string with error indicators."""
        child1 = Mock()
        child1.run = AsyncMock(return_value="Rate limit exceeded - try again later")
        child1.node_id = "error_string"
        child1.agent_id = "error_string"

        child2 = Mock()
        child2.run = AsyncMock(return_value="Operation completed successfully")
        child2.node_id = "success_string"
        child2.agent_id = "success_string"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "success_string"

    @pytest.mark.asyncio
    async def test_invalid_html_in_list(self):
        """Test rejection of HTML content in list items."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=["<input type='text'>", "Some HTML tag content"])
        child1.node_id = "html_list"
        child1.agent_id = "html_list"

        child2 = Mock()
        child2.run = AsyncMock(return_value=["Clean text 1", "Clean text 2"])
        child2.node_id = "clean_list"
        child2.agent_id = "clean_list"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "clean_list"

    @pytest.mark.asyncio
    async def test_empty_list_rejection(self):
        """Test rejection of empty list."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=[])
        child1.node_id = "empty_list"
        child1.agent_id = "empty_list"

        child2 = Mock()
        child2.run = AsyncMock(return_value=["Valid item"])
        child2.node_id = "valid_list"
        child2.agent_id = "valid_list"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "valid_list"

    @pytest.mark.asyncio
    async def test_none_result_rejection(self):
        """Test rejection of None result."""
        child1 = Mock()
        child1.run = AsyncMock(return_value=None)
        child1.node_id = "none_result"
        child1.agent_id = "none_result"

        child2 = Mock()
        child2.run = AsyncMock(return_value="Valid result")
        child2.node_id = "valid_result"
        child2.agent_id = "valid_result"

        node = FailoverNode(node_id="test", children=[child1, child2])
        result = await node.run({})

        assert result["successful_child"] == "valid_result"


class TestFailoverNodeEdgeCases:
    """Test edge cases and complex scenarios."""

    @pytest.mark.asyncio
    async def test_no_children_provided(self):
        """Test behavior with no children."""
        node = FailoverNode(node_id="no_children", children=[])
        result = await node.run({"input": "test"})

        assert result["status"] == "failed"
        assert result["successful_child"] is None

    @pytest.mark.asyncio
    async def test_large_number_of_children(self):
        """Test with many children where last one succeeds."""
        children = []
        for i in range(10):
            child = Mock()
            if i < 9:  # First 9 fail
                child.run = AsyncMock(side_effect=Exception(f"Child {i} failed"))
            else:  # Last one succeeds
                child.run = AsyncMock(return_value={"result": f"success from child {i}"})
            child.node_id = f"child_{i}"
            child.agent_id = f"child_{i}"
            children.append(child)

        node = FailoverNode(node_id="many_children", children=children)
        result = await node.run({"input": "test"})

        assert result["successful_child"] == "child_9"
        assert result["result"] == {"result": "success from child 9"}

    @pytest.mark.asyncio
    async def test_child_returns_complex_data_structure(self):
        """Test with complex return data."""
        child = Mock()
        complex_result = {
            "response": "valid response",
            "metadata": {"timestamp": "2023-01-01", "agent": "test"},
            "nested": {"data": [1, 2, 3], "info": {"status": "ok"}},
        }
        child.run = AsyncMock(return_value=complex_result)
        child.node_id = "complex_child"
        child.agent_id = "complex_child"

        node = FailoverNode(node_id="complex_test", children=[child])
        result = await node.run({"input": "test"})

        assert result["result"] == complex_result
        assert result["successful_child"] == "complex_child"

    @pytest.mark.asyncio
    async def test_exception_during_result_validation(self):
        """Test handling of exceptions during result validation."""
        child1 = Mock()
        # Create a result that might cause validation errors
        problematic_result = Mock()
        problematic_result.__str__ = Mock(side_effect=Exception("String conversion error"))
        child1.run = AsyncMock(return_value=problematic_result)
        child1.node_id = "problematic_child"
        child1.agent_id = "problematic_child"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"response": "backup result"})
        child2.node_id = "backup_child"
        child2.agent_id = "backup_child"

        node = FailoverNode(node_id="validation_error", children=[child1, child2])

        # Should handle validation error and proceed to next child
        result = await node.run({"input": "test"})
        assert result["successful_child"] == "backup_child"

    @pytest.mark.asyncio
    async def test_input_data_preservation(self):
        """Test that input data is preserved and passed correctly."""
        child1 = Mock()
        child1.run = AsyncMock(side_effect=Exception("First child fails"))
        child1.node_id = "child1"
        child1.agent_id = "child1"

        child2 = Mock()
        child2.run = AsyncMock(return_value={"input_received": True})
        child2.node_id = "child2"
        child2.agent_id = "child2"

        node = FailoverNode(node_id="data_preservation", children=[child1, child2])

        test_input = {"complex": {"nested": "data"}, "list": [1, 2, 3]}
        result = await node.run(test_input)

        # Verify both children received the same input (with formatted_prompt added)
        child1.run.assert_called_once()
        child2.run.assert_called_once()

        # Check that both children received the original input data (plus formatted_prompt)
        child1_args, _ = child1.run.call_args
        child2_args, _ = child2.run.call_args

        assert child1_args[0]["complex"] == test_input["complex"]
        assert child1_args[0]["list"] == test_input["list"]
        assert "formatted_prompt" in child1_args[0]

        assert child2_args[0]["complex"] == test_input["complex"]
        assert child2_args[0]["list"] == test_input["list"]
        assert "formatted_prompt" in child2_args[0]

        assert result["successful_child"] == "child2"
