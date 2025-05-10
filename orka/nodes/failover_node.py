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
from datetime import datetime

from .base_node import BaseNode


class FailoverNode(BaseNode):
    """
    A node that implements failover logic by trying multiple child nodes in sequence.
    If one child fails, it tries the next one until one succeeds or all fail.
    """

    def __init__(self, node_id, children, queue):
        """
        Initialize the failover node.

        Args:
            node_id (str): Unique identifier for the node.
            children (list): List of child nodes to try in sequence.
            queue (list): Queue of agents or nodes to be processed.
        """
        self.id = node_id
        self.children = children
        self.queue = queue
        self.type = self.__class__.__name__.lower()

    def run(self, input_data):
        """
        Run the failover logic by trying each child node in sequence.

        Args:
            input_data: Input data to pass to child nodes.

        Returns:
            dict: Result from the first successful child node.

        Raises:
            RuntimeError: If all child nodes fail.
        """
        for child in self.children:
            child_id = getattr(
                child, "agent_id", getattr(child, "node_id", "unknown_child")
            )
            try:
                # Try running the current child node
                result = child.run(input_data)
                if result:
                    return {child_id: result}
            except Exception as e:
                # Log the failure and continue to next child
                print(
                    f"{datetime.now()} > [ORKA][NODE][FAILOVER][WARNING] Agent '{child_id}' failed: {e}"
                )
        raise RuntimeError("All fallback agents failed.")
