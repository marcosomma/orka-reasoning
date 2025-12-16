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
LLM Client for Plan Validator
==============================

Minimal HTTP client for making LLM inference calls without dependencies
on other OrKa agent classes. Supports Ollama and OpenAI-compatible APIs.
"""

import asyncio
import logging
from typing import Any, Dict

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    requests = None
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


async def call_llm(
    prompt: str,
    model: str,
    url: str,
    provider: str,
    temperature: float = 0.2,
) -> str:
    """
    Make an async LLM inference call.

    Args:
        prompt: The prompt text to send to the LLM
        model: Model name (e.g., "gpt-oss:20b", "mistral")
        url: LLM API endpoint URL
        provider: Provider type ("ollama" or "openai_compatible")
        temperature: Temperature parameter for generation

    Returns:
        str: Generated response text from the LLM

    Raises:
        RuntimeError: If the LLM call fails
    """
    # Resolve requests at call time so tests can monkeypatch sys.modules
    try:
        import importlib

        requests_mod = importlib.import_module("requests")
    except Exception:
        logger.error("requests library not available")
        raise RuntimeError("requests library required for LLM calls")

    # Validate inputs
    if not isinstance(provider, str) or not provider.strip() or provider.startswith("MISSING_"):
        raise RuntimeError(
            "Missing/invalid LLM provider for PlanValidator call. "
            "Set provider/llm_provider explicitly (e.g. 'ollama' or 'openai_compatible')."
        )
    if not isinstance(url, str) or not url.strip() or url.startswith("MISSING_"):
        raise RuntimeError(
            "Missing/invalid LLM url for PlanValidator call. "
            "Set url/llm_url explicitly (e.g. an Ollama endpoint or an OpenAI-compatible chat completions URL)."
        )
    if not isinstance(model, str) or not model.strip() or model.startswith("MISSING_"):
        raise RuntimeError(
            "Missing/invalid LLM model for PlanValidator call. "
            "Set model/llm_model explicitly."
        )

    provider_norm = provider.lower().strip()
    if provider_norm in {"lm_studio", "lmstudio"}:
        provider_norm = "openai_compatible"

    if provider_norm not in {"ollama", "openai_compatible"}:
        raise RuntimeError(
            f"Unsupported provider '{provider}'. Supported: 'ollama', 'openai_compatible' (incl. lm_studio/lmstudio aliases)."
        )

    # Build request payload based on provider
    if provider_norm == "ollama":
        payload = _build_ollama_payload(prompt, model, temperature)
    else:
        payload = _build_openai_compatible_payload(prompt, model, temperature)

    logger.debug(f"Calling LLM at {url} with model {model}")

    try:
        # Make sync request in thread pool to avoid blocking; resolve post at runtime
        response = await asyncio.to_thread(
            requests_mod.post,
            url,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()
        response_data = response.json()

        # Extract response text based on provider
        if provider_norm == "ollama":
            return _extract_ollama_response(response_data)
        else:
            return _extract_openai_compatible_response(response_data)
    except Exception as e:
        # Normalize requests exceptions and parsing errors
        exc_type = type(e)
        req_exc = getattr(getattr(requests_mod, "exceptions", None), "RequestException", None)
        if req_exc and isinstance(e, req_exc):
            logger.error(f"LLM request failed: {e}")
            raise RuntimeError(f"Failed to call LLM at {url}: {e}") from e
        if isinstance(e, (KeyError, ValueError)):
            logger.error(f"Failed to parse LLM response: {e}")
            raise RuntimeError(f"Invalid LLM response format: {e}") from e
        # Re-raise any other unexpected exceptions
        raise


def _build_ollama_payload(prompt: str, model: str, temperature: float) -> Dict[str, Any]:
    """
    Build request payload for Ollama API.

    Args:
        prompt: Prompt text
        model: Model name
        temperature: Temperature parameter

    Returns:
        Dict: Request payload for Ollama
    """
    return {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "stream": False,
    }


def _build_openai_compatible_payload(prompt: str, model: str, temperature: float) -> Dict[str, Any]:
    """
    Build request payload for OpenAI-compatible APIs.

    Args:
        prompt: Prompt text
        model: Model name
        temperature: Temperature parameter

    Returns:
        Dict: Request payload for OpenAI-compatible API
    """
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": False,
    }


def _extract_ollama_response(response_data: Dict[str, Any]) -> str:
    """
    Extract response text from Ollama API response.

    Args:
        response_data: Parsed JSON response from Ollama

    Returns:
        str: Generated text

    Raises:
        KeyError: If response format is invalid
    """
    return str(response_data["response"])


def _extract_openai_compatible_response(response_data: Dict[str, Any]) -> str:
    """
    Extract response text from OpenAI-compatible API response.

    Args:
        response_data: Parsed JSON response

    Returns:
        str: Generated text

    Raises:
        KeyError: If response format is invalid
    """
    return str(response_data["choices"][0]["message"]["content"])
