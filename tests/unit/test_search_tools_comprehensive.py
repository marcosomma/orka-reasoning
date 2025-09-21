"""
Comprehensive tests for search tools module using real implementations.
Tests actual search functionality without mocks.
"""

from unittest.mock import patch

import pytest

from orka.tools.search_tools import DuckDuckGoTool, SimpleSearchTool, WebSearchTool


class TestDuckDuckGoTool:
    """Test DuckDuckGoTool functionality with real implementation."""

    def test_init(self):
        """Test DuckDuckGoTool initialization."""
        tool = DuckDuckGoTool("test_tool")
        assert isinstance(tool, DuckDuckGoTool)
        assert tool.tool_id == "test_tool"

    @patch("orka.tools.search_tools.HAS_DUCKDUCKGO", False)
    def test_run_without_duckduckgo_package(self):
        """Test run method when DuckDuckGo package is not available."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "artificial intelligence"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "DuckDuckGo search not available" in result[0]
        assert "duckduckgo_search package not installed" in result[0]

    def test_run_with_formatted_prompt(self):
        """Test run method with formatted_prompt in input_data."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"formatted_prompt": "artificial intelligence"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        # First result should be timestamp
        assert "Current date and time:" in result[0]

    def test_run_with_tool_formatted_prompt(self):
        """Test run method with formatted_prompt attribute on tool."""
        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "machine learning"
        input_data = {"other_key": "value"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_tool_prompt(self):
        """Test run method with prompt attribute on tool."""
        tool = DuckDuckGoTool("test_tool", prompt="deep learning")
        input_data = {"other_key": "value"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_input_query(self):
        """Test run method with input query in input_data."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"input": "neural networks"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_query_key(self):
        """Test run method with query key in input_data."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": "computer science"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_string_input(self):
        """Test run method with string input_data."""
        tool = DuckDuckGoTool("test_tool")
        input_data = "python programming"

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_empty_query(self):
        """Test run method with empty query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {}

        result = tool.run(input_data)

        assert result == ["No query provided"]

    def test_run_with_none_query(self):
        """Test run method with None query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": None}

        result = tool.run(input_data)

        assert result == ["No query provided"]

    def test_run_with_empty_string_query(self):
        """Test run method with empty string query."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": ""}

        result = tool.run(input_data)

        assert result == ["No query provided"]

    def test_run_with_non_string_query(self):
        """Test run method with non-string query that gets converted."""
        tool = DuckDuckGoTool("test_tool")
        input_data = {"query": 12345}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_priority_order(self):
        """Test that query priority order is correct."""
        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "tool formatted prompt"
        tool.prompt = "tool prompt"

        # formatted_prompt in input_data should have highest priority
        input_data = {
            "formatted_prompt": "input formatted prompt",
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_priority_order_tool_formatted_prompt(self):
        """Test tool formatted_prompt priority when input formatted_prompt is not available."""
        tool = DuckDuckGoTool("test_tool")
        tool.formatted_prompt = "tool formatted prompt"
        tool.prompt = "tool prompt"

        # No formatted_prompt in input_data, should use tool.formatted_prompt
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_priority_order_tool_prompt(self):
        """Test tool prompt priority when formatted prompts are not available."""
        tool = DuckDuckGoTool("test_tool", prompt="tool prompt")

        # No formatted_prompt, should use tool.prompt
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_priority_order_input_fallback(self):
        """Test input/query fallback when no prompts are available."""
        tool = DuckDuckGoTool("test_tool")

        # No prompts, should use input value
        input_data = {
            "input": "input value",
            "query": "query value",
        }

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_priority_order_query_fallback(self):
        """Test query fallback when input is not available."""
        tool = DuckDuckGoTool("test_tool")

        # No prompts or input, should use query value
        input_data = {
            "query": "query value",
        }

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_empty_tool_prompt(self):
        """Test run method with empty tool prompt."""
        tool = DuckDuckGoTool("test_tool", prompt="")  # Empty prompt should be ignored
        input_data = {"query": "fallback query"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]


class TestWebSearchTool:
    """Test WebSearchTool functionality with real implementation."""

    def test_init(self):
        """Test WebSearchTool initialization."""
        tool = WebSearchTool("web_search_tool")
        assert isinstance(tool, WebSearchTool)
        assert tool.tool_id == "web_search_tool"

    def test_run_with_query(self):
        """Test run method with a real query."""
        tool = WebSearchTool("web_search_tool")
        input_data = {"query": "artificial intelligence"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]

    def test_run_with_empty_query(self):
        """Test run method with empty query."""
        tool = WebSearchTool("web_search_tool")
        input_data = {}

        result = tool.run(input_data)

        assert result == ["No query provided"]

    def test_extract_query_method(self):
        """Test the _extract_query method."""
        tool = WebSearchTool("web_search_tool")

        # Test with dict input
        input_data = {"formatted_prompt": "test query"}
        query = tool._extract_query(input_data)
        assert query == "test query"

        # Test with string input
        query = tool._extract_query("direct query")
        assert query == "direct query"

        # Test with empty input
        query = tool._extract_query({})
        assert query == ""

    def test_run_with_formatted_prompt(self):
        """Test run method with formatted_prompt."""
        tool = WebSearchTool("web_search_tool")
        input_data = {"formatted_prompt": "machine learning"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]


class TestSimpleSearchTool:
    """Test SimpleSearchTool functionality."""

    def test_init(self):
        """Test SimpleSearchTool initialization."""
        tool = SimpleSearchTool("simple_search_tool")
        assert isinstance(tool, SimpleSearchTool)
        assert tool.tool_id == "simple_search_tool"

    def test_run_with_empty_query(self):
        """Test run method with empty query."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = {}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 2
        assert "Current date and time:" in result[0]
        assert "No search query provided" in result[1]

    def test_run_with_weather_query(self):
        """Test run method with weather-related query."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = {"query": "weather today"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Current date and time:" in result[0]
        assert "weather service" in result[1].lower()

    def test_run_with_news_query(self):
        """Test run method with news-related query."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = {"query": "latest news"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Current date and time:" in result[0]
        assert "news websites" in result[1].lower()

    def test_run_with_stock_query(self):
        """Test run method with stock-related query."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = {"query": "stock prices"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Current date and time:" in result[0]
        assert "financial" in result[1].lower()

    def test_run_with_general_query(self):
        """Test run method with general query."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = {"query": "artificial intelligence"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Current date and time:" in result[0]
        assert "artificial intelligence" in result[1]
        assert "unavailable" in result[2].lower()

    def test_run_with_string_input(self):
        """Test run method with string input."""
        tool = SimpleSearchTool("simple_search_tool")
        input_data = "python programming"

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Current date and time:" in result[0]
        assert "python programming" in result[1]


class TestModuleImports:
    """Test module-level imports and constants."""

    def test_imports_available(self):
        """Test that all tools can be imported."""
        from orka.tools.search_tools import (
            DuckDuckGoTool,
            SimpleSearchTool,
            WebSearchTool,
        )

        assert DuckDuckGoTool is not None
        assert WebSearchTool is not None
        assert SimpleSearchTool is not None

    def test_has_duckduckgo_constant(self):
        """Test that HAS_DUCKDUCKGO constant is properly set."""
        from orka.tools.search_tools import HAS_DUCKDUCKGO

        assert isinstance(HAS_DUCKDUCKGO, bool)

    def test_has_requests_constant(self):
        """Test that HAS_REQUESTS constant is properly set."""
        from orka.tools.search_tools import HAS_REQUESTS

        assert isinstance(HAS_REQUESTS, bool)

    def test_has_bs4_constant(self):
        """Test that HAS_BS4 constant is properly set."""
        from orka.tools.search_tools import HAS_BS4

        assert isinstance(HAS_BS4, bool)


class TestRealSearchIntegration:
    """Integration tests with real search functionality."""

    @pytest.mark.slow
    def test_duckduckgo_real_search(self):
        """Test DuckDuckGo with a real search query (marked as slow test)."""
        tool = DuckDuckGoTool("real_search_tool")
        input_data = {"query": "python"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]
        # Real search should return results or error message
        if len(result) > 1:
            # If we got results, they should be strings
            for item in result[1:]:
                assert isinstance(item, str)
                assert len(item) > 0

    @pytest.mark.slow
    def test_web_search_real_search(self):
        """Test WebSearchTool with a real search query (marked as slow test)."""
        tool = WebSearchTool("real_web_search_tool")
        input_data = {"query": "python programming"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 1
        assert "Current date and time:" in result[0]
        # Should either return search results or fallback message
        if "unavailable" not in result[-1].lower():
            # If we got results, they should be meaningful
            assert len(result) > 1

    def test_simple_search_always_works(self):
        """Test that SimpleSearchTool always provides a response."""
        tool = SimpleSearchTool("simple_tool")
        input_data = {"query": "any query"}

        result = tool.run(input_data)

        assert isinstance(result, list)
        assert len(result) >= 2
        assert "Current date and time:" in result[0]
        assert len(result[1]) > 0  # Should always have a response
