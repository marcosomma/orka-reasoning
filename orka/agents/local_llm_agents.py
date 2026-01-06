# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

import time
import aiohttp
import asyncio
import tiktoken
import re
from urllib.parse import urlparse
from jinja2 import Template as JinjaTemplate
from .llm_agents import parse_llm_json_response
from ..utils.structured_output import StructuredOutputConfig
from ..utils.json_parser import parse_llm_json
from .local_cost_calculator import calculate_local_llm_cost

"""
Local LLM Agents Module
======================

This module provides agents for interfacing with locally running large language models.
Supports various local LLM serving solutions including Ollama, LM Studio, LMDeploy,
and other OpenAI-compatible APIs.

Local LLM agents enable:
- Fully offline LLM workflows
- Privacy-preserving AI processing
- Custom model deployment flexibility
- Reduced dependency on cloud services
- Integration with self-hosted models
"""

import json
import logging
from typing import Any, Dict, Optional, Union, cast

from .base_agent import BaseAgent, Context

logger = logging.getLogger(__name__)


def _count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    if not text or not isinstance(text, str):
        return 0

    try:
        # Resolve tiktoken at call time to respect test monkeypatching of sys.modules
        import importlib

        try:
            tiktoken_mod = importlib.import_module("tiktoken")
        except Exception:
            # Fall back to the module-level tiktoken if available
            tiktoken_mod = globals().get("tiktoken")

        # Map common local models to best available tokenizers
        model_mapping = {
            "llama": "cl100k_base",  # GPT-4 tokenizer (similar to LLaMA)
            "llama3": "cl100k_base",  # Llama 3 series
            "llama3.2": "cl100k_base",  # Llama 3.2 series
            "mistral": "cl100k_base",  # Mistral models
            "deepseek": "cl100k_base",  # DeepSeek models
            "qwen": "cl100k_base",  # Qwen models
            "phi": "cl100k_base",  # Phi models
            "gemma": "cl100k_base",  # Gemma models
            "codellama": "cl100k_base",  # Code Llama
            "vicuna": "cl100k_base",  # Vicuna models
            "openchat": "cl100k_base",  # OpenChat models
            "yi": "cl100k_base",  # Yi models
            "solar": "cl100k_base",  # Solar models
        }

        # Try to get encoding for the exact model name first
        try:
            encoding = tiktoken_mod.encoding_for_model(model)
        except (KeyError, ValueError, AttributeError):
            # If exact model not found, try to find a matching encoding by pattern
            encoding_name = "cl100k_base"  # Default to GPT-4 tokenizer (most common)

            # Check if model name contains known patterns (longer patterns first)
            model_lower = model.lower()
            for known_model in sorted(model_mapping.keys(), key=len, reverse=True):
                if known_model in model_lower:
                    encoding_name = model_mapping[known_model]
                    break

            # Obtain encoding via tiktoken module if available
            if hasattr(tiktoken_mod, "get_encoding"):
                encoding = tiktoken_mod.get_encoding(encoding_name)
            else:
                raise ImportError("tiktoken encoding functions not available")

        # Encode the text and return token count
        return len(encoding.encode(text))

    except ImportError:
        # tiktoken not available, use improved character-based estimation
        # More conservative estimation: ~3.5 characters per token for most models
        return max(1, len(text) // 4)  # Ensure at least 1 token for non-empty text
    except Exception:
        # Fallback for any other errors with improved estimation
        return max(1, len(text) // 4)  # Ensure at least 1 token for non-empty text


class LocalLLMAgent(BaseAgent):
    """
    Calls a local LLM endpoint (e.g. Ollama, LM Studio) with a prompt and returns the response.

    This agent mimics the same interface as OpenAI-based agents but uses local model endpoints
    for inference. It supports various local LLM serving solutions like Ollama, LM Studio,
    LMDeploy, and other OpenAI-compatible APIs.

    Supported Providers:
    ------------------
    - ollama: Native Ollama API format
    - lm_studio: LM Studio with OpenAI-compatible endpoint
    - openai_compatible: Any OpenAI-compatible API endpoint

    Configuration Example:
    --------------------

    .. code-block:: yaml

        - id: my_local_agent
          type: local_llm
          prompt: "Summarize this: {{ input }}"
          model: "mistral"
          model_url: "http://localhost:1234"
          provider: "ollama"
          temperature: 0.7
    """

    async def _run_impl(self, ctx: Context) -> Dict[str, Any]:
        """
        Generate an answer using a local LLM endpoint.

        Args:
            ctx (Context): Context containing:
                - If dict: prompt (str), model (str), temperature (float), and other params
                - If str: Direct input text to process

        Returns:
            Dict[str, Any]: Generated answer from the local model with metrics.
        """
        # Handle Context input (dict structure)
        # Extract the actual input text from the dict structure
        # Handle OrKa's orchestrator input format properly
        # Try to get 'input' field first (OrKa standard)
        if "input" in ctx:
            input_text = str(ctx["input"])
        else:
            # Fallback to converting dict to string if no 'input' field
            input_text = str(ctx)

        # Get prompt with proper type handling
        prompt_val = ctx.get("prompt", self.prompt)
        prompt = str(prompt_val) if prompt_val is not None else "Input: {{ input }}"

        # Get model with proper type handling
        model_val = ctx.get("model", self.params.get("model", "llama3.2:latest"))
        model = str(model_val)

        # Get temperature with proper type handling
        temp_val = ctx.get("temperature", self.params.get("temperature", 0.7))
        try:
            temperature = float(str(temp_val)) if temp_val is not None else 0.7
        except (ValueError, TypeError):
            temperature = 0.7

        # Optional max token cap (completion tokens)
        max_tokens_val = ctx.get("max_tokens", self.params.get("max_tokens"))
        max_tokens: Optional[int]
        if max_tokens_val is None or max_tokens_val == "":
            max_tokens = None
        else:
            try:
                max_tokens = int(str(max_tokens_val))
                if max_tokens <= 0:
                    max_tokens = None
            except (ValueError, TypeError):
                max_tokens = None

        # Build the full prompt using template replacement
        # Convert ctx to dict if it's not already
        context_dict: Dict[str, Any] = dict(ctx) if isinstance(ctx, dict) else {"input": str(ctx)}

        # [OK] FIX: Use already-rendered prompt from execution engine if available
        if isinstance(ctx, dict) and "formatted_prompt" in ctx and ctx["formatted_prompt"]:
            render_prompt = ctx["formatted_prompt"]
            logger.debug(
                f"Using pre-rendered prompt from execution engine (length: {len(render_prompt)})"
            )
        else:
            render_prompt = self.build_prompt(input_text, prompt, context_dict)
            logger.debug(f"Using agent's own template rendering (length: {len(render_prompt)})")

        # Structured output configuration (local LLMs typically use prompt mode)
        agent_params = getattr(self, "params", {}) if hasattr(self, "params") else {}
        orchestrator_defaults = (
            ctx.get("structured_output_defaults") if isinstance(ctx, dict) else None
        )
        so_config = StructuredOutputConfig.from_params(
            agent_params=agent_params, agent_type="local_llm", orchestrator_defaults=orchestrator_defaults
        )

        # Enhanced instructions for reasoning models to force JSON output
        self_evaluation = """
            # CRITICAL INSTRUCTIONS - MUST FOLLOW EXACTLY
            
            You MUST respond with ONLY valid JSON in the following exact format:
            ```json
            {
              "response": "<your actual response here>",
              "confidence": "<score from 0.0 to 1.0>",
              "internal_reasoning": "<brief explanation of your reasoning>"
            }
            ```
            
            CONSTRAINS:
            - Minimal confidence 0.9
            - Exclusively base on evidence and data.
            
            IMPORTANT RULES:
            1. Minimal confidence 0.9
            2. ALWAYS wrap your JSON in triple backticks with 'json' language identifier
            3. Use proper JSON syntax with double quotes around all strings
            4. If you need to think through the problem, put ALL reasoning in the "internal_reasoning" field
            5. Do NOT include any text outside the JSON code block
            6. Do NOT use <think> tags - put reasoning in "internal_reasoning"
            7. Ensure valid JSON syntax (proper commas, quotes, brackets)
            
            Example format:
            ```json
            {
              "response": "Your main answer goes here",
              "confidence": "0.9",
              "internal_reasoning": "I approached this by analyzing X and concluded Y because Z"
            }
            ```
        """
        # Build final prompt
        if so_config.enabled:
            mode = so_config.resolve_mode(provider=str(self.params.get("provider", "ollama")), model=model)
            if mode != "prompt":
                logger.warning(
                    f"Structured output mode '{mode}' not supported by local provider; falling back to prompt instructions."
                )
            instructions = so_config.build_prompt_instructions()
            full_prompt = f"{render_prompt}\n\n{instructions if instructions else ''}".strip()
        else:
            full_prompt = f"{render_prompt}\n\n{self_evaluation}"

        # Get model endpoint configuration
        model_url = self.params.get("model_url", "MISSING_MODEL_URL")
        provider = self.params.get("provider", "MISSING_PROVIDER")

        try:
            # Fail-fast validation: ensure workflow explicitly configures provider + model_url
            missing_fields = []
            if not isinstance(provider, str) or not provider.strip() or provider.startswith("MISSING_"):
                missing_fields.append("provider")
            if not isinstance(model_url, str) or not model_url.strip() or model_url.startswith("MISSING_"):
                missing_fields.append("model_url")
            if missing_fields:
                raise ValueError(
                    f"LocalLLMAgent '{self.agent_id}' missing required LLM config: {', '.join(missing_fields)}. "
                    "Provide them in the workflow under this agent. Example: "
                    "type: local_llm, params: { provider: <ollama|lm_studio|openai_compatible>, model_url: <http(s)://host:port/...>, model: <model_name> }"
                )

            # Validate URL shape early to avoid requests' generic "Invalid URL" message
            # urlparse import moved to top

            parsed_url = urlparse(model_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(
                    f"LocalLLMAgent '{self.agent_id}' has invalid model_url='{model_url}'. "
                    "Expected a full URL including scheme, e.g. 'http://localhost:1234/...'."
                )

            # Track timing for local LLM calls
            # time import moved to top

            start_time = time.time()

            # Get raw response from the LLM
            provider_norm = provider.lower().strip()

            if provider_norm == "ollama":
                raw_response = await self._call_ollama(
                    model_url,
                    model,
                    full_prompt,
                    temperature,
                    max_tokens=max_tokens,
                )
            elif provider_norm in ["lm_studio", "lmstudio"]:
                raw_response = await self._call_lm_studio(
                    model_url,
                    model,
                    full_prompt,
                    temperature,
                    max_tokens=max_tokens,
                )
            elif provider_norm == "openai_compatible":
                raw_response = await self._call_openai_compatible(
                    model_url,
                    model,
                    full_prompt,
                    temperature,
                    max_tokens=max_tokens,
                )
            else:
                raise ValueError(
                    f"LocalLLMAgent '{self.agent_id}' has unsupported provider='{provider}'. "
                    "Supported: ollama, lm_studio (lmstudio), openai_compatible."
                )

            # Calculate latency
            latency_ms = round((time.time() - start_time) * 1000, 2)

            # Count tokens for local LLMs using client-side tokenizer
            prompt_tokens = _count_tokens(full_prompt, model)
            completion_tokens = _count_tokens(raw_response, model) if raw_response else 0
            total_tokens = prompt_tokens + completion_tokens

            # Import the JSON parser
            # parse_llm_json_response import moved to top

            # Parse the response
            if so_config.enabled:
                parsed_response = parse_llm_json(
                    raw_response or "",
                    schema=so_config.build_json_schema(),
                    strict=False,
                    coerce_types=so_config.coerce_types,
                    track_errors=True,
                    agent_id=self.agent_id,
                )
            else:
                # Legacy parser with reasoning and robust extraction
                parsed_response = parse_llm_json_response(raw_response)

            # Ensure we always return a valid dict
            if not parsed_response or not isinstance(parsed_response, dict):
                parsed_response = {
                    "response": str(raw_response) if raw_response else "[No response]",
                    "confidence": "0.0",
                    "internal_reasoning": "Failed to parse LLM response, returning raw text",
                }

            # Calculate real local LLM cost (electricity + hardware amortization)
            try:
                # Resolve cost calculator at call time so tests can monkeypatch it
                import importlib

                try:
                    cost_mod = importlib.import_module("orka.agents.local_cost_calculator")
                    cost_func = getattr(cost_mod, "calculate_local_llm_cost")
                except Exception:
                    # Fallback to module-level binding if dynamic import fails
                    cost_func = globals().get("calculate_local_llm_cost")

                cost_usd = cost_func(latency_ms, total_tokens, model, provider)
            except Exception as cost_error:
                # If cost calculation fails, log warning and use None to indicate unknown
                logger.warning(f"Failed to calculate local LLM cost: {cost_error}")
                cost_usd = None

            # Add local LLM metrics with real cost calculation and formatted_prompt
            parsed_response["_metrics"] = {
                "tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,  # Real cost including electricity + hardware amortization
                "model": model,
                "provider": provider,
            }

            # [OK] FIX: Store the actual rendered template, not the full_prompt with evaluation instructions
            # If we used pre-rendered template, store it; otherwise store the original prompt
            if isinstance(ctx, dict) and "formatted_prompt" in ctx and ctx["formatted_prompt"]:
                # We used pre-rendered template, so it's already fully rendered
                parsed_response["formatted_prompt"] = ctx["formatted_prompt"]
            else:
                # We used our own rendering, store the original template for consistency
                parsed_response["formatted_prompt"] = prompt

            return parsed_response

        except Exception as e:
            # Count tokens even in error case if we have the prompt
            try:
                error_prompt_tokens = (
                    _count_tokens(full_prompt, model) if "full_prompt" in locals() else 0
                )
            except Exception:
                error_prompt_tokens = 0

            # Calculate cost even for error case (we consumed some resources)
            try:
                # Resolve cost calculator at call time so tests can monkeypatch it
                import importlib

                try:
                    cost_mod = importlib.import_module("orka.agents.local_cost_calculator")
                    cost_func = getattr(cost_mod, "calculate_local_llm_cost")
                except Exception:
                    cost_func = globals().get("calculate_local_llm_cost")

                # Estimate minimal cost for failed request (some GPU cycles were used)
                error_cost = cost_func(
                    100,
                    error_prompt_tokens,
                    self.params.get("model", "unknown"),
                    self.params.get("provider", "unknown"),
                )
            except Exception:
                error_cost = None

            return {
                "response": f"[LocalLLMAgent error: {e!s}]",
                "confidence": "0.0",
                "internal_reasoning": f"Error occurred during LLM call: {e!s}",
                "_metrics": {
                    "tokens": error_prompt_tokens,
                    "prompt_tokens": error_prompt_tokens,
                    "completion_tokens": 0,
                    "latency_ms": 0,
                    "cost_usd": error_cost,  # Real cost even for errors
                    "model": self.params.get("model", "unknown"),
                    "provider": self.params.get("provider", "unknown"),
                    "error": True,
                },
                "formatted_prompt": (
                    # Use same logic as success case for consistency
                    ctx["formatted_prompt"]
                    if (
                        isinstance(ctx, dict)
                        and "formatted_prompt" in ctx
                        and ctx["formatted_prompt"]
                    )
                    else prompt if "prompt" in locals() else "Error: prompt not available"
                ),
            }

    def build_prompt(
        self,
        input_text: str,
        template: Optional[str] = None,
        full_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt from template and input data.

        Args:
            input_text (str): The main input text to substitute
            template (str, optional): Template string, defaults to self.prompt
            full_context (dict, optional): Full context dict for complex template variables

        Returns:
            str: The built prompt
        """
        if template is None:
            template = self.prompt or "Input: {{ input }}"

        # Simple template replacement first - replace {{ input }} with input_text
        rendered = template.replace("{{ input }}", str(input_text))

        # If we have full context (dict with previous_outputs), try to handle more complex templates
        if full_context and isinstance(full_context, dict):
            try:
                # Try to use Jinja2 for more advanced templating like the orchestrator does
                # JinjaTemplate import moved to top

                jinja_template = JinjaTemplate(template)

                # Create comprehensive context with input and previous_outputs
                context = {
                    "input": input_text,
                    "previous_outputs": full_context.get("previous_outputs", {}),
                }

                # If full_context has direct access to outputs, use them too
                if hasattr(full_context, "get"):
                    # Add any direct output keys from the orchestrator context
                    for key, value in full_context.items():
                        if key not in context:  # Don't override existing keys
                            context[key] = value

                rendered = jinja_template.render(context)

            except Exception:
                # If Jinja2 fails, fall back to simple replacement
                # But try to handle common template patterns manually
                if "previous_outputs" in template:
                    # Try to extract previous_outputs from full_context
                    prev_outputs = full_context.get("previous_outputs", {})
                    if prev_outputs:
                        # Handle common patterns like {{ previous_outputs.agent_name }}
                        # re import moved to top

                        for match in re.finditer(
                            r"\{\{\s*(previous_outputs)\.(\w+)\s*\}\}",
                            template,
                        ):
                            full_match = match.group(0)
                            agent_key = match.group(2)
                            if agent_key in prev_outputs:
                                # Replace with the actual output
                                replacement = str(prev_outputs[agent_key])
                                rendered = rendered.replace(full_match, replacement)

        return rendered

    async def _call_ollama(
        self,
        model_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call Ollama API endpoint (async, aiohttp).

        Returns:
            str: The model's response text
        """
        # aiohttp, asyncio import moved to top

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(model_url, json=payload) as response:
                try:
                    response.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    body = (await response.text() or "").strip()
                    if len(body) > 1200:
                        body = body[:1200] + "..."
                    raise RuntimeError(
                        f"Ollama HTTP {response.status} for url {response.url}: {body}"
                    ) from e
                result = await response.json()
                return str(result.get("response", "")).strip()

    async def _call_lm_studio(
        self,
        model_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call LM Studio API endpoint (OpenAI-compatible, async, aiohttp).

        Returns:
            str: The model's response text
        """
        # aiohttp, asyncio import moved to top

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if not model_url.endswith("/chat/completions"):
            if model_url.endswith("/"):
                model_url = model_url + "v1/chat/completions"
            else:
                model_url = model_url + "/v1/chat/completions"

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(model_url, json=payload) as response:
                try:
                    if response.status >= 400:
                        body = (await response.text() or "").strip()
                        if len(body) > 1200:
                            body = body[:1200] + "..."
                        raise RuntimeError(
                            f"LM Studio HTTP {response.status} for url {response.url}: {body}"
                        )
                except aiohttp.ClientResponseError as e:
                    raise RuntimeError(
                        f"LM Studio HTTP {response.status} for url {response.url}: {await response.text()}"
                    ) from e
                result = await response.json()
                return str(result["choices"][0]["message"]["content"]).strip()

    async def _call_openai_compatible(
        self,
        model_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call any OpenAI-compatible API endpoint (async, aiohttp).

        Returns:
            str: The model's response text
        """
        # aiohttp, asyncio import moved to top

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(model_url, json=payload) as response:
                try:
                    if response.status >= 400:
                        body = (await response.text() or "").strip()
                        if len(body) > 1200:
                            body = body[:1200] + "..."
                        raise RuntimeError(
                            f"OpenAI-compatible HTTP {response.status} for url {response.url}: {body}"
                        )
                except aiohttp.ClientResponseError as e:
                    raise RuntimeError(
                        f"OpenAI-compatible HTTP {response.status} for url {response.url}: {await response.text()}"
                    ) from e
                result = await response.json()
                return str(result["choices"][0]["message"]["content"]).strip()
