import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from orka.agents.validation_and_structuring_agent import ValidationAndStructuringAgent

@pytest.fixture
def agent_params():
    return {
        "agent_id": "test_validator",
        "prompt": "Validate this: {{ input }}",
        "store_structure": {
            "fact": "{{ fact }}",
            "category": "test_category"
        }
    }

@patch("orka.agents.validation_and_structuring_agent.OpenAIAnswerBuilder")
def test_validation_agent_initialization(mock_llm_builder, agent_params):
    """Test the initialization of the ValidationAndStructuringAgent."""
    agent = ValidationAndStructuringAgent(agent_params)
    
    assert agent.agent_id == "test_validator"
    mock_llm_builder.assert_called_once_with(
        agent_id="test_validator_llm",
        prompt="Validate this: {{ input }}",
        queue=None
    )
    assert agent.llm_agent is mock_llm_builder.return_value

def test_build_prompt(agent_params):
    """Test the build_prompt method."""
    agent = ValidationAndStructuringAgent(agent_params)
    prompt = agent.build_prompt("question", "context", "answer", agent_params["store_structure"])
    
    assert "Question: question" in prompt
    assert "Context: context" in prompt
    assert "Answer to validate: answer" in prompt
    assert "fact" in prompt
    assert "test_category" in prompt

def test_parse_llm_output_valid_json():
    """Test parsing of a valid JSON output from the LLM."""
    agent = ValidationAndStructuringAgent({"agent_id": "test"})
    raw_output = '```json\n{"valid": true, "reason": "Looks good", "memory_object": {"fact": "a thing"}}\n```'
    parsed = agent._parse_llm_output(raw_output, "prompt")
    
    assert parsed["valid"] is True
    assert parsed["reason"] == "Looks good"
    assert parsed["memory_object"]["fact"] == "a thing"

def test_parse_llm_output_invalid_json():
    """Test parsing of an invalid JSON output."""
    agent = ValidationAndStructuringAgent({"agent_id": "test"})
    raw_output = 'this is not json'
    parsed = agent._parse_llm_output(raw_output, "prompt")
    
    assert parsed["valid"] is False
    assert "Failed to parse JSON" in parsed["reason"]

def test_parse_llm_output_wrong_format():
    """Test parsing of a JSON with an unexpected structure."""
    agent = ValidationAndStructuringAgent({"agent_id": "test"})
    raw_output = '{"response": "some other agent response"}'
    parsed = agent._parse_llm_output(raw_output, "prompt")
    
    assert parsed["valid"] is False
    # Updated to match new parser's error message
    assert "missing 'valid' field" in parsed["reason"]

@pytest.mark.asyncio
async def test_run_impl(agent_params):
    """Test the main _run_impl method."""
    agent = ValidationAndStructuringAgent(agent_params)
    
    # Mock the internal llm_agent's run method
    mock_llm_run = AsyncMock()
    agent.llm_agent.run = mock_llm_run
    
    # Simulate a valid JSON response from the mocked LLM
    llm_response_payload = {
        "response": '```json\n{"valid": true, "reason": "It is correct", "memory_object": {"fact": "the fact"}}\n```'
    }
    mock_llm_run.return_value = llm_response_payload
    
    ctx = {
        "input": "the question",
        "previous_outputs": {
            "context-collector": {"result": {"response": "the context"}},
            "answer-builder": {"result": {"response": "the answer"}}
        }
    }
    
    result = await agent._run_impl(ctx)
    
    # Assert that the LLM was called correctly
    mock_llm_run.assert_called_once()
    call_args = mock_llm_run.call_args[0][0]
    assert "prompt" in call_args
    assert call_args["parse_json"] is False
    
    # Assert the final parsed result
    assert result["valid"] is True
    assert result["reason"] == "It is correct"
    assert result["memory_object"]["fact"] == "the fact"
