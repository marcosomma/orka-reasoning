# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

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

# Optional import for DuckDuckGo search
try:
    from duckduckgo_search import DDGS

    HAS_DUCKDUCKGO = True
    DDGS_INSTANCE: type[DDGS] | None = DDGS  # Assign the class to a variable
except ImportError:
    DDGS_INSTANCE = None
    HAS_DUCKDUCKGO = False

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class DuckDuckGoTool(BaseTool):
    """
    A tool that performs web searches using the DuckDuckGo search engine.
    Returns search result snippets from the top results.
    """

    def run(self, input_data):
        """
        Perform a DuckDuckGo search and return result snippets.

        Args:
            input_data (dict): Input containing search query.

        Returns:
            list: List of search result snippets.
        """
        # Check if DuckDuckGo is available
        if not HAS_DUCKDUCKGO:
            return ["DuckDuckGo search not available - duckduckgo_search package not installed"]

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

        try:
            # Execute search and get top 5 results
            with DDGS_INSTANCE() as ddgs:
                results = [r["body"] for r in ddgs.text(query, max_results=5)]
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return [f"DuckDuckGo search failed: {str(e)}"]
