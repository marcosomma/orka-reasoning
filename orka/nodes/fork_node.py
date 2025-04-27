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
from .agent_node import BaseNode

class ForkNode(BaseNode):
    def __init__(self, node_id, prompt=None, queue=None, memory_logger=None, **kwargs):
        super().__init__(node_id=node_id, prompt=prompt, queue=queue, **kwargs)
        self.memory_logger = memory_logger
        self.config = kwargs  # ✅ store config explicitly

    async def run(self, orchestrator, context):
        targets = self.config.get("targets", [])
        if not targets:
            raise ValueError(f"ForkNode '{self.node_id}' requires non-empty 'targets' list.")

        fork_group_id = orchestrator.fork_manager.generate_group_id(self.node_id)
        orchestrator.fork_manager.create_group(fork_group_id, targets)

        # Fork agents into queue
        orchestrator.enqueue_fork(targets, fork_group_id)

        return {"status": "forked", "fork_group": fork_group_id}

