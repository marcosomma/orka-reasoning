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
import time

from .base_node import BaseNode


class FailingNode(BaseNode):
    """
    A node that simulates failure for testing purposes.
    Intentionally raises a RuntimeError after a delay.
    """

    @property
    def id(self):
        """
        Get the ID of the node.

        Returns:
            str: The node ID.
        """
        return getattr(self, "agent_id", getattr(self, "node_id", "unknown"))

    def run(self, input_data):
        """
        Simulate a failing node by raising a RuntimeError after a delay.

        Args:
            input_data: Input data for the node (unused in this implementation).

        Raises:
            RuntimeError: Always raises an error to simulate failure.
        """
        # print(f"[ORKA][NODE][FAKE_NODE] {self.node_id}: Simulating failure...")
        time.sleep(5)  # simulate slow node
        raise RuntimeError(f"{self.node_id} failed intentionally after 5 seconds.")
