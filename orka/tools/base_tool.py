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
Base Tool Module
===============

This module defines the abstract base class for all tools in the OrKa framework.
It establishes the core contract that all tool implementations must follow,
ensuring consistent behavior and interoperability within orchestrated workflows.

The BaseTool class provides:
- Common initialization parameters shared by all tools
- Abstract interface definition through the run() method
- Type identification via the tool's class name
- String representation for debugging and logging
"""

import abc
import time
from typing import Any

from ..contracts import OrkaResponse
from ..response_builder import ResponseBuilder


class BaseTool(abc.ABC):
    """
    Abstract base class for all tools in the OrKa framework.
    Defines the common interface and properties that all tools must implement.
    """

    def __init__(self, tool_id, prompt=None, queue=None, **kwargs):
        """
        Initialize the base tool with common properties.

        Args:
            tool_id (str): Unique identifier for the tool.
            prompt (str, optional): Prompt or instruction for the tool.
            queue (list, optional): Queue of next tools to be processed.
            **kwargs: Additional parameters specific to the tool type.
        """
        self.tool_id = tool_id
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()

    def run(self, input_data: Any) -> OrkaResponse:
        """
        Run the tool with the given input data.

        This method handles the execution workflow including:
        - Timing the execution
        - Handling errors gracefully
        - Returning standardized OrkaResponse format

        Args:
            input_data: Input data for the tool to process.

        Returns:
            OrkaResponse: Standardized response with result, status, and metadata
        """
        execution_start_time = time.time()

        try:
            result = self._run_impl(input_data)
            return ResponseBuilder.create_success_response(
                result=result,
                component_id=self.tool_id,
                component_type="tool",
                execution_start_time=execution_start_time,
                metadata={"tool_type": self.__class__.__name__},
            )
        except Exception as e:
            return ResponseBuilder.create_error_response(
                error=str(e),
                component_id=self.tool_id,
                component_type="tool",
                execution_start_time=execution_start_time,
                metadata={"tool_type": self.__class__.__name__},
            )

    @abc.abstractmethod
    def _run_impl(self, input_data: Any) -> Any:
        """
        Implementation of the tool's run logic.

        Subclasses must implement this method to define their specific behavior.
        This method receives the input data and should return the raw result.

        Args:
            input_data: The input data to process

        Returns:
            Any: The raw result of the tool's processing
        """
        pass

    def __repr__(self):
        """
        Return a string representation of the tool.

        Returns:
            str: String representation showing tool class and ID.
        """
        return f"<{self.__class__.__name__} id={self.tool_id}>"
