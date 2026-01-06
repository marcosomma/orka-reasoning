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

import abc
import time
from typing import Any

from ..contracts import OrkaResponse
from ..response_builder import ResponseBuilder


class BaseNode(abc.ABC):
    """
    Abstract base class for all agent nodes in the OrKa orchestrator.
    Defines the common interface and properties for agent nodes.
    """

    def __init__(self, node_id, prompt, queue, **kwargs):
        """
        Initialize the base node with the given parameters.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (str): Prompt or instruction for the node.
            queue (list): Queue of agents or nodes to be processed.
            **kwargs: Additional parameters for the node.
        """
        self.node_id = node_id
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()
        if self.type == "failing":
            self.agent_id = self.node_id

    async def initialize(self) -> None:
        """Initialize the node and its resources."""
        pass

    async def run(self, input_data: Any) -> OrkaResponse:
        """
        Run the node with the given input data.

        This method handles the execution workflow including:
        - Timing the execution
        - Handling errors gracefully
        - Returning standardized OrkaResponse format

        Args:
            input_data: The input data for the node.

        Returns:
            OrkaResponse: Standardized response with result, status, and metadata
        """
        execution_start_time = time.time()

        try:
            result = await self._run_impl(input_data)
            return ResponseBuilder.create_success_response(
                result=result,
                component_id=self.node_id,
                component_type="node",
                execution_start_time=execution_start_time,
                metadata={"node_type": self.__class__.__name__},
            )
        except Exception as e:
            return ResponseBuilder.create_error_response(
                error=str(e),
                component_id=self.node_id,
                component_type="node",
                execution_start_time=execution_start_time,
                metadata={"node_type": self.__class__.__name__},
            )

    @abc.abstractmethod
    async def _run_impl(self, input_data: Any) -> Any:
        """
        Implementation of the node's run logic.

        Subclasses must implement this method to define their specific behavior.
        This method receives the input data and should return the raw result.

        Args:
            input_data: The input data to process

        Returns:
            Any: The raw result of the node's processing
        """
        pass

    def __repr__(self):
        """
        Return a string representation of the node.

        Returns:
            str: String representation of the node.
        """
        return f"<{self.__class__.__name__} id={self.node_id} queue={self.queue}>"
