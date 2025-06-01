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
- LLM Agents: Integrations with large language models (OpenAI, Local LLMs)
- Validation Agent: Validates answers and structures them into memory objects
"""

# Import all agent types from their respective modules
from .agents import BinaryAgent, ClassificationAgent
from .base_agent import BaseAgent, LegacyBaseAgent
from .llm_agents import (
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
)
from .local_llm_agents import LocalLLMAgent
from .validation_and_structuring_agent import ValidationAndStructuringAgent

# Register all available agent types
AGENT_REGISTRY = {
    "binary": BinaryAgent,
    "classification": ClassificationAgent,
    "local_llm": LocalLLMAgent,
    "openai-builder": OpenAIAnswerBuilder,
    "openai-binary": OpenAIBinaryAgent,
    "openai-classification": OpenAIClassificationAgent,
    "validate_and_structure": ValidationAndStructuringAgent,
}
