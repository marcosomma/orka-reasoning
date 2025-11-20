"""Unit tests for orka.tools.search_tools."""

import pytest
from unittest.mock import Mock, patch, MagicMock, create_autospec
from datetime import datetime

# Import tools directly - ddgs is available in the environment
from orka.tools.search_tools import DuckDuckGoTool, WebSearchTool, SimpleSearchTool


class TestDuckDuckGoTool:
    """Test suite for DuckDuckGoTool class."""

    @pytest.fixture
    def mock_ddgs_instance(self):
        """Create a mock DDGS instance."""
        mock_ddgs_obj = MagicMock()
        mock_ddgs_obj.__enter__ = Mock(return_value=mock_ddgs_obj)
        mock_ddgs_obj.__exit__ = Mock(return_value=None)
        
        # Patch DDGS class to return our mock instance
        with patch('orka.tools.search_tools.DDGS_INSTANCE', return_value=mock_ddgs_obj):
            yield mock_ddgs_obj

    @pytest.fixture
    def search_tool(self):
        """Create a DuckDuckGoTool instance."""
        tool = DuckDuckGoTool(
            tool_id="search_tool",
            prompt="Search for: {{ query }}",
            queue=[],
            max_results=5
        )
        return tool

    def test_init(self, search_tool):
        """Test DuckDuckGoTool initialization."""
        assert search_tool.tool_id == "search_tool"
        assert search_tool.prompt == "Search for: {{ query }}"
        # max_results is passed but may not be stored as instance attribute

    def test_run_impl_no_duckduckgo_available(self):
        """Test _run_impl when DuckDuckGo module is not available."""
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', False):
            tool = DuckDuckGoTool(tool_id="search_tool", prompt="Test", queue=[])
            result = tool._run_impl({"input": "test query"})
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert "not available" in result[0].lower()
            assert "ddgs" in result[0].lower()

    def test_run_impl_no_query_provided(self, search_tool, mock_ddgs_instance):
        """Test _run_impl with no query."""
        # Empty query causes search to fail, returning timestamp + error
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_instance.news.return_value = []
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({})
            
            assert isinstance(result, list)
            assert len(result) >= 1  # timestamp + error message
            # Empty input leads to empty query which causes search failure

    def test_run_impl_with_formatted_prompt(self, search_tool, mock_ddgs_instance):
        """Test _run_impl with formatted_prompt in input_data."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Result 1", "body": "Test content 1", "href": "https://example1.com"},
            {"title": "Result 2", "body": "Test content 2", "href": "https://example2.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({"formatted_prompt": "artificial intelligence"})
            
            assert isinstance(result, list)
            assert len(result) >= 2  # timestamp + results
            assert "Test content 1" in result[1]
            assert "Test content 2" in result[2]

    def test_run_impl_with_dict_input(self, search_tool, mock_ddgs_instance):
        """Test _run_impl with dict containing 'input' key."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Python", "body": "Python programming language", "href": "https://python.org"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({"input": "python tutorial"})
            
            assert isinstance(result, list)
            assert len(result) >= 2
            assert "Python programming" in result[1]

    def test_run_impl_with_query_key(self, search_tool, mock_ddgs_instance):
        """Test _run_impl with dict containing 'query' key."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Machine Learning", "body": "ML basics", "href": "https://ml.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({"query": "machine learning"})
            
            assert isinstance(result, list)
            assert "ML basics" in result[1]

    def test_run_impl_with_string_input(self, search_tool, mock_ddgs_instance):
        """Test _run_impl with direct string input."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Test", "body": "Test result", "href": "https://test.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl("test query string")
            
            assert isinstance(result, list)
            assert "Test result" in result[1]

    def test_execute_search_text_success(self, search_tool, mock_ddgs_instance):
        """Test successful text search."""
        mock_ddgs_instance.text.return_value = [
            {"title": "R1", "body": "Content 1", "href": "https://1.com"},
            {"title": "R2", "body": "Content 2", "href": "https://2.com"},
            {"title": "R3", "body": "Content 3", "href": "https://3.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test query")
            
            assert len(result) >= 3  # timestamp + at least 2 results
            assert any("Content 1" in r for r in result)
            assert any("Content 2" in r for r in result)

    def test_execute_search_truncates_long_content(self, search_tool, mock_ddgs_instance):
        """Test that long content is truncated."""
        long_content = "x" * 600
        mock_ddgs_instance.text.return_value = [
            {"title": "Long", "body": long_content, "href": "https://long.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            # Should be truncated to 500 chars + "..."
            assert len(result[1]) <= 503
            assert result[1].endswith("...")

    def test_execute_search_text_fails_news_succeeds(self, search_tool, mock_ddgs_instance):
        """Test fallback to news search when text search fails."""
        mock_ddgs_instance.text.side_effect = Exception("Text search failed")
        mock_ddgs_instance.news.return_value = [
            {"title": "News", "body": "News content", "href": "https://news.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("breaking news")
            
            assert len(result) >= 2
            assert any("News content" in r for r in result)

    def test_execute_search_both_fail_returns_error(self, search_tool, mock_ddgs_instance):
        """Test error message when both text and news searches fail."""
        mock_ddgs_instance.text.side_effect = Exception("Text failed")
        mock_ddgs_instance.news.side_effect = Exception("News failed")
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            assert len(result) >= 2
            assert "temporarily unavailable" in result[1].lower()

    def test_execute_search_empty_results(self, search_tool, mock_ddgs_instance):
        """Test handling of empty search results."""
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_instance.news.return_value = []
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("obscure query")
            
            assert len(result) >= 2
            assert "temporarily unavailable" in result[1].lower()

    def test_execute_search_malformed_results(self, search_tool, mock_ddgs_instance):
        """Test handling of malformed search results."""
        mock_ddgs_instance.text.return_value = [
            {"title": "No body field"},  # Missing 'body'
            {"body": ""},  # Empty body
            {"body": "   "},  # Whitespace only
            {"body": "Valid content"}  # Valid
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            # Should only include valid results
            assert len(result) == 2  # timestamp + 1 valid result
            assert "Valid content" in result[1]

    def test_execute_search_includes_timestamp(self, search_tool, mock_ddgs_instance):
        """Test that results include a timestamp."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Test", "body": "Test content", "href": "https://test.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            # First item should be timestamp
            assert "Current date and time:" in result[0]
            assert len(result[0]) > 20  # Should include date

    def test_execute_search_max_results_limit(self, search_tool, mock_ddgs_instance):
        """Test that results are limited to max_results."""
        # Return 10 results
        mock_ddgs_instance.text.return_value = [
            {"title": f"R{i}", "body": f"Content {i}", "href": f"https://{i}.com"}
            for i in range(10)
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            # Should be timestamp + 5 results (max_results=5)
            assert len(result) <= 6

    def test_execute_search_ddgs_initialization_fails(self, search_tool):
        """Test handling when DDGS initialization fails."""
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            with patch('orka.tools.search_tools.DDGS_INSTANCE', side_effect=Exception("Init failed")):
                result = search_tool._execute_search("test")
                
                assert len(result) >= 2
                assert "temporarily unavailable" in result[1].lower()

    def test_run_impl_with_formatted_prompt_attribute(self, search_tool, mock_ddgs_instance):
        """Test _run_impl when tool has formatted_prompt attribute."""
        search_tool.formatted_prompt = "test formatted prompt"
        mock_ddgs_instance.text.return_value = [
            {"title": "Test", "body": "Test content", "href": "https://test.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({})
            
            assert len(result) >= 2
            assert "Test content" in result[1]

    def test_run_impl_with_prompt_attribute(self, search_tool, mock_ddgs_instance):
        """Test _run_impl falling back to prompt attribute."""
        # Remove formatted_prompt if exists
        if hasattr(search_tool, 'formatted_prompt'):
            delattr(search_tool, 'formatted_prompt')
        
        search_tool.prompt = "test prompt attribute"
        mock_ddgs_instance.text.return_value = [
            {"title": "Test", "body": "Test content", "href": "https://test.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({})
            
            assert len(result) >= 2
            assert "Test content" in result[1]

    def test_execute_search_retry_logic(self, search_tool, mock_ddgs_instance):
        """Test retry logic on transient failures."""
        # Fail first attempt, succeed on second
        call_count = 0
        
        def side_effect_text(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            return [{"title": "Success", "body": "Retry worked", "href": "https://test.com"}]
        
        mock_ddgs_instance.text.side_effect = side_effect_text
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._execute_search("test")
            
            # Should eventually succeed
            assert any("Retry worked" in r for r in result)
            assert call_count == 2  # Called twice (1 fail + 1 success)


class TestWebSearchTool:
    """Test suite for WebSearchTool class with multiple fallback methods."""

    @pytest.fixture
    def mock_ddgs_instance(self):
        """Create a mock DDGS instance for WebSearchTool."""
        mock_ddgs_obj = MagicMock()
        mock_ddgs_obj.__enter__ = Mock(return_value=mock_ddgs_obj)
        mock_ddgs_obj.__exit__ = Mock(return_value=None)
        
        # Patch DDGS class to return our mock instance
        with patch('orka.tools.search_tools.DDGS_INSTANCE', return_value=mock_ddgs_obj):
            yield mock_ddgs_obj

    @pytest.fixture
    def search_tool(self):
        """Create a WebSearchTool instance."""
        tool = WebSearchTool(
            tool_id="web_search",
            prompt="Search: {{ query }}",
            queue=[]
        )
        return tool

    def test_init(self, search_tool):
        """Test WebSearchTool initialization."""
        assert search_tool.tool_id == "web_search"
        assert search_tool.prompt == "Search: {{ query }}"

    def test_run_impl_no_query(self, search_tool):
        """Test _run_impl with no query provided."""
        # When input is empty dict, _extract_query falls back to self.prompt attribute
        # which is "Search: {{ query }}" from fixture, so search actually runs
        # Mock all search methods to fail
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', False):
            with patch('orka.tools.search_tools.HAS_REQUESTS', False):
                result = search_tool._run_impl({})
        
                assert isinstance(result, list)
                assert len(result) >= 2
                assert "unavailable" in result[1].lower()

    def test_run_impl_duckduckgo_success(self, search_tool, mock_ddgs_instance):
        """Test successful search using DuckDuckGo fallback."""
        mock_ddgs_instance.text.return_value = [
            {"title": "Result", "body": "Test content", "href": "https://example.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({"input": "test query"})
            
            assert isinstance(result, list)
            assert len(result) >= 2  # timestamp + results
            assert any("Test content" in r for r in result)

    def test_run_impl_all_methods_fail(self, search_tool):
        """Test when all search methods fail."""
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', False):
            with patch('orka.tools.search_tools.HAS_REQUESTS', False):
                result = search_tool._run_impl({"input": "test"})
                
                assert isinstance(result, list)
                assert len(result) >= 2
                assert "unavailable" in result[1].lower()

    def test_extract_query_from_formatted_prompt(self, search_tool):
        """Test _extract_query with formatted_prompt."""
        query = search_tool._extract_query({"formatted_prompt": "test query"})
        assert query == "test query"

    def test_extract_query_from_input(self, search_tool):
        """Test _extract_query from input key."""
        # search_tool fixture has prompt attribute, which takes precedence
        # Create a fresh tool without prompt attribute
        tool = WebSearchTool(tool_id="test", prompt="")
        query = tool._extract_query({"input": "search this"})
        assert query == "search this"

    def test_extract_query_from_query_key(self, search_tool):
        """Test _extract_query from query key."""
        # search_tool fixture has prompt attribute, which takes precedence
        # Create a fresh tool without prompt attribute
        tool = WebSearchTool(tool_id="test", prompt="")
        query = tool._extract_query({"query": "find this"})
        assert query == "find this"

    def test_extract_query_from_string(self, search_tool):
        """Test _extract_query with direct string."""
        query = search_tool._extract_query("direct query")
        assert query == "direct query"

    def test_extract_query_with_prompt_attribute(self, search_tool):
        """Test _extract_query falls back to prompt attribute."""
        search_tool.prompt = "fallback query"
        query = search_tool._extract_query({})
        assert query == "fallback query"

    def test_duckduckgo_search_not_available(self, search_tool):
        """Test _duckduckgo_search when module not available."""
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', False):
            with pytest.raises(Exception, match="DuckDuckGo not available"):
                search_tool._duckduckgo_search("test")

    def test_duckduckgo_search_no_results(self, search_tool, mock_ddgs_instance):
        """Test _duckduckgo_search with no results."""
        mock_ddgs_instance.text.return_value = []
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            with pytest.raises(Exception, match="No results from DuckDuckGo"):
                search_tool._duckduckgo_search("test")

    def test_duckduckgo_search_success(self, search_tool, mock_ddgs_instance):
        """Test successful _duckduckgo_search."""
        mock_ddgs_instance.text.return_value = [
            {"title": "T1", "body": "Content 1", "href": "https://1.com"},
            {"title": "T2", "body": "Content 2", "href": "https://2.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._duckduckgo_search("test")
            
            assert len(result) >= 2
            assert any("Content 1" in r for r in result)
            assert any("Content 2" in r for r in result)

    def test_searx_search_no_requests(self, search_tool):
        """Test _searx_search when requests not available."""
        with patch('orka.tools.search_tools.HAS_REQUESTS', False):
            with pytest.raises(Exception, match="Requests library not available"):
                search_tool._searx_search("test")

    def test_fallback_search_no_libraries(self, search_tool):
        """Test _fallback_search when required libraries missing."""
        with patch('orka.tools.search_tools.HAS_REQUESTS', False):
            with pytest.raises(Exception, match="Required libraries not available"):
                search_tool._fallback_search("test")
    
    def test_fallback_search_fails(self, search_tool):
        """Test when fallback search fails due to network error."""
        with patch('orka.tools.search_tools.HAS_REQUESTS', True):
            with patch('orka.tools.search_tools.HAS_BS4', True):
                with patch('orka.tools.search_tools.requests.get') as mock_get:
                    mock_get.side_effect = Exception("Network error")
                    
                    with pytest.raises(Exception, match="Fallback search failed"):
                        search_tool._fallback_search("test")

    def test_run_impl_with_formatted_prompt_attribute(self, search_tool, mock_ddgs_instance):
        """Test search with formatted_prompt attribute set."""
        search_tool.formatted_prompt = "attributed query"
        mock_ddgs_instance.text.return_value = [
            {"title": "T", "body": "Found it", "href": "https://t.com"}
        ]
        
        with patch('orka.tools.search_tools.HAS_DUCKDUCKGO', True):
            result = search_tool._run_impl({})
            
            assert len(result) >= 2
            assert any("Found it" in r for r in result)
    
    def test_searx_search_success(self, search_tool):
        """Test successful SearX search."""
        with patch('orka.tools.search_tools.HAS_REQUESTS', True):
            with patch('orka.tools.search_tools.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "results": [
                        {"content": "SearX result 1"},
                        {"content": "SearX result 2"}
                    ]
                }
                mock_get.return_value = mock_response
                
                result = search_tool._searx_search("test")
                
                assert isinstance(result, list)
                assert len(result) >= 2
                assert any("SearX result" in r for r in result)
    
    def test_searx_search_all_instances_fail(self, search_tool):
        """Test when all SearX instances fail."""
        with patch('orka.tools.search_tools.HAS_REQUESTS', True):
            with patch('orka.tools.search_tools.requests.get') as mock_get:
                mock_get.side_effect = Exception("Connection error")
                
                with pytest.raises(Exception, match="No working SearX instances"):
                    search_tool._searx_search("test")


class TestSimpleSearchTool:
    """Test suite for SimpleSearchTool class."""
    
    @pytest.fixture
    def search_tool(self):
        """Create a SimpleSearchTool instance."""
        from orka.tools.search_tools import SimpleSearchTool
        return SimpleSearchTool(tool_id="simple", prompt="", queue=[])
    
    def test_init(self, search_tool):
        """Test SimpleSearchTool initialization."""
        assert search_tool.tool_id == "simple"
    
    def test_no_query(self, search_tool):
        """Test with no query."""
        result = search_tool._run_impl({})
        
        assert isinstance(result, list)
        assert len(result) >= 2
        assert "No search query provided" in result[1]
    
    def test_weather_query(self, search_tool):
        """Test weather-related query."""
        result = search_tool._run_impl({"input": "what is the weather today?"})
        
        assert isinstance(result, list)
        assert any("weather" in r.lower() for r in result)
    
    def test_news_query(self, search_tool):
        """Test news-related query."""
        result = search_tool._run_impl({"query": "latest news today"})
        
        assert isinstance(result, list)
        assert any("news" in r.lower() for r in result)
    
    def test_stock_query(self, search_tool):
        """Test stock/market query."""
        result = search_tool._run_impl("stock market prices")
        
        assert isinstance(result, list)
        assert any("financial" in r.lower() or "market" in r.lower() for r in result)
    
    def test_generic_query(self, search_tool):
        """Test generic query."""
        result = search_tool._run_impl({"input": "random search query"})
        
        assert isinstance(result, list)
        assert len(result) >= 2
        assert "Search query received" in result[1]

