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

import abc


class BaseAgent(abc.ABC):
    """
    Abstract base class for all agents in the OrKa framework.
    Defines the common interface and properties that all agents must implement.
    """

    def __init__(self, agent_id, prompt, queue, **kwargs):
        """
        Initialize the base agent with common properties.

        Args:
            agent_id (str): Unique identifier for the agent.
            prompt (str): Prompt or instruction for the agent.
            queue (list): Queue of agents or nodes to be processed.
            **kwargs: Additional parameters specific to the agent type.
        """
        self.agent_id = agent_id
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()

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

    def __repr__(self):
        """
        Return a string representation of the agent.

        Returns:
            str: String representation showing agent class, ID, and queue.
        """
        return f"<{self.__class__.__name__} id={self.agent_id} queue={self.queue}>"
