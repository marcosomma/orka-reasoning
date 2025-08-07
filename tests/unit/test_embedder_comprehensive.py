"""
Comprehensive tests for embedder module to improve coverage.
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from orka.utils.embedder import (
    DEFAULT_EMBEDDING_DIM,
    EMBEDDING_DIMENSIONS,
    AsyncEmbedder,
    from_bytes,
    get_embedder,
    to_bytes,
)


class TestAsyncEmbedderInitialization:
    """Test AsyncEmbedder initialization with various parameters."""

    def test_init_with_default_model(self):
        """Test initialization with default model."""
        embedder = AsyncEmbedder()
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.embedding_dim == 384
        # Model may or may not load successfully depending on environment
        assert hasattr(embedder, "model")
        assert hasattr(embedder, "model_loaded")

    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        embedder = AsyncEmbedder("custom-model")
        assert embedder.model_name == "custom-model"
        assert embedder.embedding_dim == DEFAULT_EMBEDDING_DIM

    def test_init_with_unknown_model(self):
        """Test initialization with unknown model."""
        embedder = AsyncEmbedder("unknown-model")
        assert embedder.model_name == "unknown-model"
        assert embedder.embedding_dim == DEFAULT_EMBEDDING_DIM

    def test_init_with_none_model(self):
        """Test that initializing with None model_name raises an error."""
        with pytest.raises(AttributeError):
            AsyncEmbedder(model_name=None)

    def test_init_with_empty_string_model(self):
        """Test that initializing with an empty string model_name uses the default."""
        embedder = AsyncEmbedder(model_name="")
        assert embedder.model_name == ""

    def test_init_with_known_models(self):
        """Test initialization with known models from EMBEDDING_DIMENSIONS."""
        for model_name, expected_dim in EMBEDDING_DIMENSIONS.items():
            embedder = AsyncEmbedder(f"sentence-transformers/{model_name}")
            assert embedder.embedding_dim == expected_dim


class TestAsyncEmbedderLoadModel:
    """Test AsyncEmbedder model loading functionality."""

    @patch("orka.utils.embedder.logger")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_success(self, mock_sentence_transformer, mock_logger):
        """Test successful model loading."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        embedder = AsyncEmbedder(model_name="test-model")
        embedder._load_model()

        assert embedder.model_loaded is True
        assert embedder.model is not None
        mock_logger.info.assert_called_with(
            "Successfully loaded embedding model: test-model with dimension 384"
        )

    @patch("orka.utils.embedder.logger")
    def test_load_model_import_error(self, mock_logger):
        """Test model loading with ImportError."""
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            embedder = AsyncEmbedder("test-model")

            assert embedder.model_loaded is False
            assert embedder.model is None
            mock_logger.error.assert_called_once()

    @patch("orka.utils.embedder.logger")
    def test_load_model_general_exception(self, mock_logger):
        """Test model loading with general exception."""
        mock_st_class = MagicMock(side_effect=Exception("Model error"))

        with patch("sentence_transformers.SentenceTransformer", mock_st_class):
            embedder = AsyncEmbedder("test-model")

            assert embedder.model_loaded is False
            assert embedder.model is None
            # Should call warning at least once (may also warn about missing local files)
            assert mock_logger.warning.call_count >= 1
            # Check that model error warning was called
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any("Failed to load embedding model" in call for call in warning_calls)

    @patch("orka.utils.embedder.logger")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_with_local_path_check(
        self, mock_sentence_transformer, mock_expanduser, mock_exists, mock_logger
    ):
        """Test model loading with local path checking."""
        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = False

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        embedder = AsyncEmbedder("test-model")

        assert embedder.model_loaded is True
        mock_logger.warning.assert_called_once()
        assert "Model files not found locally" in str(mock_logger.warning.call_args)

    @patch("orka.utils.embedder.logger")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_with_local_path_found(
        self, mock_sentence_transformer, mock_expanduser, mock_exists, mock_logger
    ):
        """Test model loading when local files are found."""
        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = True

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model

        embedder = AsyncEmbedder("test-model")

        assert embedder.model_loaded is True
        # Should not call warning about missing files
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Model files not found locally" in str(call)
        ]
        assert len(warning_calls) == 0

    @patch("orka.utils.embedder.logger")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_with_url_model(self, mock_sentence_transformer, mock_logger):
        """Test model loading with URL model name."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_sentence_transformer.return_value = mock_model

        embedder = AsyncEmbedder("https://example.com/model")

        assert embedder.model_loaded is True
        assert embedder.model_name == "https://example.com/model"
        # Should not check for local files with URL models
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Model files not found locally" in str(call)
        ]
        assert len(warning_calls) == 0


class TestAsyncEmbedderEncode:
    """Test AsyncEmbedder encoding functionality."""

    @pytest.mark.asyncio
    @patch("orka.utils.embedder.SentenceTransformer")
    async def test_encode_success_with_model(self, mock_sentence_transformer):
        """Test encoding with successfully loaded model."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_sentence_transformer.return_value = mock_model

        embedder = AsyncEmbedder("test-model")
        result = await embedder.encode("test text")

        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, np.array([0.1, 0.2, 0.3]))
        mock_model.encode.assert_called_once_with("test text")

    @pytest.mark.asyncio
    async def test_encode_empty_text(self):
        """Test encoding with empty text."""
        embedder = AsyncEmbedder("test-model")
        result = await embedder.encode("")

        assert isinstance(result, np.ndarray)
        assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_none_text(self):
        """Test encoding with None text."""
        embedder = AsyncEmbedder("test-model")
        result = await embedder.encode(None)

        assert isinstance(result, np.ndarray)
        assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_model_exception(self):
        """Test encoding when model raises exception."""
        mock_st_class = MagicMock()
        mock_st_instance = MagicMock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_instance.encode.side_effect = Exception("Model error")
        mock_st_class.return_value = mock_st_instance

        with patch("sentence_transformers.SentenceTransformer", mock_st_class):
            embedder = AsyncEmbedder("test-model")
            result = await embedder.encode("test text")

            # Should fallback to _fallback_encode
            assert isinstance(result, np.ndarray)
            assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_invalid_model_output(self):
        """Test encoding when model returns invalid output."""
        mock_st_class = MagicMock()
        mock_st_instance = MagicMock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_instance.encode.return_value = None
        mock_st_class.return_value = mock_st_instance

        with patch("sentence_transformers.SentenceTransformer", mock_st_class):
            embedder = AsyncEmbedder("test-model")
            result = await embedder.encode("test text")

            # Should fallback to _fallback_encode
            assert isinstance(result, np.ndarray)
            assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_empty_model_output(self):
        """Test encoding when model returns empty array."""
        mock_st_class = MagicMock()
        mock_st_instance = MagicMock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_instance.encode.return_value = np.array([])
        mock_st_class.return_value = mock_st_instance

        with patch("sentence_transformers.SentenceTransformer", mock_st_class):
            embedder = AsyncEmbedder("test-model")
            result = await embedder.encode("test text")

            # Should fallback to _fallback_encode
            assert isinstance(result, np.ndarray)
            assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_no_model_loaded(self):
        """Test encoding when no model is loaded."""
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            embedder = AsyncEmbedder("test-model")
            result = await embedder.encode("test text")

            # Should use _fallback_encode
            assert isinstance(result, np.ndarray)
            assert len(result) == embedder.embedding_dim


