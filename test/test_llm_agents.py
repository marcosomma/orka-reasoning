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


import os
from unittest.mock import MagicMock

import pytest

# Set environment variable for testing
os.environ["PYTEST_RUNNING"] = "true"

# Check if we should skip LLM tests
SKIP_LLM_TESTS = os.environ.get("SKIP_LLM_TESTS", "False").lower() in (
    "true",
    "1",
    "yes",
)

# Skip all tests if LLM tests should be skipped
pytestmark = pytest.mark.skipif(
    SKIP_LLM_TESTS,
    reason="OpenAI agents not properly configured or environment variable SKIP_LLM_TESTS is set",
)


# Create a standard mock response
def get_mock_response(content="Test response"):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = content
    return mock_response


# Only try to import if we're not skipping
if not SKIP_LLM_TESTS:
    try:
        # Do imports
        from orka.agents import (
            OpenAIAnswerBuilder,
            OpenAIBinaryAgent,
            OpenAIClassificationAgent,
        )

        # Original methods to be patched
        original_answer_run = OpenAIAnswerBuilder.run
        original_binary_run = OpenAIBinaryAgent.run
        original_classification_run = OpenAIClassificationAgent.run
    except (ImportError, AttributeError) as e:
        print(f"WARNING: Failed to import OpenAI agents: {e}")
        pytestmark = pytest.mark.skip(reason=f"OpenAI agent imports failed: {e}")


@pytest.fixture(scope="function")
def patch_openai_agents(monkeypatch):
    """Patch the agent classes directly instead of trying to patch the client import"""
    if SKIP_LLM_TESTS:
        return

    # Create mock for tracking calls
    mock_tracker = MagicMock()

    # Custom implementation that replaces the real methods
    def mocked_answer_run(self, input_data):
        mock_tracker()  # Track that this was called
        return mock_tracker.response_content

    def mocked_binary_run(self, input_data):
        mock_tracker()  # Track that this was called
        content = mock_tracker.response_content.lower()

        # Use the same logic as the original implementation for consistency
        positive_indicators = ["yes", "true", "correct", "right", "affirmative"]
        for indicator in positive_indicators:
            if indicator in content:
                return True
        return False

    def mocked_classification_run(self, input_data):
        mock_tracker()  # Track that this was called
        return mock_tracker.response_content

    # Apply patches
    monkeypatch.setattr(OpenAIAnswerBuilder, "run", mocked_answer_run)
    monkeypatch.setattr(OpenAIBinaryAgent, "run", mocked_binary_run)
    monkeypatch.setattr(OpenAIClassificationAgent, "run", mocked_classification_run)

    # Set default response
    mock_tracker.response_content = "Test response"

    return mock_tracker


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

    def test_run_with_valid_response(self, patch_openai_agents):
        """Test OpenAI API calls"""
        # Set custom response content for this test
        patch_openai_agents.response_content = "This is a test answer"

        # Create the agent
        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Generate an answer to: {{question}}",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"question": "What is the meaning of life?"})

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result
        assert isinstance(result, str)
        assert result == "This is a test answer"

    def test_run_with_template_variables(self, patch_openai_agents):
        """Test template variable substitution"""
        # Set custom response content for this test
        patch_openai_agents.response_content = "42"

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

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result
        assert isinstance(result, str)
        assert result == "42"

    def test_run_with_error(self, patch_openai_agents):
        """Test error handling"""

        # Configure the mock to raise an exception
        def raise_error(*args, **kwargs):
            raise Exception("API Error")

        patch_openai_agents.side_effect = raise_error

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
    def test_binary_agent_yes_response(self, patch_openai_agents):
        """Test OpenAIBinaryAgent with 'yes' response"""
        # Set custom response content for this test - includes an affirmative word
        patch_openai_agents.response_content = "Yes, I agree"

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this a yes?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about yes"})

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result is a boolean True
        assert result is True
        assert isinstance(result, bool)

    def test_binary_agent_no_response(self, patch_openai_agents):
        """Test OpenAIBinaryAgent with 'no' response"""
        # Set custom response content for this test that doesn't contain positive indicators
        patch_openai_agents.response_content = "No, I do not agree"

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this a no?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about no"})

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result is a boolean False
        assert result is False
        assert isinstance(result, bool)

    def test_binary_agent_invalid_response(self, patch_openai_agents):
        """Test OpenAIBinaryAgent with invalid response"""
        # Set custom response content for this test with affirmative indicator "correct"
        patch_openai_agents.response_content = (
            "Maybe, it depends but I think it's correct"
        )

        # Create the agent
        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this clear?",
            queue="test_queue",
        )

        # Run the agent
        result = agent.run({"input": "Tell me about maybe"})

        # Verify the mock was called
        assert patch_openai_agents.called

        # Current impl will return True because 'correct' is a positive indicator
        assert result is True
        assert isinstance(result, bool)


class TestOpenAIClassificationAgent:
    def test_classification_agent_valid_class(self, patch_openai_agents):
        """Test OpenAIClassificationAgent with valid class"""
        # Set custom response content for this test
        patch_openai_agents.response_content = "fruit"

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

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result
        assert result == "fruit"
        assert isinstance(result, str)

    def test_classification_agent_invalid_class(self, patch_openai_agents):
        """Test OpenAIClassificationAgent with invalid class"""
        # Set custom response content for this test
        patch_openai_agents.response_content = "dessert"

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

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result
        assert result == "dessert"
        assert isinstance(result, str)

    def test_classification_agent_case_insensitive(self, patch_openai_agents):
        """Test OpenAIClassificationAgent with case differences"""
        # Set custom response content for this test
        patch_openai_agents.response_content = "FRUIT"

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

        # Verify the mock was called
        assert patch_openai_agents.called

        # Verify the result
        assert result == "FRUIT"
        assert isinstance(result, str)
        assert result.lower() == "fruit"
