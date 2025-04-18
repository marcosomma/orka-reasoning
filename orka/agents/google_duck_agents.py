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
import json
from .agent_base import BaseAgent
from googleapiclient.discovery import build
from duckduckgo_search import DDGS

# Google config
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

class GoogleSearchAgent(BaseAgent):
    def run(self, input_data):
        if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
            raise EnvironmentError("Missing GOOGLE_API_KEY or GOOGLE_CSE_ID")
        try:
            service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
            result = service.cse().list(q=input_data, cx=GOOGLE_CSE_ID, num=3).execute()
            items = result.get("items", [])
            return [item.get("snippet", "") for item in items if isinstance(item, dict)]
        except Exception as e:
            return [f"Google API error: {e}"]


class DuckDuckGoAgent(BaseAgent):
    def run(self, input_data):
        query = input_data["input"]
        if not query:
            return ["No query provided"]
        try:
            with DDGS() as ddgs:
                results = [r["body"] for r in ddgs.text(query, max_results=5)]
            return results
        except Exception as e:
            return [f"DuckDuckGo search failed: {str(e)}"]
        