import pytest
import sys

from orka.agents.plan_validator import llm_client


pytestmark = [pytest.mark.unit]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_call_llm_normalizes_lm_studio_to_openai_compatible(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        # OpenAI-compatible response shape
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    async def fake_to_thread(func, *args, **kwargs):
        # Execute synchronously to keep the test deterministic
        return func(*args, **kwargs)

    monkeypatch.setattr(llm_client.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setitem(sys.modules, "requests", type("R", (), {"post": staticmethod(fake_post)}))

    result = await llm_client.call_llm(
        prompt="hi",
        model="openai/gpt-oss-20b",
        url="http://localhost:1234/v1/chat/completions",
        provider="lm_studio",
        temperature=0.2,
    )

    assert result == "ok"
    # Must be OpenAI-compatible payload (messages)
    assert "messages" in captured["json"]
    assert captured["json"]["model"] == "openai/gpt-oss-20b"


@pytest.mark.asyncio
async def test_call_llm_uses_ollama_payload_when_provider_is_ollama(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        # Ollama response shape
        return _FakeResponse({"response": "ok"})

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(llm_client.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setitem(sys.modules, "requests", type("R", (), {"post": staticmethod(fake_post)}))

    result = await llm_client.call_llm(
        prompt="hi",
        model="llama3.2:latest",
        url="http://localhost:11434/api/generate",
        provider="ollama",
        temperature=0.2,
    )

    assert result == "ok"
    # Must be Ollama payload (prompt)
    assert "prompt" in captured["json"]
    assert captured["json"]["model"] == "llama3.2:latest"
