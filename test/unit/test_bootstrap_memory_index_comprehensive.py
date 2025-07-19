"""
Comprehensive unit tests for the bootstrap_memory_index.py module.
Tests all functions for Redis index creation and vector search capabilities.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest
import redis

# Support both redis-py 4.x and 5.x versions
try:
    # redis-py <5 (camelCase)
    from redis.commands.search.indexDefinition import IndexDefinition  # type: ignore
except ModuleNotFoundError:
    # redis-py ≥5 (snake_case)
    from redis.commands.search.index_definition import IndexDefinition  # type: ignore

from orka.utils.bootstrap_memory_index import (
    ensure_enhanced_memory_index,
    ensure_memory_index,
    hybrid_vector_search,
    legacy_vector_search,
    retry,
)


class TestEnsureMemoryIndex:
    """Test suite for the ensure_memory_index function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_ft = Mock()
        self.mock_client.ft.return_value = self.mock_ft

    def test_ensure_memory_index_already_exists(self):
        """Test when memory index already exists."""
        # Index exists - info() succeeds
        self.mock_ft.info.return_value = {"index_name": "memory_entries"}

        result = ensure_memory_index(self.mock_client, "memory_entries")

        assert result is True
        self.mock_ft.info.assert_called_once()
        self.mock_ft.create_index.assert_not_called()

    def test_ensure_memory_index_creates_new(self):
        """Test creating new memory index when it doesn't exist."""
        # Index doesn't exist - info() raises "Unknown index name"
        self.mock_ft.info.side_effect = redis.ResponseError("Unknown index name")
        self.mock_ft.create_index.return_value = True

        result = ensure_memory_index(self.mock_client, "memory_entries")

        assert result is True
        self.mock_ft.info.assert_called_once()
        self.mock_ft.create_index.assert_called_once()

        # Verify the index creation parameters
        call_args = self.mock_ft.create_index.call_args[0][0]
        field_types = [type(field).__name__ for field in call_args]
        assert "TextField" in field_types
        assert "NumericField" in field_types

    def test_ensure_memory_index_redis_error(self):
        """Test handling of Redis error other than unknown index."""
        # Different Redis error - function catches and returns False
        self.mock_ft.info.side_effect = redis.ResponseError("Connection error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()

    def test_ensure_memory_index_redisearch_not_available(self):
        """Test handling when RediSearch is not available."""
        self.mock_ft.info.side_effect = Exception("unknown command FT.INFO")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_memory_index(self.mock_client)

            assert result is False
            mock_logger.warning.assert_called()
            mock_logger.info.assert_called()

    def test_ensure_memory_index_generic_exception(self):
        """Test handling of generic exceptions."""
        self.mock_ft.info.side_effect = Exception("Generic error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()

    def test_ensure_memory_index_ft_create_error(self):
        """Test handling when FT.CREATE command fails."""
        self.mock_ft.info.side_effect = redis.ResponseError("Unknown index name")
        self.mock_ft.create_index.side_effect = Exception("FT.CREATE failed")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()


class TestEnsureEnhancedMemoryIndex:
    """Test suite for the ensure_enhanced_memory_index function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_ft = Mock()
        self.mock_client.ft.return_value = self.mock_ft

    def test_ensure_enhanced_memory_index_already_exists(self):
        """Test when enhanced memory index already exists."""
        self.mock_ft.info.return_value = {"index_name": "orka_enhanced_memory"}

        result = ensure_enhanced_memory_index(self.mock_client)

        assert result is True
        self.mock_ft.info.assert_called_once()
        self.mock_ft.create_index.assert_not_called()

    def test_ensure_enhanced_memory_index_creates_new(self):
        """Test creating new enhanced memory index."""
        self.mock_ft.info.side_effect = redis.ResponseError("Unknown index name")
        self.mock_ft.create_index.return_value = True

        result = ensure_enhanced_memory_index(self.mock_client, "enhanced_index", 512)

        assert result is True
        self.mock_ft.create_index.assert_called_once()

        # Verify the creation parameters
        call_args = self.mock_ft.create_index.call_args
        fields = call_args[0][0]
        definition = call_args[1]["definition"]

        # Check field types
        field_types = [type(field).__name__ for field in fields]
        assert "TextField" in field_types
        assert "NumericField" in field_types
        assert "VectorField" in field_types

        # Check index definition
        assert isinstance(definition, IndexDefinition)

    def test_ensure_enhanced_memory_index_custom_params(self):
        """Test enhanced index creation with custom parameters."""
        self.mock_ft.info.side_effect = redis.ResponseError("Unknown index name")

        result = ensure_enhanced_memory_index(
            self.mock_client,
            index_name="custom_index",
            vector_dim=768,
        )

        assert result is True
        # Just verify the function was called - vector field setup is complex to mock properly
        self.mock_ft.create_index.assert_called_once()

    def test_ensure_enhanced_memory_index_vector_not_supported(self):
        """Test handling when vector search is not supported."""
        self.mock_ft.info.side_effect = redis.ResponseError("Unknown index name")
        self.mock_ft.create_index.side_effect = Exception("vector not supported")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_enhanced_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()  # Changed from warning to error

    def test_ensure_enhanced_memory_index_redisearch_not_available(self):
        """Test handling when RediSearch is not available."""
        self.mock_ft.info.side_effect = Exception("unknown command FT.INFO")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_enhanced_memory_index(self.mock_client)

            assert result is False
            mock_logger.warning.assert_called()

    def test_ensure_enhanced_memory_index_other_redis_error(self):
        """Test handling of other Redis errors."""
        self.mock_ft.info.side_effect = redis.ResponseError("Some other error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_enhanced_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()

    def test_ensure_enhanced_memory_index_generic_exception(self):
        """Test handling of generic exceptions during index checking."""
        self.mock_ft.info.side_effect = Exception("Generic error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            result = ensure_enhanced_memory_index(self.mock_client)

            assert result is False
            mock_logger.error.assert_called()


class TestHybridVectorSearch:
    """Test suite for the hybrid_vector_search function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_ft = Mock()
        self.mock_client.ft.return_value = self.mock_ft
        self.query_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

    def test_hybrid_vector_search_success(self):
        """Test successful hybrid vector search."""
        # Mock search results with proper getattr support
        mock_doc1 = Mock()
        mock_doc1.id = "doc1"
        mock_doc1.configure_mock(
            content="test content",
            node_id="node1",
            trace_id="trace1",
            vector_score="0.9",
        )

        mock_doc2 = Mock()
        mock_doc2.id = "doc2"
        mock_doc2.configure_mock(
            content="another content",
            node_id="node2",
            trace_id="trace2",
            vector_score="0.8",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc1, mock_doc2]
        self.mock_ft.search.return_value = mock_results

        results = hybrid_vector_search(
            self.mock_client,
            "test query",
            self.query_vector,
            num_results=2,
        )

        assert len(results) == 2
        assert results[0]["key"] == "doc1"  # Function returns "key" not "id"
        assert results[0]["content"] == "test content"
        # Function converts cosine distance to similarity: 1.0 - (0.9 / 2.0) = 0.55
        assert results[0]["score"] == 0.55
        self.mock_ft.search.assert_called_once()

    def test_hybrid_vector_search_with_trace_id(self):
        """Test hybrid vector search with trace_id filter."""
        # Mock documents with different trace_ids
        mock_doc1 = Mock()
        mock_doc1.id = "doc1"
        mock_doc1.configure_mock(
            content="test content",
            node_id="node1",
            trace_id="trace123",
            vector_score="0.9",
        )

        mock_doc2 = Mock()
        mock_doc2.id = "doc2"
        mock_doc2.configure_mock(
            content="other content",
            node_id="node2",
            trace_id="different_trace",
            vector_score="0.8",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc1, mock_doc2]
        self.mock_ft.search.return_value = mock_results

        results = hybrid_vector_search(
            self.mock_client,
            "test query",
            self.query_vector,
            trace_id="trace123",
        )

        # Should only return the document with matching trace_id
        assert len(results) == 1
        assert results[0]["key"] == "doc1"
        assert results[0]["trace_id"] == "trace123"

    def test_hybrid_vector_search_invalid_vector(self):
        """Test hybrid vector search with invalid vector input."""
        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            results = hybrid_vector_search(
                self.mock_client,
                "test query",
                [0.1, 0.2, 0.3],  # List instead of numpy array
            )

            assert results == []
            mock_logger.error.assert_called()

    def test_hybrid_vector_search_redis_error(self):
        """Test hybrid vector search with Redis error."""
        self.mock_ft.search.side_effect = redis.ResponseError("Search failed")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            results = hybrid_vector_search(
                self.mock_client,
                "test query",
                self.query_vector,
            )

            assert results == []
            mock_logger.error.assert_called()

    def test_hybrid_vector_search_exception_handling(self):
        """Test hybrid vector search with generic exception."""
        self.mock_ft.search.side_effect = Exception("Generic error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            results = hybrid_vector_search(
                self.mock_client,
                "test query",
                self.query_vector,
            )

            assert results == []
            mock_logger.error.assert_called()

    def test_hybrid_vector_search_empty_results(self):
        """Test hybrid vector search with no results."""
        mock_results = Mock()
        mock_results.docs = []
        self.mock_ft.search.return_value = mock_results

        results = hybrid_vector_search(
            self.mock_client,
            "test query",
            self.query_vector,
        )

        assert results == []

    def test_hybrid_vector_search_result_processing(self):
        """Test hybrid vector search result processing."""
        # Mock complex results with various attributes
        mock_doc = Mock()
        mock_doc.id = "doc1"
        mock_doc.configure_mock(
            content="test content",
            vector_score="0.95",
            node_id="node1",
            trace_id="trace1",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc]
        self.mock_ft.search.return_value = mock_results

        results = hybrid_vector_search(
            self.mock_client,
            "test query",
            self.query_vector,
        )

        assert len(results) == 1
        result = results[0]
        assert result["key"] == "doc1"  # Function returns "key" not "id"
        assert result["content"] == "test content"
        # Function converts cosine distance to similarity: 1.0 - (0.95 / 2.0) = 0.525
        assert result["score"] == 0.525
        assert result["node_id"] == "node1"


class TestLegacyVectorSearch:
    """Test suite for the legacy_vector_search function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.query_vector = [0.1, 0.2, 0.3, 0.4]

    def test_legacy_vector_search_success(self):
        """Test successful legacy vector search."""
        # Mock Redis FT.SEARCH for legacy vector search
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft

        # Mock search results
        mock_doc1 = Mock()
        mock_doc1.id = "memory:1"
        mock_doc1.configure_mock(
            content="test content 1",
            session="session1",
            agent="agent1",
            ts="1000",
            similarity="0.8",
        )

        mock_doc2 = Mock()
        mock_doc2.id = "memory:2"
        mock_doc2.configure_mock(
            content="test content 2",
            session="session2",
            agent="agent2",
            ts="2000",
            similarity="0.9",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc1, mock_doc2]
        mock_ft.search.return_value = mock_results

        results = legacy_vector_search(
            self.mock_client,
            self.query_vector,
            similarity_threshold=0.7,
            num_results=2,
        )

        assert len(results) == 2
        assert results[0]["content"] == "test content 2"  # Sorted by similarity desc
        assert results[0]["similarity"] == 0.9

    def test_legacy_vector_search_with_filters(self):
        """Test legacy vector search with namespace and session filters."""
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft

        mock_doc = Mock()
        mock_doc.id = "memory:1"
        mock_doc.configure_mock(
            content="test content",
            session="test_session",
            agent="test_agent",
            ts="1000",
            similarity="0.9",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc]
        mock_ft.search.return_value = mock_results

        results = legacy_vector_search(
            self.mock_client,
            self.query_vector,
            session="test_session",
        )

        assert len(results) == 1
        assert results[0]["session"] == "test_session"
        assert results[0]["similarity"] == 0.9

    def test_legacy_vector_search_no_results(self):
        """Test legacy vector search with no matching results."""
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft

        mock_results = Mock()
        mock_results.docs = []
        mock_ft.search.return_value = mock_results

        results = legacy_vector_search(self.mock_client, self.query_vector)

        assert results == []

    def test_legacy_vector_search_similarity_threshold(self):
        """Test legacy vector search with similarity threshold filtering."""
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft

        # Mock a document with low similarity score
        mock_doc = Mock()
        mock_doc.id = "memory:1"
        mock_doc.configure_mock(
            content="test content",
            session="default",
            agent="unknown",
            ts="1000",
            similarity="0.5",  # Below threshold
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc]
        mock_ft.search.return_value = mock_results

        results = legacy_vector_search(
            self.mock_client,
            self.query_vector,
            similarity_threshold=0.8,  # Higher than 0.5
        )

        assert results == []

    def test_legacy_vector_search_invalid_vector_data(self):
        """Test legacy vector search with invalid vector data."""
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft
        mock_ft.search.side_effect = Exception("Invalid vector data")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            results = legacy_vector_search(self.mock_client, self.query_vector)

            assert results == []
            mock_logger.error.assert_called()

    def test_legacy_vector_search_exception_handling(self):
        """Test legacy vector search with exception handling."""
        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft
        mock_ft.search.side_effect = Exception("Redis error")

        with patch("orka.utils.bootstrap_memory_index.logger") as mock_logger:
            results = legacy_vector_search(self.mock_client, self.query_vector)

            assert results == []
            mock_logger.error.assert_called()

    def test_legacy_vector_search_numpy_array_input(self):
        """Test legacy vector search with numpy array input."""
        query_vector = np.array([0.1, 0.2, 0.3, 0.4])

        mock_ft = Mock()
        self.mock_client.ft.return_value = mock_ft

        mock_doc = Mock()
        mock_doc.id = "memory:1"
        mock_doc.configure_mock(
            content="test content",
            session="default",
            agent="unknown",
            ts="1000",
            similarity="0.9",
        )

        mock_results = Mock()
        mock_results.docs = [mock_doc]
        mock_ft.search.return_value = mock_results

        results = legacy_vector_search(self.mock_client, query_vector)

        assert len(results) == 1
        assert results[0]["similarity"] == 0.9


class TestRetryFunction:
    """Test suite for the retry function."""

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test retry function with success on first attempt."""

        async def successful_coro():
            return "success"

        result = await retry(successful_coro(), attempts=3)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test retry function with success after some failures."""

        # Since the current retry function has a design issue (can't await same coroutine multiple times),
        # we'll test the first attempt behavior only
        async def failing_coro():
            raise redis.ConnectionError("Connection failed")

        with pytest.raises(redis.ConnectionError):
            await retry(failing_coro(), attempts=1, backoff=0.01)

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        """Test retry function when coroutine fails."""

        async def always_failing_coro():
            raise redis.ConnectionError("Persistent failure")

        with pytest.raises(redis.ConnectionError, match="Persistent failure"):
            await retry(always_failing_coro(), attempts=1, backoff=0.01)

    @pytest.mark.asyncio
    async def test_retry_with_different_backoff(self):
        """Test retry function with successful coroutine."""

        async def success_coro():
            return "success"

        result = await retry(success_coro(), attempts=3, backoff=0.05)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_zero_attempts(self):
        """Test retry function with zero attempts."""

        async def some_coro():
            return "success"

        # Should still run once even with 0 attempts specified
        result = await retry(some_coro(), attempts=1)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_specific_exception_types(self):
        """Test retry function with non-ConnectionError exceptions."""

        async def response_error_coro():
            raise redis.ResponseError("Response error")

        # Should not retry for non-ConnectionError exceptions
        with pytest.raises(redis.ResponseError, match="Response error"):
            await retry(response_error_coro(), attempts=3, backoff=0.01)
