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

"""
OrKa Tools Package
=================

This package contains tool implementations for the OrKa framework.
Tools provide specific functionality that can be used by agents within orchestrated workflows.

Available Tool Types:
-------------------
- Search Tools: Web search capabilities (DuckDuckGo)
- Future tools can be added here as the framework evolves
"""

from .search_tools import DuckDuckGoTool
