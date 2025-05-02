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
import time
from .agent_node import BaseNode

class JoinNode(BaseNode):
    """
    A node that waits for and merges results from parallel branches created by a ForkNode.
    Implements timeout and waiting mechanisms for branch completion.
    """

    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        """
        Initialize the join node.
        
        Args:
            node_id (str): Unique identifier for the node.
            prompt (str): Prompt or instruction for the node.
            queue (list): Queue of agents or nodes to be processed.
            memory_logger: Logger for tracking node state.
            **kwargs: Additional configuration parameters.
        """
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.group_id = kwargs.get("group")
        self.timeout_seconds = kwargs.get("timeout_seconds", 60)
        self.output_key = f"{self.node_id}:output"

    def run(self, input_data):
        """
        Wait for and merge results from all branches in the fork group.
        
        Args:
            input_data (dict): Input data containing fork group information.
        
        Returns:
            dict: Status and merged results if complete, waiting status if not.
        """
        # print(f"[ORKA][NODE][JOIN] {self.node_id} received input: {input_data}")
        start_time = time.time()

        # Get fork group ID from input or configuration
        fork_group_id = input_data.get("fork_group_id", self.group_id)
        state_key = f"waitfor:join_parallel_checks:inputs"

        # Get list of received inputs and expected targets
        inputs_received = self.memory_logger.hkeys(state_key)
        received = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]

        fork_targets = self.memory_logger.smembers(f"fork_group:{fork_group_id}")
        fork_targets = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]

        # print(f"[ORKA][NODE][JOIN] All agents in group '{fork_group_id}' merging... Found {received}")

        # Check if all expected agents have completed
        if all(agent in received for agent in fork_targets):
            return self._complete(fork_targets, state_key)

        # Check for timeout
        if time.time() - start_time > self.timeout_seconds:
            return {"status": "timeout", "received": received}

        # Return waiting status if not all agents have completed
        return {"status": "waiting", "received": received}

    def _complete(self, fork_targets, state_key):
        """
        Complete the join operation by merging results from all branches.
        
        Args:
            fork_targets (list): List of agent IDs in the fork group.
            state_key (str): Redis key for storing state information.
        
        Returns:
            dict: Merged results from all branches.
        """
        # Merge results from all agents
        merged = {
            agent_id: json.loads(self.memory_logger.hget(state_key, agent_id))
            for agent_id in fork_targets
        }

        # Store merged results and clean up
        self.memory_logger.redis.set(self.output_key, json.dumps(merged))
        self.memory_logger.redis.delete(state_key)
        self.memory_logger.redis.delete(f"fork_group:{self.group_id}")

        return {"status": "done", "merged": merged}
