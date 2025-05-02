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

import os
from openai import OpenAI
from dotenv import load_dotenv
from .agent_base import BaseAgent

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
            temperature=1.0
        )
        # Extract and clean the response
        answer = response.choices[0].message.content.strip()
        return answer 

class OpenAIBinaryAgent(BaseAgent):
    """
    An agent that performs binary classification using OpenAI's GPT models.
    Returns True or False based on the input and prompt.
    """

    def run(self, input_data):
        """
        Perform binary classification using OpenAI's GPT model.
        
        Args:
            input_data (str): Input text to classify.
        
        Returns:
            bool: True if the model's response indicates positive, False otherwise.
        """
        # Construct prompt with strict constraints for binary output
        full_prompt = f"""
            {self.prompt}\n\n{input_data}. 
            ###Constrains: 
            - Answer strictly TRUE or FALSE.
        """
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0  # Use deterministic output
        )
        # Parse the response into a boolean
        answer = response.choices[0].message.content.strip().lower()
        return answer in ["true", "yes", "1"]

class OpenAIClassificationAgent(BaseAgent):
    """
    An agent that performs multi-class classification using OpenAI's GPT models.
    Returns one of the specified options based on the input.
    """

    def run(self, input_data):
        """
        Perform multi-class classification using OpenAI's GPT model.
        
        Args:
            input_data (str): Input text to classify.
        
        Returns:
            str: Selected category from the available options, or "unknown" if no match.
        """
        # Get classification options from agent parameters
        options = self.params.get("options", [])
        # Construct prompt with constraints for classification
        full_prompt = f"""{self.prompt}\n\n{input_data} 
            ###Constrains: 
            - Answer ONLY with one word.
            - Answer ONLY with one of the options.
            - Only pick from those options [{options}].
        """
        # Make API call to OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0  # Use deterministic output
        )
        # Parse the response and validate against options
        answer = response.choices[0].message.content.strip().lower()
        return answer if answer in options else "unknown"
