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
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar('T')  # Input type
R = TypeVar('R')  # Return type

class BaseTool(abc.ABC, Generic[T, R]):
    """
    Abstract base class for all tools in the OrKa framework.
    Defines the common interface and properties that all tools must implement.
    """

    def __init__(
        self,
        tool_id: str,
        prompt: Optional[str] = None,
        queue: Optional[List[Any]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the base tool with common properties.

        Args:
            tool_id (str): Unique identifier for the tool.
            prompt (str, optional): Prompt or instruction for the tool.
            queue (list, optional): Queue of next tools to be processed.
            **kwargs: Additional parameters specific to the tool type.
        """
        self.tool_id: str = tool_id
        self.prompt: Optional[str] = prompt
        self.queue: Optional[List[Any]] = queue
        self.params: Dict[str, Any] = kwargs
        self.type: str = self.__class__.__name__.lower()

    @abc.abstractmethod
    def run(self, input_data: T) -> R:
        """
        Abstract method to run the tool's functionality.
        Must be implemented by all concrete tool classes.

        Args:
            input_data: Input data for the tool to process.

        Returns:
            The result of the tool's processing.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        pass

    def __repr__(self) -> str:
        """
        Return a string representation of the tool.

        Returns:
            str: String representation showing tool class and ID.
        """
        return f"<{self.__class__.__name__} id={self.tool_id}>"
