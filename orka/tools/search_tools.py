# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Search Tools Module
=================

This module implements web search tools for the OrKa framework.
These tools provide capabilities to search the web using various search engines.

The search tools in this module include:
- GoogleSearchTool: Searches the web using Google Custom Search API
- DuckDuckGoTool: Searches the web using DuckDuckGo search engine

These tools can be used within workflows to retrieve real-time information
from the web, enabling agents to access up-to-date knowledge that might not
be present in their training data.
"""

import logging
from typing import Any, List

# Optional imports for search engines
try:
    import ddgs
    from ddgs import DDGS as DDGS_INSTANCE
    HAS_DUCKDUCKGO = True
except Exception:
    DDGS_INSTANCE = None
    HAS_DUCKDUCKGO = False

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    requests = None
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    HAS_BS4 = False

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class DuckDuckGoTool(BaseTool):
    """
    A tool that performs web searches using the DuckDuckGo search engine.
    Returns search result snippets from the top results.
    """

    def _run_impl(self, input_data: Any) -> List[str]:
        """
        Perform a DuckDuckGo search and return result snippets.

        Args:
            input_data (dict): Input containing search query.

        Returns:
            list: List of search result snippets.
        """
        # Check if DuckDuckGo is available
        if not HAS_DUCKDUCKGO:
            return ["DuckDuckGo search not available - ddgs package not installed"]

        # Get query - prioritize formatted_prompt from orchestrator, then fallback to other sources
        query = ""

        if isinstance(input_data, dict):
            # First check if orchestrator has provided a formatted_prompt via payload
            if "formatted_prompt" in input_data:
                query = input_data["formatted_prompt"]
            # Then check if we have a prompt that was rendered by orchestrator
            elif hasattr(self, "formatted_prompt"):
                query = self.formatted_prompt
            # Fall back to the raw prompt (which should be rendered by orchestrator)
            elif hasattr(self, "prompt") and self.prompt:
                query = self.prompt
            # Finally, try to get from input data
            else:
                query = input_data.get("input") or input_data.get("query") or ""
        else:
            query = input_data

        if not query:
            return ["No query provided"]

        # Convert to string if needed
        query = str(query)

        # Execute real search
        return self._execute_search(query)

    def _execute_search(self, query: str) -> List[str]:
        """Execute actual DuckDuckGo search with improved error handling."""
        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            # Initialize DDGS with timeout and retry logic
            import time

            max_retries = 2
            retry_delay = 1

            for attempt in range(max_retries):
                try:
                    with DDGS_INSTANCE(timeout=10) as ddgs:
                        # Try text search first
                        try:
                            results = list(ddgs.text(query, max_results=5))
                            if results:
                                search_results = []
                                for r in results:
                                    if isinstance(r, dict) and "body" in r:
                                        # Clean and truncate result
                                        body = str(r["body"]).strip()
                                        if len(body) > 500:
                                            body = body[:500] + "..."
                                        if body:
                                            search_results.append(body)

                                if search_results:
                                    logger.info(
                                        f"DuckDuckGo text search returned {len(search_results)} results"
                                    )
                                    return [timestamp] + search_results[:5]

                        except Exception as text_error:
                            logger.warning(
                                f"Text search failed on attempt {attempt + 1}: {str(text_error)}"
                            )

                        # Fallback to news search
                        try:
                            results = list(ddgs.news(query, max_results=5))
                            if results:
                                search_results = []
                                for r in results:
                                    if isinstance(r, dict) and "body" in r:
                                        # Clean and truncate result
                                        body = str(r["body"]).strip()
                                        if len(body) > 500:
                                            body = body[:500] + "..."
                                        if body:
                                            search_results.append(body)

                                if search_results:
                                    logger.info(
                                        f"DuckDuckGo news search returned {len(search_results)} results"
                                    )
                                    return [timestamp] + search_results[:5]

                        except Exception as news_error:
                            logger.warning(
                                f"News search failed on attempt {attempt + 1}: {str(news_error)}"
                            )

                        # If we get here, both searches returned empty results
                        logger.warning(
                            f"Both text and news searches returned empty results on attempt {attempt + 1}"
                        )

                except Exception as ddgs_error:
                    logger.warning(
                        f"DDGS initialization failed on attempt {attempt + 1}: {str(ddgs_error)}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff

            # All attempts failed
            logger.error("All DuckDuckGo search attempts failed")
            return [timestamp, "Search temporarily unavailable - please try again later"]

        except Exception as e:
            logger.error(f"DuckDuckGo search failed with unexpected error: {str(e)}")
            return [timestamp, f"Search error: {str(e)}"]


class WebSearchTool(BaseTool):
    """
    A more robust web search tool that tries multiple search methods.
    Falls back through different search engines and methods.
    """

    def _run_impl(self, input_data: Any) -> List[str]:
        """
        Perform web search using multiple fallback methods.

        Args:
            input_data: Input containing search query.

        Returns:
            list: List of search result snippets.
        """
        # Get query using same logic as DuckDuckGoTool
        query = self._extract_query(input_data)
        if not query:
            return ["No query provided"]

        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Try search methods in order of preference
        search_methods = [self._duckduckgo_search, self._searx_search, self._fallback_search]

        for method in search_methods:
            try:
                results = method(query)
                if results and len(results) > 1:  # More than just timestamp
                    logger.info(f"Search successful using {method.__name__}")
                    return results
            except Exception as e:
                logger.warning(f"Search method {method.__name__} failed: {str(e)}")
                continue

        # All methods failed
        return [timestamp, "All search methods unavailable - please check internet connection"]

    def _extract_query(self, input_data: Any) -> str:
        """Extract query from input data using same logic as DuckDuckGoTool."""
        query = ""

        if isinstance(input_data, dict):
            if "formatted_prompt" in input_data:
                query = input_data["formatted_prompt"]
            elif hasattr(self, "formatted_prompt"):
                query = self.formatted_prompt
            elif hasattr(self, "prompt") and self.prompt:
                query = self.prompt
            else:
                query = input_data.get("input") or input_data.get("query") or ""
        else:
            query = input_data

        return str(query) if query else ""

    def _duckduckgo_search(self, query: str) -> List[str]:
        """Try DuckDuckGo search."""
        if not HAS_DUCKDUCKGO:
            raise Exception("DuckDuckGo not available")

        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        with DDGS_INSTANCE(timeout=10) as ddgs:
            # Try text search
            results = list(ddgs.text(query, max_results=5))
            if results:
                search_results = []
                for r in results:
                    if isinstance(r, dict) and "body" in r:
                        body = str(r["body"]).strip()
                        if len(body) > 500:
                            body = body[:500] + "..."
                        if body:
                            search_results.append(body)

                if search_results:
                    return [timestamp] + search_results[:5]

        raise Exception("No results from DuckDuckGo")

    def _searx_search(self, query: str) -> List[str]:
        """Try SearX public instances."""
        if not HAS_REQUESTS:
            raise Exception("Requests library not available")

        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Public SearX instances (these change frequently)
        searx_instances = ["https://searx.be", "https://search.sapti.me", "https://searx.info"]

        for instance in searx_instances:
            try:
                response = requests.get(
                    f"{instance}/search",
                    params={"q": query, "format": "json", "categories": "general"},
                    timeout=10,
                    headers={"User-Agent": "OrKa-Search/1.0"},
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])

                    if results:
                        search_results = []
                        for r in results[:5]:
                            content = r.get("content", "").strip()
                            if len(content) > 500:
                                content = content[:500] + "..."
                            if content:
                                search_results.append(content)

                        if search_results:
                            return [timestamp] + search_results

            except Exception as e:
                logger.debug(f"SearX instance {instance} failed: {str(e)}")
                continue

        raise Exception("No working SearX instances")

    def _fallback_search(self, query: str) -> List[str]:
        """Fallback search using simple web scraping."""
        if not (HAS_REQUESTS and HAS_BS4):
            raise Exception("Required libraries not available for fallback search")

        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # This is a very basic fallback - in production you'd want more sophisticated methods
        try:
            # Try a simple search on a public site (this is just an example)
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OrKa-Search/1.0)"},
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                results = soup.find_all("a", class_="result__snippet")

                if results:
                    search_results = []
                    for r in results[:3]:
                        text = r.get_text().strip()
                        if len(text) > 300:
                            text = text[:300] + "..."
                        if text:
                            search_results.append(text)

                    if search_results:
                        return [timestamp] + search_results

        except Exception as e:
            logger.debug(f"Fallback search failed: {str(e)}")

        raise Exception("Fallback search failed")


class SimpleSearchTool(BaseTool):
    """
    A simple search tool that provides basic information without external APIs.
    Useful as a last resort when all other search methods fail.
    """

    def _run_impl(self, input_data: Any) -> List[str]:
        """
        Provide basic search information without external APIs.

        Args:
            input_data: Input containing search query.

        Returns:
            list: List with timestamp and basic information.
        """
        # Get query
        if isinstance(input_data, dict):
            query = (
                input_data.get("formatted_prompt")
                or input_data.get("input")
                or input_data.get("query")
                or ""
            )
        else:
            query = str(input_data) if input_data else ""

        from datetime import datetime

        timestamp = f"Current date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        if not query:
            return [timestamp, "No search query provided"]

        # Provide basic information based on common query patterns
        query_lower = query.lower()

        if any(word in query_lower for word in ["weather", "temperature", "climate"]):
            return [
                timestamp,
                "For current weather information, please check a weather service like weather.com or your local weather app.",
                "Weather data requires real-time APIs that are not available in this search tool.",
            ]
        elif any(word in query_lower for word in ["news", "latest", "recent", "today"]):
            return [
                timestamp,
                "For latest news, please visit news websites like BBC, Reuters, or AP News.",
                "Real-time news requires access to news APIs or RSS feeds.",
            ]
        elif any(word in query_lower for word in ["stock", "price", "market", "trading"]):
            return [
                timestamp,
                "For financial information, please check financial websites like Yahoo Finance or Bloomberg.",
                "Stock prices and market data require real-time financial APIs.",
            ]
        else:
            return [
                timestamp,
                f"Search query received: '{query}'",
                "External search services are currently unavailable. Please try again later or use a web browser for searching.",
            ]
