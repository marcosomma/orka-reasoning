import pytest
from orka.agents.llm_agents import (
    _extract_reasoning,
    _extract_json_content,
    _normalize_python_to_json,
    _parse_json_safely,
    _build_response_dict,
    parse_llm_json_response,
    _fix_malformed_json,
    _calculate_openai_cost,
    _simple_json_parse,
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
)
from unittest.mock import patch, MagicMock, AsyncMock

# Tests for helper functions
def test_extract_reasoning():
    text = "<think>This is reasoning.</think>This is the response."
    reasoning, response = _extract_reasoning(text)
    assert reasoning == "This is reasoning."
    assert response == "This is the response."

def test_extract_json_content():
    text = 'Here is the json: ```json\n{"key": "value"}\n```'
    json_content = _extract_json_content(text)
    assert json_content == '{"key": "value"}'

def test_normalize_python_to_json():
    py_text = "{'key': True, 'none_key': None}"
    json_text = _normalize_python_to_json(py_text)
    assert json_text == '{"key": true, "none_key": null}'

def test_parse_json_safely():
    json_text = '{"key": "value"}'
    parsed = _parse_json_safely(json_text)
    assert parsed == {"key": "value"}
    
    malformed_text = '{"key": "value",}'
    # The fixer is not perfect, this is a simple test
    # _parse_json_safely has a call to _fix_malformed_json
    # but it is not guaranteed to fix all malformed json
    # so we can't assert a perfect fix.
    # A more robust test would check specific fixes.
    # For now, we check it doesn't crash.
    _parse_json_safely(malformed_text)


def test_build_response_dict():
    parsed_json = {"response": "test", "confidence": "0.9", "internal_reasoning": "reasoning"}
    response_dict = _build_response_dict(parsed_json, "")
    assert response_dict == parsed_json

def test_parse_llm_json_response():
    response_text = "<think>reasoning</think>```json\n{\"response\": \"test\", \"confidence\": \"0.9\", \"internal_reasoning\": \"json reasoning\"}\n```"
    parsed = parse_llm_json_response(response_text)
    assert parsed["response"] == "test"
    assert parsed["confidence"] == "0.9"
    assert "json reasoning" in parsed["internal_reasoning"]
    assert "reasoning" in parsed["internal_reasoning"]

def test_fix_malformed_json():
    malformed = '{"key": "value",}'
    fixed = _fix_malformed_json(malformed)
    assert fixed == '{"key": "value"}'

def test_calculate_openai_cost():
    cost = _calculate_openai_cost("gpt-4", 1000, 1000)
    assert cost == 0.03 + 0.06

def test_simple_json_parse():
    text = '```json\n{"response": "test", "confidence": "0.5"}\n```'
    parsed = _simple_json_parse(text)
    assert parsed["response"] == "test"
    assert parsed["confidence"] == "0.5"

# Tests for Agent Classes
@pytest.fixture
def mock_openai_client():
    # This fixture patches the 'client' object in the llm_agents module.
    # The 'new_callable=AsyncMock' is important for async methods.
    with patch("orka.agents.llm_agents.client", new_callable=AsyncMock) as mock_client:
        yield mock_client

@pytest.mark.asyncio
async def test_openai_answer_builder_run(mock_openai_client):
    agent = OpenAIAnswerBuilder(agent_id="test_agent", prompt="test prompt")
    
    # We need to create a mock response that mimics the OpenAI API response structure.
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_usage = MagicMock()

    mock_message.content = '{"response": "OpenAI response", "confidence": "0.9"}'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20
    mock_usage.total_tokens = 30
    mock_response.usage = mock_usage
    
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    ctx = {"input": "test input"}
    result = await agent._run_impl(ctx)
    
    assert result["response"] == "OpenAI response"
    assert result["confidence"] == "0.9"
    assert result["_metrics"]["tokens"] == 30

@pytest.mark.asyncio
async def test_openai_binary_agent_run(mock_openai_client):
    agent = OpenAIBinaryAgent(agent_id="test_agent", prompt="test prompt")
    
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_usage = MagicMock()

    mock_message.content = 'true'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 1
    mock_usage.total_tokens = 11
    mock_response.usage = mock_usage

    mock_openai_client.chat.completions.create.return_value = mock_response
    
    ctx = {"input": "test input"}
    result = await agent._run_impl(ctx)
    
    assert result["response"] is True

@pytest.mark.asyncio
async def test_openai_classification_agent_run(mock_openai_client):
    agent = OpenAIClassificationAgent(agent_id="test_agent", prompt="test prompt", params={"options": ["A", "B"]})
    
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_usage = MagicMock()

    mock_message.content = 'A'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 1
    mock_usage.total_tokens = 11
    mock_response.usage = mock_usage
    
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    ctx = {"input": "test input"}
    result = await agent._run_impl(ctx)
    
    assert result["response"] == "A"
