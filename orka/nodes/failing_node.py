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

    async def _run_impl(self, input_data):
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
