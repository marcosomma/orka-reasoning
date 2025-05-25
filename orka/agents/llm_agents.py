# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
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

# Check if we're running in test mode
PYTEST_RUNNING = os.getenv("PYTEST_RUNNING", "").lower() in ("true", "1", "yes")

# Validate OpenAI API key, except in test environments
if not PYTEST_RUNNING and not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable is required")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY or "dummy_key_for_testing")


class OpenAIAnswerBuilder(BaseAgent):
    """
    An agent that uses OpenAI's GPT models to generate answers based on a prompt.
    This is a base class for various OpenAI-powered agents.
    """

    def run(self, input_data):
        """
        Generate an answer using OpenAI's GPT model.

        Args:
            input_data (dict): Input data containing:
                - prompt (str): The prompt to use (optional, defaults to agent's prompt)
                - model (str): The model to use (optional, defaults to OPENAI_MODEL)
                - temperature (float): Temperature for generation (optional, defaults to 0.7)

        Returns:
            str: Generated answer from the model.
        """
        # Extract parameters from input_data
        prompt = input_data.get("prompt", self.prompt)
        model = input_data.get("model", OPENAI_MODEL)
        temperature = float(input_data.get("temperature", 0.7))
        full_prompt = f"{prompt}\n\n{input_data}"

        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=temperature,
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
            input_data (dict): Input data containing:
                - prompt (str): The prompt to use (optional, defaults to agent's prompt)
                - model (str): The model to use (optional, defaults to OPENAI_MODEL)
                - temperature (float): Temperature for generation (optional, defaults to 0.7)

        Returns:
            bool: True or False based on the model's response.
        """
        # Override the parent method to add constraints to the prompt
        # Ask the model to only return a "true" or "false" response
        constraints = (
            "**CONSTRAINTS** ONLY and STRICTLY Return boolean 'true' or 'false' value."
        )

        # Get the original prompt and add constraints
        original_prompt = input_data.get("prompt", self.prompt)
        enhanced_prompt = f"{original_prompt}\n\n{constraints}"

        # Create new input_data with enhanced prompt
        enhanced_input = input_data.copy()
        enhanced_input["prompt"] = enhanced_prompt

        # Get the answer using the enhanced prompt
        answer = super().run(enhanced_input)

        # Convert to binary decision
        positive_indicators = ["yes", "true", "correct", "right", "affirmative"]
        for indicator in positive_indicators:
            if indicator in answer.lower():
                return True

        return False


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
            input_data (dict): Input data containing:
                - prompt (str): The prompt to use (optional, defaults to agent's prompt)
                - model (str): The model to use (optional, defaults to OPENAI_MODEL)
                - temperature (float): Temperature for generation (optional, defaults to 0.7)

        Returns:
            str: Category name based on the model's classification.
        """
        # Extract categories from params or use defaults
        categories = self.params.get("options", [])
        constrains = "**CONSTRAINS**ONLY Return values from the given options. If not return 'not-classified'"

        # Get the base prompt
        base_prompt = input_data.get("prompt", self.prompt)

        # Create enhanced prompt with categories
        enhanced_prompt = f"{base_prompt} {constrains}\n Options:{categories}"

        # Create new input_data with enhanced prompt
        enhanced_input = input_data.copy()
        enhanced_input["prompt"] = enhanced_prompt

        # Use parent class to make the API call
        answer = super().run(enhanced_input)
        return answer
