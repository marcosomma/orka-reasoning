"""
Tests for the fixes to the RedisStack vector field configuration and FT.SEARCH issues.
"""

import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
import redis
from redis.commands.search.field import VectorField

from orka.memory.redisstack_logger import RedisStackMemoryLogger
from orka.utils.bootstrap_memory_index import (
    ensure_enhanced_memory_index,
    verify_memory_index,
)


class TestRedisStackVectorFieldFixes:
    """Test suite for the RedisStack vector field configuration fixes."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock embedder
        self.mock_embedder = Mock()
        self.mock_embedder.embedding_dim = 384
        self.mock_embedder.model_name = "test-model"
        self.mock_embedder._fallback_encode = Mock(
            return_value=np.random.rand(384).astype(np.float32),
        )
        self.mock_embedder.encode = Mock(return_value=np.random.rand(384).astype(np.float32))

        # Create mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.ft().info = Mock()
        self.mock_redis.ft().create_index = Mock()
        self.mock_redis.ft().dropindex = Mock()
        self.mock_redis.ft().search = Mock()
        self.mock_redis.hgetall = Mock(return_value={})
        self.mock_redis.keys = Mock(return_value=[])

        # Patch Redis client creation
        self.redis_patcher = patch(
            "orka.memory.redisstack_logger.redis.from_url", return_value=self.mock_redis
        )
        self.redis_patcher.start()

        # Create logger instance with mocks
        self.logger = RedisStackMemoryLogger(
            redis_url="redis://localhost:6379/0",
            index_name="test_index",
            embedder=self.mock_embedder,
            enable_hnsw=True,
            vector_params={"force_recreate": False},
        )

    def teardown_method(self):
        """Clean up after tests."""
        self.redis_patcher.stop()

    def test_verify_index_with_missing_vector_field(self):
        """Test verify_memory_index correctly identifies missing vector field."""
        # Mock index info with missing vector field
        mock_info = {
            "num_docs": 10,
            "attributes": [
                ["identifier", b"content", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"node_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"trace_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"orka_expire_time", "attribute", b"NUMERIC"],
            ],
        }
        self.mock_redis.ft().info.return_value = mock_info

        # Call verify_memory_index
        with patch(
            "orka.utils.bootstrap_memory_index.verify_memory_index", wraps=verify_memory_index
        ) as mock_verify:
            index_info = verify_memory_index(self.mock_redis, "test_index")

            # Verify results
            assert index_info["exists"] is True
            assert index_info["vector_field_exists"] is False
            assert "content" in index_info["fields"]
            assert "content_vector" not in index_info["fields"]

    def test_verify_index_with_vector_field(self):
        """Test verify_memory_index correctly identifies existing vector field."""
        # Mock index info with vector field
        mock_info = {
            "num_docs": 10,
            "attributes": [
                ["identifier", b"content", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"node_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"trace_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"orka_expire_time", "attribute", b"NUMERIC"],
                [
                    "identifier",
                    b"content_vector",
                    "attribute",
                    b"VECTOR",
                    "TYPE",
                    "FLOAT32",
                    "DIM",
                    384,
                    "DISTANCE_METRIC",
                    "COSINE",
                ],
            ],
        }
        self.mock_redis.ft().info.return_value = mock_info

        # Call verify_memory_index
        index_info = verify_memory_index(self.mock_redis, "test_index")

        # Verify results
        assert index_info["exists"] is True
        assert index_info["vector_field_exists"] is True
        assert index_info["vector_field_name"] == "content_vector"

    def test_ensure_index_recreates_when_missing_vector_field(self):
        """Test ensure_enhanced_memory_index recreates index when vector field is missing."""
        # First call to info returns index without vector field
        mock_info_without_vector = {
            "num_docs": 10,
            "attributes": [
                ["identifier", b"content", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"node_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"trace_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"orka_expire_time", "attribute", b"NUMERIC"],
            ],
        }

        # Second call to info returns index with vector field (after recreation)
        mock_info_with_vector = {
            "num_docs": 0,
            "attributes": [
                ["identifier", b"content", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"node_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"trace_id", "attribute", b"TEXT", "WEIGHT", "1"],
                ["identifier", b"orka_expire_time", "attribute", b"NUMERIC"],
                [
                    "identifier",
                    b"content_vector",
                    "attribute",
                    b"VECTOR",
                    "TYPE",
                    "FLOAT32",
                    "DIM",
                    384,
                    "DISTANCE_METRIC",
                    "COSINE",
                ],
            ],
        }

        # Set up mock to return different values on subsequent calls
        self.mock_redis.ft().info.side_effect = [mock_info_without_vector, mock_info_with_vector]

        # Call ensure_enhanced_memory_index with force_recreate=True
        result = ensure_enhanced_memory_index(
            self.mock_redis, index_name="test_index", vector_dim=384, force_recreate=True
        )

        # Verify results
        assert result is True
        self.mock_redis.ft().dropindex.assert_called_once()
        # The create_index is called multiple times due to retries, so we check the last call
        assert self.mock_redis.ft().create_index.call_count >= 1
        last_call = self.mock_redis.ft().create_index.call_args_list[-1]
        assert len(last_call[0][0]) == 5  # Check number of fields
        assert isinstance(last_call[0][0][-1], VectorField)  # Check last field is VectorField

    def test_query_escaping_for_special_characters(self):
        """Test the query escaping functionality for special characters."""
        # Test the _escape_redis_search_query method
        special_query = "test:query with (special) characters & symbols!"
        escaped_query = self.logger._escape_redis_search_query(special_query)

        # Verify all special characters are escaped
        # First check that the escaped sequences are present
        assert "\\:" in escaped_query  # Check that colon is escaped
        assert "\\(" in escaped_query  # Check that parentheses are escaped
        assert "\\)" in escaped_query
        assert "\\&" in escaped_query  # Check that ampersand is escaped
        assert "\\!" in escaped_query  # Check that exclamation mark is escaped

        # Then check that the original string is properly escaped
        assert escaped_query == "test\\:query with \\(special\\) characters \\& symbols\\!"

    def test_search_memories_with_vector_field_missing(self):
        """Test search_memories handles missing vector field gracefully."""
        # Mock verify_memory_index to return index without vector field
        mock_index_info = {
            "exists": True,
            "num_docs": 10,
            "fields": {
                "content": "TEXT",
                "node_id": "TEXT",
                "trace_id": "TEXT",
                "orka_expire_time": "NUMERIC",
            },
            "vector_field_exists": False,
            "content_field_exists": True,
            "vector_field_name": None,
            "vector_field_type": None,
            "vector_field_dim": None,
        }

        with patch(
            "orka.utils.bootstrap_memory_index.verify_memory_index", return_value=mock_index_info
        ):
            with patch.object(self.logger, "_fallback_text_search") as mock_fallback:
                mock_fallback.return_value = [{"content": "test result"}]

                # Call search_memories
                results = self.logger.search_memories("test query")

                # Verify fallback was used
                mock_fallback.assert_called_once()
                assert results == [{"content": "test result"}]

    def test_yaml_config_parameters(self):
        """Test that YAML configuration parameters are properly passed."""
        # Create a logger with custom YAML parameters
        custom_params = {
            "force_recreate": True,
            "type": "FLOAT32",
            "distance_metric": "COSINE",
            "ef_construction": 300,
            "m": 24,
            "vector_field_name": "custom_vector_field",
        }

        with patch(
            "orka.utils.bootstrap_memory_index.ensure_enhanced_memory_index"
        ) as mock_ensure_index:
            logger = RedisStackMemoryLogger(
                redis_url="redis://localhost:6379/0",
                index_name="custom_index",
                embedder=self.mock_embedder,
                enable_hnsw=True,
                vector_params=custom_params,
            )

            # Verify parameters were passed correctly
            assert logger.vector_params["force_recreate"] is True
            assert logger.vector_params["type"] == "FLOAT32"
            assert logger.vector_params["distance_metric"] == "COSINE"
            assert logger.vector_params["ef_construction"] == 300
            assert logger.vector_params["m"] == 24
            assert logger.vector_params["vector_field_name"] == "custom_vector_field"
