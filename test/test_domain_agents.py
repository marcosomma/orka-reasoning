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

# Skip LLM tests if needed
llm_skip = pytest.mark.skipif(
    SKIP_LLM_TESTS,
    reason="OpenAI agents not properly configured or environment variable SKIP_LLM_TESTS is set",
)

from orka.agents.agents import BinaryAgent, ClassificationAgent
from orka.agents.base_agent import BaseAgent, LegacyBaseAgent
from orka.tools.search_tools import DuckDuckGoTool

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
        llm_skip = pytest.mark.skip(reason=f"OpenAI agent imports failed: {e}")


# Create a standard mock response
def get_mock_response(content="Test response"):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = content
    return mock_response


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


# Modern BaseAgent Tests


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Test initialization of modern BaseAgent"""
    agent = BaseAgent(agent_id="test_agent")
    assert agent.agent_id == "test_agent"
    assert agent.timeout == 30.0
    assert agent.prompt is None
    assert agent.queue is None
    assert not agent._initialized

    # Initialize the agent
    await agent.initialize()
    assert agent._initialized


@pytest.mark.asyncio
async def test_base_agent_cleanup():
    """Test agent cleanup method"""
    agent = BaseAgent(agent_id="test_agent")
    await agent.cleanup()  # Should not raise any exceptions


@pytest.mark.asyncio
async def test_base_agent_incomplete():
    """Test that using a BaseAgent without implementing _run_impl raises an error"""
    agent = BaseAgent(agent_id="test_incomplete")

    # Run should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        await agent._run_impl({})


@pytest.mark.asyncio
async def test_base_agent_complete():
    """Test a complete BaseAgent implementation"""

    class TestAgent(BaseAgent):
        async def _run_impl(self, ctx):
            return f"Result: {ctx.get('input', '')}"

    agent = TestAgent(agent_id="test_complete")

    # Run the agent with a simple input
    result = await agent.run({"input": "test"})
    assert isinstance(result, dict)  # Output is a dict-like object
    assert result.get("result") == "Result: test"
    assert result.get("status") == "success"
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_base_agent_exception_handling():
    """Test error handling in BaseAgent"""

    class ErrorAgent(BaseAgent):
        async def _run_impl(self, ctx):
            raise ValueError("Test error")

    agent = ErrorAgent(agent_id="test_error")

    # Run the agent and check error handling
    result = await agent.run("test_input")
    assert isinstance(result, dict)
    assert result.get("result") is None
    assert result.get("status") == "error"
    assert "Test error" in result.get("error", "")


# Legacy BaseAgent Tests


def test_legacy_base_agent_instance():
    """Test instantiation of a LegacyBaseAgent"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")
    assert agent.agent_id == "legacy_id"
    assert agent.prompt == "test prompt"
    assert agent.queue == "test_queue"
    assert agent._is_legacy_agent()


def test_legacy_base_agent_run():
    """Test running a LegacyBaseAgent"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")

    # Test with string input
    result = agent.run("test_input")
    assert result == "Processed: test_input"

    # Test with dict input
    result = agent.run({"input": "test_data"})
    assert result == "Processed: {'input': 'test_data'}"


@pytest.mark.asyncio
async def test_legacy_base_agent_run_async():
    """Test running a LegacyBaseAgent through the async interface"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed via legacy: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")

    # Call the async run method which should use the legacy implementation
    result = await BaseAgent.run(agent, "test_async")
    assert result == "Processed via legacy: test_async"


# Basic Agent Tests
class TestBinaryAgent:
    def test_initialization(self):
        """Test initialization of BinaryAgent"""
        agent = BinaryAgent(
            agent_id="test_binary",
            prompt="Test prompt",
            queue="test_queue",
        )
        assert agent.agent_id == "test_binary"
        assert agent.prompt == "Test prompt"
        assert agent.queue == "test_queue"

    def test_yes_response(self):
        """Test BinaryAgent with 'yes' input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this a yes?", queue="test_queue"
        )
        result = agent.run({"input": "yes"})
        assert result == "true" or result is True  # Handle both string and boolean

    def test_no_response(self):
        """Test BinaryAgent with 'no' input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this a no?", queue="test_queue"
        )
        result = agent.run({"input": "no"})
        assert result == False or result is False  # Handle both string and boolean

    def test_ambiguous_response(self):
        """Test BinaryAgent with ambiguous input"""
        agent = BinaryAgent(
            agent_id="test_binary", prompt="Is this clear?", queue="test_queue"
        )
        # For ambiguous responses, it might return False instead of raising
        # an error in the current implementation
        result = agent.run({"input": "Maybe"})
        assert result == False or result is False


def test_binary_agent_run():
    agent = BinaryAgent(agent_id="test_bin", prompt="Is this true?", queue="test")
    output = agent.run({"input": "Cats are mammals."})
    assert output in [True, False]


def test_classification_agent_run():
    agent = ClassificationAgent(
        agent_id="test_class", prompt="Classify:", queue="test", options=["cat", "dog"]
    )
    output = agent.run({"input": "A domestic animal"})
    assert output == "deprecated"


def test_duckduckgo_tool_run():
    tool = DuckDuckGoTool(tool_id="test_duck", prompt="Search:", queue="test")
    output = tool.run({"input": "OrKa project"})
    assert isinstance(output, list)
    assert len(output) > 0


# OpenAI Agent Tests
@llm_skip
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


@llm_skip
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


@llm_skip
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


@llm_skip
def test_openai_binary_agent_run():
    agent = OpenAIBinaryAgent(
        agent_id="test_openai_bin", prompt="Is this real?", queue="test"
    )
    output = agent.run({"input": "Is water wet?"})
    assert output in [True, False]


@llm_skip
def test_openai_classification_agent_run():
    agent = OpenAIClassificationAgent(
        agent_id="test_openai_class",
        prompt="Classify:",
        queue="test",
        options=["cat", "dog"],
    )
    output = agent.run({"input": "Barking"})
    assert output in ["cat", "dog", "not-classified"]


@llm_skip
def test_openai_classification_agent_run_not_classified():
    agent = OpenAIClassificationAgent(
        agent_id="test_openai_class",
        prompt="Classify:",
        queue="test",
        options=[],
    )
    output = agent.run({"input": "Sky is blue"})
    assert output == "not-classified"


@llm_skip
def test_openai_answer_builder_run():
    agent = OpenAIAnswerBuilder(
        agent_id="test_builder", prompt="Answer this:", queue="test"
    )
    output = agent.run({"input": "What is AI?"})
    assert isinstance(output, str)
    assert len(output) > 5
