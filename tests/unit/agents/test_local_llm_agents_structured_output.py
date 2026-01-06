import pytest

from orka.agents.local_llm_agents import LocalLLMAgent


@pytest.mark.asyncio
async def test_prompt_mode_with_schema_parsing(monkeypatch):
    # Monkeypatch network call to return a JSON string
    async def fake_call_openai_compatible(self, model_url, model, prompt, temperature, max_tokens=None):
        return '{"response": "summary", "confidence": 0.7}'

    monkeypatch.setattr(LocalLLMAgent, "_call_openai_compatible", fake_call_openai_compatible, raising=True)

    agent = LocalLLMAgent(
        agent_id="loc1",
        prompt="Summarize: {{ input }}",
        provider="openai_compatible",
        model_url="http://localhost:9999/v1/chat/completions",
        model="llama3.2:latest",
    )
    # Enable structured output in prompt mode
    agent.params.setdefault("structured_output", {"enabled": True, "mode": "prompt"})

    ctx = {
        "input": "text",
        "prompt": "Summarize: {{ input }}",
        "model": "llama3.2:latest",
    }

    result = await agent._run_impl(ctx)
    assert result["response"] == "summary"


@pytest.mark.asyncio
async def test_unsupported_mode_fallback_to_prompt(monkeypatch):
    async def fake_call_ollama(self, model_url, model, prompt, temperature, max_tokens=None):
        # The instructions should not break parsing; return JSON anyway
        return '{"response": "ok", "confidence": 0.6}'

    monkeypatch.setattr(LocalLLMAgent, "_call_ollama", fake_call_ollama, raising=True)

    agent = LocalLLMAgent(
        agent_id="loc2",
        prompt="Say: {{ input }}",
        provider="ollama",
        model_url="http://localhost:11434/api/generate",
        model="llama3.2:latest",
    )
    # Request unsupported mode (tool_call) and ensure fallback works
    agent.params.setdefault("structured_output", {"enabled": True, "mode": "tool_call"})

    ctx = {
        "input": "hi",
        "prompt": "Say: {{ input }}",
        "model": "llama3.2:latest",
    }

    result = await agent._run_impl(ctx)
    assert result["response"] == "ok"
