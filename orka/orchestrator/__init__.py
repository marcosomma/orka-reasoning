# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Orchestrator Package
===================

The orchestrator package contains the modular components that make up OrKa's core
orchestration engine. The orchestrator was designed with a modular architecture
for specialized components while maintaining 100% backward compatibility.

Architecture Overview
---------------------

The orchestrator uses a **multiple inheritance composition pattern** to combine
specialized functionality from focused components:

**Core Components**

:class:`~orka.orchestrator.base.OrchestratorBase`
    Handles initialization, configuration loading, and basic setup

:class:`~orka.orchestrator.agent_factory.AgentFactory`
    Manages agent registry, instantiation, and the AGENT_TYPES mapping

:class:`~orka.orchestrator.execution_engine.ExecutionEngine`
    Contains the main execution loop, agent coordination, and workflow management

:class:`~orka.orchestrator.simplified_prompt_rendering.SimplifiedPromptRenderer`
    Handles Jinja2 template rendering and prompt formatting

:class:`~orka.orchestrator.error_handling.ErrorHandler`
    Provides comprehensive error tracking, retry logic, and failure reporting

:class:`~orka.orchestrator.metrics.MetricsCollector`
    Collects LLM metrics, runtime information, and generates performance reports

Composition Strategy
--------------------

The main :class:`Orchestrator` class inherits from all components using multiple
inheritance, ensuring that:

1. **Method Resolution Order** is preserved for consistent behavior
2. **All functionality** remains accessible through the same interface
3. **Zero breaking changes** are introduced for existing code
4. **Internal modularity** improves maintainability and testing

Usage Example
-------------

.. code-block:: python

    from orka.orchestrator import Orchestrator

    # Initialize with YAML configuration
    orchestrator = Orchestrator("workflow.yml")

    # Run the workflow (uses all components seamlessly)
    result = await orchestrator.run("input data")

Module Components
-----------------

**Available Modules:**

* ``base`` - Core initialization and configuration
* ``agent_factory`` - Agent registry and instantiation
* ``execution_engine`` - Main execution loop and coordination
* ``simplified_prompt_rendering`` - Template processing and formatting
* ``error_handling`` - Error tracking and retry logic
* ``metrics`` - Performance metrics and reporting

Benefits of Modular Design
--------------------------

**Maintainability**
    Each component has a single, focused responsibility

**Testability**
    Components can be tested in isolation

**Extensibility**
    New functionality can be added without affecting other components

**Code Organization**
    Related functionality is grouped together logically

**Backward Compatibility**
    Existing code continues to work without modification
"""

from .agent_factory import AGENT_TYPES, AgentFactory
from .base import OrchestratorBase
from .error_handling import ErrorHandler
from .execution_engine import ExecutionEngine
from .metrics import MetricsCollector
from .simplified_prompt_rendering import SimplifiedPromptRenderer


# Create the main Orchestrator class using multiple inheritance
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


__all__ = [
    "AGENT_TYPES",
    "AgentFactory",
    "ErrorHandler",
    "ExecutionEngine",
    "MetricsCollector",
    "Orchestrator",
    "OrchestratorBase",
    "SimplifiedPromptRenderer",
]
