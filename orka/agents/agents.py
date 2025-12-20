# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

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

from ..contracts import Context
from .base_agent import BaseAgent


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

    async def _run_impl(self, ctx: Context):
        """
        Make a binary decision based on text content.

        Args:
            ctx (dict): Input containing text to analyze, expected to have
                an 'input' field with the text content.

        Returns:
            str: 'true' if input contains positive indicators, 'false' otherwise.

        Note:
            This is a simplified implementation for demonstration purposes.
            In production, this would typically use more sophisticated rules
            or a trained classifier.
        """
        input_value = ctx.get("input", "")
        text = str(input_value) if not isinstance(input_value, str) else input_value

        positive = ["yes", "true", "correct"]
        if any(p in text.lower() for p in positive):
            return True
        else:
            return False


class ClassificationAgent(BaseAgent):
    """
    A simple agent that performs multi-class classification.

    .. deprecated:: 0.5.6
        This agent is deprecated and will be removed in a future version.
        The run method now returns "deprecated" instead of performing
        classification. Use other classification agents from the
        :mod:`orka.agents.llm_agents` module for current classification needs.

    Legacy Implementation:
        This agent previously categorized input text into predefined classes
        based on keyword matching using a simple rule-based approach.
    """

    async def _run_impl(self, ctx: Context):
        """
        Deprecated method that returns "deprecated".

        .. deprecated:: 0.5.6
            This method no longer performs classification and simply
            returns the string "deprecated" to indicate the agent
            should not be used.

        Args:
            ctx: Input data (ignored)

        Returns:
            str: Always returns "deprecated"
        """
        return "deprecated"
