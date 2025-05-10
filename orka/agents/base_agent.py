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
Base Agent Module
===============

This module defines the modern implementation of the base agent class for the OrKa framework
with support for asynchronous execution, concurrency control, and resource management.

The BaseAgent class in this module provides:
- Asynchronous execution with timeout handling
- Concurrency control for limiting parallel executions
- Resource lifecycle management (initialization and cleanup)
- Standardized error handling and result formatting
- Integration with the resource registry for dependency injection

This implementation follows a more structured approach than the legacy agent_base.py,
using TypedDict contracts from the contracts module to enforce type safety and
providing a uniform interface for all derived agent classes.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from ..contracts import Context, Output, Registry
from ..utils.concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for all modern agents in the OrKa framework.

    Provides common functionality for asynchronous execution, concurrency control,
    error handling, and resource management that all derived agent classes inherit.
    """

    def __init__(
        self,
        agent_id: str,
        registry: Registry,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
    ):
        """
        Initialize the base agent with common properties.

        Args:
            agent_id (str): Unique identifier for the agent
            registry (Registry): Resource registry for dependency injection
            timeout (Optional[float]): Maximum execution time in seconds
            max_concurrency (int): Maximum number of concurrent executions
        """
        self.agent_id = agent_id
        self.registry = registry
        self.timeout = timeout
        self.concurrency = ConcurrencyManager(max_concurrency=max_concurrency)
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the agent and its resources.

        This method is called automatically before the first execution and
        should be overridden by derived classes to set up any required resources.
        """
        if self._initialized:
            return
        self._initialized = True

    async def run(self, ctx: Context) -> Output:
        """
        Run the agent with the given context.

        This method handles the execution workflow including:
        - Lazy initialization of the agent
        - Adding trace information to the context
        - Managing concurrency and timeouts
        - Standardizing error handling and result formatting

        Args:
            ctx (Context): The execution context containing input and metadata

        Returns:
            Output: Standardized output with result, status, and metadata
        """
        if not self._initialized:
            await self.initialize()

        # Add trace information if not present
        if "trace_id" not in ctx:
            ctx["trace_id"] = str(uuid.uuid4())
        if "timestamp" not in ctx:
            ctx["timestamp"] = datetime.now()

        try:
            # Use concurrency manager to run the agent
            result = await self.concurrency.run_with_timeout(
                self._run_impl, self.timeout, ctx
            )
            return Output(
                result=result,
                status="success",
                error=None,
                metadata={"agent_id": self.agent_id},
            )
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed: {str(e)}")
            return Output(
                result=None,
                status="error",
                error=str(e),
                metadata={"agent_id": self.agent_id},
            )

    async def _run_impl(self, ctx: Context) -> Any:
        """
        Implementation of the agent's run logic.

        This method must be implemented by all derived agent classes to
        provide the specific execution logic for that agent type.

        Args:
            ctx (Context): The execution context containing input and metadata

        Returns:
            Any: The result of the agent's processing

        Raises:
            NotImplementedError: If not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement _run_impl")

    async def cleanup(self) -> None:
        """
        Clean up agent resources.

        This method should be called when the agent is no longer needed to
        release any resources it may be holding, such as network connections,
        file handles, or memory.
        """
        await self.concurrency.shutdown()
