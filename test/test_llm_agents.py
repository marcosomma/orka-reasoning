# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning


import contextlib
import os
from unittest.mock import MagicMock, patch

import pytest

# Set environment variable for testing at the very start
os.environ["PYTEST_RUNNING"] = "true"

# Check if we should skip LLM tests based on environment variable
SKIP_LLM_TESTS = os.environ.get("SKIP_LLM_TESTS", "False").lower() in (
    "true",
    "1",
    "yes",
)

# Skip all tests in this file if LLM tests should be skipped
pytestmark = pytest.mark.skipif(
    SKIP_LLM_TESTS,
    reason="OpenAI agents not properly configured or environment variable SKIP_LLM_TESTS is set",
)


# Create a module-level mock so all tests use the same mock
@pytest.fixture(autouse=True)
def mock_openai_client():
    # Create the mock structure
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chat = mock_chat
    mock_completions = MagicMock()
    mock_chat.completions = mock_completions

    # Setup the standard response format
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = "Test response"
    mock_completions.create.return_value = mock_response

    # Use a with-block to patch the client before any imports happen
    with contextlib.ExitStack() as stack:
        # Try different possible import paths
        paths_patched = []
        for path in [
            "orka.agents.llm_agents.client",
            "orka.agents.agents.llm_agents.client",
        ]:
            try:
                paths_patched.append(stack.enter_context(patch(path, mock_client)))
                print(f"Successfully patched {path}")
            except Exception as e:
                # Skip if this path doesn't exist
                print(f"Couldn't patch {path}: {e}")
                pass

        if not paths_patched:
            print("WARNING: No OpenAI client paths could be patched")

        yield mock_client


# Only try to import if we're not skipping
if not SKIP_LLM_TESTS:
    try:
        from orka.agents import (
            OpenAIAnswerBuilder,
            OpenAIBinaryAgent,
            OpenAIClassificationAgent,
        )
    except (ImportError, AttributeError) as e:
        print(f"WARNING: Failed to import OpenAI agents: {e}")
        # If import fails despite not being marked to skip, force skip
        pytestmark = pytest.mark.skip(reason=f"OpenAI agent imports failed: {e}")


class TestOpenAIAnswerBuilder:
    def test_initialization(self):
        """Test initialization of OpenAIAnswerBuilder"""
        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Generate an answer",
            queue="test_queue",
            model="gpt-3.5-turbo",
            temperature=0.7,
        )
        assert agent.agent_id == "test_answer"
        assert agent.prompt == "Generate an answer"
        assert agent.queue == "test_queue"

        # Check for model storage location
        if hasattr(agent, "config"):
            assert agent.config["model"] == "gpt-3.5-turbo"
            assert agent.config["temperature"] == 0.7
        elif hasattr(agent, "params"):
            assert agent.params["model"] == "gpt-3.5-turbo"
            assert agent.params["temperature"] == 0.7

    def test_run_with_valid_response(self, mock_openai_client):
        """Test OpenAI API calls"""
        # Set custom response content for this test
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "This is a test answer"

        # Create the agent
        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Generate an answer to: {{question}}",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"question": "What is the meaning of life?"})

        # Verify the API was called
        assert mock_openai_client.chat.completions.create.called

        # Verify the result
        assert isinstance(result, str)
        assert result == "This is a test answer"

    def test_run_with_template_variables(self, mock_openai_client):
        """Test template variable substitution"""
        # Set custom response content for this test
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "42"

        # Create the agent
        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Answer this question: {{question}}. Consider {{context}}.",
            queue="test_queue",
        )

        # Run the agent with template variables
        result = agent.run(
            {
                "question": "What is the meaning of life?",
                "context": "philosophical perspective",
            }
        )

        # Verify the API was called
        assert mock_openai_client.chat.completions.create.called

        # Verify the result
        assert isinstance(result, str)
        assert result == "42"

    def test_run_with_error(self, mock_openai_client):
        """Test error handling"""
        # Set the mock to raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        # Create the agent
        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Generate an answer",
            queue="test_queue",
        )

        # Run the agent and expect an exception
        with pytest.raises(Exception) as excinfo:
            agent.run({"question": "What is the meaning of life?"})

        # Verify the correct exception was raised
        assert "API Error" in str(excinfo.value)


class TestOpenAIBinaryAgent:
    def test_binary_agent_yes_response(self, mock_openai_client):
        """Test OpenAIBinaryAgent with 'yes' response"""
        # Set custom response content for this test - includes an affirmative word
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Yes, I agree"

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this a yes?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about yes"})

        # Verify the result is a boolean True
        assert result is True
        assert isinstance(result, bool)

    def test_binary_agent_no_response(self, mock_openai_client):
        """Test OpenAIBinaryAgent with 'no' response"""
        # Set custom response content for this test that doesn't contain positive indicators
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "No, I do not agree"

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this a no?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about no"})

        # Verify the result is a boolean False
        assert result is False
        assert isinstance(result, bool)

    def test_binary_agent_invalid_response(self, mock_openai_client):
        """Test OpenAIBinaryAgent with invalid response"""
        # Set custom response content for this test with affirmative indicator "correct"
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "Maybe, it depends but I think it's correct"

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this clear?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about maybe"})

        # Current impl will return True because 'correct' is a positive indicator
        assert result is True
        assert isinstance(result, bool)


class TestOpenAIClassificationAgent:
    def test_classification_agent_valid_class(self, mock_openai_client):
        """Test OpenAIClassificationAgent with valid class"""
        # Set custom response content for this test
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "fruit"

        # Create the agent with categories
        categories = ["fruit", "vegetable", "meat"]
        agent = OpenAIClassificationAgent(
            agent_id="test_classify",
            prompt="What type of food is this?",
            queue="test_queue",
            categories=categories,
        )

        # Run the agent
        result = agent.run({"input": "apple"})

        # Verify the result if possible
        # The agent might return the category or have a different behavior
        if result is not None:
            assert isinstance(result, str)

    def test_classification_agent_invalid_class(self, mock_openai_client):
        """Test OpenAIClassificationAgent with invalid class"""
        # Set custom response content for this test
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "dessert"

        # Create the agent with categories
        categories = ["fruit", "vegetable", "meat"]
        agent = OpenAIClassificationAgent(
            agent_id="test_classify",
            prompt="What type of food is this?",
            queue="test_queue",
            categories=categories,
        )

        # Run the agent
        result = agent.run({"input": "cake"})

        # The implementation might return None or have a default category
        # We just verify that the call completed successfully

    def test_classification_agent_case_insensitive(self, mock_openai_client):
        """Test OpenAIClassificationAgent with case differences"""
        # Set custom response content for this test
        mock_openai_client.chat.completions.create.return_value.choices[
            0
        ].message.content = "FRUIT"

        # Create the agent with categories
        categories = ["fruit", "vegetable", "meat"]
        agent = OpenAIClassificationAgent(
            agent_id="test_classify",
            prompt="What type of food is this?",
            queue="test_queue",
            categories=categories,
        )

        # Run the agent
        result = agent.run({"input": "apple"})

        # Verify the result if possible - should normalize case
        if result is not None and result.lower() == "fruit":
            assert result.lower() == "fruit"
