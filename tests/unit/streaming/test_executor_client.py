"""Unit tests for orka.streaming.executor_client (OpenAICompatClient)."""

import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from orka.streaming.executor_client import OpenAICompatClient

pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestOpenAICompatClient:
    """Test suite for OpenAICompatClient class."""

    def test_init_with_defaults(self):
        """Test client initialization with default values."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        assert client.base_url == "http://localhost:1234"
        assert client.api_key == "sk-no-key"
        assert client.timeout == 30.0

    def test_init_with_custom_values(self):
        """Test client initialization with custom values."""
        client = OpenAICompatClient(
            base_url="https://api.example.com/",
            api_key="custom-key-123",
            timeout=60.0
        )
        
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "custom-key-123"
        assert client.timeout == 60.0

    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are removed from base_url."""
        client = OpenAICompatClient(base_url="http://localhost:1234///")
        assert client.base_url == "http://localhost:1234"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """Test successful non-streaming completion."""
        client = OpenAICompatClient(base_url="http://localhost:1234", api_key="test-key")
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a test response"}}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.complete(
                model="gpt-4",
                system="You are a helpful assistant",
                user="Hello, how are you?"
            )
            
            assert result == "This is a test response"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://localhost:1234/v1/chat/completions"
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"
            assert call_args[1]["json"]["model"] == "gpt-4"
            assert call_args[1]["json"]["stream"] is False

    @pytest.mark.asyncio
    async def test_complete_with_null_content(self):
        """Test completion when content is None."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": None}}
            ]
        }
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.complete(
                model="gpt-4",
                system="System prompt",
                user="User prompt"
            )
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_complete_with_malformed_response(self):
        """Test completion with malformed response structure."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid response"}
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await client.complete(
                model="gpt-4",
                system="System prompt",
                user="User prompt"
            )
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_complete_http_error(self):
        """Test completion when HTTP error occurs."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=Mock(),
            response=Mock()
        )
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.complete(
                    model="gpt-4",
                    system="System prompt",
                    user="User prompt"
                )

    @pytest.mark.asyncio
    async def test_stream_complete_success(self):
        """Test successful streaming completion."""
        client = OpenAICompatClient(base_url="http://localhost:1234", api_key="test-key")
        
        # Simulate SSE stream lines
        stream_lines = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"}}]}',
            'data: {"choices":[{"delta":{"content":"!"}}]}',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="You are helpful",
                user="Say hello"
            ):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " world", "!"]
            mock_client.stream.assert_called_once()
            call_args = mock_client.stream.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "http://localhost:1234/v1/chat/completions"
            assert call_args[1]["json"]["stream"] is True

    @pytest.mark.asyncio
    async def test_stream_complete_with_empty_lines(self):
        """Test streaming with empty lines (should be skipped)."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = [
            '',
            'data: {"choices":[{"delta":{"content":"Test"}}]}',
            '',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == ["Test"]

    @pytest.mark.asyncio
    async def test_stream_complete_with_non_data_lines(self):
        """Test streaming with lines that don't start with 'data: '."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = [
            'event: message',
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'retry: 1000',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == ["Hello"]

    @pytest.mark.asyncio
    async def test_stream_complete_with_malformed_json(self):
        """Test streaming with malformed JSON (should be skipped)."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = [
            'data: {"choices":[{"delta":{"content":"Valid"}}]}',
            'data: {invalid json}',
            'data: {"choices":[{"delta":{"content":"Also valid"}}]}',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == ["Valid", "Also valid"]

    @pytest.mark.asyncio
    async def test_stream_complete_with_no_content(self):
        """Test streaming when delta has no content field."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = [
            'data: {"choices":[{"delta":{"role":"assistant"}}]}',
            'data: {"choices":[{"delta":{"content":"Text"}}]}',
            'data: {"choices":[{"delta":{}}]}',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == ["Text"]

    @pytest.mark.asyncio
    async def test_stream_complete_with_multiple_choices(self):
        """Test streaming with multiple choices (should yield all content)."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = [
            'data: {"choices":[{"delta":{"content":"First"}},{"delta":{"content":"Second"}}]}',
            'data: [DONE]',
        ]
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == ["First", "Second"]

    @pytest.mark.asyncio
    async def test_stream_complete_http_error(self):
        """Test streaming when HTTP error occurs."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=Mock(),
            response=Mock()
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(httpx.HTTPStatusError):
                async for _ in client.stream_complete(
                    model="gpt-4",
                    system="System",
                    user="User"
                ):
                    pass

    @pytest.mark.asyncio
    async def test_stream_complete_empty_stream(self):
        """Test streaming with no data chunks."""
        client = OpenAICompatClient(base_url="http://localhost:1234")
        
        stream_lines = ['data: [DONE]']
        
        async def mock_aiter_lines():
            for line in stream_lines:
                yield line
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.stream = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            chunks = []
            async for chunk in client.stream_complete(
                model="gpt-4",
                system="System",
                user="User"
            ):
                chunks.append(chunk)
            
            assert chunks == []

    @pytest.mark.asyncio
    async def test_complete_uses_correct_timeout(self):
        """Test that complete method respects timeout parameter."""
        client = OpenAICompatClient(
            base_url="http://localhost:1234",
            timeout=120.0
        )
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await client.complete(model="gpt-4", system="Sys", user="User")
            
            # Verify AsyncClient was instantiated with correct timeout
            mock_client_class.assert_called_once_with(timeout=120.0)
