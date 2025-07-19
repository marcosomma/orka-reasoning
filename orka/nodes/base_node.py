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

import abc
from typing import Any, Dict, List, Optional, TypeVar, Generic

T = TypeVar('T')  # Input type
R = TypeVar('R')  # Return type

class BaseNode(abc.ABC, Generic[T, R]):
    """
    Abstract base class for all agent nodes in the OrKa orchestrator.
    Defines the common interface and properties for agent nodes.
    """

    def __init__(
        self,
        node_id: str,
        prompt: Optional[str] = None,
        queue: Optional[List[Any]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize the base node with the given parameters.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (Optional[str]): Prompt or instruction for the node.
            queue (Optional[List]): Queue of agents or nodes to be processed.
            **kwargs: Additional parameters for the node.
        """
        self.node_id: str = node_id
        self.prompt: Optional[str] = prompt
        self.queue: List[Any] = queue or []
        self.params: Dict[str, Any] = kwargs
        self.type: str = self.__class__.__name__.lower()
        if self.type == "failing":
            self.agent_id: str = self.node_id

    async def initialize(self) -> None:
        """Initialize the node and its resources."""
        pass

    @abc.abstractmethod
    async def run(self, input_data: T) -> R:
        """
        Abstract method to run the logical node.

        Args:
            input_data: Input data for the node to process.

        Returns:
            The result of processing the input data.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        pass

    def __repr__(self) -> str:
        """
        Return a string representation of the node.

        Returns:
            str: String representation of the node.
        """
        return f"<{self.__class__.__name__} id={self.node_id} queue={self.queue}>"
