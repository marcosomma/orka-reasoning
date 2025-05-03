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
    A node that waits for and merges results from parallel branches created by a ForkNode.
    Uses a max retry counter to prevent infinite waiting.
    """

    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.group_id = kwargs.get("group")
        self.max_retries = kwargs.get("max_retries", 30)
        self.output_key = f"{self.node_id}:output"
        self._retry_key = f"{self.node_id}:join_retry_count"

    def run(self, input_data):
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
        merged = {
            agent_id: json.loads(self.memory_logger.hget(state_key, agent_id))
            for agent_id in fork_targets
        }
        self.memory_logger.redis.set(self.output_key, json.dumps(merged))
        self.memory_logger.redis.delete(state_key)
        self.memory_logger.redis.delete(f"fork_group:{fork_targets[0] if fork_targets else ''}")
        return {"status": "done", "merged": merged}