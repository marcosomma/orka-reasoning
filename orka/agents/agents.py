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
    """
    A simple agent that performs binary classification.
    Returns True or False based on input content.
    """

    def run(self, input_data):
        """
        Perform binary classification on the input.

        Args:
            input_data (str or dict): Input to classify.

        Returns:
            bool: True if input doesn't contain 'not', False otherwise.
        """
        # Placeholder logic: in real use, this would call an LLM or heuristic
        if isinstance(input_data, str) and "not" in input_data.lower():
            return False
        return True


class ClassificationAgent(BaseAgent):
    """
    A simple agent that performs multi-class classification.
    Classifies input into 'cat' or 'dog' based on question words.
    """

    def run(self, input_data):
        """
        Classify the input into categories based on question words.

        Args:
            input_data (dict): Input containing text to classify.

        Returns:
            str: 'cat' if input contains 'why' or 'how', 'dog' otherwise.
        """
        text = input_data.get("input", "")
        if "why" in text.lower() or "how" in text.lower():
            return "cat"
        else:
            return "dog"