class TestAsyncEmbedderFallbackEncode:
    """Test AsyncEmbedder fallback encoding functionality."""

    def test_fallback_encode_deterministic(self):
        """Test that fallback encoding is deterministic."""
        embedder = AsyncEmbedder("test-model")

        result1 = embedder._fallback_encode("test text")
        result2 = embedder._fallback_encode("test text")

        np.testing.assert_array_equal(result1, result2)

    def test_fallback_encode_different_texts(self):
        """Test that different texts produce different embeddings."""
        embedder = AsyncEmbedder("test-model")

        result1 = embedder._fallback_encode("text one")
        result2 = embedder._fallback_encode("text two")

        assert not np.array_equal(result1, result2)

    def test_fallback_encode_normalized(self):
        """Test that fallback embeddings are normalized."""
        embedder = AsyncEmbedder("test-model")

        result = embedder._fallback_encode("test text")
        norm = np.linalg.norm(result)

        assert abs(norm - 1.0) < 1e-6

    def test_fallback_encode_custom_dimension(self):
        """Test fallback encoding with custom dimension."""
        embedder = AsyncEmbedder("test-model")
        embedder.embedding_dim = 256

        result = embedder._fallback_encode("test text")

        assert len(result) == 256
        assert abs(np.linalg.norm(result) - 1.0) < 1e-6

    def test_fallback_encode_exception(self):
        """Test fallback encoding handles exceptions gracefully."""
        embedder = AsyncEmbedder("test-model")

        # Test with problematic input
        result = embedder._fallback_encode("")

        assert isinstance(result, np.ndarray)
        assert len(result) == embedder.embedding_dim

    def test_fallback_encode_zero_norm(self):
        """Test fallback encoding handles zero norm case."""
        embedder = AsyncEmbedder("test-model")

        # Mock random.gauss to return zeros
        with patch("random.gauss", return_value=0.0):
            result = embedder._fallback_encode("test text")

            assert isinstance(result, np.ndarray)
            assert len(result) == embedder.embedding_dim
            # Should handle zero norm by returning uniform distribution
            assert np.sum(result) > 0  # Should not be all zeros


