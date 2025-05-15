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
OrKa Agents Package
=================

This package contains all agent implementations for the OrKa framework.
Agents are the fundamental building blocks that perform specific tasks
within orchestrated workflows.

Available Agent Types:
-------------------
- Base Agent: Abstract base class that defines the agent interface
  - Modern BaseAgent: Async implementation with full concurrency support
  - Legacy BaseAgent: Backward-compatible synchronous implementation
- Binary Agent: Makes binary (yes/no) decisions based on input
- Classification Agent: Classifies input into predefined categories
- LLM Agents: Integrations with large language models (OpenAI)
"""

# Import all agent types from their respective modules
from .agents import BinaryAgent, ClassificationAgent
from .base_agent import BaseAgent, LegacyBaseAgent
from .llm_agents import (
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
)
