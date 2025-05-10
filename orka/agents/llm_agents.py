# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import os

from dotenv import load_dotenv
from openai import OpenAI

from .base_agent import LegacyBaseAgent as BaseAgent

# Load environment variables
load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("BASE_OPENAI_MODEL", "gpt-3.5-turbo")

# Validate OpenAI API key
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable is required")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


class OpenAIAnswerBuilder(BaseAgent):
    """
    An agent that uses OpenAI's GPT models to generate answers based on a prompt.
    This is a base class for various OpenAI-powered agents.
    """

    def run(self, input_data):
        """
        Generate an answer using OpenAI's GPT model.

        Args:
            input_data (str): Input text to process.

        Returns:
            str: Generated answer from the model.
        """
        # Combine the agent's prompt with the input data
        full_prompt = f"{self.prompt}\n\n{input_data}"
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=1.0,
        )
        # Extract and clean the response
        answer = response.choices[0].message.content.strip()
        return answer


class OpenAIBinaryAgent(OpenAIAnswerBuilder):
    """
    An agent that uses OpenAI's models to make binary (yes/no) decisions.

    This agent processes the input text with GPT and extracts a true/false decision
    from the generated response. It uses the same mechanism as the OpenAIAnswerBuilder
    but interprets the output as a binary decision.
    """

    def run(self, input_data):
        """
        Make a true/false decision using OpenAI's GPT model.

        Args:
            input_data (str): Input text to process.

        Returns:
            str: "true" or "false" based on the model's response.
        """
        # Get the full answer from the base class
        answer = super().run(input_data)

        # Convert to binary decision
        positive_indicators = ["yes", "true", "correct", "right", "affirmative"]
        for indicator in positive_indicators:
            if indicator in answer.lower():
                return "true"

        return "false"


class OpenAIClassificationAgent(OpenAIAnswerBuilder):
    """
    An agent that uses OpenAI's models to classify input into categories.

    This agent processes the input text with GPT and classifies it into one of the
    predefined categories based on the model's response. The categories can be
    customized by setting them in the agent's params.
    """

    def run(self, input_data):
        """
        Classify input using OpenAI's GPT model.

        Args:
            input_data (str): Input text to classify.

        Returns:
            str: Category name based on the model's classification.
        """
        # Get the full answer from the base class
        answer = super().run(input_data)

        # Extract categories from params or use defaults
        categories = self.params.get("categories", ["cat", "dog"])

        # Simple classification approach: check for each category in the response
        for category in categories:
            if category.lower() in answer.lower():
                return category

        # Default to the first category if none matched
        return categories[0]
