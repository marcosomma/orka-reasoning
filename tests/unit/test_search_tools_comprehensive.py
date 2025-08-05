"""
Comprehensive tests for search tools module to improve coverage.
"""

from unittest.mock import MagicMock, patch

from orka.tools.search_tools import HAS_DUCKDUCKGO, DuckDuckGoTool


class TestDuckDuckGoTool:
    """Test DuckDuckGoTool functionality."""

    def test_init(self):
        """Test DuckDuckGoTool initialization."""
        tool = DuckDuckGoTool("test_tool")
        assert isinstance(tool, DuckDuckGoTool)
        assert tool.tool_id == "test_tool"

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", False)
    def test_run_without_duckduckgo_package(self):
        """Test run method when DuckDuckGo package is not available."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "test query"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "DuckDuckGo search not available" in result[0]
        assert "duckduckgo_search package not installed" in result[0]

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_formatted_prompt(self, mock_ddgs):
        """Test run method with formatted_prompt in input_data."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Result 1"},
            {"body": "Result 2"},
            {"body": "Result 3"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"formatted_prompt": "test formatted query"}

        result = tool.run(input_data)

        assert result == ["Result 1", "Result 2", "Result 3"]
        mock_ddgs_instance.text.assert_called_once_with("test formatted query", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_tool_formatted_prompt(self, mock_ddgs):
        """Test run method with formatted_prompt attribute on tool."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Tool formatted result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "tool formatted query"
        input_data = {"other_key": "value"}

        result = tool.run(input_data)

        assert result == ["Tool formatted result"]
        mock_ddgs_instance.text.assert_called_once_with("tool formatted query", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_tool_prompt(self, mock_ddgs):
        """Test run method with prompt attribute on tool."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Tool prompt result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool", prompt="tool prompt query")
        input_data = {"other_key": "value"}

        result = tool.run(input_data)

        assert result == ["Tool prompt result"]
        mock_ddgs_instance.text.assert_called_once_with("tool prompt query", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_input_query(self, mock_ddgs):
        """Test run method with input query in input_data."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Input query result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"input": "input query"}

        result = tool.run(input_data)

        assert result == ["Input query result"]
        mock_ddgs_instance.text.assert_called_once_with("input query", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_query_key(self, mock_ddgs):
        """Test run method with query key in input_data."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Query key result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "query key"}

        result = tool.run(input_data)

        assert result == ["Query key result"]
        mock_ddgs_instance.text.assert_called_once_with("query key", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_string_input(self, mock_ddgs):
        """Test run method with string input_data."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "String input result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = "string query"

        result = tool.run(input_data)

        assert result == ["String input result"]
        mock_ddgs_instance.text.assert_called_once_with("string query", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_empty_query(self, mock_ddgs):
        """Test run method with empty query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {}

        result = tool.run(input_data)

        assert result == ["No query provided"]
        mock_ddgs_instance = mock_ddgs.return_value.__enter__.return_value
        mock_ddgs_instance.text.assert_not_called()

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_none_query(self, mock_ddgs):
        """Test run method with None query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": None}

        result = tool.run(input_data)

        assert result == ["No query provided"]
        mock_ddgs_instance = mock_ddgs.return_value.__enter__.return_value
        mock_ddgs_instance.text.assert_not_called()

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_empty_string_query(self, mock_ddgs):
        """Test run method with empty string query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": ""}

        result = tool.run(input_data)

        assert result == ["No query provided"]
        mock_ddgs_instance = mock_ddgs.return_value.__enter__.return_value
        mock_ddgs_instance.text.assert_not_called()

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_non_string_query(self, mock_ddgs):
        """Test run method with non-string query that gets converted."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Number query result"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": 12345}

        result = tool.run(input_data)

        assert result == ["Number query result"]
        mock_ddgs_instance.text.assert_called_once_with("12345", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_multiple_results(self, mock_ddgs):
        """Test run method with multiple search results."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"body": "Result 1"},
            {"body": "Result 2"},
            {"body": "Result 3"},
            {"body": "Result 4"},
            {"body": "Result 5"},
        ]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "multiple results"}

        result = tool.run(input_data)

        assert len(result) == 5
        assert result == ["Result 1", "Result 2", "Result 3", "Result 4", "Result 5"]
        mock_ddgs_instance.text.assert_called_once_with("multiple results", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_search_exception(self, mock_ddgs):
        """Test run method when search raises an exception."""
        # Setup mock to raise exception
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.side_effect = Exception("Search API error")
        mock_ddgs_instance.news.side_effect = Exception(
            "Search API error"
        )  # Mock news search to also fail
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "error query"}

        with patch("orka.tools.search_tools.logger") as mock_logger:
            result = tool.run(input_data)

            assert len(result) == 1
            assert "DuckDuckGo search failed: Search API error" in result[0]
            mock_logger.error.assert_called_once_with("DuckDuckGo search failed: Search API error")

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_empty_results(self, mock_ddgs):
        """Test run method when search returns empty results."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "no results"}

        result = tool.run(input_data)

        assert result == []
        mock_ddgs_instance.text.assert_called_once_with("no results", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_priority_order(self, mock_ddgs):
        """Test that query priority order is correct."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Priority test"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "tool formatted"
        tool.prompt = "tool prompt"

        # formatted_prompt in input_data should have highest priority
        input_data = {
            "formatted_prompt": "input formatted",
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        mock_ddgs_instance.text.assert_called_once_with("input formatted", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_priority_order_tool_formatted_prompt(self, mock_ddgs):
        """Test tool formatted_prompt priority when input formatted_prompt is not available."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Priority test"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "tool formatted"
        tool.prompt = "tool prompt"

        # No formatted_prompt in input_data, should use tool.formatted_prompt
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        mock_ddgs_instance.text.assert_called_once_with("tool formatted", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_priority_order_tool_prompt(self, mock_ddgs):
        """Test tool prompt priority when formatted prompts are not available."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Priority test"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool", prompt="tool prompt")

        # No formatted_prompt, should use tool.prompt
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        mock_ddgs_instance.text.assert_called_once_with("tool prompt", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_priority_order_input_fallback(self, mock_ddgs):
        """Test input/query fallback when no prompts are available."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Priority test"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")

        # No prompts, should use input value
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        mock_ddgs_instance.text.assert_called_once_with("input value", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_priority_order_query_fallback(self, mock_ddgs):
        """Test query fallback when input is not available."""
        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Priority test"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        tool = DuckDuckGoTool("test_tool")

        # No prompts or input, should use query value
        input_data = {
            "query": "query value",
        }

        result = tool.run(input_data)

        mock_ddgs_instance.text.assert_called_once_with("query value", max_results=5)

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", True)
    @patch("orka.tools.search_tools.DDGS")
    def test_run_with_empty_tool_prompt(self, mock_ddgs):
        """Test run method with empty tool prompt."""
        tool = DuckDuckGoTool("test_tool", prompt="")  # Empty prompt should be ignored
        input_data = {"query": "fallback query"}

        # Setup mock
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [{"body": "Fallback result"}]
        mock_ddgs_instance.news.return_value = []  # Mock news search to return empty results
        mock_ddgs.return_value.__exit__.return_value = None

        result = tool.run(input_data)

        assert result == ["Fallback result"]
        mock_ddgs_instance.text.assert_called_once_with("fallback query", max_results=5)


class TestModuleImports:
    """Test module-level imports and constants."""

    def test_has_duckduckgo_constant(self):
        """Test that HAS_DUCKDUCKGO constant is properly set."""
        # This will be True or False depending on whether duckduckgo_search is installed
        assert isinstance(HAS_DUCKDUCKGO, bool)

    @patch("orka.tools.search_tools.DDGS", None)
    def test_ddgs_none_when_not_available(self):
        """Test that DDGS is None when package is not available."""
        # When DDGS is None, HAS_DUCKDUCKGO should be False
        # This tests the import error handling logic
        # Reload the module to test import behavior
        import importlib

        from orka.tools import search_tools

        importlib.reload(search_tools)

        # After reload with DDGS=None, it should handle gracefully
        tool = search_tools.DuckDuckGoTool("test_tool")
        assert isinstance(tool, search_tools.DuckDuckGoTool)
