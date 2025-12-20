# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
"""Tests for EmbeddingMixin - embedding and content formatting operations."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from orka.memory.redisstack.embedding_mixin import EmbeddingMixin


class MockEmbeddingLogger(EmbeddingMixin):
    """Mock class to test EmbeddingMixin."""

    def __init__(self):
        self.format_params = {}
        self.embedder = None


class TestEmbeddingMixinFormat:
    """Tests for _format_content method."""

    def test_format_content_no_params(self):
        logger = MockEmbeddingLogger()

        result = logger._format_content("Hello\nWorld")

        assert result == "Hello\nWorld"

    def test_format_content_remove_newlines(self):
        logger = MockEmbeddingLogger()
        logger.format_params = {"format_response": True, "preserve_newlines": False}

        result = logger._format_content("Hello\nWorld")

        assert result == "Hello World"

    def test_format_content_preserve_newlines(self):
        logger = MockEmbeddingLogger()
        logger.format_params = {"format_response": True, "preserve_newlines": True}

        result = logger._format_content("Hello\nWorld")

        assert result == "Hello\nWorld"

    def test_format_content_with_replace_filter(self):
        logger = MockEmbeddingLogger()
        logger.format_params = {
            "format_response": True,
            "preserve_newlines": True,
            "format_filters": [
                {"type": "replace", "pattern": "foo", "replacement": "bar"}
            ],
        }

        result = logger._format_content("Hello foo World")

        assert result == "Hello bar World"

    def test_format_content_multiple_filters(self):
        logger = MockEmbeddingLogger()
        logger.format_params = {
            "format_response": True,
            "preserve_newlines": True,
            "format_filters": [
                {"type": "replace", "pattern": "a", "replacement": "X"},
                {"type": "replace", "pattern": "e", "replacement": "Y"},
            ],
        }

        result = logger._format_content("aeiou")

        assert result == "XYiou"

    def test_format_content_error_handling(self):
        logger = MockEmbeddingLogger()
        logger.format_params = {"format_response": True, "format_filters": "invalid"}

        result = logger._format_content("content")

        # Should return original content on error
        assert result == "content"


class TestEmbeddingMixinGetEmbedding:
    """Tests for _get_embedding_sync method."""

    def test_get_embedding_no_event_loop(self):
        logger = MockEmbeddingLogger()
        mock_embedder = MagicMock()
        mock_embedder.embedding_dim = 384
        embedding = np.array([0.1, 0.2, 0.3])

        async def mock_encode(text):
            return embedding

        mock_embedder.encode = mock_encode
        logger.embedder = mock_embedder

        result = logger._get_embedding_sync("test text")

        assert result is not None
        np.testing.assert_array_equal(result, embedding)

    def test_get_embedding_with_fallback(self):
        logger = MockEmbeddingLogger()
        mock_embedder = MagicMock()
        mock_embedder.embedding_dim = 384
        mock_embedder._fallback_encode.return_value = np.array([0.5, 0.5, 0.5])
        logger.embedder = mock_embedder

        # Simulate being in an async context
        with patch("orka.memory.redisstack.embedding_mixin.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.return_value = MagicMock()
            result = logger._get_embedding_sync("test text")

        assert result is not None
        mock_embedder._fallback_encode.assert_called_once_with("test text")

    def test_get_embedding_error_returns_zeros(self):
        logger = MockEmbeddingLogger()
        mock_embedder = MagicMock()
        mock_embedder.embedding_dim = 384

        async def mock_encode(text):
            raise Exception("Embedding failed")

        mock_embedder.encode = mock_encode
        logger.embedder = mock_embedder

        with patch("orka.memory.redisstack.embedding_mixin.asyncio") as mock_asyncio:
            mock_asyncio.get_running_loop.side_effect = RuntimeError("No loop")
            mock_asyncio.run.side_effect = Exception("Failed")
            result = logger._get_embedding_sync("test text")

        assert result is not None
        assert result.shape == (384,)
        assert np.all(result == 0)

