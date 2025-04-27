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
    async def run(self, orchestrator, context):
        targets = self.config.get("targets", [])
        if not targets:
            raise ValueError(f"ForkNode {self.id} requires non-empty 'targets' list")

        group_id = f"{self.id}_{context['execution_id']}"
        orchestrator.create_fork_group(group_id, targets)

        await orchestrator.launch_parallel_agents(targets, parent_context=context, group_id=group_id)

        return {"status": "forked", "group_id": group_id}
