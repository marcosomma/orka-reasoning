# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import os

from duckduckgo_search import DDGS
from googleapiclient.discovery import build

from .agent_base import BaseAgent

# Google config
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")


class GoogleSearchAgent(BaseAgent):
    """
    An agent that performs web searches using the Google Custom Search API.
    Returns search result snippets from the top results.
    """

    def run(self, input_data):
        """
        Perform a Google search and return result snippets.

        Args:
            input_data (str): Search query.

        Returns:
            list: List of search result snippets.

        Raises:
            EnvironmentError: If Google API credentials are missing.
        """
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            raise EnvironmentError("Missing GOOGLE_API_KEY or GOOGLE_CSE_ID")
        try:
            # Initialize Google Custom Search API client
            service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
            # Execute search and get top 3 results
            result = service.cse().list(q=input_data, cx=GOOGLE_CSE_ID, num=3).execute()
            items = result.get("items", [])
            # Extract snippets from results
            return [item.get("snippet", "") for item in items if isinstance(item, dict)]
        except Exception as e:
            return [f"Google API error: {e}"]


class DuckDuckGoAgent(BaseAgent):
    """
    An agent that performs web searches using the DuckDuckGo search engine.
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

        # Replace template variables in prompt
        query = self.prompt
        if "{{input}}" in query:
            query = query.replace("{{input}}", input_data["input"])

        # Replace any previous_outputs variables
        for key, value in input_data.get("previous_outputs", {}).items():
            template_var = f"{{{{ previous_outputs.{key} }}}}"
            if template_var in query:
                query = query.replace(template_var, str(value))

        if not query:
            return ["No query provided"]
        try:
            # Execute search and get top 5 results
            with DDGS() as ddgs:
                results = [r["body"] for r in ddgs.text(query, max_results=5)]
            return results
        except Exception as e:
            return [f"DuckDuckGo search failed: {str(e)}"]
        print()
