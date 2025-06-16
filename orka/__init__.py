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
OrKa: Orchestrator Kit Agents
==============================

OrKa is a flexible and powerful orchestration framework for AI agents. It provides
a structured way to build, connect, and manage various AI agents in a workflow.

**Modular Architecture**
    OrKa features a modular architecture with specialized components for improved
    maintainability while preserving 100% backward compatibility.

Key Components
--------------

**Orchestrator**
    Core engine that manages agent workflows and execution using modular components:

    * :class:`~orka.orchestrator.base.OrchestratorBase` - Core initialization and configuration
    * :class:`~orka.orchestrator.agent_factory.AgentFactory` - Agent registry and initialization
    * :class:`~orka.orchestrator.execution_engine.ExecutionEngine` - Main execution loop
    * :class:`~orka.orchestrator.metrics.MetricsCollector` - Performance metrics and reporting
    * :class:`~orka.orchestrator.error_handling.ErrorHandler` - Error tracking and reporting
    * :class:`~orka.orchestrator.prompt_rendering.PromptRenderer` - Template processing

**Agents**
    Various task-specific agents for different cognitive functions:

    * LLM agents (OpenAI, local models)
    * Classification and binary decision agents
    * Search agents (DuckDuckGo, Google)
    * Validation and structuring agents

**Nodes**
    Special workflow control components:

    * Router nodes for conditional branching
    * Fork/Join nodes for parallel execution
    * Memory reader/writer nodes for data persistence

**Memory System**
    Persistent storage with multiple backend support:

    * :class:`~orka.memory.redis_logger.RedisMemoryLogger` - Redis-based storage
    * :class:`~orka.memory.kafka_logger.KafkaMemoryLogger` - Kafka-based event streaming
    * Modular components for serialization, file operations, and compression

**Fork/Join Management**
    Advanced workflow patterns for parallel execution and synchronization

Usage
-----

**Basic Workflow**
    1. Define your agent workflows in YAML configuration
    2. Initialize the Orchestrator with your config
    3. Run the workflow with your input data
    4. Retrieve and process the results

**Example Code**

.. code-block:: python

    from orka import Orchestrator

    # Initialize with your YAML config
    orchestrator = Orchestrator("my_workflow.yml")

    # Run the workflow
    result = await orchestrator.run({"input": "Your query here"})

**Memory Backend Selection**

.. code-block:: python

    from orka.memory_logger import create_memory_logger

    # Redis backend (default)
    redis_memory = create_memory_logger("redis")

    # Kafka backend
    kafka_memory = create_memory_logger("kafka")

Architecture Benefits
--------------------

**Backward Compatibility**
    All existing imports and APIs remain unchanged

**Modularity**
    Components are focused on single responsibilities for easier maintenance

**Extensibility**
    Modular structure makes contributing and extending much easier

**Performance**
    Improved memory management and optimized execution paths

For More Information
--------------------

* **Documentation**: https://github.com/marcosomma/orka-resoning
* **Issues**: https://github.com/marcosomma/orka-resoning/issues
* **License**: Apache 2.0
* **Author**: Marco Somma (marcosomma.work@gmail.com)
"""

from .agents import *
from .fork_group_manager import ForkGroupManager
from .loader import YAMLLoader
from .memory_logger import RedisMemoryLogger
from .nodes import *
from .orchestrator import Orchestrator
from .orka_cli import run_cli_entrypoint
