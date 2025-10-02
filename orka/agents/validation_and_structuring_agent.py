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
import logging
from typing import Any, Dict, Optional, Union, cast

from jinja2 import Template

logger = logging.getLogger(__name__)

from .base_agent import BaseAgent, Context
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

    def __init__(self, params: Dict[str, Any]):
        """Initialize the agent with an OpenAIAnswerBuilder for LLM calls."""
        _agent_id = params.get("agent_id", "validation_agent")
        super().__init__(
            agent_id=_agent_id,  # Pass agent_id to BaseAgent
            stream_key=_agent_id,  # Use agent_id as stream_key
            debug_keep_previous_outputs=False,  # Default value
            decay_config=None,  # Default value
        )
        # Initialize LLM agent with required parameters
        prompt = params.get("prompt", "")
        queue = params.get("queue")
        agent_id = params.get("agent_id", "validation_agent")
        self.llm_agent = OpenAIAnswerBuilder(
            agent_id=f"{agent_id}_llm",
            prompt=prompt,
            queue=queue,
        )

    def _parse_llm_output(
        self, raw_llm_output: str, prompt: str, formatted_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse the LLM output and extract the validation result.

        Args:
            raw_llm_output: The raw output from the LLM
            prompt: The prompt used to generate the output

        Returns:
            Dict[str, Any]: The parsed validation result
        """
        # Create base response with common fields
        base_response = {
            "prompt": prompt,
            "formatted_prompt": formatted_prompt if formatted_prompt else prompt,
            "raw_llm_output": raw_llm_output,
        }

        try:
            # Look for JSON in markdown code blocks first
            import re

            json_match = re.search(r"```json\s*(.*?)\s*```", raw_llm_output, re.DOTALL)
            json_text = json_match.group(1) if json_match else raw_llm_output

            # Clean up the JSON text to handle potential formatting issues
            json_text = json_text.strip()

            # Try to fix common JSON issues
            # Replace single quotes with double quotes (if any)
            json_text = re.sub(r"'([^']*)':", r'"\1":', json_text)

            # Parse JSON
            result = json.loads(json_text)

            # Handle non-dict responses
            if not isinstance(result, dict):
                return {
                    **base_response,
                    "valid": False,
                    "reason": "Invalid JSON structure - not a dictionary",
                    "memory_object": None,
                }

            # Handle dict responses based on their content
            if "valid" in result:
                # Add common fields to the result
                result.update(base_response)
                return result

            if "response" in result:
                return {
                    **base_response,
                    "valid": False,
                    "reason": f"LLM returned wrong JSON format. Response: {result.get('response', 'Unknown')}",
                    "memory_object": None,
                }

            # Handle unknown dict structure
            return {
                **base_response,
                "valid": False,
                "reason": "Invalid JSON structure - unrecognized format",
                "memory_object": None,
            }

        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            return {
                **base_response,
                "valid": False,
                "reason": f"Failed to parse JSON: {e}",
                "memory_object": None,
            }
        except Exception as e:
            return {
                **base_response,
                "valid": False,
                "reason": f"Unexpected error: {e}",
                "memory_object": None,
            }

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """
        Process the input data to validate and structure the answer.

        Args:
            ctx: Context containing:
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
        # Convert ctx to dict if it's not already
        input_dict = dict(ctx) if isinstance(ctx, dict) else {"input": str(ctx)}

        question = input_dict.get("input", "")

        # Extract clean response text from complex agent outputs
        previous_outputs = input_dict.get("previous_outputs", {})
        context_output = (
            previous_outputs.get("context-collector", {})
            if isinstance(previous_outputs, dict)
            else {}
        )
        if isinstance(context_output, dict) and "result" in context_output:
            result = context_output["result"]
            context = result.get("response", "NONE") if isinstance(result, dict) else str(result)
        else:
            context = str(context_output) if context_output else "NONE"

        answer_output = (
            previous_outputs.get("answer-builder", {}) if isinstance(previous_outputs, dict) else {}
        )
        if isinstance(answer_output, dict) and "result" in answer_output:
            result = answer_output["result"]
            answer = result.get("response", "NONE") if isinstance(result, dict) else str(result)
        else:
            answer = str(answer_output) if answer_output else "NONE"

        store_structure = self.params.get("store_structure")

        # ✅ FIX: Check for pre-rendered prompt from execution engine first
        if isinstance(ctx, dict) and "formatted_prompt" in ctx and ctx["formatted_prompt"]:
            prompt = ctx["formatted_prompt"]
            logger.debug(f"Using pre-rendered prompt from execution engine (length: {len(prompt)})")
        # Check if we have a custom prompt that needs template rendering
        elif (
            hasattr(self.llm_agent, "prompt")
            and self.llm_agent.prompt
            and self.llm_agent.prompt.strip()
        ):
            # Use custom prompt with template rendering
            try:
                template = Template(self.llm_agent.prompt)
                prompt = template.render(**input_dict)
            except Exception:
                # Fallback to original prompt if rendering fails
                prompt = self.llm_agent.prompt
        else:
            # Use default prompt building logic
            prompt = self.build_prompt(str(question), str(context), str(answer), store_structure)

        # Create LLM input with prompt but disable automatic JSON parsing
        # We'll handle JSON parsing manually since we expect a different schema
        llm_input = {"prompt": prompt, "parse_json": False}

        # ✅ FIX: Pass the rendered prompt to the inner LLM agent
        if isinstance(ctx, dict) and "formatted_prompt" in ctx and ctx["formatted_prompt"]:
            llm_input["formatted_prompt"] = ctx["formatted_prompt"]
        else:
            llm_input["formatted_prompt"] = prompt

        # Get response from LLM
        response = await self.llm_agent.run(llm_input)

        # Extract the raw LLM output
        if isinstance(response, dict):
            raw_llm_output = response.get("response", "")
        else:
            raw_llm_output = str(response)  # type: ignore [unreachable]

        # Parse the LLM output - pass the correct formatted prompt
        formatted_prompt_to_use = (
            ctx["formatted_prompt"]
            if (isinstance(ctx, dict) and "formatted_prompt" in ctx and ctx["formatted_prompt"])
            else prompt
        )
        return self._parse_llm_output(
            str(raw_llm_output), str(prompt), str(formatted_prompt_to_use)
        )

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
        # Handle cases where context or answer is "NONE" or empty
        context = "No context available" if context in ["NONE", "", None] else context
        answer = "No answer provided" if answer in ["NONE", "", None] else answer

        # Build the prompt parts
        parts = [
            "Validate the following situation and structure it into a memory format.",
            f"\nQuestion: {question}",
            f"\nContext: {context}",
            f"\nAnswer to validate: {answer}",
        ]

        # Add special instructions for no-information cases
        if answer == "No answer provided" and context == "No context available":
            parts.extend(
                [
                    "\nThis appears to be a case where no information was found for the question. "
                    'Please validate this as a legitimate "no information available" response '
                    "and structure it appropriately.",
                    "\nIMPORTANT: You MUST respond with the exact JSON format specified below. "
                    "Do not use any other format.",
                    "\nFor cases where no information is available, you should:",
                    '1. Mark as valid=true (since "no information available" is a valid response)',
                    "2. Set confidence to 0.1 (low but not zero)",
                    "3. Create a memory object that captures the fact that no information was found",
                ]
            )
        else:
            parts.extend(
                [
                    "\nPlease validate if the answer is correct and contextually coherent. "
                    "Then structure the information into a memory object.",
                    "\nIMPORTANT: You MUST respond with the exact JSON format specified below. "
                    "Do not use any other format.",
                ]
            )

        # Add structure instructions
        parts.append(self._get_structure_instructions(store_structure))

        # Add response format
        parts.extend(
            [
                "\nReturn your response in the following JSON format:",
                "{",
                '    "valid": true/false,',
                '    "reason": "explanation of validation decision",',
                '    "memory_object": {',
                "        // structured memory object if valid, null if invalid",
                "    }",
                "}",
            ]
        )

        # Combine all parts
        return "\n".join(parts)

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
