# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
🧠 **Agents Domain** - Intelligent Processing Units
================================================

This module defines the foundation for all OrKa agents - the cognitive building blocks
of your AI workflows. Agents are specialized processing units that transform inputs
into structured outputs while maintaining context and handling errors gracefully.

**Core Agent Philosophy:**
Think of agents as expert consultants in your workflow - each with specialized knowledge
and capabilities, working together to solve complex problems. They provide:

- 🎯 **Specialized Intelligence**: Each agent excels at specific tasks
- 🧠 **Context Awareness**: Maintains conversation and processing context
- 🔄 **Error Resilience**: Graceful failure handling with fallback strategies
- ⚡ **Performance**: Async execution with concurrency control
- 🔧 **Flexibility**: Support for both cloud LLMs and local models

**Agent Types:**
- **Classification Agents**: Route and categorize inputs intelligently
- **Answer Builders**: Synthesize complex information into coherent responses
- **Binary Agents**: Make precise true/false decisions
- **Memory Agents**: Store and retrieve contextual information
- **Tool Agents**: Integrate with external services and APIs

**Real-world Applications:**
- Customer service workflows with intelligent routing
- Content moderation with multi-stage validation
- Research assistants that combine search and synthesis
- Conversational AI with persistent memory
"""

import abc
import logging
import time
import uuid
from datetime import datetime
from typing import Any, TypeVar, Union

from ..contracts import Context, OrkaResponse, Registry
from ..response_builder import ResponseBuilder
from ..utils.concurrency import ConcurrencyManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseAgent(abc.ABC):
    """
    Agent Base Classes
    ==================

    This module defines the foundation for all OrKa agents - the processing units that
    transform inputs into outputs within orchestrated workflows.

    Agent Architecture
    -----------------

    OrKa provides two agent patterns to support different implementation needs:

    **Modern Async Pattern (BaseAgent)**
    - Full async/await support for concurrent execution
    - Structured output handling with automatic error wrapping
    - Built-in timeout and concurrency control
    - Lifecycle hooks for initialization and cleanup
    - Context-aware execution with trace information

    **Legacy Sync Pattern (LegacyBaseAgent)**
    - Simple synchronous execution model
    - Compatible with existing agent implementations
    - Direct result return without output wrapping
    - Backward compatibility for older agents

    Core Concepts
    ------------

    **Agent Lifecycle:**
    1. **Initialization**: Set up resources and validate configuration
    2. **Execution**: Process inputs with context awareness
    3. **Result Handling**: Structure outputs for downstream processing
    4. **Cleanup**: Release resources and maintain system health

    **Context Management:**
    - Agents receive context dictionaries containing input data and metadata
    - Trace IDs are automatically added for debugging and monitoring
    - Previous outputs from other agents are available in the context
    - Error information is captured and structured for debugging

    **Concurrency Control:**
    - Built-in concurrency manager limits parallel executions
    - Configurable timeout handling prevents hanging operations
    - Thread-safe execution for multi-agent workflows
    - Resource pooling for efficient memory usage

    Implementation Patterns
    ----------------------

    **Modern Agent Example:**
    ```python
    from orka.agents.base_agent import BaseAgent

    class MyModernAgent(BaseAgent):
        async def _run_impl(self, ctx):
            input_data = ctx.get("input")
            # Process input asynchronously
            result = await self.process_async(input_data)
            return result
    ```

    **Legacy Agent Example:**
    ```python
    from orka.agents.base_agent import LegacyBaseAgent

    class MyLegacyAgent(LegacyBaseAgent):
        def run(self, input_data):
            # Simple synchronous processing
            return self.process_sync(input_data)
    ```

    Error Handling
    --------------

    **Modern Agents:**
    - Exceptions are automatically caught and wrapped in Output objects
    - Error details are preserved for debugging
    - Status indicators show success/failure state
    - Metadata includes agent identification

    **Legacy Agents:**
    - Exceptions propagate directly to the orchestrator
    - Simple error handling for backward compatibility
    - Direct return values without wrapping

    Integration Features
    -------------------

    **Registry Integration:**
    - Agents can access shared resources through the registry
    - Dependency injection for memory, embedders, and other services
    - Lazy initialization of expensive resources

    **Orchestrator Integration:**
    - Agents are automatically discovered and instantiated
    - Configuration is passed through constructor parameters
    - Results flow seamlessly between agents in workflows

    **Monitoring and Debugging:**
    - Automatic trace ID generation for request tracking
    - Execution timing and performance metrics
    - Comprehensive logging for troubleshooting
    """

    def __init__(
        self,
        agent_id: str,
        registry: Registry | None = None,
        prompt: str | None = None,
        queue: list[str] | None = None,
        timeout: float | None = 30.0,
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

    async def run(self, ctx: Context | Any) -> OrkaResponse:
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
            OrkaResponse: Standardized response with result, status, and metadata
        """
        if not self._initialized:
            await self.initialize()

        # Process the context
        if not isinstance(ctx, dict):
            ctx = {"input": ctx}

        # Add trace information if not present
        trace_id = ctx.get("trace_id") or str(uuid.uuid4())
        if "trace_id" not in ctx:
            ctx["trace_id"] = trace_id
        if "timestamp" not in ctx:
            ctx["timestamp"] = datetime.now()

        execution_start_time = time.time()

        try:
            # Use concurrency manager to run the agent
            result = await self.concurrency.run_with_timeout(
                self._run_impl,
                self.timeout,
                ctx,
            )

            return ResponseBuilder.create_success_response(
                result=result,
                component_id=self.agent_id,
                component_type="agent",
                execution_start_time=execution_start_time,
                trace_id=trace_id,
                metadata={"agent_type": self.__class__.__name__},
            )
        except Exception as e:
            logger.error(f"Agent {self.agent_id} failed: {e!s}")
            return ResponseBuilder.create_error_response(
                error=str(e),
                component_id=self.agent_id,
                component_type="agent",
                execution_start_time=execution_start_time,
                trace_id=trace_id,
                metadata={"agent_type": self.__class__.__name__},
            )

    @abc.abstractmethod
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
        pass

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
