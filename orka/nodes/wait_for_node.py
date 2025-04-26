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

class WaitForNode(BaseNode):
    def __init__(self, node_id, prompt, queue, memory_logger=None, **kwargs):
        super().__init__(node_id, prompt, queue, **kwargs)
        self.memory_logger = memory_logger
        self.inputs = kwargs.get("inputs", [])
        self.output_key = f"{self.node_id}:output"
        self.state_key = f"waitfor:{self.node_id}:inputs"

    def run(self, input_data):
        previous_outputs = input_data.get("previous_outputs", {})
        for agent_id in self.inputs:
            if agent_id in previous_outputs:
                self.memory_logger.redis.hset(self.state_key, agent_id, json.dumps(previous_outputs[agent_id]))

        inputs_received = self.memory_logger.redis.hkeys(self.state_key)
        received = [i.decode() if isinstance(i, bytes) else i for i in inputs_received]
        if all(agent in received for agent in self.inputs):
            return self._complete()
        else:
            return {"status": "waiting", "received": received}


    def _complete(self):
        merged = {
            agent_id: json.loads(self.memory_logger.redis.hget(self.state_key, agent_id))
            for agent_id in self.inputs
        }

        self.memory_logger.redis.set(self.output_key, json.dumps(merged))
        self.memory_logger.log(
            agent_id=self.node_id,
            event_type="wait_complete",
            payload=merged
        )
        self.memory_logger.redis.delete(self.state_key)

        return {"status": "done", "merged": merged}
