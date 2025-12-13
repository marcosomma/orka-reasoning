import pytest
from unittest.mock import patch, MagicMock
from orka.agents.local_llm_agents import LocalLLMAgent, _count_tokens

# Tests for _count_tokens
def test_count_tokens_with_tiktoken():
    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
    mock_tiktoken.encoding_for_model.side_effect = KeyError
    mock_tiktoken.get_encoding.return_value = mock_encoding
    
    with patch.dict('sys.modules', {'tiktoken': mock_tiktoken}):
        count = _count_tokens("some text", model="llama3")
        assert count == 5
        mock_tiktoken.encoding_for_model.assert_called_once_with("llama3")
        mock_tiktoken.get_encoding.assert_called_with("cl100k_base")

def test_count_tokens_without_tiktoken():
    with patch.dict('sys.modules', {'tiktoken': None}):
        # a simple estimate is used when tiktoken is not available
        count = _count_tokens("This is a test sentence.")
        assert count == len("This is a test sentence.") // 4

# Tests for LocalLLMAgent
@pytest.fixture
def local_llm_agent():
    params = {
        "model": "test_model",
        "model_url": "http://localhost:1234",
        "provider": "ollama",
    }
    return LocalLLMAgent(agent_id="test_llm_agent", **params)

@pytest.mark.asyncio
@patch("orka.agents.local_llm_agents.LocalLLMAgent._call_ollama")
@patch("orka.agents.local_cost_calculator.calculate_local_llm_cost", return_value=0.0001)
async def test_local_llm_agent_run_ollama(mock_cost, mock_call_ollama, local_llm_agent):
    ollama_response_str = '{"response": "Ollama response text", "confidence": 0.9, "internal_reasoning": "some reasoning"}'
    mock_call_ollama.return_value = ollama_response_str
    
    ctx = {"input": "test input"}
    result = await local_llm_agent._run_impl(ctx)
    
    assert result["response"] == "Ollama response text"
    assert result["confidence"] == "0.9"
    assert result["internal_reasoning"] == "some reasoning"
    assert result["_metrics"]["cost_usd"] == 0.0001
    mock_call_ollama.assert_called_once()

@pytest.mark.asyncio
@patch("orka.agents.local_llm_agents.LocalLLMAgent._call_lm_studio")
@patch("orka.agents.local_cost_calculator.calculate_local_llm_cost", return_value=0.0002)
async def test_local_llm_agent_run_lm_studio(mock_cost, mock_call_lm_studio):
    params = {
        "model": "test_model",
        "model_url": "http://localhost:1234/v1",
        "provider": "lm_studio",
    }
    agent = LocalLLMAgent(agent_id="test_llm_agent", **params)
    
    lm_studio_response_str = '{"response": "LM Studio response text", "confidence": 0.8, "internal_reasoning": "other reasoning"}'
    mock_call_lm_studio.return_value = lm_studio_response_str
    
    ctx = {"input": "test input"}
    result = await agent._run_impl(ctx)
    
    assert result["response"] == "LM Studio response text"
    assert result["confidence"] == "0.8"
    assert result["internal_reasoning"] == "other reasoning"
    assert result["_metrics"]["cost_usd"] == 0.0002
    mock_call_lm_studio.assert_called_once()

@pytest.mark.asyncio
@patch("orka.agents.local_llm_agents.LocalLLMAgent._call_openai_compatible")
@patch("orka.agents.local_cost_calculator.calculate_local_llm_cost", return_value=0.0003)
async def test_local_llm_agent_run_openai_compatible(mock_cost, mock_call_openai):
    params = {
        "model": "test_model",
        "model_url": "http://localhost:8000/v1/chat/completions",
        "provider": "openai_compatible",
    }
    agent = LocalLLMAgent(agent_id="test_llm_agent", **params)
    
    openai_response_str = '{"response": "OpenAI compatible response text", "confidence": 0.7, "internal_reasoning": "another reasoning"}'
    mock_call_openai.return_value = openai_response_str
    
    ctx = {"input": "test input"}
    result = await agent._run_impl(ctx)
    
    assert result["response"] == "OpenAI compatible response text"
    assert result["confidence"] == "0.7"
    assert result["internal_reasoning"] == "another reasoning"
    assert result["_metrics"]["cost_usd"] == 0.0003
    mock_call_openai.assert_called_once()

@pytest.mark.asyncio
@patch("orka.agents.local_llm_agents.LocalLLMAgent._call_ollama", side_effect=Exception("API error"))
@patch("orka.agents.local_cost_calculator.calculate_local_llm_cost", return_value=None)
async def test_local_llm_agent_run_error(mock_cost, mock_call_ollama, local_llm_agent):
    ctx = {"input": "test input"}
    result = await local_llm_agent._run_impl(ctx)
    assert "error" in result["response"]
    assert "API error" in result["response"]
    assert result["_metrics"]["cost_usd"] is None

def test_build_prompt(local_llm_agent):
    input_text = "world"
    template = "Hello {{ input }}"
    prompt = local_llm_agent.build_prompt(input_text, template)
    assert prompt == "Hello world"

def test_build_prompt_with_full_context(local_llm_agent):
    input_text = "test"
    template = "Input: {{ input }}, Previous: {{ previous_outputs.agent1.response }}"
    full_context = {
        "previous_outputs": {
            "agent1": {"response": "previous response"}
        }
    }
    prompt = local_llm_agent.build_prompt(input_text, template, full_context)
    assert prompt == "Input: test, Previous: previous response"
