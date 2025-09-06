# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
🤖 **LLM Agents** - Cloud-Powered Intelligent Processing
======================================================

This module contains specialized agents that leverage cloud LLMs (OpenAI GPT models)
for sophisticated natural language understanding and generation tasks.

**Core LLM Agent Types:**

🎨 **OpenAIAnswerBuilder**: The master craftsman of responses
- Synthesizes multiple data sources into coherent answers
- Perfect for final response generation in complex workflows
- Handles context-aware formatting and detailed explanations

🎯 **OpenAIClassificationAgent**: The intelligent router
- Classifies inputs into predefined categories with high precision
- Essential for workflow branching and content routing
- Supports complex multi-class classification scenarios

✅ **OpenAIBinaryAgent**: The precise decision maker
- Makes accurate true/false determinations
- Ideal for validation, filtering, and gate-keeping logic
- Optimized for clear yes/no decision points

**Advanced Features:**
- 🧠 **Reasoning Extraction**: Captures internal reasoning from <think> blocks
- 📊 **Cost Tracking**: Automatic token usage and cost calculation
- 🔧 **JSON Parsing**: Robust handling of structured LLM responses
- ⚡ **Error Recovery**: Graceful degradation for malformed responses
- 🎛️ **Flexible Prompting**: Jinja2 template support for dynamic prompts

