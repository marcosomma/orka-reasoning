# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for LLMProviderMixin."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from orka.orchestrator.dry_run.llm_providers import LLMProviderMixin


class ConcreteLLMProvider(LLMProviderMixin):
    """Concrete implementation for testing."""

    pass


class TestLLMProviderMixin:
    """Tests for LLMProviderMixin."""

    @pytest.fixture
    def provider(self):
        """Create a LLMProviderMixin instance."""
        return ConcreteLLMProvider()

    def test_extract_json_from_response_valid(self, provider):
        """Test extracting valid JSON from response."""
        response = '{"key": "value", "number": 42}'

        with patch(
            "orka.orchestrator.dry_run.llm_providers.extract_json_from_text",
            return_value='{"key": "value", "number": 42}',
        ):
            result = provider._extract_json_from_response(response)

        assert result == '{"key": "value", "number": 42}'

    def test_extract_json_from_response_with_text(self, provider):
        """Test extracting JSON wrapped in text."""
        response = 'Here is the result: {"key": "value"} done'

        with patch(
            "orka.orchestrator.dry_run.llm_providers.extract_json_from_text",
            return_value='{"key": "value"}',
        ):
            result = provider._extract_json_from_response(response)

        assert result == '{"key": "value"}'

    def test_extract_json_from_response_needs_repair(self, provider):
        """Test extracting JSON that needs repair."""
        response = "{'key': 'value'}"  # Single quotes need repair

        with patch(
            "orka.orchestrator.dry_run.llm_providers.extract_json_from_text",
            return_value=None,
        ):
            with patch(
                "orka.orchestrator.dry_run.llm_providers.repair_malformed_json",
                return_value='{"key": "value"}',
            ):
                result = provider._extract_json_from_response(response)

        assert result == '{"key": "value"}'

    def test_extract_json_from_response_no_json(self, provider):
        """Test when response has no JSON."""
        response = "This is just plain text with no JSON"

        with patch(
            "orka.orchestrator.dry_run.llm_providers.extract_json_from_text",
            return_value=None,
        ):
            with patch(
                "orka.orchestrator.dry_run.llm_providers.repair_malformed_json",
                return_value=None,
            ):
                result = provider._extract_json_from_response(response)

        assert result is None

    @pytest.mark.asyncio
    async def test_call_ollama_async_connection_error(self, provider):
        """Test Ollama API call with connection error."""
        import aiohttp

        with patch(
            "orka.orchestrator.dry_run.llm_providers.aiohttp.ClientSession"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = aiohttp.ClientError(
                "Connection refused"
            )

            with pytest.raises(RuntimeError) as exc_info:
                await provider._call_ollama_async(
                    "http://localhost:11434/api/generate",
                    "llama2",
                    "test prompt",
                    0.1,
                )

            assert "connection error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_ollama_async_timeout(self, provider):
        """Test Ollama API call timeout handling."""
        with patch(
            "orka.orchestrator.dry_run.llm_providers.aiohttp.ClientSession"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = asyncio.TimeoutError()

            with pytest.raises(RuntimeError) as exc_info:
                await provider._call_ollama_async(
                    "http://localhost:11434/api/generate",
                    "llama2",
                    "test prompt",
                    0.1,
                )

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_call_lm_studio_async_general_error(self, provider):
        """Test LM Studio API call with general error."""
        with patch(
            "orka.orchestrator.dry_run.llm_providers.aiohttp.ClientSession"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception("Test error")

            with pytest.raises(Exception) as exc_info:
                await provider._call_lm_studio_async(
                    "http://localhost:1234",
                    "gpt-model",
                    "test prompt",
                    0.0,
                )

            assert "Test error" in str(exc_info.value)