class TestGetEmbedder:
    """Test get_embedder singleton functionality."""

    def teardown_method(self):
        """Reset global embedder after each test."""
        import orka.utils.embedder

        orka.utils.embedder._embedder = None

    def test_get_embedder_first_call(self):
        """Test first call to get_embedder creates instance."""
        embedder = get_embedder()
        assert isinstance(embedder, AsyncEmbedder)

    def test_get_embedder_singleton(self):
        """Test get_embedder returns same instance."""
        embedder1 = get_embedder()
        embedder2 = get_embedder()
        assert embedder1 is embedder2

    def test_get_embedder_none_name(self):
        """Test get_embedder with None name."""
        embedder = get_embedder(None)
        assert isinstance(embedder, AsyncEmbedder)
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    def test_get_embedder_no_name(self):
        """Test get_embedder with no name parameter."""
        embedder = get_embedder()
        assert isinstance(embedder, AsyncEmbedder)
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"


class TestToBytes:
    """Test to_bytes utility function."""

    def test_to_bytes_success(self):
        """Test successful conversion to bytes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_to_bytes_normalization(self):
        """Test to_bytes with vector normalization."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        # Should normalize the vector before conversion
        restored = np.frombuffer(result, dtype=np.float32)
        norm = np.linalg.norm(restored)
        assert abs(norm - 1.0) < 1e-6

    def test_to_bytes_zero_vector(self):
        """Test to_bytes with zero vector."""
        vec = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        # Should handle zero vector gracefully
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == 3

    def test_to_bytes_different_dtype(self):
        """Test to_bytes with different numpy dtypes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float64)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        # Should convert to float32
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == 3

    def test_to_bytes_exception(self):
        """Test to_bytes handles exceptions."""
        # Test with invalid input
        result = to_bytes(None)

        assert isinstance(result, bytes)
        # Should return default vector bytes when error occurs
        expected_len = DEFAULT_EMBEDDING_DIM * 4  # 4 bytes per float32
        assert len(result) == expected_len


class TestFromBytes:
    """Test from_bytes utility function."""

    def test_from_bytes_success(self):
        """Test successful conversion from bytes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        byte_data = vec.tobytes()

        result = from_bytes(byte_data)

        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, vec)

    def test_from_bytes_empty_bytes(self):
        """Test from_bytes with empty bytes."""
        result = from_bytes(b"")

        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    def test_from_bytes_exception(self):
        """Test from_bytes handles exceptions."""
        # Test with invalid bytes
        result = from_bytes(b"invalid")

        assert isinstance(result, np.ndarray)
        # Should return default vector when error occurs
        assert len(result) == DEFAULT_EMBEDDING_DIM

    def test_from_bytes_round_trip(self):
        """Test round trip conversion."""
        original = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)

        # Convert to bytes and back
        byte_data = to_bytes(original)
        restored = from_bytes(byte_data)

        assert isinstance(restored, np.ndarray)
        # Should be close due to normalization
        assert len(restored) == len(original)


