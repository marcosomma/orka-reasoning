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

"""
LLM Provider Integration
========================

Async methods for calling LLM providers (Ollama, LM Studio).
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from ...utils.json_parser import extract_json_from_text, repair_malformed_json

logger = logging.getLogger(__name__)


class LLMProviderMixin:
    """Mixin providing LLM provider integration for path evaluation."""

    async def _call_ollama_async(
        self, model_url: str, model: str, prompt: str, temperature: float
    ) -> str:
        """Call Ollama API endpoint asynchronously."""
        try:
            logger.debug(
                f"Calling Ollama: model={model}, url={model_url}, prompt_length={len(prompt)}"
            )

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(model_url, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return str(result.get("response", "")).strip()

        except asyncio.TimeoutError as e:
            logger.error(f"Ollama API call timeout after 30s: model={model}, url={model_url}")
            logger.error(
                f"Ensure Ollama is running and model '{model}' is available (ollama pull {model})"
            )
            raise RuntimeError(
                f"Ollama timeout: model '{model}' did not respond within 30s"
            ) from e
        except aiohttp.ClientError as e:
            logger.error(f"Ollama API connection failed: {e.__class__.__name__}: {e}")
            logger.error(f"Check if Ollama is running at {model_url}")
            raise RuntimeError(f"Ollama connection error: {e}") from e
        except Exception as e:
            logger.error(f"Ollama API call failed: {e.__class__.__name__}: {e}")
            logger.exception("Full traceback:")
            raise

    async def _call_lm_studio_async(
        self, model_url: str, model: str, prompt: str, temperature: float
    ) -> str:
        """Call LM Studio API endpoint asynchronously."""
        try:
            # LM Studio uses OpenAI-compatible format
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": 500,
            }

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{model_url}/v1/chat/completions", json=payload
                ) as response:
                    if response.status >= 400:
                        body = (await response.text() or "").strip()
                        if len(body) > 1200:
                            body = body[:1200] + "..."
                        raise RuntimeError(
                            f"LM Studio HTTP {response.status} for url {response.url}: {body}"
                        )

                    result = await response.json()
                    return str(result["choices"][0]["message"]["content"]).strip()

        except Exception as e:
            logger.error(f"LM Studio API call failed: {e}")
            raise

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """
        Extract JSON from LLM response, handling various formats.

        Uses the robust JSON parser from orka.utils.json_parser.
        """
        # First try to extract
        extracted = extract_json_from_text(response)
        if extracted:
            return extracted

        # If extraction failed, try repair on the original response
        repaired = repair_malformed_json(response)
        return repaired

