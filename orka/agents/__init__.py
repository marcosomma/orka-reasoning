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
===================

This package contains all agent implementations for the OrKa framework.
Agents are the fundamental building blocks that perform specific tasks
within orchestrated workflows.

Agent Architecture
------------------

OrKa supports two agent implementation patterns:

**Modern Async Pattern (Recommended)**
    Inherits from :class:`~orka.agents.base_agent.BaseAgent`

    * Full async/await support for concurrent execution
    * Built-in timeout and concurrency control
    * Structured output handling with automatic error wrapping
    * Lifecycle hooks for initialization and cleanup

**Legacy Sync Pattern (Backward Compatibility)**
    Inherits from :class:`~orka.agents.base_agent.LegacyBaseAgent`

    * Simple synchronous execution model
    * Compatible with existing agent implementations
    * Direct result return without wrapping

Available Agent Types
---------------------

**Core Decision Agents**

:class:`~orka.agents.agents.BinaryAgent`
    Makes binary (yes/no) decisions based on input criteria

:class:`~orka.agents.agents.ClassificationAgent`
    Classifies input into predefined categories

**LLM Integration Agents**

:class:`~orka.agents.llm_agents.OpenAIAnswerBuilder`
    Generates text responses using OpenAI models

:class:`~orka.agents.llm_agents.OpenAIBinaryAgent`
    Makes binary decisions using OpenAI model reasoning

:class:`~orka.agents.llm_agents.OpenAIClassificationAgent`
    Performs classification using OpenAI models

:class:`~orka.agents.local_llm_agents.LocalLLMAgent`
    Integrates with local LLM providers (Ollama, LM Studio, etc.)

**Specialized Agents**

:class:`~orka.agents.validation_and_structuring_agent.ValidationAndStructuringAgent`
    Validates answers and structures them into memory objects

Agent Registry
-------------

The package maintains a central registry mapping agent type identifiers
to their implementation classes:

.. code-block:: python

    AGENT_REGISTRY = {
        "binary": BinaryAgent,
        "classification": ClassificationAgent,
        "local_llm": LocalLLMAgent,
        "openai-builder": OpenAIAnswerBuilder,
        "openai-binary": OpenAIBinaryAgent,
        "openai-classification": OpenAIClassificationAgent,
        "validate_and_structure": ValidationAndStructuringAgent,
    }

Usage Examples
--------------

**Creating Custom Agents**

.. code-block:: python

    from orka.agents.base_agent import BaseAgent

    class MyCustomAgent(BaseAgent):
        async def _run_impl(self, ctx):
            input_data = ctx.get("input")
            # Process input asynchronously
            return "processed result"

**Using Existing Agents**

.. code-block:: python

    from orka.agents import OpenAIAnswerBuilder

    # Agent is typically instantiated by the orchestrator
    # based on YAML configuration
    agent = OpenAIAnswerBuilder(agent_id="my_agent")

Agent Configuration
------------------

Agents are typically configured through YAML workflow definitions:

.. code-block:: yaml

    agents:
      - id: my_classifier
        type: classification
        prompt: "Classify this input: {{ input }}"
        options: [positive, negative, neutral]
        timeout: 30.0
        max_concurrency: 5

Module Components
----------------

**Available Modules:**

* ``base_agent`` - Base classes and interfaces
* ``agents`` - Core decision agents (binary, classification)
* ``llm_agents`` - OpenAI integration agents
* ``local_llm_agents`` - Local LLM integration
* ``validation_and_structuring_agent`` - Validation utilities
* ``local_cost_calculator`` - Cost calculation for local models
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
