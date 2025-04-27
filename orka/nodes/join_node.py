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
    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.group_id = kwargs.get("group")  # track which fork group
        self.timeout_seconds = kwargs.get("timeout_seconds", 60)
        self.output_key = f"{self.node_id}:output"
        self.state_key = f"waitfor:{self.node_id}:inputs"

    def run(self, input_data):
        start_time = time.time()

        # 🔥 Get dynamic fork group id from input_data (fallback to self.group_id if missing)
        fork_group_id = input_data.get("fork_group_id", self.group_id)

        state_key = f"waitfor:{fork_group_id}:inputs"

        # Fetch completed outputs
        inputs_received = self.memory_logger.redis.hkeys(state_key)
        received = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]

        # Fetch correct forked agent ids
        fork_targets = self.memory_logger.redis.smembers(f"fork_group:{fork_group_id}")
        fork_targets = [i.decode() if isinstance(i, bytes) else i for i in fork_targets]

        print(f"[JOIN] All agents in group '{fork_group_id}' merging... Found {received}")

        if all(agent in received for agent in fork_targets):
            return self._complete(fork_targets, state_key)

        if time.time() - start_time > self.timeout_seconds:
            return {"status": "timeout", "received": received}

        return {"status": "waiting", "received": received}



    def _complete(self, fork_targets, state_key):
        merged = {
            agent_id: json.loads(self.memory_logger.redis.hget(state_key, agent_id))
            for agent_id in fork_targets
        }

        self.memory_logger.redis.set(self.output_key, json.dumps(merged))
        self.memory_logger.log(
            agent_id=self.node_id,
            event_type="wait_complete",
            payload=merged
        )

        self.memory_logger.redis.delete(state_key)
        self.memory_logger.redis.delete(f"fork_group:{self.group_id}")

        return {"status": "done", "merged": merged}



