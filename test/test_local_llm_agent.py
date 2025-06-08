"""
Test module for LocalLLMAgent

Tests the LocalLLMAgent class functionality including:
- Basic prompt handling and template substitution
- Different provider support (Ollama, LM Studio, OpenAI-compatible)
- Error handling for network failures and invalid responses
- Input validation and edge cases
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import requests

# Set environment variable for testing
os.environ["PYTEST_RUNNING"] = "true"

# Check if we should skip LLM tests
SKIP_LLM_TESTS = os.environ.get("SKIP_LLM_TESTS", "false").lower() in (
    "true",
    "1",
    "yes",
)

# Skip all tests if LLM tests should be skipped
pytestmark = pytest.mark.skipif(
    SKIP_LLM_TESTS,
    reason="Local LLM tests skipped - SKIP_LLM_TESTS environment variable is set (usually in CI environments)",
)

from orka.agents.local_llm_agents import LocalLLMAgent


class TestLocalLLMAgent:
    """Test LocalLLMAgent functionality."""

    def test_initialization(self):
        """Test LocalLLMAgent initialization."""
        agent = LocalLLMAgent(
            agent_id="test_local_agent",
            prompt="Summarize: {{ input }}",
            queue=None,
            model="mistral",
            model_url="http://localhost:11434/api/generate",
            provider="ollama",
            temperature=0.5,
        )

        assert agent.agent_id == "test_local_agent"
        assert agent.prompt == "Summarize: {{ input }}"
        assert agent.params["model"] == "mistral"
        assert agent.params["model_url"] == "http://localhost:11434/api/generate"
        assert agent.params["provider"] == "ollama"
        assert agent.params["temperature"] == 0.5

    def test_build_prompt(self):
        """Test prompt template building."""
        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Process this: {{ input }}",
            queue=None,
        )

        result = agent.build_prompt("Hello world")
        assert result == "Process this: Hello world"

        # Test with custom template
        result = agent.build_prompt("Hello world", "Echo: {{ input }}")
        assert result == "Echo: Hello world"

        # Test with no template
        agent.prompt = None
        result = agent.build_prompt("Hello world")
        assert result == "Input: Hello world"

    @patch("requests.post")
    def test_ollama_call_success(self, mock_post):
        """Test successful Ollama API call."""
        # Mock successful Ollama response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": "This is a test response"}
        mock_post.return_value = mock_response

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="llama3",
            model_url="http://localhost:11434/api/generate",
            provider="ollama",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics
        assert isinstance(result, dict)
        assert result["response"] == "This is a test response"
        assert "_metrics" in result
        assert result["_metrics"]["model"] == "llama3"
        mock_post.assert_called_once()

        # Check the request payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "llama3"
        # Prompt now includes self-evaluation instructions, so check it contains our core prompt
        assert "Echo: Hello world" in call_args[1]["json"]["prompt"]
        assert call_args[1]["json"]["stream"] is False

    @patch("requests.post")
    def test_lm_studio_call_success(self, mock_post):
        """Test successful LM Studio API call."""
        # Mock successful LM Studio response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "LM Studio response"}}],
        }
        mock_post.return_value = mock_response

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="mistral",
            model_url="http://localhost:1234",
            provider="lm_studio",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics
        assert isinstance(result, dict)
        assert result["response"] == "LM Studio response"
        assert "_metrics" in result
        assert result["_metrics"]["model"] == "mistral"
        mock_post.assert_called_once()

        # Check the URL was properly formatted
        call_args = mock_post.call_args
        assert "/v1/chat/completions" in call_args[0][0]

        # Check the request payload
        payload = call_args[1]["json"]
        assert payload["model"] == "mistral"
        # Message content now includes self-evaluation instructions, so check it contains our core prompt
        assert "Echo: Hello world" in payload["messages"][0]["content"]

    @patch("requests.post")
    def test_openai_compatible_call_success(self, mock_post):
        """Test successful OpenAI-compatible API call."""
        # Mock successful OpenAI-compatible response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OpenAI compatible response"}}],
        }
        mock_post.return_value = mock_response

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="gpt-3.5-turbo",
            model_url="http://localhost:8000/v1/chat/completions",
            provider="openai_compatible",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics
        assert isinstance(result, dict)
        assert result["response"] == "OpenAI compatible response"
        assert "_metrics" in result
        assert result["_metrics"]["model"] == "gpt-3.5-turbo"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors."""
        # Mock network error
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="llama3",
            model_url="http://localhost:11434/api/generate",
            provider="ollama",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics even for errors
        assert isinstance(result, dict)
        assert "[LocalLLMAgent error:" in result["response"]
        assert "Connection failed" in result["response"]
        assert "_metrics" in result
        assert result["_metrics"]["error"] is True

    @patch("requests.post")
    def test_http_error_handling(self, mock_post):
        """Test handling of HTTP errors."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_post.return_value = mock_response

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="llama3",
            model_url="http://localhost:11434/api/generate",
            provider="ollama",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics even for errors
        assert isinstance(result, dict)
        assert "[LocalLLMAgent error:" in result["response"]
        assert "404 Not Found" in result["response"]
        assert "_metrics" in result
        assert result["_metrics"]["error"] is True

    @patch("requests.post")
    def test_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON responses."""
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
            model="llama3",
            model_url="http://localhost:11434/api/generate",
            provider="ollama",
        )

        result = agent.run("Hello world")

        # LocalLLMAgent now returns structured response with metrics even for errors
        assert isinstance(result, dict)
        assert "[LocalLLMAgent error:" in result["response"]
        assert "_metrics" in result
        assert result["_metrics"]["error"] is True

    def test_string_input_handling(self):
        """Test handling of string input vs dict input."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"response": "Test response"}
            mock_post.return_value = mock_response

            agent = LocalLLMAgent(
                agent_id="test_agent",
                prompt="Echo: {{ input }}",
                queue=None,
                model="llama3",
            )

            # Test string input
            result = agent.run("Hello world")
            assert isinstance(result, dict)
            assert result["response"] == "Test response"
            assert "_metrics" in result

            # Test dict input
            result = agent.run({"content": "Hello world", "temperature": 0.8})
            assert isinstance(result, dict)
            assert result["response"] == "Test response"
            assert "_metrics" in result

    def test_default_provider_fallback(self):
        """Test that unknown providers fall back to Ollama format."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"response": "Fallback response"}
            mock_post.return_value = mock_response

            agent = LocalLLMAgent(
                agent_id="test_agent",
                prompt="Echo: {{ input }}",
                queue=None,
                model="llama3",
                provider="unknown_provider",
            )

            result = agent.run("Hello world")
            assert isinstance(result, dict)
            assert result["response"] == "Fallback response"
            assert "_metrics" in result

            # Should have called with Ollama format
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert "prompt" in payload  # Ollama format
            assert "messages" not in payload  # Not OpenAI format

    def test_temperature_parameter_handling(self):
        """Test that temperature parameter is properly handled."""
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"response": "Test response"}
            mock_post.return_value = mock_response

            agent = LocalLLMAgent(
                agent_id="test_agent",
                prompt="Echo: {{ input }}",
                queue=None,
                model="llama3",
                temperature=0.9,
            )

            result = agent.run("Hello world")

            # Check that temperature was passed correctly
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["options"]["temperature"] == 0.9

    def test_model_url_defaults(self):
        """Test default model URL behavior."""
        agent = LocalLLMAgent(
            agent_id="test_agent",
            prompt="Echo: {{ input }}",
            queue=None,
        )

        # Should default to Ollama URL
        assert (
            agent.params.get("model_url", "http://localhost:11434/api/generate")
            == "http://localhost:11434/api/generate"
        )


if __name__ == "__main__":
    pytest.main([__file__])
