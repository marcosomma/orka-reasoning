"""
Unit tests for the orka.agents module.
Tests agent initialization, execution, and error handling with mocked dependencies.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.agents.agents import BinaryAgent, ClassificationAgent
from orka.agents.base_agent import BaseAgent, LegacyBaseAgent
from orka.agents.llm_agents import (
    OpenAIAnswerBuilder,
    OpenAIBinaryAgent,
    OpenAIClassificationAgent,
    _build_response_dict,
    _calculate_openai_cost,
    _extract_json_content,
    _extract_reasoning,
    _parse_json_safely,
    parse_llm_json_response,
)


class TestBaseAgent:
    """Test the BaseAgent class functionality."""

    def test_base_agent_initialization(self):
        """Test BaseAgent initialization with basic parameters."""
        agent = BaseAgent(
            agent_id="test_agent",
            timeout=60.0,
            max_concurrency=5,
        )

        assert agent.agent_id == "test_agent"
        assert agent.timeout == 60.0
        assert agent.type == "baseagent"
        assert not agent._initialized
        # ConcurrencyManager doesn't expose max_concurrency directly
        assert agent.concurrency.semaphore._value == 5

    def test_base_agent_initialization_with_registry(self):
        """Test BaseAgent initialization with registry."""
        mock_registry = {"llm": "mock_llm", "embedder": "mock_embedder"}

        agent = BaseAgent(
            agent_id="registry_agent",
            registry=mock_registry,
            prompt="test prompt",
            queue=["queue1", "queue2"],
        )

        assert agent.registry == mock_registry
        assert agent.prompt == "test prompt"
        assert agent.queue == ["queue1", "queue2"]

    @pytest.mark.asyncio
    async def test_base_agent_initialize(self):
        """Test agent initialization method."""
        agent = BaseAgent(agent_id="init_test")

        assert not agent._initialized
        await agent.initialize()
        assert agent._initialized

        # Should be idempotent
        await agent.initialize()
        assert agent._initialized

    @pytest.mark.asyncio
    async def test_base_agent_run_modern_pattern(self):
        """Test BaseAgent run with modern context pattern."""

        class TestAgent(BaseAgent):
            async def _run_impl(self, ctx):
                return {"processed": ctx["input"], "agent": self.agent_id}

        agent = TestAgent(agent_id="modern_agent")

        # Test with context dict
        result = await agent.run({"input": "test input", "user_id": "123"})

        assert result["status"] == "success"
        assert result["result"]["processed"] == "test input"
        assert result["result"]["agent"] == "modern_agent"
        assert result["metadata"]["agent_id"] == "modern_agent"
        # trace_id is added to context, not returned in output
        assert "trace_id" not in result

    @pytest.mark.asyncio
    async def test_base_agent_run_with_simple_input(self):
        """Test BaseAgent run with simple input conversion."""

        class TestAgent(BaseAgent):
            async def _run_impl(self, ctx):
                return f"Processed: {ctx['input']}"

        agent = TestAgent(agent_id="simple_agent")

        # Test with simple string input
        result = await agent.run("simple input")

        assert result["status"] == "success"
        assert result["result"] == "Processed: simple input"

    @pytest.mark.asyncio
    async def test_base_agent_run_with_error(self):
        """Test BaseAgent run with error handling."""

        class FailingAgent(BaseAgent):
            async def _run_impl(self, ctx):
                raise ValueError("Test error")

        agent = FailingAgent(agent_id="failing_agent")

        result = await agent.run({"input": "test"})

        assert result["status"] == "error"
        assert result["result"] is None
        assert "Test error" in str(result["error"])

    @pytest.mark.asyncio
    async def test_base_agent_run_legacy_pattern(self):
        """Test BaseAgent run with legacy agent pattern."""

        class LegacyTestAgent(LegacyBaseAgent):
            def run(self, input_data):
                return f"Legacy: {input_data}"

        agent = LegacyTestAgent(agent_id="legacy_agent", prompt="test", queue=[])

        # Legacy agents use sync run method
        result = agent.run("legacy input")
        assert result == "Legacy: legacy input"

    @pytest.mark.asyncio
    async def test_base_agent_cleanup(self):
        """Test agent cleanup method."""
        agent = BaseAgent(agent_id="cleanup_test")

        # Should not raise any errors
        await agent.cleanup()

    def test_base_agent_repr(self):
        """Test BaseAgent string representation."""
        agent = BaseAgent(agent_id="repr_test", timeout=45.0)

        repr_str = repr(agent)
        assert "BaseAgent" in repr_str
        assert "repr_test" in repr_str

    @pytest.mark.asyncio
    async def test_base_agent_with_timeout(self):
        """Test BaseAgent timeout handling."""

        class SlowAgent(BaseAgent):
            async def _run_impl(self, ctx):
                await asyncio.sleep(0.1)  # Simulate slow operation
                return "completed"

        agent = SlowAgent(agent_id="slow_agent", timeout=0.05)  # Very short timeout

        result = await agent.run({"input": "test"})

        # Should handle timeout gracefully
        assert result["status"] == "error"


class TestLegacyBaseAgent:
    """Test the LegacyBaseAgent class functionality."""

    def test_legacy_base_agent_initialization(self):
        """Test LegacyBaseAgent initialization."""

        class TestLegacyAgent(LegacyBaseAgent):
            def run(self, input_data):
                return "test result"

        agent = TestLegacyAgent(
            agent_id="legacy_test",
            prompt="test prompt",
            queue=["q1", "q2"],
            custom_param="value",
        )

        assert agent.agent_id == "legacy_test"
        assert agent.prompt == "test prompt"
        assert agent.queue == ["q1", "q2"]
        assert agent.params["custom_param"] == "value"

    def test_legacy_base_agent_is_legacy(self):
        """Test legacy agent identification."""

        class TestLegacyAgent(LegacyBaseAgent):
            def run(self, input_data):
                return "test"

        agent = TestLegacyAgent("legacy", "prompt", [])
        assert agent._is_legacy_agent() is True

    def test_legacy_base_agent_abstract_run(self):
        """Test that LegacyBaseAgent requires run implementation."""

        # Should not be able to instantiate without run method
        with pytest.raises(TypeError):
            LegacyBaseAgent("test", "prompt", [])


class TestBinaryAgent:
    """Test the BinaryAgent class functionality."""

    def test_binary_agent_initialization(self):
        """Test BinaryAgent initialization."""
        agent = BinaryAgent(agent_id="binary_test", prompt="test", queue=[])

        assert agent.agent_id == "binary_test"
        assert isinstance(agent, LegacyBaseAgent)

    def test_binary_agent_positive_cases(self):
        """Test BinaryAgent with positive inputs."""
        agent = BinaryAgent(agent_id="binary_pos", prompt="test", queue=[])

        test_cases = [
            {"input": "yes, this is correct"},
            {"input": "true statement"},
            {"input": "that's correct"},
            {"input": "YES INDEED"},
            {"input": {"input": "yes it is"}},  # Nested input
        ]

        for case in test_cases:
            result = agent.run(case)
            assert result is True, f"Failed for case: {case}"

    def test_binary_agent_negative_cases(self):
        """Test BinaryAgent with negative inputs."""
        agent = BinaryAgent(agent_id="binary_neg", prompt="test", queue=[])

        test_cases = [
            {"input": "no, this is wrong"},
            {"input": "false statement"},
            {"input": "maybe not"},
            {"input": ""},  # Empty input
            {},  # No input key
        ]

        for case in test_cases:
            result = agent.run(case)
            assert result is False, f"Failed for case: {case}"

    def test_binary_agent_edge_cases(self):
        """Test BinaryAgent with edge cases."""
        agent = BinaryAgent(agent_id="binary_edge", prompt="test", queue=[])

        # Test with None input - this will fail in current implementation
        with pytest.raises(AttributeError):
            agent.run({"input": None})

        # Test with numeric input - this will also fail in current implementation
        with pytest.raises(AttributeError):
            agent.run({"input": 123})

        # Test with mixed case
        result = agent.run({"input": "Yes, TRUE and Correct"})
        assert result is True

        # Test "incorrect" should return True because it contains "correct"
        result = agent.run({"input": "incorrect answer"})
        assert result is True  # This is the actual behavior


class TestClassificationAgent:
    """Test the ClassificationAgent class functionality."""

    def test_classification_agent_initialization(self):
        """Test ClassificationAgent initialization."""
        agent = ClassificationAgent(agent_id="class_test", prompt="test", queue=[])

        assert agent.agent_id == "class_test"
        assert isinstance(agent, LegacyBaseAgent)

    def test_classification_agent_deprecated(self):
        """Test ClassificationAgent returns deprecated message."""
        agent = ClassificationAgent(agent_id="class_dep", prompt="test", queue=[])

        result = agent.run({"input": "any input"})
        assert result == "deprecated"


class TestLLMAgentFunctions:
    """Test LLM agent utility functions."""

    def test_extract_reasoning_with_think_blocks(self):
        """Test reasoning extraction from <think> blocks."""
        text_with_thinking = """
        <think>
        I need to analyze this carefully.
        The user is asking about X.
        </think>
        Here is my final answer.
        """

        reasoning, cleaned = _extract_reasoning(text_with_thinking)

        assert "analyze this carefully" in reasoning
        assert "Here is my final answer." in cleaned
        assert "<think>" not in cleaned

    def test_extract_reasoning_without_think_blocks(self):
        """Test reasoning extraction when no <think> blocks present."""
        text_without_thinking = "Just a regular response"

        reasoning, cleaned = _extract_reasoning(text_without_thinking)

        assert reasoning == ""
        assert cleaned == "Just a regular response"

    def test_extract_json_content_from_code_blocks(self):
        """Test JSON extraction from markdown code blocks."""
        text_with_json = """
        Here's the result:
        ```json
        {"answer": "test", "confidence": 0.9}
        ```
        """

        json_content = _extract_json_content(text_with_json)
        assert '{"answer": "test", "confidence": 0.9}' in json_content

    def test_extract_json_content_from_braces(self):
        """Test JSON extraction from text with braces."""
        text_with_braces = 'The result is {"status": "success", "value": 42} as shown.'

        json_content = _extract_json_content(text_with_braces)
        assert json_content == '{"status": "success", "value": 42}'

    def test_parse_json_safely_valid(self):
        """Test safe JSON parsing with valid JSON."""
        valid_json = '{"key": "value", "number": 123}'

        result = _parse_json_safely(valid_json)
        assert result == {"key": "value", "number": 123}

    def test_parse_json_safely_invalid(self):
        """Test safe JSON parsing with invalid JSON."""
        invalid_json = '{"key": "value", "missing_quote: 123}'

        result = _parse_json_safely(invalid_json)
        # Should return None for completely invalid JSON
        assert result is None

    def test_build_response_dict_perfect_structure(self):
        """Test response dict building with perfect JSON structure."""
        perfect_json = {
            "response": "The answer is 42",
            "confidence": "0.95",
            "internal_reasoning": "Based on calculation",
        }

        result = _build_response_dict(perfect_json, "fallback")

        assert result["response"] == "The answer is 42"
        assert result["confidence"] == "0.95"
        assert result["internal_reasoning"] == "Based on calculation"

    def test_build_response_dict_task_description_structure(self):
        """Test response dict building with task_description structure."""
        task_desc_json = {
            "task_description": {
                "response": "Task completed",
                "confidence": "0.8",
            },
        }

        result = _build_response_dict(task_desc_json, "fallback")

        assert result["response"] == "Task completed"
        assert result["confidence"] == "0.8"

    def test_build_response_dict_fallback(self):
        """Test response dict building with fallback."""
        invalid_json = None
        fallback_text = "This is the fallback response"

        result = _build_response_dict(invalid_json, fallback_text)

        assert result["response"] == fallback_text
        assert result["confidence"] == "0.3"
        assert "Could not parse" in result["internal_reasoning"]

    def test_parse_llm_json_response_complete(self):
        """Test complete LLM JSON response parsing."""
        response_text = """
        <think>Let me think about this</think>
        ```json
        {"response": "Final answer", "confidence": "0.9", "internal_reasoning": "My logic"}
        ```
        """

        result = parse_llm_json_response(response_text)

        assert result["response"] == "Final answer"
        assert result["confidence"] == "0.9"
        # The function appends reasoning from <think> blocks
        assert "My logic" in result["internal_reasoning"]
        assert "Let me think about this" in result["internal_reasoning"]

    def test_parse_llm_json_response_empty(self):
        """Test LLM JSON response parsing with empty input."""
        result = parse_llm_json_response("")

        assert result["response"] == ""
        assert result["confidence"] == "0.0"
        assert result["internal_reasoning"] == "Empty or invalid response"

    def test_calculate_openai_cost(self):
        """Test OpenAI cost calculation."""
        # Test GPT-4 pricing
        cost = _calculate_openai_cost("gpt-4", 1000, 500)
        assert cost > 0

        # Test GPT-3.5 pricing (should be cheaper)
        cost_35 = _calculate_openai_cost("gpt-3.5-turbo", 1000, 500)
        assert cost_35 > 0
        assert cost_35 < cost  # Should be cheaper than GPT-4

        # Test unknown model - might return default pricing rather than 0
        cost_unknown = _calculate_openai_cost("unknown-model", 1000, 500)
        assert isinstance(cost_unknown, (int, float))  # Should return a number


@patch("orka.agents.llm_agents.client")  # Mock the OpenAI client
class TestOpenAIAgents:
    """Test OpenAI agent classes with mocked API calls."""

    def test_openai_answer_builder_initialization(self, mock_client):
        """Test OpenAIAnswerBuilder initialization."""
        agent = OpenAIAnswerBuilder(
            agent_id="answer_builder",
            prompt="Answer this: {{ input }}",
            queue=[],
        )

        assert agent.agent_id == "answer_builder"
        assert "{{ input }}" in agent.prompt

    @pytest.mark.asyncio
    async def test_openai_answer_builder_run(self, mock_client):
        """Test OpenAIAnswerBuilder run method."""
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {"response": "Test answer", "confidence": "0.9", "internal_reasoning": "Logic"}
        """
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = OpenAIAnswerBuilder(
            agent_id="test_answer",
            prompt="Answer: {{ input }}",
            queue=[],
        )

        result = await agent.run({"input": "What is 2+2?"})

        assert isinstance(result, dict)
        assert "response" in result
        mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_binary_agent_run(self, mock_client):
        """Test OpenAIBinaryAgent run method."""
        # Mock the OpenAI response for true case
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {"response": "true", "confidence": "0.9", "internal_reasoning": "Clear yes"}
        """
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = OpenAIBinaryAgent(
            agent_id="test_binary",
            prompt="Is this true: {{ input }}",
            queue=[],
        )

        result = await agent.run({"input": "The sky is blue"})

        assert isinstance(result, dict)
        assert result["response"] is True

    @pytest.mark.asyncio
    async def test_openai_binary_agent_false_response(self, mock_client):
        """Test OpenAIBinaryAgent with false response."""
        # Mock the OpenAI response for false case
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {"response": "false", "confidence": "0.8", "internal_reasoning": "Clear no"}
        """
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = OpenAIBinaryAgent(
            agent_id="test_binary_false",
            prompt="Is this true: {{ input }}",
            queue=[],
        )

        result = await agent.run({"input": "1+1=3"})

        assert isinstance(result, dict)
        assert result["response"] is False

    @pytest.mark.asyncio
    async def test_openai_classification_agent_run(self, mock_client):
        """Test OpenAIClassificationAgent run method."""
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {"response": "urgent", "confidence": "0.95", "internal_reasoning": "Contains urgent keywords"}
        """
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = OpenAIClassificationAgent(
            agent_id="test_classifier",
            prompt="Classify: {{ input }}",
            queue=[],
            options=["urgent", "normal", "low"],
        )

        result = await agent.run({"input": "URGENT: Server is down!"})

        assert isinstance(result, dict)
        assert result["response"] == "urgent"

    @pytest.mark.asyncio
    async def test_openai_agent_with_api_error(self, mock_client):
        """Test OpenAI agent behavior with API errors."""
        # Mock an API error
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        agent = OpenAIAnswerBuilder(
            agent_id="error_test",
            prompt="Test: {{ input }}",
            queue=[],
        )

        # The error is not caught in the current implementation
        with pytest.raises(Exception):
            await agent.run({"input": "test"})

    @pytest.mark.asyncio
    async def test_openai_agent_with_malformed_response(self, mock_client):
        """Test OpenAI agent with malformed JSON response."""
        # Mock malformed response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not JSON at all"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = OpenAIAnswerBuilder(
            agent_id="malformed_test",
            prompt="Answer: {{ input }}",
            queue=[],
        )

        result = await agent.run({"input": "test"})

        # Should handle malformed response gracefully
        assert isinstance(result, dict)
        assert "response" in result
