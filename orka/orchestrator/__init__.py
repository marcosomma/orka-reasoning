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

import logging
import os

from .agent_factory import AGENT_TYPES, AgentFactory
from .base import OrchestratorBase
from .error_handling import ErrorHandler
from .execution_engine import ExecutionEngine
from .metrics import MetricsCollector
from .simplified_prompt_rendering import SimplifiedPromptRenderer

logger = logging.getLogger(__name__)

# Feature registry for optional modules
_FEATURE_REGISTRY = {
    "support_triage": "orka.support_triage",
}

_loaded_features: set = set()


def load_feature(feature_name: str) -> bool:
    """
    Load an optional feature module and register its agents.

    Args:
        feature_name: Name of the feature (e.g., "support_triage")

    Returns:
        True if feature was loaded successfully, False otherwise
    """
    if feature_name in _loaded_features:
        return True

    if feature_name not in _FEATURE_REGISTRY:
        logger.warning(f"Unknown feature: {feature_name}")
        return False

    module_path = _FEATURE_REGISTRY[feature_name]
    try:
        import importlib

        module = importlib.import_module(module_path)
        if hasattr(module, "register_agents"):
            module.register_agents()
            _loaded_features.add(feature_name)
            logger.info(f"Loaded feature: {feature_name}")
            return True
        else:
            logger.warning(f"Feature {feature_name} has no register_agents function")
            return False
    except ImportError as e:
        logger.error(f"Failed to import feature {feature_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to load feature {feature_name}: {e}")
        return False


def load_features_from_env() -> None:
    """
    Load features specified in ORKA_FEATURES environment variable.

    Set ORKA_FEATURES to a comma-separated list of feature names:
        export ORKA_FEATURES=support_triage,other_feature
    """
    features_str = os.environ.get("ORKA_FEATURES", "")
    if not features_str:
        return

    features = [f.strip() for f in features_str.split(",") if f.strip()]
    for feature in features:
        load_feature(feature)


def get_loaded_features() -> set:
    """Get the set of currently loaded features."""
    return _loaded_features.copy()


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

    Features:
        Optional feature modules can be loaded by setting the ORKA_FEATURES
        environment variable to a comma-separated list of feature names:

            export ORKA_FEATURES=support_triage

        Or by calling load_feature() before creating an Orchestrator:

            from orka.orchestrator import load_feature
            load_feature("support_triage")
    """

    def __init__(self, config_path: str) -> None:
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        # Load features from environment variable (auto-discovery)
        load_features_from_env()

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
    # Feature loading
    "load_feature",
    "load_features_from_env",
    "get_loaded_features",
]
