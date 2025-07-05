"""
Comprehensive tests for FailoverNode class to improve coverage.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.nodes.failover_node import FailoverNode


class TestFailoverNodeInitialization:
    """Test FailoverNode initialization scenarios."""

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        children = [Mock(), Mock()]
        queue = [Mock()]
        prompt = "test prompt"

        node = FailoverNode(
            node_id="test_node",
            children=children,
            queue=queue,
            prompt=prompt,
            extra_param="extra_value",
        )

        assert node.node_id == "test_node"
        assert node.agent_id == "test_node"
        assert node.children == children
        assert node.prompt == prompt
        assert len(node.children) == 2

    def test_init_with_minimal_parameters(self):
        """Test initialization with minimal parameters."""
        node = FailoverNode(node_id="minimal_node")

        assert node.node_id == "minimal_node"
        assert node.agent_id == "minimal_node"
        assert node.children == []
        assert node.prompt == ""

    def test_init_with_none_parameters(self):
        """Test initialization with None parameters."""
        node = FailoverNode(
            node_id="none_node",
            children=None,
            queue=None,
            prompt=None,
        )

        assert node.node_id == "none_node"
        assert node.agent_id == "none_node"
        assert node.children == []
        assert node.prompt == ""

    def test_init_with_empty_lists(self):
        """Test initialization with empty lists."""
        node = FailoverNode(
            node_id="empty_node",
            children=[],
            queue=[],
        )

        assert node.node_id == "empty_node"
        assert node.children == []


class TestFailoverNodeRun:
    """Test FailoverNode run method scenarios."""

    @pytest.fixture
    def input_data(self):
        """Fixture providing test input data."""
        return {"test_key": "test_value", "input": "test input"}

    @pytest.fixture
    def success_child(self):
        """Fixture providing a mock child that succeeds."""
        child = Mock()
        child.agent_id = "success_child"
        child.run = AsyncMock(return_value={"response": "success response"})
        return child

    @pytest.fixture
    def sync_success_child(self):
        """Fixture providing a synchronous mock child that succeeds."""
        child = Mock()
        child.agent_id = "sync_success_child"
        child.run = Mock(return_value={"response": "sync success response"})
        return child

    @pytest.fixture
    def failure_child(self):
        """Fixture providing a mock child that fails."""
        child = Mock()
        child.agent_id = "failure_child"
        child.run = AsyncMock(side_effect=Exception("Child failed"))
        return child

    @pytest.fixture
    def empty_result_child(self):
        """Fixture providing a mock child that returns empty result."""
        child = Mock()
        child.agent_id = "empty_child"
        child.run = AsyncMock(return_value=None)
        return child

    @pytest.fixture
    def invalid_result_child(self):
        """Fixture providing a mock child that returns invalid result."""
        child = Mock()
        child.agent_id = "invalid_child"
        child.run = AsyncMock(return_value={"status": "error"})
        return child

    @pytest.mark.asyncio
    async def test_run_first_child_succeeds(self, input_data, success_child):
        """Test successful execution with first child succeeding."""
        node = FailoverNode(node_id="test_node", children=[success_child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "success response"}
        assert result["successful_child"] == "success_child"
        assert result["success_child"] == {"response": "success response"}
        success_child.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_second_child_succeeds(self, input_data, failure_child, success_child):
        """Test successful execution with second child succeeding after first fails."""
        node = FailoverNode(node_id="test_node", children=[failure_child, success_child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "success response"}
        assert result["successful_child"] == "success_child"
        failure_child.run.assert_called_once()
        success_child.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_sync_child_succeeds(self, input_data, sync_success_child):
        """Test successful execution with synchronous child."""
        node = FailoverNode(node_id="test_node", children=[sync_success_child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "sync success response"}
        assert result["successful_child"] == "sync_success_child"
        sync_success_child.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_all_children_fail(self, input_data, failure_child):
        """Test execution when all children fail."""
        failure_child2 = Mock()
        failure_child2.agent_id = "failure_child2"
        failure_child2.run = AsyncMock(side_effect=Exception("Child 2 failed"))

        node = FailoverNode(node_id="test_node", children=[failure_child, failure_child2])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None
        assert "Child 2 failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_empty_children_list(self, input_data):
        """Test execution with empty children list."""
        node = FailoverNode(node_id="test_node", children=[])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None
        assert "All children failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_child_without_run_method(self, input_data):
        """Test execution with child that has no run method."""
        child = Mock()
        child.agent_id = "no_run_child"
        # Remove run method from child to simulate no run method
        delattr(child, "run")

        node = FailoverNode(node_id="test_node", children=[child])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None

    @pytest.mark.asyncio
    async def test_run_child_with_non_callable_run(self, input_data):
        """Test execution with child that has non-callable run attribute."""
        child = Mock()
        child.agent_id = "non_callable_child"
        child.run = "not_callable"

        node = FailoverNode(node_id="test_node", children=[child])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None

    @pytest.mark.asyncio
    async def test_run_child_returns_empty_result(self, input_data, empty_result_child):
        """Test execution with child that returns empty result."""
        node = FailoverNode(node_id="test_node", children=[empty_result_child])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None
        empty_result_child.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_child_returns_invalid_result(self, input_data, invalid_result_child):
        """Test execution with child that returns invalid result."""
        node = FailoverNode(node_id="test_node", children=[invalid_result_child])

        result = await node.run(input_data)

        assert result["status"] == "failed"
        assert result["successful_child"] is None
        invalid_result_child.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_rate_limit_error(self, input_data):
        """Test execution with rate limit error triggers delay."""
        child = Mock()
        child.agent_id = "rate_limit_child"
        child.run = AsyncMock(side_effect=Exception("Rate limit exceeded"))

        node = FailoverNode(node_id="test_node", children=[child])

        with patch("asyncio.sleep") as mock_sleep:
            result = await node.run(input_data)

            assert result["status"] == "failed"
            mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_run_with_ratelimit_error_variation(self, input_data):
        """Test execution with ratelimit error (different case) triggers delay."""
        child = Mock()
        child.agent_id = "ratelimit_child"
        child.run = AsyncMock(side_effect=Exception("ratelimit error"))

        node = FailoverNode(node_id="test_node", children=[child])

        with patch("asyncio.sleep") as mock_sleep:
            result = await node.run(input_data)

            assert result["status"] == "failed"
            mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_run_child_with_node_id_fallback(self, input_data, success_child):
        """Test execution with child using node_id instead of agent_id."""
        # Remove agent_id attribute and set node_id
        del success_child.agent_id
        success_child.node_id = "node_id_child"

        node = FailoverNode(node_id="test_node", children=[success_child])

        result = await node.run(input_data)

        assert result["successful_child"] == "node_id_child"

    @pytest.mark.asyncio
    async def test_run_child_with_unknown_id(self, input_data, success_child):
        """Test execution with child having neither agent_id nor node_id."""
        # Remove both agent_id and node_id attributes
        del success_child.agent_id
        if hasattr(success_child, "node_id"):
            del success_child.node_id

        node = FailoverNode(node_id="test_node", children=[success_child])

        result = await node.run(input_data)

        assert result["successful_child"] == "unknown_child_0"


class TestFailoverNodePromptRendering:
    """Test FailoverNode prompt rendering scenarios."""

    @pytest.fixture
    def templated_child(self):
        """Fixture providing a mock child with template prompt."""
        child = Mock()
        child.agent_id = "templated_child"
        child.prompt = "Hello {{ input }}"
        child.run = AsyncMock(return_value={"response": "templated response"})
        return child

    @pytest.fixture
    def input_data(self):
        """Fixture providing test input data."""
        return {"input": "world"}

    @pytest.mark.asyncio
    async def test_run_with_template_rendering(self, input_data, templated_child):
        """Test execution with successful template rendering."""
        node = FailoverNode(node_id="test_node", children=[templated_child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "templated response"}
        # Check that the child was called with formatted_prompt
        call_args = templated_child.run.call_args[0][0]
        assert call_args["formatted_prompt"] == "Hello world"

    @pytest.mark.asyncio
    async def test_run_with_template_rendering_failure(self, input_data, templated_child):
        """Test execution with template rendering failure."""
        # Make template rendering fail with invalid syntax
        templated_child.prompt = "Hello {{ invalid_var.nonexistent }}"

        node = FailoverNode(node_id="test_node", children=[templated_child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "templated response"}
        # Check that the child was called with original prompt as fallback
        call_args = templated_child.run.call_args[0][0]
        assert call_args["formatted_prompt"] == "Hello {{ invalid_var.nonexistent }}"

    @pytest.mark.asyncio
    async def test_run_with_no_prompt(self, input_data):
        """Test execution with child having no prompt."""
        child = Mock()
        child.agent_id = "no_prompt_child"
        child.run = AsyncMock(return_value={"response": "no prompt response"})
        # Remove prompt attribute from child
        if hasattr(child, "prompt"):
            delattr(child, "prompt")

        node = FailoverNode(node_id="test_node", children=[child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "no prompt response"}
        # Check that formatted_prompt was not added
        call_args = child.run.call_args[0][0]
        assert "formatted_prompt" not in call_args

    @pytest.mark.asyncio
    async def test_run_with_empty_prompt(self, input_data):
        """Test execution with child having empty prompt."""
        child = Mock()
        child.agent_id = "empty_prompt_child"
        child.prompt = ""
        child.run = AsyncMock(return_value={"response": "empty prompt response"})

        node = FailoverNode(node_id="test_node", children=[child])

        result = await node.run(input_data)

        assert result["result"] == {"response": "empty prompt response"}
        # Check that formatted_prompt was not added for empty prompt
        call_args = child.run.call_args[0][0]
        assert "formatted_prompt" not in call_args


class TestFailoverNodeResultValidation:
    """Test FailoverNode result validation logic."""

    def test_is_valid_result_empty_or_none(self):
        """Test validation of empty or None results."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result(None)
        assert not node._is_valid_result("")
        assert not node._is_valid_result({})
        assert not node._is_valid_result([])

    def test_is_valid_result_dict_with_error_status(self):
        """Test validation of dict with error status."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result({"status": "error"})
        assert node._is_valid_result({"status": "success"})

    def test_is_valid_result_dict_with_response(self):
        """Test validation of dict with response content."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result({"response": None})
        assert not node._is_valid_result({"response": ""})
        assert not node._is_valid_result({"response": "NONE"})
        assert node._is_valid_result({"response": "valid response"})

    def test_is_valid_result_dict_with_html_response(self):
        """Test validation of dict with HTML response."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result({"response": "<html>content</html>"})
        assert not node._is_valid_result({"response": "<div>This is an HTML tag</div>"})
        assert node._is_valid_result({"response": "This is valid content"})

    def test_is_valid_result_dict_with_nested_result(self):
        """Test validation of dict with nested result."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result(
            {
                "result": {"response": None},
            },
        )
        assert not node._is_valid_result(
            {
                "result": {"response": "NONE"},
            },
        )
        assert not node._is_valid_result(
            {
                "result": {"response": "<div>html content</div>"},
            },
        )
        assert node._is_valid_result(
            {
                "result": {"response": "valid nested response"},
            },
        )

    def test_is_valid_result_list_empty(self):
        """Test validation of empty list."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result([])

    def test_is_valid_result_list_with_error_messages(self):
        """Test validation of list with error messages."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result(["failed to process"])
        assert not node._is_valid_result(["error occurred"])
        assert not node._is_valid_result(["ratelimit exceeded"])
        assert not node._is_valid_result(["rate limit reached"])
        assert not node._is_valid_result(["timeout error"])
        assert not node._is_valid_result(["connection error"])
        assert not node._is_valid_result(["404 not found"])
        assert not node._is_valid_result(["500 server error"])
        assert not node._is_valid_result(["503 service unavailable"])

    def test_is_valid_result_list_with_html_content(self):
        """Test validation of list with HTML content."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result(["<input type='text'>"])
        assert not node._is_valid_result(["HTML element input"])
        assert not node._is_valid_result(["HTML tag form attribute value"])
        assert not node._is_valid_result(["HTML w3schools tutorial"])
        assert not node._is_valid_result(["HTML tag CSS styling guide"])
        assert not node._is_valid_result(["HTML tag javascript function"])
        assert not node._is_valid_result(["HTML tag web-based application"])

        # These should be valid since they don't contain "tag", "html", or "element"
        assert node._is_valid_result(["form attribute value"])
        assert node._is_valid_result(["input field"])
        assert node._is_valid_result(["CSS styling"])
        assert node._is_valid_result(["javascript code"])
        assert node._is_valid_result(["w3schools tutorial"])
        assert node._is_valid_result(["CSS styling guide"])
        assert node._is_valid_result(["javascript function"])
        assert node._is_valid_result(["web-based application"])

    def test_is_valid_result_list_with_valid_content(self):
        """Test validation of list with valid content."""
        node = FailoverNode(node_id="test_node")

        assert node._is_valid_result(["valid content"])
        assert node._is_valid_result(["item 1", "item 2"])
        assert node._is_valid_result([{"key": "value"}])

    def test_is_valid_result_string_none_or_empty(self):
        """Test validation of None or empty strings."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result("NONE")
        assert not node._is_valid_result("")

    def test_is_valid_result_string_with_error_messages(self):
        """Test validation of string with error messages."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result("failed to process")
        assert not node._is_valid_result("error occurred")
        assert not node._is_valid_result("ratelimit exceeded")
        assert not node._is_valid_result("rate limit reached")
        assert not node._is_valid_result("timeout error")
        assert not node._is_valid_result("connection error")
        assert not node._is_valid_result("404 not found")
        assert not node._is_valid_result("500 server error")
        assert not node._is_valid_result("503 service unavailable")

    def test_is_valid_result_string_with_html_content(self):
        """Test validation of string with HTML content."""
        node = FailoverNode(node_id="test_node")

        assert not node._is_valid_result("<html>content</html>")
        assert not node._is_valid_result("<div>This is an HTML tag</div>")

    def test_is_valid_result_string_valid_content(self):
        """Test validation of string with valid content."""
        node = FailoverNode(node_id="test_node")

        assert node._is_valid_result("valid response")
        assert node._is_valid_result("This is a good response")

    def test_is_valid_result_other_types(self):
        """Test validation of other data types."""
        node = FailoverNode(node_id="test_node")

        # Numbers should be valid
        assert node._is_valid_result(42)
        assert node._is_valid_result(3.14)

        # Booleans should be valid
        assert node._is_valid_result(True)
        # False is falsy, but we'll just test that it doesn't crash
        # The actual logic returns False for falsy values like False, 0, ""
        assert not node._is_valid_result(False)
