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


import json
from .agent_node import BaseNode

class JoinNode(BaseNode):
    """
    JoinNode is responsible for synchronizing and merging results from parallel branches
    created by a ForkNode in a workflow. It waits for all expected agents to complete
    their tasks, merges their results, and handles timeouts if not all agents respond
    within a specified number of retries.

    Attributes:
        node_id (str): Unique identifier for the node.
        prompt (str): Prompt or description for the node.
        queue: Queue object for task management.
        memory_logger: Logger with Redis interface for state management.
        group_id (str): Identifier for the group of parallel agents to join.
        max_retries (int): Maximum number of retries before timing out.
        output_key (str): Redis key for storing merged output.
        _retry_key (str): Redis key for tracking retry count.
    """

    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        """
        Initialize a JoinNode.

        Args:
            node_id (str): Unique identifier for the node.
            prompt (str): Prompt or description for the node.
            queue: Queue object for task management.
            memory_logger: Logger with Redis interface for state management.
            **kwargs: Additional keyword arguments (e.g., group, max_retries).
        """
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.group_id = kwargs.get("group")
        self.max_retries = kwargs.get("max_retries", 30)
        self.output_key = f"{self.node_id}:output"
        self._retry_key = f"{self.node_id}:join_retry_count"

    def run(self, input_data):
        """
        Main execution method for the JoinNode. Waits for all expected parallel agents
        to complete, merges their results, and handles timeouts.

        Args:
            input_data (dict): Input data containing at least 'fork_group_id'.

        Returns:
            dict: Status information, including 'waiting', 'timeout', or 'done'.
        """
        fork_group_id = input_data.get("fork_group_id", self.group_id)
        state_key = f"waitfor:join_parallel_checks:inputs"

        # Get or increment retry count in Redis
        retry_count = self.memory_logger.redis.get(self._retry_key)
        if retry_count is None:
            retry_count = 3
        else:
            retry_count = int(retry_count) + 1
        self.memory_logger.redis.set(self._retry_key, retry_count)

        # Get list of received inputs and expected targets
        inputs_received = self.memory_logger.hkeys(state_key)
        received = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]
        fork_targets = self.memory_logger.smembers(f"fork_group:{fork_group_id}")
        fork_targets = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]
        pending = [agent for agent in fork_targets if agent not in received]

        # Check if all expected agents have completed
        if not pending:
            self.memory_logger.redis.delete(self._retry_key)
            return self._complete(fork_targets, state_key)

        # Check for max retries
        if retry_count >= self.max_retries:
            self.memory_logger.redis.delete(self._retry_key)
            return {
                "status": "timeout",
                "pending": pending,
                "received": received,
                "max_retries": self.max_retries,
            }

        # Return waiting status if not all agents have completed
        return {
            "status": "waiting",
            "pending": pending,
            "received": received,
            "retry_count": retry_count,
            "max_retries": self.max_retries,
        }

    def _complete(self, fork_targets, state_key):
        """
        Merge results from all completed agents and clean up Redis state.

        Args:
            fork_targets (list): List of agent IDs expected to complete.
            state_key (str): Redis key where agent results are stored.

        Returns:
            dict: Status 'done' and the merged results.
        """
        merged = {
            agent_id: json.loads(self.memory_logger.hget(state_key, agent_id))
            for agent_id in fork_targets
        }
        self.memory_logger.redis.set(self.output_key, json.dumps(merged))
        self.memory_logger.redis.delete(state_key)
        self.memory_logger.redis.delete(f"fork_group:{fork_targets[0] if fork_targets else ''}")
        return {"status": "done", "merged": merged}