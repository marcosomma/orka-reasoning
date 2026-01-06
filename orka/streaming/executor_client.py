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
Simple OpenAI-compatible HTTP client for streaming executor integration.

Used optionally when ORKA_STREAMING_HTTP_ENABLE=1 is set.
Designed to work with LM Studio / OpenAI-compatible endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, AsyncIterator

import asyncio
import httpx
import json


class OpenAICompatClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "sk-no-key"
        self.timeout = timeout

    async def complete(self, model: str, system: str, user: str, stream: bool = False) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"] or ""
            except Exception:
                return ""

    async def stream_complete(self, model: str, system: str, user: str) -> AsyncIterator[str]:
        """OpenAI-compatible SSE streaming. Yields token/content deltas as they arrive.

        This method reads Server-Sent Events from /v1/chat/completions with stream=true
        and yields the content deltas from choices[].delta.content until [DONE].
        """
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except Exception:
                        continue
                    for choice in obj.get("choices", []):
                        delta = choice.get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
