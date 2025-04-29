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
from datetime import datetime
from .agent_node import BaseNode


class FailoverNode(BaseNode):
    def __init__(self, node_id, children, queue):
        self.id = node_id
        self.children = children
        self.queue = queue
        self.type = self.__class__.__name__.lower() 

    def run(self, input_data):
        for child in self.children:
            child_id = getattr(child, "agent_id", getattr(child, "node_id", "unknown_child"))
            try:        
                # print(f"[ORKA][NODE][FAILOVER] Trying agent '{child_id}'")
                result = child.run(input_data)
                if result:
                    # print(f"[ORKA][NODE][FAILOVER] Agent '{child_id}' succeeded.")
                    return {child_id: result}
            except Exception as e:
                print(f"{datetime.now()} > [ORKA][NODE][FAILOVER][WARNING] Agent '{child_id}' failed: {e}")
        raise RuntimeError("All fallback agents failed.")
