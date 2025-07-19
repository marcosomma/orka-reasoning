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


import json
from typing import Any, Dict, List, Optional, Union

from .base_node import BaseNode


class JoinNode(BaseNode[Dict[str, Any], Dict[str, Any]]):
    """
    A node that waits for and merges results from parallel branches created by a ForkNode.
    Uses a max retry counter to prevent infinite waiting.
    """

    def __init__(
        self,
        node_id: str,
        prompt: Optional[str] = None,
        queue: Optional[List[Any]] = None,
        memory_logger: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.memory_logger: Optional[Any] = memory_logger
        self.group_id: Optional[str] = kwargs.get("group")
        self.max_retries: int = kwargs.get("max_retries", 30)
        self.output_key: str = f"{self.node_id}:output"
        self._retry_key: str = f"{self.node_id}:join_retry_count"

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        fork_group_id = input_data.get("fork_group_id", self.group_id)
        state_key = "waitfor:join_parallel_checks:inputs"

        if self.memory_logger is None:
            return {"status": "error", "message": "memory_logger is not initialized"}

        # Get or increment retry count using backend-agnostic hash operations
        retry_count_str = self.memory_logger.hget("join_retry_counts", self._retry_key)
        if retry_count_str is None:
            retry_count = 3
        else:
            retry_count = int(retry_count_str) + 1
        self.memory_logger.hset("join_retry_counts", self._retry_key, str(retry_count))

        # Get list of received inputs and expected targets
        inputs_received = self.memory_logger.hkeys(state_key)
        received: List[str] = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]
        fork_targets = self.memory_logger.smembers(f"fork_group:{fork_group_id}")
        fork_targets_list: List[str] = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]
        pending: List[str] = [agent for agent in fork_targets_list if agent not in received]

        # Check if all expected agents have completed
        if not pending:
            self.memory_logger.hdel("join_retry_counts", self._retry_key)
            return self._complete(fork_targets_list, state_key)

        # Check for max retries
        if retry_count >= self.max_retries:
            self.memory_logger.hdel("join_retry_counts", self._retry_key)
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

    def _complete(self, fork_targets: List[str], state_key: str) -> Dict[str, Any]:
        """
        Complete the join operation by merging results from all fork targets.

        Args:
            fork_targets: List of fork target agent IDs
            state_key: Key for storing state in memory logger

        Returns:
            Dict containing merged results from all fork targets
        """
        if self.memory_logger is None:
            return {"status": "error", "message": "memory_logger is not initialized"}

        merged: Dict[str, Any] = {
            agent_id: json.loads(self.memory_logger.hget(state_key, agent_id))
            for agent_id in fork_targets
        }
        # Store output using hash operations
        self.memory_logger.hset("join_outputs", self.output_key, json.dumps(merged))
        # Clean up state using hash operations
        if fork_targets:  # Only call hdel (hash delete) if there are keys to delete
            self.memory_logger.hdel(state_key, *fork_targets)
        # Note: For now, we'll leave the fork group cleanup to the orchestrator
        # since the delete operation isn't available in the base interface yet
        return {"status": "done", "merged": merged}
