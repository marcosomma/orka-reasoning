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
Orchestrator package for OrKa orchestration components.
"""

from .agent_factory import AGENT_TYPES, AgentFactory
from .base import OrchestratorBase
from .error_handling import ErrorHandler
from .execution_engine import ExecutionEngine
from .metrics import MetricsCollector
from .prompt_rendering import PromptRenderer


# Create the main Orchestrator class using multiple inheritance
class Orchestrator(
    OrchestratorBase,
    AgentFactory,
    PromptRenderer,
    ErrorHandler,
    MetricsCollector,
    ExecutionEngine,
):
    """
    The Orchestrator is the core engine that loads a YAML configuration,
    instantiates agents and nodes, and manages the execution of the reasoning workflow.
    It supports parallelism, dynamic routing, and full trace logging.

    This class now inherits from multiple mixins to provide all functionality
    while maintaining the same public interface.
    """

    def __init__(self, config_path):
        """
        Initialize the Orchestrator with a YAML config file.
        Loads orchestrator and agent configs, sets up memory and fork management.
        """
        # Initialize the base orchestrator
        super().__init__(config_path)

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
    "PromptRenderer",
]
