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

from jinja2 import Template

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
        queue = params.get("queue") if params else None
        agent_id = params.get("agent_id", "validation_agent") if params else "validation_agent"
        self.llm_agent = OpenAIAnswerBuilder(
            agent_id=f"{agent_id}_llm",
            prompt=prompt,
            queue=queue,
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

        # Extract clean response text from complex agent outputs
        context_output = input_data.get("previous_outputs", {}).get("context-collector", {})
        if isinstance(context_output, dict) and "result" in context_output:
            context = context_output["result"].get("response", "NONE")
        else:
            context = str(context_output) if context_output else "NONE"

        answer_output = input_data.get("previous_outputs", {}).get("answer-builder", {})
        if isinstance(answer_output, dict) and "result" in answer_output:
            answer = answer_output["result"].get("response", "NONE")
        else:
            answer = str(answer_output) if answer_output else "NONE"

        store_structure = self.params.get("store_structure")

        # Check if we have a custom prompt that needs template rendering
        if (
            hasattr(self.llm_agent, "prompt")
            and self.llm_agent.prompt
            and self.llm_agent.prompt.strip()
        ):
            # Use custom prompt with template rendering
            try:
                template = Template(self.llm_agent.prompt)
                prompt = template.render(**input_data)
            except Exception:
                # Fallback to original prompt if rendering fails
                prompt = self.llm_agent.prompt
        else:
            # Use default prompt building logic
            prompt = self.build_prompt(question, context, answer, store_structure)

        # Create LLM input with prompt but disable automatic JSON parsing
        # We'll handle JSON parsing manually since we expect a different schema
        llm_input = {"prompt": prompt, "parse_json": False}

        # Get response from LLM
        response = self.llm_agent.run(llm_input)

        # Extract the raw LLM output
        if isinstance(response, dict):
            raw_llm_output = response.get("response", "")
        else:
            raw_llm_output = str(response)

        try:
            # Manual JSON extraction from markdown code blocks
            import re

            # Look for JSON in markdown code blocks first
            json_match = re.search(r"```json\s*(.*?)\s*```", raw_llm_output, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Look for JSON object directly - use a more robust pattern
                # Find the first { and match to the corresponding }
                start_idx = raw_llm_output.find("{")
                if start_idx != -1:
                    # Count braces to find the matching closing brace
                    brace_count = 0
                    end_idx = start_idx
                    for i, char in enumerate(raw_llm_output[start_idx:], start_idx):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break

                    if brace_count == 0:  # Found matching closing brace
                        json_text = raw_llm_output[start_idx:end_idx]
                    else:
                        raise ValueError("Unmatched braces in JSON")
                else:
                    raise ValueError("No JSON structure found in response")

            # Parse the extracted JSON
            # Clean up the JSON text to handle potential formatting issues
            json_text = json_text.strip()

            # Try to fix common JSON issues
            # Replace single quotes with double quotes (if any)
            json_text = re.sub(r"'([^']*)':", r'"\1":', json_text)

            result = json.loads(json_text)

            # Check if we have the expected validation format
            if isinstance(result, dict) and "valid" in result:
                # Perfect - we have the expected format
                result["prompt"] = prompt
                result["formatted_prompt"] = prompt
                result["raw_llm_output"] = raw_llm_output
                return result
            elif isinstance(result, dict) and "response" in result:
                # LLM returned wrong format - convert it to validation format
                return {
                    "valid": False,
                    "reason": f"LLM returned wrong JSON format. Response: {result.get('response', 'Unknown')}",
                    "memory_object": None,
                    "prompt": prompt,
                    "formatted_prompt": prompt,
                    "raw_llm_output": raw_llm_output,
                }
            else:
                # Unknown JSON structure
                raise ValueError("Invalid JSON structure - unrecognized format")

        except Exception as e:
            # Fallback error handling
            return {
                "valid": False,
                "reason": f"Failed to parse model output: {e}. Raw output: {raw_llm_output}",
                "memory_object": None,
                "prompt": prompt,
                "formatted_prompt": prompt,
                "raw_llm_output": raw_llm_output,
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
        # If we have a custom prompt from the configuration, use it instead of the default logic
        if (
            hasattr(self.llm_agent, "prompt")
            and self.llm_agent.prompt
            and self.llm_agent.prompt.strip()
        ):
            # Use the custom prompt from the YAML configuration
            # The custom prompt should handle template variables itself
            return self.llm_agent.prompt

        # Fallback to default prompt building logic if no custom prompt is provided
        # Handle cases where context or answer is "NONE" or empty
        if context in ["NONE", "", None]:
            context = "No context available"
        if answer in ["NONE", "", None]:
            answer = "No answer provided"

        # Special handling for "NONE" responses - treat them as valid but low confidence
        if answer == "No answer provided" and context == "No context available":
            prompt = f"""Validate the following situation and structure it into a memory format.

Question: {question}

Context: {context}

Answer to validate: {answer}

This appears to be a case where no information was found for the question. Please validate this as a legitimate "no information available" response and structure it appropriately.

IMPORTANT: You MUST respond with the exact JSON format specified below. Do not use any other format.

For cases where no information is available, you should:
1. Mark as valid=true (since "no information available" is a valid response)
2. Set confidence to 0.1 (low but not zero)
3. Create a memory object that captures the fact that no information was found

{self._get_structure_instructions(store_structure)}

Return your response in the following JSON format:
{{
    "valid": true/false,
    "reason": "explanation of validation decision",
    "memory_object": {{
        // structured memory object if valid, null if invalid
    }}
}}"""
        else:
            prompt = f"""Validate the following answer and structure it into a memory format.

Question: {question}

Context: {context}

Answer to validate: {answer}

Please validate if the answer is correct and contextually coherent. Then structure the information into a memory object.

IMPORTANT: You MUST respond with the exact JSON format specified below. Do not use any other format.

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
- category: The category or type of information (e.g., 'fact', 'opinion', 'data')
- confidence: A number between 0 and 1 indicating confidence in the fact
- source: The source of the information (e.g., 'context', 'answer', 'inferred')"""
