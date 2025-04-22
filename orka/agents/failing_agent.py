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
from .agent_base import BaseAgent

class FailingAgent(BaseAgent):
    def run(self, input_data):
        print(f"[FAKE_AGENT] {self.agent_id}: Simulating failure...")
        time.sleep(5)  # simulate slow agent
        raise RuntimeError(f"{self.agent_id} failed intentionally after 5 seconds.")