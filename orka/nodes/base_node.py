# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import abc


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

    @abc.abstractmethod
    async def run(self, input_data):
        """
        Abstract method to run the logical node.

        Args:
            input_data: Input data for the node to process.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    def __repr__(self):
        """
        Return a string representation of the node.

        Returns:
            str: String representation of the node.
        """
        return f"<{self.__class__.__name__} id={self.node_id} queue={self.queue}>"
