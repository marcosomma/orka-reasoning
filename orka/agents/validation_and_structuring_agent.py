"""
Validation and Structuring Agent
==============================

This module provides the ValidationAndStructuringAgent class, which is responsible for
validating answers and structuring them into a memory format. The agent ensures answers
are correct and contextually coherent, then extracts key information into a structured
memory object.

Classes
-------
ValidationAndStructuringAgent
    Agent that validates answers and structures them into memory objects.
"""

import json
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from .llm_agents import OpenAIAnswerBuilder


class ValidationAndStructuringAgent(BaseAgent):
    """
    Agent that validates answers and structures them into memory objects.

    This agent performs two main functions:
    1. Validates if an answer is correct and contextually coherent
    2. Structures valid answers into a memory object format

    The agent uses an LLM (Language Model) to perform validation and structuring.
    It returns a dictionary containing:
    - valid: Boolean indicating if the answer is valid
    - reason: Explanation of the validation decision
    - memory_object: Structured memory object if valid, None otherwise

    Parameters
    ----------
    params : Dict[str, Any], optional
        Configuration parameters for the agent, including:
        - prompt: The base prompt for the LLM
        - queue: Optional queue for async operations
        - agent_id: Unique identifier for the agent
        - store_structure: Optional template for memory object structure

    Attributes
    ----------
    llm_agent : OpenAIAnswerBuilder
        The LLM agent used for validation and structuring
    """

    def __init__(self, params: Dict[str, Any] = None):
        """Initialize the agent with an OpenAIAnswerBuilder for LLM calls."""
        super().__init__(params)
        # Initialize LLM agent with required parameters
        prompt = params.get("prompt", "") if params else ""
        queue = params.get("queue", None) if params else None
        agent_id = (
            params.get("agent_id", "validation_agent") if params else "validation_agent"
        )
        self.llm_agent = OpenAIAnswerBuilder(
            agent_id=f"{agent_id}_llm", prompt=prompt, queue=queue
        )

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the input data to validate and structure the answer.

        Args:
            input_data: Dictionary containing:
                - question: The original question
                - full_context: The context used to generate the answer
                - latest_answer: The answer to validate and structure
                - store_structure: Optional structure template for memory objects

        Returns:
            Dictionary containing:
                - valid: Boolean indicating if the answer is valid
                - reason: Explanation of validation decision
                - memory_object: Structured memory object if valid, None otherwise
        """
        question = input_data.get("input", "")
        context = input_data.get("previous_outputs", {}).get("context-collector", "")
        answer = input_data.get("previous_outputs", {}).get("answer-builder", "")
        store_structure = self.params.get("store_structure")

        prompt = self.build_prompt(question, context, answer, store_structure)

        # Create LLM input with prompt
        llm_input = {"prompt": prompt}

        # Get response from LLM
        response = self.llm_agent.run(llm_input)

        try:
            return json.loads(response)
        except Exception as e:
            return {
                "valid": False,
                "reason": f"Failed to parse model output: {e}",
                "memory_object": None,
            }

    def build_prompt(
        self,
        question: str,
        context: str,
        answer: str,
        store_structure: Optional[str] = None,
    ) -> str:
        """
        Build the prompt for the validation and structuring task.

        Args:
            question: The original question
            context: The context used to generate the answer
            answer: The answer to validate and structure
            store_structure: Optional structure template for memory objects

        Returns:
            The complete prompt for the LLM
        """
        prompt = f"""Validate the following answer and structure it into a memory format.

Question: {question}

Context: {context}

Answer to validate: {answer}

Please validate if the answer is correct and contextually coherent. Then structure the information into a memory object.

{self._get_structure_instructions(store_structure)}

Return your response in the following JSON format:
{{
    "valid": true/false,
    "reason": "explanation of validation decision",
    "memory_object": {{
        // structured memory object if valid, null if invalid
    }}
}}"""

        return prompt

    def _get_structure_instructions(self, store_structure: Optional[str] = None) -> str:
        """
        Get the structure instructions for the memory object.

        Args:
            store_structure: Optional structure template for memory objects

        Returns:
            Instructions for structuring the memory object
        """
        if store_structure:
            return f"""Structure the memory object according to this template:
{store_structure}

Ensure all required fields are present and properly formatted."""
        else:
            return """Structure the memory object with these fields:
- fact: The validated fact or information
- category: The category or type of information
- confidence: A number between 0 and 1 indicating confidence in the fact
- source: The source of the information (e.g., 'context', 'answer', 'inferred')"""
