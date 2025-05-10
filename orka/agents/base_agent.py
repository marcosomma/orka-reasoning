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
Base Agent Module
===============

This module defines the base agent classes for the OrKa framework,
providing both modern async and legacy sync implementations for
backward compatibility.

The BaseAgent class provides:
- Asynchronous execution with timeout handling
- Concurrency control for limiting parallel executions
- Resource lifecycle management (initialization and cleanup)
- Standardized error handling and result formatting
- Integration with the resource registry for dependency injection
- Backward compatibility with legacy sync agents

This unified implementation supports both the modern async pattern
and the legacy synchronous pattern for backward compatibility.
"""

import abc
import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional, TypeVar, Union

from ..contracts import Context, Output, Registry
from ..utils.concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseAgent:
    """
    Base class for all modern agents in the OrKa framework.

    Provides common functionality for asynchronous execution, concurrency control,
    error handling, and resource management that all derived agent classes inherit.

    This class supports both modern async patterns and legacy sync patterns
    for backward compatibility.
    """

    def __init__(
        self,
        agent_id: str,
        registry: Optional[Registry] = None,
        prompt: Optional[str] = None,
        queue: Optional[List[str]] = None,
        timeout: Optional[float] = 30.0,
        max_concurrency: int = 10,
        **kwargs,
    ):
        """
        Initialize the base agent with common properties.

        Args:
            agent_id (str): Unique identifier for the agent
            registry (Registry, optional): Resource registry for dependency injection
            prompt (str, optional): Prompt or instruction for the agent (legacy)
            queue (List[str], optional): Queue of agents or nodes (legacy)
            timeout (Optional[float]): Maximum execution time in seconds
            max_concurrency (int): Maximum number of concurrent executions
            **kwargs: Additional parameters specific to the agent type
        """
        self.agent_id = agent_id
        self.registry = registry
        self.timeout = timeout
        self.concurrency = ConcurrencyManager(max_concurrency=max_concurrency)
        self._initialized = False

        # Legacy attributes
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()

    async def initialize(self) -> None:
        """
        Initialize the agent and its resources.

        This method is called automatically before the first execution and
        should be overridden by derived classes to set up any required resources.
        """
        if self._initialized:
            return
        self._initialized = True

    async def run(self, ctx: Union[Context, Any]) -> Union[Output, Any]:
        """
        Run the agent with the given context.

        This method handles the execution workflow including:
        - Lazy initialization of the agent
        - Adding trace information to the context
        - Managing concurrency and timeouts
        - Standardizing error handling and result formatting

        Args:
            ctx: The execution context containing input and metadata.
                Can be a Context object for modern agents or any input for legacy agents.

        Returns:
            Output or Any: Standardized output for modern agents or direct result for legacy agents
        """
        if not self._initialized:
            await self.initialize()

        # Check if this is a legacy call pattern
        if hasattr(self, "_is_legacy_agent") and self._is_legacy_agent():
            # Call the legacy implementation
            if hasattr(self, "run") and not isinstance(self.run, type(BaseAgent.run)):
                return self.run(ctx)
            # Default to calling _run_legacy for compatibility
            return await self._run_legacy(ctx)

        # Modern agent pattern - process the context
        if not isinstance(ctx, dict):
            ctx = {"input": ctx}

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

    async def _run_legacy(self, input_data: Any) -> Any:
        """
        Legacy implementation that modern async classes should override
        if they need to support the legacy sync interface.

        Args:
            input_data: The input data to process

        Returns:
            Any: The result of processing the input data

        Raises:
            NotImplementedError: If not implemented by a subclass that needs legacy support
        """
        raise NotImplementedError(
            "Legacy agents must implement _run_legacy or override run"
        )

    async def cleanup(self) -> None:
        """
        Clean up agent resources.

        This method should be called when the agent is no longer needed to
        release any resources it may be holding, such as network connections,
        file handles, or memory.
        """
        await self.concurrency.shutdown()

    def __repr__(self):
        """
        Return a string representation of the agent.

        Returns:
            str: String representation showing agent class, ID, and queue.
        """
        return f"<{self.__class__.__name__} id={self.agent_id} queue={self.queue}>"


# Legacy abstract base class for backward compatibility
class LegacyBaseAgent(abc.ABC, BaseAgent):
    """
    Abstract base class for legacy agents in the OrKa framework.
    Provides compatibility with the older synchronous agent pattern.

    New agent implementations should use BaseAgent directly with async methods.
    This class exists only for backward compatibility.
    """

    def __init__(self, agent_id, prompt, queue, **kwargs):
        """
        Initialize the legacy base agent.

        Args:
            agent_id (str): Unique identifier for the agent.
            prompt (str): Prompt or instruction for the agent.
            queue (list): Queue of agents or nodes to be processed.
            **kwargs: Additional parameters specific to the agent type.
        """
        super().__init__(agent_id=agent_id, prompt=prompt, queue=queue, **kwargs)

    def _is_legacy_agent(self):
        """Identify this as a legacy agent for the unified run method"""
        return True

    @abc.abstractmethod
    def run(self, input_data):
        """
        Abstract method to run the agent's reasoning process.
        Must be implemented by all concrete agent classes.

        Args:
            input_data: Input data for the agent to process.

        Returns:
            The result of the agent's processing.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        pass
