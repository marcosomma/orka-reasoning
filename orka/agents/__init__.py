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
OrKa Agents Package
=================

This package contains all agent implementations for the OrKa framework.
Agents are the fundamental building blocks that perform specific tasks
within orchestrated workflows.

Available Agent Types:
-------------------
- Base Agent: Abstract base class that defines the agent interface
- Binary Agent: Makes binary (yes/no) decisions based on input
- Classification Agent: Classifies input into predefined categories
- LLM Agents: Integrations with large language models (OpenAI)
"""

from .agent_base import BaseAgent
from .agents import BinaryAgent, ClassificationAgent
from .llm_agents import (
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
)
