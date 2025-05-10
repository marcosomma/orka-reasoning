# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Agent Base Module (Legacy Compatibility Layer)
===============

This module provides backward compatibility for the legacy agent pattern
by importing the LegacyBaseAgent class from the new base_agent.py module.

This file exists solely for backward compatibility and will be deprecated
in future versions. New code should use the BaseAgent class from base_agent.py
directly.

Example of migrating from legacy to modern pattern:

Old pattern:
```python
from orka.agents.agent_base import BaseAgent

class MyAgent(BaseAgent):
    def run(self, input_data):
        # synchronous implementation
        return result
```

New pattern:
```python
from orka.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def _run_impl(self, ctx):
        # async implementation
        return result
```
"""

# Import the compatibility class from the new implementation
from .base_agent import LegacyBaseAgent as BaseAgent

# Re-export for backward compatibility
__all__ = ["BaseAgent"]
