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

    @abc.abstractmethod
    def run(self, input_data):
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

    def __repr__(self):
        """
        Return a string representation of the tool.

        Returns:
            str: String representation showing tool class and ID.
        """
        return f"<{self.__class__.__name__} id={self.tool_id}>"
