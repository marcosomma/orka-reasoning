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

from .agent_base import BaseAgent

class RouterAgent(BaseAgent):
    def __init__(self, agent_id, params=None, **kwargs):
        super().__init__(agent_id=agent_id, prompt=None, queue=None, **kwargs)
        if params is None:
            raise ValueError("RouterAgent requires 'params' with 'decision_key' and 'routing_map'.")
        self.params = params

    def run(self, input_data):
        previous_outputs = input_data.get("previous_outputs", {})
        decision_key = self.params.get("decision_key")
        routing_map = self.params.get("routing_map", {})

        decision_value = previous_outputs.get(decision_key)

        # Normalize decision value for flexible matching
        decision_value_str = str(decision_value).strip().lower()

        # Try matching: str, bool, fallback to ""
        route = (
            routing_map.get(decision_value) or                     # literal (True, False)
            routing_map.get(decision_value_str) or                 # string "true"/"false"
            routing_map.get(self._bool_key(decision_value_str)) or
            []
        )

        return route

    def _bool_key(self, val):
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
        return val
