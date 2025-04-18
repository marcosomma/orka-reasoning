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

class BinaryAgent(BaseAgent):
    def run(self, input_data):
        # Placeholder logic: in real use, this would call an LLM or heuristic
        if isinstance(input_data, str) and "not" in input_data.lower():
            return False
        return True

class ClassificationAgent(BaseAgent):
    def run(self, input_data):
        # Placeholder logic: naive keyword classification
        if "why" in input_data.lower() or "how" in input_data.lower():
            return "opinion"
        elif "is" in input_data.lower() or "are" in input_data.lower():
            return "fact"
        else:
            return "question"
