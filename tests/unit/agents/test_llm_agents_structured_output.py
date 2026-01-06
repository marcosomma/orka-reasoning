import asyncio
import json
import types
import pytest

from orka.agents.llm_agents import OpenAIAnswerBuilder, OpenAIBinaryAgent, OpenAIClassificationAgent


class _FakeFunction:
    def __init__(self, arguments: str):
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, arguments: str):
        self.function = _FakeFunction(arguments)


class _FakeMessage:
    def __init__(self, content: str | None = None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeUsage:
    def __init__(self):
        self.prompt_tokens = 10
        self.completion_tokens = 5
        self.total_tokens = 15


class _FakeChoice:
    def __init__(self, message: _FakeMessage):
        self.message = message


class _FakeResponse:
    def __init__(self, message: _FakeMessage):
        self.choices = [_FakeChoice(message)]
        self.usage = _FakeUsage()


class _Recorder:
    def __init__(self):
        self.calls = []


class _FakeCompletions:
    def __init__(self, recorder: _Recorder, response_factory):
        self._recorder = recorder
        self._response_factory = response_factory

    async def create(self, **kwargs):
        self._recorder.calls.append(kwargs)
        return self._response_factory(kwargs)


class _FakeChat:
    def __init__(self, recorder: _Recorder, response_factory):
        self.completions = _FakeCompletions(recorder, response_factory)


class _FakeClient:
    def __init__(self, recorder: _Recorder, response_factory):
        self.chat = _FakeChat(recorder, response_factory)


@pytest.mark.asyncio
async def test_model_json_mode(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        # Ensure response_format was set for model_json mode
        assert kwargs.get("response_format") == {"type": "json_object"}
        message = _FakeMessage(content='{"response": "ok", "confidence": 0.9}')
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIAnswerBuilder(agent_id="a1", prompt="Answer: {{ input }}", model="gpt-4o")
    # Enable structured output in params
    agent.params.setdefault("structured_output", {"enabled": True, "mode": "model_json"})

    ctx = {"input": "hi", "prompt": "Answer: {{ input }}", "model": "gpt-4o"}
    result = await agent._run_impl(ctx)

    assert isinstance(result, dict)
    assert result["response"] == "ok"
    assert "_metrics" in result
    # Verify request recorder captured a call
    assert len(recorder.calls) == 1


@pytest.mark.asyncio
async def test_tool_call_mode(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        # Ensure tools and tool_choice were set
        tools = kwargs.get("tools")
        assert isinstance(tools, list) and tools
        assert kwargs.get("tool_choice") == "required"
        args = json.dumps({"response": "yes", "confidence": 0.8})
        message = _FakeMessage(content="ignored", tool_calls=[_FakeToolCall(args)])
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIAnswerBuilder(agent_id="a2", prompt="Answer: {{ input }}")
    agent.params.setdefault(
        "structured_output", {"enabled": True, "mode": "tool_call", "strict": True}
    )

    ctx = {"input": "hi", "prompt": "Answer: {{ input }}", "model": "gpt-4o"}
    result = await agent._run_impl(ctx)

    assert result["response"] == "yes"
    assert result.get("confidence") == 0.8 or result.get("confidence") == "0.8"
    assert len(recorder.calls) == 1


@pytest.mark.asyncio
async def test_prompt_mode_fallback_injects_instructions(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        # Verify prompt contains JSON fenced block instruction
        messages = kwargs.get("messages")
        assert isinstance(messages, list)
        content = messages[0]["content"]
        assert "```json" in content
        message = _FakeMessage(content='{"response": "ok"}')
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIAnswerBuilder(agent_id="a3", prompt="Answer: {{ input }}")
    agent.params.setdefault(
        "structured_output", {"enabled": True, "mode": "prompt"}
    )

    ctx = {"input": "hi", "prompt": "Answer: {{ input }}", "model": "gpt-3.5-turbo"}
    result = await agent._run_impl(ctx)

    assert result["response"] == "ok"


@pytest.mark.asyncio
async def test_backward_compat_disabled(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        message = _FakeMessage(content="Some plain text response")
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIAnswerBuilder(agent_id="a4", prompt="Say: {{ input }}")
    # No structured_output in params (disabled by default)

    ctx = {"input": "hello", "prompt": "Say: {{ input }}", "model": "gpt-4o"}
    result = await agent._run_impl(ctx)

    assert isinstance(result, dict)
    assert "response" in result


@pytest.mark.asyncio
async def test_binary_agent_structured_tool_call(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        args = json.dumps({"result": True, "confidence": 0.95})
        message = _FakeMessage(content="ignored", tool_calls=[_FakeToolCall(args)])
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIBinaryAgent(agent_id="b1", prompt="Is valid? {{ input }}")
    agent.params.setdefault(
        "structured_output", {"enabled": True, "mode": "tool_call"}
    )

    ctx = {"input": "test", "prompt": "Is valid? {{ input }}", "model": "gpt-4o"}
    result = await agent._run_impl(ctx)

    assert result["response"] is True


@pytest.mark.asyncio
async def test_classification_agent_category_and_validation(monkeypatch):
    recorder = _Recorder()

    def make_response(kwargs):
        args = json.dumps({"category": "positive", "confidence": 0.7})
        # Simulate tool call to force structured output
        message = _FakeMessage(content="ignored", tool_calls=[_FakeToolCall(args)])
        return _FakeResponse(message)

    fake_client = _FakeClient(recorder, make_response)
    import orka.agents.llm_agents as llm_mod

    monkeypatch.setattr(llm_mod, "client", fake_client, raising=True)

    agent = OpenAIClassificationAgent(agent_id="c1", prompt="Classify: {{ input }}", options=["positive", "negative"])
    agent.params.setdefault(
        "structured_output", {"enabled": True, "mode": "tool_call"}
    )

    ctx = {"input": "great", "prompt": "Classify: {{ input }}", "model": "gpt-4o"}
    result = await agent._run_impl(ctx)

    assert result["response"] == "positive"