**Real-world Applications:**
- Customer service with intelligent intent classification
- Content moderation with nuanced decision making
- Research synthesis combining multiple information sources
- Multi-step reasoning workflows with transparent logic
"""

import logging
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Initialize logging first
from orka.utils.logging_utils import setup_logging

setup_logging()

logger = logging.getLogger(__name__)

from .base_agent import LegacyBaseAgent as BaseAgent

# Load environment variables
load_dotenv()

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("BASE_OPENAI_MODEL", "gpt-3.5-turbo")

# Check if we're running in test mode
PYTEST_RUNNING = os.getenv("PYTEST_RUNNING", "").lower() in ("true", "1", "yes")

# Initialize OpenAI client with optional API key
client = None
if OPENAI_API_KEY:
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
elif PYTEST_RUNNING:
    client = AsyncOpenAI(api_key="dummy_key_for_testing")
else:
    logger.info(
        "[WARNING] - OPENAI_API_KEY environment variable is not set. OpenAI-based agents will not be available. Use local LLM agents instead. Or add OPENAI_API_KEY to a .env in the current path."
    )


def _extract_reasoning(text: str) -> tuple[str, str]:
    """Extract reasoning content from <think> blocks."""
    if "<think>" not in text or "</think>" not in text:
        return "", text

    think_pattern = r"<think>(.*?)</think>"
    think_match = re.search(think_pattern, text, re.DOTALL)
    if not think_match:
        return "", text

    reasoning = think_match.group(1).strip()
    cleaned_text = re.sub(think_pattern, "", text, flags=re.DOTALL).strip()
    return reasoning, cleaned_text


def _extract_json_content(text: str) -> str:
    """Extract JSON content from various formats (code blocks, braces, etc.)."""
    # Try markdown code blocks first
    code_patterns = [r"```(?:json|markdown)?\s*(.*?)```", r"```\s*(.*?)```"]

    for pattern in code_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            match = match.strip()
            if match and match.startswith(("{", "[")):
                return str(match)  # Ensure str return type

    # Try to find JSON-like braces
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    return str(brace_match.group(0)) if brace_match else text


def _parse_json_safely(json_content: str) -> dict[str, Any] | None:
    """Safely parse JSON with fallback for malformed content."""
    import json

    try:
        result = json.loads(json_content)
        if isinstance(result, dict):
            return result
        return None
    except json.JSONDecodeError:
        try:
            fixed_json = _fix_malformed_json(json_content)
            result = json.loads(fixed_json)
            if isinstance(result, dict):
                return result
            return None
        except Exception:
            return None


def _build_response_dict(parsed_json: dict[str, Any] | None, fallback_text: str) -> dict[str, Any]:
    """Build standardized response dictionary from parsed JSON or fallback text."""
    if not parsed_json or not isinstance(parsed_json, dict):
        return {
            "response": fallback_text,
            "confidence": "0.3",
            "internal_reasoning": "Could not parse as JSON, using raw response",
        }

    # Handle perfect structure
    if all(key in parsed_json for key in ["response", "confidence", "internal_reasoning"]):
        return {
            "response": str(parsed_json["response"]),
            "confidence": str(parsed_json["confidence"]),
            "internal_reasoning": str(parsed_json["internal_reasoning"]),
        }

    # Handle task_description structure
    if "task_description" in parsed_json:
        task_desc = parsed_json["task_description"]
        if isinstance(task_desc, dict):
            return {
                "response": str(task_desc.get("response", "")),
                "confidence": str(task_desc.get("confidence", "0.0")),
                "internal_reasoning": str(task_desc.get("internal_reasoning", "")),
            }
        return {
            "response": str(task_desc),
            "confidence": "0.5",
            "internal_reasoning": "Extracted from task_description field",
        }

    # Extract any meaningful content
    return {
        "response": str(
            parsed_json.get(
                "response",
                parsed_json.get("answer", parsed_json.get("result", str(parsed_json))),
            ),
        ),
        "confidence": str(parsed_json.get("confidence", parsed_json.get("score", "0.5"))),
        "internal_reasoning": str(
            parsed_json.get(
                "internal_reasoning",
                parsed_json.get("reasoning", "Parsed from JSON response"),
            ),
        ),
    }


def parse_llm_json_response(
    response_text: str,
    error_tracker: Any = None,
    agent_id: str = "unknown",
) -> dict[str, Any]:
    """
    Parse JSON response from LLM that may contain reasoning (<think> blocks) or be in various formats.

    This parser is specifically designed for local LLMs and reasoning models.
    It handles reasoning blocks, JSON in code blocks, and malformed JSON.

    Args:
        response_text (str): Raw response from LLM
        error_tracker: Optional error tracking object for silent degradations
        agent_id (str): Agent ID for error tracking

    Returns:
        dict: Parsed response with 'response', 'confidence', 'internal_reasoning' keys
    """
    try:
        if not response_text or not isinstance(response_text, str):
            return {
                "response": str(response_text) if response_text else "",
                "confidence": "0.0",
                "internal_reasoning": "Empty or invalid response",
            }

        cleaned_text = response_text.strip()

        # Extract reasoning and clean text
        reasoning_content, cleaned_text = _extract_reasoning(cleaned_text)

        # Extract JSON content
        json_content = _extract_json_content(cleaned_text)

        # Parse JSON safely
        parsed_json = _parse_json_safely(json_content)

        # Track silent degradation if JSON parsing failed
        if not parsed_json and error_tracker:
            error_tracker.record_silent_degradation(
                agent_id,
                "json_parsing_failure",
                f"Failed to parse JSON, falling back to raw text: {json_content[:100]}...",
            )

        # Build response dictionary
        result = _build_response_dict(parsed_json, cleaned_text)

        # Add reasoning if extracted from <think> blocks
        if reasoning_content:
            if not result.get("internal_reasoning"):
                result["internal_reasoning"] = f"Reasoning: {reasoning_content[:200]}..."
            else:
                current = result["internal_reasoning"]
                result["internal_reasoning"] = (
                    f"{current} | Reasoning: {reasoning_content[:200]}..."
                )

        return result

    except Exception as e:
        # Track silent degradation for parsing errors
        if error_tracker:
            error_tracker.record_silent_degradation(
                agent_id,
                "parser_exception",
                f"Parser exception: {e!s}",
            )

        return {
            "response": str(response_text).strip() if response_text else "[Parse error]",
            "confidence": "0.0",
            "internal_reasoning": f"Parser error: {e!s}",
        }


def _fix_malformed_json(json_str: str) -> str:
    """
    Attempt to fix common JSON formatting issues.

    Args:
        json_str (str): Potentially malformed JSON string

    Returns:
        str: Fixed JSON string
    """

    # Remove comments and extra whitespace
    json_str = re.sub(r"//.*?\n", "\n", json_str)
    json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

    # Fix missing commas between fields
    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
    json_str = re.sub(r'}\s*\n\s*"', '},\n"', json_str)

    # Fix missing quotes around keys
    json_str = re.sub(r"(\w+):", r'"\1":', json_str)

    # Fix trailing commas
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    return json_str


def _calculate_openai_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate approximate cost for OpenAI API usage.

    Args:
        model: OpenAI model name
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    # Pricing as of January 2025 (per 1K tokens)
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.0025, "output": 0.01},  # Updated 2025 pricing
        "gpt-4o-2024-08-06": {"input": 0.0025, "output": 0.01},
        "gpt-4o-2024-11-20": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},  # Updated 2025 pricing
        "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.002},
        "o1": {"input": 0.015, "output": 0.06},
        "o1-preview": {"input": 0.015, "output": 0.06},
        "o1-mini": {"input": 0.003, "output": 0.012},
        "o3": {"input": 0.001, "output": 0.004},  # New 2025 model
        "o3-mini": {"input": 0.0011, "output": 0.0044},
        "o4-mini": {"input": 0.0011, "output": 0.0044},
        "gpt-4.1": {"input": 0.002, "output": 0.008},  # New 2025 model
        "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
        "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004},
    }

    # Default pricing for unknown models
    default_pricing = {"input": 0.01, "output": 0.03}

    # Get pricing for the model (with fallbacks for model variants)
    # Sort by length descending to match most specific model first
    model_pricing = None
    for known_model in sorted(pricing.keys(), key=len, reverse=True):
        if model.startswith(known_model):
            model_pricing = pricing[known_model]
            break

    if not model_pricing:
        model_pricing = default_pricing

    # Calculate cost
    input_cost = (prompt_tokens / 1000) * model_pricing["input"]
    output_cost = (completion_tokens / 1000) * model_pricing["output"]
    total_cost = round(input_cost + output_cost, 6)

    return total_cost


def _simple_json_parse(response_text: str) -> dict[str, Any]:
    """
    Simple JSON parser for OpenAI models (no reasoning support).

    Args:
        response_text (str): Raw response from OpenAI

    Returns:
        dict: Parsed JSON with 'response', 'confidence', 'internal_reasoning' keys
    """
    if not response_text or not isinstance(response_text, str):
        return {
            "response": str(response_text) if response_text else "",
            "confidence": "0.0",
            "internal_reasoning": "Empty or invalid response",
        }

    # Try to extract JSON from code blocks first
    import json

    # Look for ```json blocks
    if json_match := re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL):
        json_text = json_match.group(1)
    elif json_match := re.search(r'\{[^{}]*"response"[^{}]*\}', response_text, re.DOTALL):
        json_text = json_match.group(0)
    else:
        # Fallback: treat entire response as answer
        return {
            "response": response_text.strip(),
            "confidence": "0.5",
            "internal_reasoning": "Could not parse JSON, using raw response",
        }

    try:
        parsed = json.loads(json_text)
        if isinstance(parsed, dict) and "response" in parsed:
            return {
                "response": str(parsed.get("response", "")),
                "confidence": str(parsed.get("confidence", "0.5")),
                "internal_reasoning": str(parsed.get("internal_reasoning", "")),
            }
        return {
            "response": response_text.strip(),
            "confidence": "0.5",
            "internal_reasoning": "JSON parsing failed, using raw response",
        }
    except json.JSONDecodeError:
        pass

    # Final fallback
    return {
        "response": response_text.strip(),
        "confidence": "0.5",
        "internal_reasoning": "JSON parsing failed, using raw response",
    }


class OpenAIAnswerBuilder(BaseAgent):
    """
    🎨 **The master craftsman of responses** - builds comprehensive answers from complex inputs.

    **What makes it special:**
    - **Multi-source Synthesis**: Combines search results, context, and knowledge seamlessly
    - **Context Awareness**: Understands conversation history and user intent
    - **Structured Output**: Generates well-formatted, coherent responses
    - **Template Power**: Uses Jinja2 for dynamic prompt construction
    - **Cost Optimization**: Tracks token usage and provides cost insights

    **Perfect for:**
    - Final answer generation in research workflows
    - Customer service response crafting
    - Content creation with multiple input sources
    - Detailed explanations combining technical and user-friendly language

    **Example Use Cases:**

    .. code-block:: yaml

        # Comprehensive Q&A system
        - id: answer_builder
          type: openai-answer
          prompt: |
            Create a comprehensive answer using:
            - Search results: {{ previous_outputs.web_search }}
            - User context: {{ previous_outputs.user_profile }}
            - Classification: {{ previous_outputs.intent_classifier }}

            Provide a helpful, accurate response that addresses the user's specific needs.

    **Advanced Features:**
    - Automatic reasoning extraction from <think> blocks
    - Confidence scoring for answer quality assessment
    - JSON response parsing with fallback handling
    - Template variable resolution with rich context
    """

    async def run(self, input_data: Any) -> dict[str, Any]:
        # Extract parameters from input_data
        original_prompt = input_data.get("prompt", self.prompt)
        model = input_data.get("model", OPENAI_MODEL)
        temperature = float(input_data.get("temperature", 0.7))
        parse_json = input_data.get("parse_json", True)
        error_tracker = input_data.get("error_tracker")
        agent_id = input_data.get(
            "agent_id",
            self.agent_id if hasattr(self, "agent_id") else "unknown",
        )

        # ✅ FIX: Use already-rendered prompt from execution engine if available
        if (
            isinstance(input_data, dict)
            and "formatted_prompt" in input_data
            and input_data["formatted_prompt"]
        ):
            render_prompt = input_data["formatted_prompt"]
            logger.debug(
                f"Using pre-rendered prompt from execution engine (length: {len(render_prompt)})"
            )
        else:
            render_prompt = original_prompt
            logger.debug(f"Using original prompt template (length: {len(render_prompt)})")

        self_evaluation = """
            # CONSTRAINS
            - Minimal confidence 0.9
            - Exclusively base on evidence and data.
            - Always follow this JSON schema to return:
                ```json
                    { 
                      "response": "<task response>",
                      "confidence": "<score from 0 to 1 about task performed>",
                      "internal_reasoning": "<a short sentence explaining internal reasoning tha generate the response>"
                    }
                ```
        """
        full_prompt = f"{render_prompt}\n\n{input_data}\n\n{self_evaluation}"

        # Make API call to OpenAI
        import time

        start_time = time.time()
        status_code = 200  # Default success

        try:
            if client is None:
                raise RuntimeError(
                    "OpenAI client is not available. Please set OPENAI_API_KEY environment variable or use local LLM agents."
                )

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature,
            )

            # Extract usage and cost metrics
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            # Calculate cost (rough estimates for GPT models)
            cost_usd = _calculate_openai_cost(model, prompt_tokens, completion_tokens)

            # Extract and clean the response
            answer = response.choices[0].message.content
            if answer is not None:
                answer = answer.strip()
            else:
                answer = ""

            # Calculate latency
            latency_ms = round((time.time() - start_time) * 1000, 2)

            # Create metrics object
            metrics = {
                "tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "model": model,
                "status_code": status_code,
            }

            # Parse JSON if requested (simple parsing for OpenAI models)
            if parse_json:
                # Simple JSON extraction for OpenAI models (not reasoning models)
                parsed_response = _simple_json_parse(answer)

                # Track silent degradation if JSON parsing failed and fell back to raw text
                if (
                    error_tracker
                    and parsed_response.get("internal_reasoning")
                    == "JSON parsing failed, using raw response"
                ):
                    error_tracker.record_silent_degradation(
                        agent_id,
                        "openai_json_parsing_fallback",
                        f"OpenAI response was not valid JSON, using raw text: {answer[:100]}...",
                    )
            else:
                # When JSON parsing is disabled, return raw response in expected format
                parsed_response = {
                    "response": answer,
                    "confidence": "0.5",
                    "internal_reasoning": "Raw response without JSON parsing",
                }

            # Add metrics and formatted_prompt to parsed response
            parsed_response["_metrics"] = metrics

            # ✅ FIX: Store the actual rendered template, not the original template
            if (
                isinstance(input_data, dict)
                and "formatted_prompt" in input_data
                and input_data["formatted_prompt"]
            ):
                # We used pre-rendered template, so it's already fully rendered
                parsed_response["formatted_prompt"] = input_data["formatted_prompt"]
            else:
                # We used original template, store it for consistency
                parsed_response["formatted_prompt"] = original_prompt

            return parsed_response

        except Exception as e:
            # Track API errors and status codes
            if error_tracker:
                # Extract status code if it's an HTTP error
                status_code = getattr(e, "status_code", getattr(e, "code", 500))
                error_tracker.record_error(
                    "openai_api_error",
                    agent_id,
                    f"OpenAI API call failed: {e}",
                    e,
                    status_code=status_code,
                )

            # Return error response before raising
            error_response = {
                "response": f"Error: {str(e)}",
                "confidence": "0.0",
                "internal_reasoning": "API call failed",
                "_metrics": {
                    "tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency_ms": 0,
                    "cost_usd": 0,
                    "model": model,
                    "status_code": status_code,
                },
                "formatted_prompt": (
                    # Use same logic as success case for consistency
                    input_data["formatted_prompt"]
                    if (
                        isinstance(input_data, dict)
                        and "formatted_prompt" in input_data
                        and input_data["formatted_prompt"]
                    )
                    else (
                        original_prompt
                        if "original_prompt" in locals()
                        else "Error: prompt not available"
                    )
                ),
            }
            raise type(e)(str(e)) from e  # Re-raise with the same type and message


class OpenAIBinaryAgent(OpenAIAnswerBuilder):
    """
    ✅ **The precise decision maker** - makes accurate true/false determinations.

    **Decision-making excellence:**
    - **High Precision**: Optimized for clear binary classifications
    - **Context Sensitive**: Considers full context for nuanced decisions
    - **Confidence Scoring**: Provides certainty metrics for decisions
    - **Fast Processing**: Streamlined for quick yes/no determinations

    **Essential for:**
    - Content moderation (toxic/safe, appropriate/inappropriate)
    - Workflow gating (proceed/stop, valid/invalid)
    - Quality assurance (pass/fail, correct/incorrect)
    - User intent validation (question/statement, urgent/routine)

    **Real-world scenarios:**

    .. code-block:: yaml

        # Content safety check
        - id: safety_check
          type: openai-binary
          prompt: "Is this content safe for all audiences? {{ input }}"

        # Search requirement detection
        - id: needs_search
          type: openai-binary
          prompt: "Does this question require current information? {{ input }}"

        # Priority classification
        - id: is_urgent
          type: openai-binary
          prompt: "Is this request urgent based on content and context? {{ input }}"

    **Decision Quality:**
    - Leverages full GPT reasoning capabilities
    - Provides transparent decision rationale
    - Handles edge cases and ambiguous inputs gracefully
    """

    async def run(self, input_data: Any) -> dict[str, Any]:
        # Override the parent method to add constraints to the prompt
        # Ask the model to only return a "true" or "false" value.
        constraints = "**CONSTRAINTS** ONLY and STRICTLY Return boolean 'true' or 'false' value."

        # Get the original prompt and add constraints
        original_prompt = input_data.get("prompt", self.prompt)
        enhanced_prompt = f"{original_prompt}\n\n{constraints}"

        # Create new input_data with enhanced prompt
        enhanced_input = input_data.copy()
        enhanced_input["prompt"] = enhanced_prompt

        # Store the agent-enhanced prompt with template variables resolved
        # We need to render the enhanced prompt with the input data to show the actual prompt sent
        try:
            from jinja2 import Template

            template = Template(enhanced_prompt)
            rendered_enhanced_prompt = template.render(input=input_data.get("input", ""))
            self._last_formatted_prompt = rendered_enhanced_prompt
        except Exception:
            # Fallback: simple replacement if Jinja2 fails
            self._last_formatted_prompt = enhanced_prompt.replace(
                "{{ input }}",
                str(input_data.get("input", "")),
            )

        # Get the answer using the enhanced prompt
        response_data = await super().run(enhanced_input)

        # Extract answer and preserve metrics and LLM response details
        if isinstance(response_data, dict):
            answer = response_data.get("response", "")
            # Preserve metrics and LLM response details for bubbling up
            self._last_metrics = response_data.get("_metrics", {})
            self._last_response = response_data.get("response", "")
            self._last_confidence = response_data.get("confidence", "0.0")
            self._last_internal_reasoning = response_data.get("internal_reasoning", "")
        else:
            answer = str(response_data)  # type: ignore [unreachable]
            self._last_metrics = {}
            self._last_response = answer
            self._last_confidence = "0.0"
            self._last_internal_reasoning = "Non-JSON response from LLM"

        # Convert to binary decision
        is_true = False
        positive_indicators = ["yes", "true", "correct", "right", "affirmative"]
        for indicator in positive_indicators:
            if indicator in answer.lower():
                is_true = True
                break

        # Return a dictionary matching the supertype's return
        return {
            "response": is_true,
            "confidence": self._last_confidence,
            "internal_reasoning": self._last_internal_reasoning,
            "_metrics": self._last_metrics,
            "formatted_prompt": response_data.get(
                "formatted_prompt", ""
            ),  # ✅ FIX: Preserve formatted_prompt
        }


class OpenAIClassificationAgent(OpenAIAnswerBuilder):
    """
    🎯 **The intelligent router** - classifies inputs into predefined categories with precision.

    **Classification superpowers:**
    - **Multi-class Intelligence**: Handles complex category systems with ease
    - **Context Awareness**: Uses conversation history for better classification
    - **Confidence Metrics**: Provides certainty scores for each classification
    - **Dynamic Categories**: Supports runtime category adjustment
    - **Fallback Handling**: Graceful degradation for unknown categories

    **Essential for:**
    - Intent detection in conversational AI
    - Content categorization and routing
    - Topic classification for knowledge systems
    - Sentiment and emotion analysis
    - Domain-specific classification tasks

    **Classification patterns:**

    .. code-block:: yaml

        # Customer service routing
        - id: intent_classifier
          type: openai-classification
          options: [question, complaint, compliment, request, technical_issue]
          prompt: "Classify customer intent: {{ input }}"

        # Content categorization
        - id: topic_classifier
          type: openai-classification
          options: [technology, science, business, entertainment, sports]
          prompt: "What topic does this article discuss? {{ input }}"

        # Urgency assessment
        - id: priority_classifier
          type: openai-classification
      options: [low, medium, high, critical]
      prompt: "Assess priority level based on content and context: {{ input }}"
    ```

    **Advanced capabilities:**
    - Hierarchical classification support
    - Multi-label classification for complex content
    - Confidence thresholding for quality control
    - Custom category definitions with examples
    """

    async def run(self, input_data: Any) -> dict[str, Any]:
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

        # Store the agent-enhanced prompt with template variables resolved
        # We need to render the enhanced prompt with the input data to show the actual prompt sent
        try:
            from jinja2 import Template

            template = Template(enhanced_prompt)
            rendered_enhanced_prompt = template.render(input=input_data.get("input", ""))
            self._last_formatted_prompt = rendered_enhanced_prompt
        except Exception:
            # Fallback: simple replacement if Jinja2 fails
            self._last_formatted_prompt = enhanced_prompt.replace(
                "{{ input }}",
                str(input_data.get("input", "")),
            )

        # Use parent class to make the API call
        response_data = await super().run(enhanced_input)

        # Extract answer and preserve metrics and LLM response details
        if isinstance(response_data, dict):
            answer = response_data.get("response", "")
            # Preserve metrics and LLM response details for bubbling up
            self._last_metrics = response_data.get("_metrics", {})
            self._last_response = response_data.get("response", "")
            self._last_confidence = response_data.get("confidence", "0.0")
            self._last_internal_reasoning = response_data.get("internal_reasoning", "")
        else:
            answer = str(response_data)  # type: ignore [unreachable]
            self._last_metrics = {}
            self._last_response = answer
            self._last_confidence = "0.0"
            self._last_internal_reasoning = "Non-JSON response from LLM"

        # Return a dictionary matching the supertype's return
        return {
            "response": answer,
            "confidence": self._last_confidence,
            "internal_reasoning": self._last_internal_reasoning,
            "_metrics": self._last_metrics,
            "formatted_prompt": response_data.get(
                "formatted_prompt", ""
            ),  # ✅ FIX: Preserve formatted_prompt
        }
