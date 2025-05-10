# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Basic Agents Module
=================

This module implements simple rule-based agents for the OrKa framework that don't
rely on external APIs or complex ML models. These agents serve as building blocks
for basic decision-making and classification tasks within orchestrated workflows.

The agents in this module include:
- BinaryAgent: Makes true/false decisions based on simple text patterns
- ClassificationAgent: Categorizes input into predefined classes using keyword matching

These simple agents can be used for:
- Quick prototyping of workflows
- Testing the orchestration infrastructure
- Implementing basic decision logic without external dependencies
- Serving as fallbacks when more complex agents fail or are unavailable

Both agent types inherit from the BaseAgent class and implement the required run()
method with simple rule-based logic.
"""

from .base_agent import LegacyBaseAgent as BaseAgent


class BinaryAgent(BaseAgent):
    """
    A simple agent that performs binary (true/false) decisions.

    This agent processes input text and returns either "true" or "false"
    based on simple text pattern matching. It demonstrates the most basic
    form of decision-making in the OrKa framework.

    The current implementation checks for the presence of 'yes', 'true',
    or 'correct' in the input to determine if the result should be true.
    This can be extended to more complex pattern matching or rule-based
    decision logic.
    """

    def run(self, input_data):
        """
        Make a binary decision based on text content.

        Args:
            input_data (dict): Input containing text to analyze, expected to have
                an 'input' field with the text content.

        Returns:
            str: 'true' if input contains positive indicators, 'false' otherwise.

        Note:
            This is a simplified implementation for demonstration purposes.
            In production, this would typically use more sophisticated rules
            or a trained classifier.
        """
        text = input_data.get("input", "")
        if isinstance(text, dict):
            text = text.get("input", "")

        positive = ["yes", "true", "correct"]
        if any(p in text.lower() for p in positive):
            return "true"
        else:
            return "false"


class ClassificationAgent(BaseAgent):
    """
    A simple agent that performs multi-class classification.

    This agent categorizes input text into predefined classes based on
    keyword matching. It demonstrates how to implement basic classification
    functionality in the OrKa framework.

    The current implementation uses a simple rule-based approach to classify
    input into 'cat' or 'dog' categories based on the presence of specific
    question words, but could be extended to support more sophisticated
    classification schemes.
    """

    def run(self, input_data):
        """
        Classify the input into categories based on question words.

        Args:
            input_data (dict): Input containing text to classify, expected to have
                an 'input' field with the text content.

        Returns:
            str: 'cat' if input contains 'why' or 'how', 'dog' otherwise.

        Note:
            This is a simplified implementation for demonstration purposes.
            In production, this would typically use a trained classifier
            or a more complex rule-based system.
        """
        text = input_data.get("input", "")
        if "why" in text.lower() or "how" in text.lower():
            return "cat"
        else:
            return "dog"