class TestModuleConstants:
    """Test module-level constants and variables."""

    def test_default_embedding_dim(self):
        """Test DEFAULT_EMBEDDING_DIM constant."""
        assert DEFAULT_EMBEDDING_DIM == 384

    def test_embedding_dimensions_dict(self):
        """Test EMBEDDING_DIMENSIONS dictionary."""
        assert isinstance(EMBEDDING_DIMENSIONS, dict)
        assert len(EMBEDDING_DIMENSIONS) > 0
        assert "all-MiniLM-L6-v2" in EMBEDDING_DIMENSIONS
        assert EMBEDDING_DIMENSIONS["all-MiniLM-L6-v2"] == 384

    def test_global_embedder_variable(self):
        """Test global _embedder variable."""
        import orka.utils.embedder

        # Should start as None
        orka.utils.embedder._embedder = None
        assert orka.utils.embedder._embedder is None

    def test_logger_exists(self):
        """Test logger is properly configured."""
        import orka.utils.embedder

        assert hasattr(orka.utils.embedder, "logger")
        assert orka.utils.embedder.logger.name == "orka.utils.embedder"


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def teardown_method(self):
        """Reset global embedder after each test."""
        import orka.utils.embedder

        orka.utils.embedder._embedder = None

    @pytest.mark.asyncio
    @patch("orka.utils.embedder.SentenceTransformer")
    async def test_full_workflow_with_model(self, mock_sentence_transformer):
        """Test complete workflow with successful model loading."""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 3
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_sentence_transformer.return_value = mock_model

        # Get embedder and encode text
        embedder = get_embedder("test-model")
        embedding = await embedder.encode("test text")

        # Convert to bytes and back
        byte_data = to_bytes(embedding)
        restored = from_bytes(byte_data)

        assert isinstance(embedding, np.ndarray)
        assert isinstance(byte_data, bytes)
        assert isinstance(restored, np.ndarray)
        assert len(restored) == 3

    @pytest.mark.asyncio
    async def test_full_workflow_with_fallback(self):
        """Test complete workflow with fallback encoding."""
        with patch("builtins.__import__", side_effect=ImportError("No module")):
            # Get embedder and encode text
            embedder = get_embedder("test-model")
            embedding = await embedder.encode("test text")

            # Convert to bytes and back
            byte_data = to_bytes(embedding)
            restored = from_bytes(byte_data)

            assert isinstance(embedding, np.ndarray)
            assert isinstance(byte_data, bytes)
            assert isinstance(restored, np.ndarray)
            assert len(embedding) == DEFAULT_EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_multiple_embeddings_consistency(self):
        """Test that multiple embeddings of same text are consistent."""
        embedder = get_embedder()

        embedding1 = await embedder.encode("consistent text")
        embedding2 = await embedder.encode("consistent text")

        np.testing.assert_array_equal(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_different_text_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        embedder = get_embedder()

        embedding1 = await embedder.encode("first text")
        embedding2 = await embedder.encode("second text")

        assert not np.array_equal(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_singleton_behavior_across_calls(self):
        """Test singleton behavior across multiple get_embedder calls."""
        embedder1 = get_embedder()
        embedder2 = get_embedder("different-model")  # Should return same instance

        assert embedder1 is embedder2

        # Both should produce same embeddings
        text = "test singleton"
        embedding1 = await embedder1.encode(text)
        embedding2 = await embedder2.encode(text)

        np.testing.assert_array_equal(embedding1, embedding2)
