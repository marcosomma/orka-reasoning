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
import time
from .agent_node import BaseNode

class FailingNode(BaseNode):
    @property
    def id(self):
        return getattr(self, "agent_id", getattr(self, "node_id", "unknown"))
    
    def run(self, input_data):
        # print(f"[ORKA][NODE][FAKE_NODE] {self.node_id}: Simulating failure...")
        time.sleep(5)  # simulate slow node
        raise RuntimeError(f"{self.node_id} failed intentionally after 5 seconds.")