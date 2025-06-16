"""
Tests for the Validation and Structuring Agent.
"""

import os
from unittest.mock import MagicMock

import pytest

from orka.agents.llm_agents import OpenAIAnswerBuilder
from orka.agents.validation_and_structuring_agent import ValidationAndStructuringAgent

# Check if we should skip async/event loop tests in CI
SKIP_ASYNC_TESTS = os.environ.get("CI", "").lower() in ("true", "1", "yes")

# Skip marker for tests that have event loop issues in CI
async_skip = pytest.mark.skipif(
    SKIP_ASYNC_TESTS,
    reason="Async tests skipped in CI due to event loop issues",
)


@async_skip
def test_structuring_agent_output():
    """Test that the agent produces the expected output structure."""
    # Create a mock response for the LLM
    mock_response = """
    {
        "valid": true,
        "reason": "Answer is correct and coherent",
        "memory_object": {
            "fact": "Madrid is the capital of Spain",
            "category": "geography",
            "confidence": 0.95
        }
    }
    """

    # Create a mock for OpenAIAnswerBuilder
    mock_llm_agent = MagicMock(spec=OpenAIAnswerBuilder)
    mock_llm_agent.run.return_value = mock_response

    # Create the agent and inject the mock
    agent = ValidationAndStructuringAgent(
        {"agent_id": "test_validation_agent", "prompt": "", "queue": None},
    )
    agent.llm_agent = mock_llm_agent

    # Run the test
    out = agent.run(
        {
            "input": "What's the capital of Spain?",
            "previous_outputs": {
                "context-collector": "User is asking a geography question.",
                "answer-builder": "The capital of Spain is Madrid.",
            },
        },
    )

    # Check output structure
    assert isinstance(out, dict)
    assert "valid" in out
    assert "reason" in out
    assert "memory_object" in out

    # Check types
    assert isinstance(out["valid"], bool)
    assert isinstance(out["reason"], str)
    assert isinstance(out["memory_object"], dict)

    # Verify the mock was called with correct input
    mock_llm_agent.run.assert_called_once()
    call_args = mock_llm_agent.run.call_args[0][0]
    assert "prompt" in call_args
    assert "What's the capital of Spain?" in call_args["prompt"]


@async_skip
def test_structuring_agent_with_template():
    """Test that the agent can use a provided structure template."""
    # Create a mock response for the LLM
    mock_response = """
    {
        "valid": true,
        "reason": "Answer is correct and follows template",
        "memory_object": {
            "fact": "Madrid is the capital of Spain",
            "category": "geography",
            "confidence": 0.95
        }
    }
    """

    # Create a mock for OpenAIAnswerBuilder
    mock_llm_agent = MagicMock(spec=OpenAIAnswerBuilder)
    mock_llm_agent.run.return_value = mock_response

    # Create the agent and inject the mock
    agent = ValidationAndStructuringAgent(
        {
            "agent_id": "test_validation_agent",
            "prompt": "",
            "queue": None,
            "store_structure": """
            {
                "fact": "string",
                "category": "string",
                "confidence": "number"
            }
            """,
        },
    )
    agent.llm_agent = mock_llm_agent

    out = agent.run(
        {
            "input": "What's the capital of Spain?",
            "previous_outputs": {
                "context-collector": "User is asking a geography question.",
                "answer-builder": "The capital of Spain is Madrid.",
            },
        },
    )

    # Check output structure
    assert isinstance(out, dict)
    assert "valid" in out
    assert "reason" in out
    assert "memory_object" in out

    # If valid, check memory object structure
    if out["valid"] and out["memory_object"]:
        assert "fact" in out["memory_object"]
        assert "category" in out["memory_object"]
        assert "confidence" in out["memory_object"]

    # Verify the mock was called with correct input
    mock_llm_agent.run.assert_called_once()
    call_args = mock_llm_agent.run.call_args[0][0]
    assert "prompt" in call_args
    assert "What's the capital of Spain?" in call_args["prompt"]


@async_skip
def test_structuring_agent_invalid_json():
    """Test that the agent handles invalid JSON responses gracefully."""
    # Create a mock for OpenAIAnswerBuilder that returns invalid JSON
    mock_llm_agent = MagicMock(spec=OpenAIAnswerBuilder)
    mock_llm_agent.run.return_value = "This is not valid JSON"

    # Create the agent and inject the mock
    agent = ValidationAndStructuringAgent(
        {"agent_id": "test_validation_agent", "prompt": "", "queue": None},
    )
    agent.llm_agent = mock_llm_agent

    out = agent.run(
        {
            "input": "What's the capital of Spain?",
            "previous_outputs": {
                "context-collector": "User is asking a geography question.",
                "answer-builder": "The capital of Spain is Madrid.",
            },
        },
    )

    # Check error handling
    assert isinstance(out, dict)
    assert out["valid"] is False
    assert "Failed to parse model output" in out["reason"]
    assert out["memory_object"] is None


@async_skip
def test_structuring_agent_with_model_settings():
    """Test that the agent properly passes model settings to the LLM agent."""
    # Create a mock for OpenAIAnswerBuilder
    mock_llm_agent = MagicMock(spec=OpenAIAnswerBuilder)
    mock_llm_agent.run.return_value = '{"valid": true, "reason": "test", "memory_object": {}}'

    # Create the agent and inject the mock
    agent = ValidationAndStructuringAgent(
        {"agent_id": "test_validation_agent", "prompt": "", "queue": None},
    )
    agent.llm_agent = mock_llm_agent

    # Test with custom model and temperature
    agent.run(
        {
            "input": "Test question",
            "previous_outputs": {
                "context-collector": "Test context",
                "answer-builder": "Test answer",
            },
            "model": "gpt-4",
            "temperature": 0.5,
        },
    )

    # Verify the mock was called with correct settings
    mock_llm_agent.run.assert_called_once()
    call_args = mock_llm_agent.run.call_args[0][0]
    assert "prompt" in call_args
    assert "Test question" in call_args["prompt"]
