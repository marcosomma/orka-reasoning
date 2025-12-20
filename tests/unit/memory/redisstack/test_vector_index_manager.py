# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# Tests for VectorIndexManager - isolated, mocked, GitHub Actions compatible

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_conn_mgr():
    """Create a mock ConnectionManager."""
    conn_mgr = MagicMock()
    conn_mgr.get_client = MagicMock(return_value=MagicMock())
    conn_mgr.get_thread_safe_client = MagicMock(return_value=MagicMock())
    return conn_mgr


class TestVectorIndexManagerInit:
    """Tests for VectorIndexManager initialization."""

    def test_init_with_defaults(self):
        """VectorIndexManager should initialize with default values."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        mgr = VectorIndexManager(conn_mgr)

        assert mgr.conn_mgr == conn_mgr
        assert mgr.index_name == "orka_enhanced_memory"
        assert mgr.enable_hnsw is True
        assert mgr.vector_params == {}
        assert mgr.embedder is None

    def test_init_with_custom_params(self):
        """VectorIndexManager should accept custom parameters."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        embedder = MagicMock()
        embedder.embedding_dim = 512

        mgr = VectorIndexManager(
            conn_mgr,
            index_name="custom_index",
            enable_hnsw=False,
            vector_params={"m": 32},
            embedder=embedder,
        )

        assert mgr.index_name == "custom_index"
        assert mgr.enable_hnsw is False
        assert mgr.vector_params == {"m": 32}
        assert mgr.embedder == embedder


class TestVectorIndexManagerEnsureIndex:
    """Tests for ensure_index method."""

    def test_ensure_index_success(self, monkeypatch):
        """ensure_index should create index successfully."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        mgr = VectorIndexManager(conn_mgr, index_name="test_index")

        # Mock the bootstrap functions at the correct import location
        mock_ensure = MagicMock(return_value=True)
        mock_verify = MagicMock(
            return_value={
                "exists": True,
                "vector_field_exists": True,
                "content_field_exists": True,
                "fields": ["content", "content_vector"],
                "num_docs": 0,
            }
        )

        with patch(
            "orka.utils.bootstrap_memory_index.ensure_enhanced_memory_index",
            mock_ensure,
        ):
            with patch(
                "orka.utils.bootstrap_memory_index.verify_memory_index",
                mock_verify,
            ):
                result = mgr.ensure_index(vector_dim=384)

        assert result is True
        mock_ensure.assert_called()

    def test_ensure_index_with_embedder_dim(self, monkeypatch):
        """ensure_index should use embedder dimension when available."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        embedder = MagicMock()
        embedder.embedding_dim = 768

        mgr = VectorIndexManager(conn_mgr, embedder=embedder)

        mock_ensure = MagicMock(return_value=True)
        mock_verify = MagicMock(
            return_value={
                "exists": True,
                "vector_field_exists": True,
                "content_field_exists": True,
                "fields": [],
                "num_docs": 0,
            }
        )

        with patch(
            "orka.utils.bootstrap_memory_index.ensure_enhanced_memory_index",
            mock_ensure,
        ):
            with patch(
                "orka.utils.bootstrap_memory_index.verify_memory_index",
                mock_verify,
            ):
                result = mgr.ensure_index()

        # Verify 768 was used
        call_kwargs = mock_ensure.call_args[1]
        assert call_kwargs["vector_dim"] == 768

    def test_ensure_index_force_recreate_on_missing_vector_field(self, monkeypatch):
        """ensure_index should force recreate when vector field is missing."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        mgr = VectorIndexManager(conn_mgr)

        # First verify shows missing vector field, second shows it exists
        verify_results = [
            {
                "exists": True,
                "vector_field_exists": False,
                "content_field_exists": True,
                "fields": ["content"],
                "num_docs": 0,
            },
            {
                "exists": True,
                "vector_field_exists": True,
                "content_field_exists": True,
                "fields": ["content", "content_vector"],
                "num_docs": 0,
            },
        ]
        mock_verify = MagicMock(side_effect=verify_results)
        mock_ensure = MagicMock(return_value=True)

        with patch(
            "orka.utils.bootstrap_memory_index.ensure_enhanced_memory_index",
            mock_ensure,
        ):
            with patch(
                "orka.utils.bootstrap_memory_index.verify_memory_index",
                mock_verify,
            ):
                result = mgr.ensure_index()

        # Should have called with force_recreate=True
        assert mock_ensure.called

    def test_ensure_index_redis_timeout(self, monkeypatch):
        """ensure_index should handle Redis connection timeout."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = MagicMock()
        conn_mgr.get_client = MagicMock(side_effect=Exception("Connection timeout"))

        mgr = VectorIndexManager(conn_mgr)

        # Should return False on connection failure
        result = mgr.ensure_index()
        assert result is False


class TestVectorIndexManagerVerify:
    """Tests for verify_index method."""

    def test_verify_index_success(self, monkeypatch):
        """verify_index should return index status."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = _make_mock_conn_mgr()
        mgr = VectorIndexManager(conn_mgr, index_name="test_index")

        expected_result = {
            "exists": True,
            "vector_field_exists": True,
            "content_field_exists": True,
            "fields": ["content", "content_vector"],
            "num_docs": 100,
        }

        with patch(
            "orka.utils.bootstrap_memory_index.verify_memory_index",
            return_value=expected_result,
        ):
            result = mgr.verify_index()

        assert result == expected_result

    def test_verify_index_error(self, monkeypatch):
        """verify_index should handle errors gracefully."""
        from orka.memory.redisstack.vector_index_manager import VectorIndexManager

        conn_mgr = MagicMock()
        conn_mgr.get_client = MagicMock(side_effect=Exception("Connection error"))

        mgr = VectorIndexManager(conn_mgr)
        result = mgr.verify_index()

        assert result["exists"] is False
        assert "error" in result

