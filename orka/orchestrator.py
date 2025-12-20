# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Orchestrator
============

The main orchestrator class that coordinates all components for workflow execution.
This file uses modular components while maintaining 100% backward compatibility.

**Modular Architecture**
    This orchestrator is composed of specialized components using multiple inheritance
    to provide a clean separation of concerns while preserving the identical public API.

Architecture Overview
--------------------

The :class:`Orchestrator` class combines functionality from multiple specialized mixins:

**Component Hierarchy**

.. inheritance-diagram:: Orchestrator
   :parts: 1

**Core Components**

1. :class:`~orka.orchestrator.base.OrchestratorBase`
   Base initialization, configuration loading, memory backend setup

2. :class:`~orka.orchestrator.agent_factory.AgentFactory`
   Agent registry management, instantiation, and AGENT_TYPES mapping

3. :class:`~orka.orchestrator.simplified_prompt_rendering.SimplifiedPromptRenderer`
   Jinja2 template processing and prompt formatting

4. :class:`~orka.orchestrator.error_handling.ErrorHandler`
   Error tracking, retry logic, and failure reporting

5. :class:`~orka.orchestrator.metrics.MetricsCollector`
   LLM metrics collection, performance analysis, and reporting

6. :class:`~orka.orchestrator.execution_engine.ExecutionEngine`
   Main execution loop, agent coordination, and workflow management

Benefits of Modular Design
--------------------------

**Maintainability**
    Each component handles a specific aspect of orchestration

**Testability**
    Components can be unit tested in isolation

**Extensibility**
    New functionality can be added without affecting other components

**Code Organization**
    Related functionality is logically grouped together

**Zero Breaking Changes**
    Existing code continues to work without modification

Usage
-----

The orchestrator usage remains identical to previous versions:

.. code-block:: python

    from orka.orchestrator import Orchestrator

    # Initialize with YAML configuration
    orchestrator = Orchestrator("workflow.yml")

    # Execute workflow
    result = await orchestrator.run("input data")

Internal Structure
-----------------

The multiple inheritance composition ensures proper method resolution order
and seamless integration of all components. The class definition uses the
Diamond Pattern to handle multiple inheritance correctly.

**Method Resolution Order**
    1. Orchestrator (this class)
    2. OrchestratorBase
    3. AgentFactory
    4. PromptRenderer
    5. ErrorHandler
    6. MetricsCollector
    7. ExecutionEngine
    8. object

This ensures that initialization and core methods are properly inherited
and that all functionality remains accessible through the main interface.
"""

import logging

from orka.orchestrator.agent_factory import AgentFactory
from orka.orchestrator.base import OrchestratorBase
from orka.orchestrator.error_handling import ErrorHandler
from orka.orchestrator.execution_engine import ExecutionEngine
from orka.orchestrator.metrics import MetricsCollector
from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer

logger = logging.getLogger(__name__)


class Orchestrator(
    ExecutionEngine,  # First since it has the run method
    OrchestratorBase,  # Base class next
    AgentFactory,  # Then the mixins in order of dependency
    ErrorHandler,
    MetricsCollector,
):
    """
    The Orchestrator is the core engine that loads a YAML configuration,
    instantiates agents and nodes, and manages the execution of the reasoning workflow.
    It supports parallelism, dynamic routing, and full trace logging.

    This class now inherits from multiple mixins to provide all functionality
    while maintaining the same public interface.
    """

    def __init__(self, config_path: str) -> None:
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        # Initialize all parent classes
        ExecutionEngine.__init__(self, config_path)
        OrchestratorBase.__init__(self, config_path)
        AgentFactory.__init__(self, self.orchestrator_cfg, self.agent_cfgs, self.memory)
        ErrorHandler.__init__(self)
        MetricsCollector.__init__(self)

        # Initialize agents using the agent factory
        self.agents = self._init_agents()  # Dict of agent_id -> agent instance
