# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
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

from duckduckgo_search import DDGS

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
        # Get initial query from prompt or input
        if hasattr(self, "prompt") and self.prompt:
            query = self.prompt
        elif isinstance(input_data, dict):
            query = input_data.get("input", "")
        else:
            query = input_data

        if not query:
            return ["No query provided"]

        # Replace input variable if prompt template is used
        if isinstance(query, str) and "{{ input }}" in query:
            if isinstance(input_data, dict):
                input_value = input_data.get("input", "")
            else:
                input_value = input_data
            query = query.replace("{{ input }}", str(input_value))

        # Replace any previous_outputs variables if available
        if isinstance(input_data, dict) and isinstance(query, str):
            for key, value in input_data.get("previous_outputs", {}).items():
                template_var = f"{{{{ previous_outputs.{key} }}}}"
                if template_var in query:
                    query = query.replace(template_var, str(value))

        try:
            # Execute search and get top 5 results
            with DDGS() as ddgs:
                results = [r["body"] for r in ddgs.text(query, max_results=5)]
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return [f"DuckDuckGo search failed: {str(e)}"]
