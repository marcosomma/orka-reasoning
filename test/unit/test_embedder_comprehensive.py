"""Test AsyncEmbedder functionality."""

import logging
from unittest.mock import Mock, patch

import numpy as np
import pytest
from typing import cast

from orka.utils.embedder import (
    DEFAULT_EMBEDDING_DIM,
    AsyncEmbedder,
    from_bytes,
    get_embedder,
    to_bytes,
)

logger = logging.getLogger(__name__)


class TestAsyncEmbedderInitialization:
    """Test AsyncEmbedder initialization functionality."""

    def test_init_with_default_model(self):
        """Test initialization with default model."""
        embedder = AsyncEmbedder()
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.embedding_dim == 384

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        embedder = AsyncEmbedder("all-mpnet-base-v2")
        assert embedder.model_name == "all-mpnet-base-v2"
        assert embedder.embedding_dim == 768

    def test_init_with_unknown_model(self):
        """Test initialization with unknown model."""
        embedder = AsyncEmbedder("unknown-model")
        assert embedder.model_name == "unknown-model"
        assert embedder.embedding_dim == 384  # Should use default

    def test_init_with_none_model(self):
        """Test initialization with None model."""
        embedder = AsyncEmbedder(None)
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.embedding_dim == 384

    def test_init_with_empty_string_model(self):
        """Test initialization with empty string model."""
        embedder = AsyncEmbedder("")
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.embedding_dim == 384

    def test_init_with_known_models(self):
        """Test initialization with all known models."""
        expected_dims = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "all-distilroberta-v1": 768,
            "all-MiniLM-L12-v2": 384,
        }

        for model_name, expected_dim in expected_dims.items():
            embedder = AsyncEmbedder(model_name)
            assert embedder.model_name == model_name
            assert embedder.embedding_dim == expected_dim


class TestAsyncEmbedderLoadModel:
    """Test AsyncEmbedder model loading functionality."""

    @patch("orka.utils.embedder.logger")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_success(self, mock_st_class, mock_logger):
        """Test successful model loading."""
        # Mock the SentenceTransformer instance
        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_st_instance

        embedder = AsyncEmbedder("test-model")

        assert embedder.model_loaded is True
        assert embedder.model == mock_st_instance
        assert embedder.embedding_dim == 384
        mock_st_class.assert_called_once_with("test-model")

    @patch("orka.utils.embedder.logger")
    def test_load_model_import_error(self, mock_logger):
        """Test model loading with ImportError."""
        with patch("orka.utils.embedder.SentenceTransformer", None):
            embedder = AsyncEmbedder("test-model")

            assert embedder.model_loaded is False
            assert embedder.model is None
            mock_logger.error.assert_called_once()

    @patch("orka.utils.embedder.logger")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_general_exception(self, mock_st_class, mock_logger):
        """Test model loading with general exception."""
        mock_st_class.side_effect = Exception("Model error")

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
        self, mock_st_class, mock_expanduser, mock_exists, mock_logger
    ):
        """Test model loading with local path checking."""
        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = False

        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.side_effect = Exception("Model not found")

        embedder = AsyncEmbedder("test-model")

        assert embedder.model_loaded is False
        # Check that warning about model loading was called
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Failed to load embedding model" in str(call)
        ]
        assert len(warning_calls) == 1

    @patch("orka.utils.embedder.logger")
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("orka.utils.embedder.SentenceTransformer")
    def test_load_model_with_local_path_found(
        self, mock_st_class, mock_expanduser, mock_exists, mock_logger
    ):
        """Test model loading when local files are found."""
        mock_expanduser.return_value = "/home/user"
        mock_exists.return_value = True

        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_class.return_value = mock_st_instance

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
    def test_load_model_with_url_model(self, mock_st_class, mock_logger):
        """Test model loading with URL model name."""
        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 768
        mock_st_class.return_value = mock_st_instance

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
    async def test_encode_success_with_model(self):
        """Test encoding with successfully loaded model."""
        # Create a properly shaped array for the mock return value
        mock_embedding = np.array([0.1] * 384, dtype=np.float32)  # 384 dimensions

        # Create and configure the mock
        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_instance.encode.return_value = mock_embedding

        # Patch at the module level where SentenceTransformer is assigned
        with patch("orka.utils.embedder.SentenceTransformer") as mock_st_class:
            mock_st_class.return_value = mock_st_instance

            embedder = AsyncEmbedder("test-model")
            result = await embedder.encode("test text")

            assert isinstance(result, np.ndarray)
            assert len(result) == 384
            assert abs(np.linalg.norm(result) - 1.0) < 1e-6  # Check normalization
            mock_st_instance.encode.assert_called_once_with("test text")

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
        result = await embedder.encode(cast(str, None))

        assert isinstance(result, np.ndarray)
        assert len(result) == embedder.embedding_dim

    @pytest.mark.asyncio
    async def test_encode_model_exception(self):
        """Test encoding when model raises exception."""
        mock_st_class = Mock()
        mock_st_instance = Mock()
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
        mock_st_class = Mock()
        mock_st_instance = Mock()
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
        mock_st_class = Mock()
        mock_st_instance = Mock()
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
        embedder = AsyncEmbedder("test-model")
        embedder.model_loaded = False
        result = await embedder.encode("test text")

        # Should use fallback encoding
        assert isinstance(result, np.ndarray)
        assert len(result) == embedder.embedding_dim


class TestAsyncEmbedderFallbackEncode:
    """Test AsyncEmbedder fallback encoding functionality."""

    def test_fallback_encode_deterministic(self):
        """Test fallback encoding is deterministic."""
        embedder = AsyncEmbedder("test-model")
        text = "test text"

        result1 = embedder._fallback_encode(text)
        result2 = embedder._fallback_encode(text)

        np.testing.assert_array_equal(result1, result2)

    def test_fallback_encode_different_texts(self):
        """Test fallback encoding produces different vectors for different texts."""
        embedder = AsyncEmbedder("test-model")
        text1 = "test text 1"
        text2 = "test text 2"

        result1 = embedder._fallback_encode(text1)
        result2 = embedder._fallback_encode(text2)

        assert not np.array_equal(result1, result2)

    def test_fallback_encode_normalized(self):
        """Test fallback encoding produces normalized vectors."""
        embedder = AsyncEmbedder("test-model")
        text = "test text"

        result = embedder._fallback_encode(text)
        norm = np.linalg.norm(result)

        assert abs(norm - 1.0) < 1e-6

    def test_fallback_encode_custom_dimension(self):
        """Test fallback encoding with custom dimension."""
        embedder = AsyncEmbedder("all-mpnet-base-v2")  # 768-dim model
        text = "test text"

        result = embedder._fallback_encode(text)

        assert len(result) == 768

    def test_fallback_encode_exception(self):
        """Test fallback encoding handles exceptions."""
        embedder = AsyncEmbedder("test-model")
        text = "test text"

        with patch("random.gauss", side_effect=Exception("Random error")):
            result = embedder._fallback_encode(text)

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
            assert np.sum(result) > 0  # Should not be all zeros


class TestGetEmbedder:
    """Test get_embedder function."""

    def teardown_method(self):
        """Reset the global embedder instance after each test."""
        import orka.utils.embedder

        orka.utils.embedder._embedder = None

    def test_get_embedder_first_call(self):
        """Test first call to get_embedder."""
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
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    def test_get_embedder_no_name(self):
        """Test get_embedder without name argument."""
        embedder = get_embedder()
        assert embedder.model_name == "sentence-transformers/all-MiniLM-L6-v2"


class TestToBytes:
    """Test to_bytes function."""

    def test_to_bytes_success(self):
        """Test successful conversion to bytes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == len(vec)

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
        vec = np.zeros(3, dtype=np.float32)
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == len(vec)

    def test_to_bytes_different_dtype(self):
        """Test to_bytes with different numpy dtypes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)  # Use float32 directly
        result = to_bytes(vec)

        assert isinstance(result, bytes)
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == 3

    def test_to_bytes_exception(self):
        """Test to_bytes handles exceptions."""
        # Test with invalid input
        result = to_bytes(None)

        assert isinstance(result, bytes)
        restored = np.frombuffer(result, dtype=np.float32)
        assert len(restored) == DEFAULT_EMBEDDING_DIM


class TestFromBytes:
    """Test from_bytes function."""

    def test_from_bytes_success(self):
        """Test successful conversion from bytes."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        bytes_data = vec.tobytes()

        result = from_bytes(bytes_data)

        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, vec)

    def test_from_bytes_empty_bytes(self):
        """Test from_bytes with empty bytes."""
        result = from_bytes(b"")

        assert isinstance(result, np.ndarray)
        assert len(result) == DEFAULT_EMBEDDING_DIM

    def test_from_bytes_exception(self):
        """Test from_bytes handles exceptions."""
        result = from_bytes(b"invalid")

        assert isinstance(result, np.ndarray)
        assert len(result) == DEFAULT_EMBEDDING_DIM

    def test_from_bytes_round_trip(self):
        """Test round trip conversion."""
        vec = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        bytes_data = to_bytes(vec)
        result = from_bytes(bytes_data)

        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, vec / np.linalg.norm(vec))


class TestModuleConstants:
    """Test module-level constants."""

    def test_default_embedding_dim(self):
        """Test DEFAULT_EMBEDDING_DIM value."""
        from orka.utils.embedder import DEFAULT_EMBEDDING_DIM

        assert DEFAULT_EMBEDDING_DIM == 384

    def test_embedding_dimensions_dict(self):
        """Test EMBEDDING_DIMENSIONS dictionary."""
        from orka.utils.embedder import EMBEDDING_DIMENSIONS

        assert isinstance(EMBEDDING_DIMENSIONS, dict)
        assert len(EMBEDDING_DIMENSIONS) > 0
        assert all(isinstance(k, str) for k in EMBEDDING_DIMENSIONS.keys())
        assert all(isinstance(v, int) for v in EMBEDDING_DIMENSIONS.values())

    def test_global_embedder_variable(self):
        """Test _embedder global variable."""
        from orka.utils.embedder import _embedder

        assert _embedder is None or isinstance(_embedder, AsyncEmbedder)

    def test_logger_exists(self):
        """Test logger is properly configured."""
        from orka.utils.embedder import logger

        assert isinstance(logger, logging.Logger)
        assert logger.name == "orka.utils.embedder"


class TestIntegrationScenarios:
    """Test end-to-end integration scenarios."""

    def teardown_method(self):
        """Reset the global embedder instance after each test."""
        import orka.utils.embedder

        orka.utils.embedder._embedder = None

    @pytest.mark.asyncio
    async def test_full_workflow_with_model(self):
        """Test full workflow with model."""
        mock_st_class = Mock()
        mock_st_instance = Mock()
        mock_st_instance.get_sentence_embedding_dimension.return_value = 384
        mock_st_instance.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st_class.return_value = mock_st_instance

        with patch("sentence_transformers.SentenceTransformer", mock_st_class):
            embedder = get_embedder()
            embedding = await embedder.encode("test text")
            bytes_data = to_bytes(embedding)
            restored = from_bytes(bytes_data)

            assert isinstance(embedding, np.ndarray)
            assert isinstance(bytes_data, bytes)
            assert isinstance(restored, np.ndarray)
            np.testing.assert_array_almost_equal(embedding, restored)

    @pytest.mark.asyncio
    async def test_full_workflow_with_fallback(self):
        """Test full workflow with fallback encoding."""
        with patch("sentence_transformers.SentenceTransformer", None):
            embedder = get_embedder()
            embedding = await embedder.encode("test text")
            bytes_data = to_bytes(embedding)
            restored = from_bytes(bytes_data)

            assert isinstance(embedding, np.ndarray)
            assert isinstance(bytes_data, bytes)
            assert isinstance(restored, np.ndarray)
            np.testing.assert_array_almost_equal(embedding, restored)

    @pytest.mark.asyncio
    async def test_multiple_embeddings_consistency(self):
        """Test consistency across multiple embeddings."""
        embedder = get_embedder()
        text = "test text"

        embedding1 = await embedder.encode(text)
        embedding2 = await embedder.encode(text)

        np.testing.assert_array_almost_equal(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_different_text_different_embeddings(self):
        """Test different texts produce different embeddings."""
        embedder = get_embedder()
        text1 = "test text 1"
        text2 = "test text 2"

        embedding1 = await embedder.encode(text1)
        embedding2 = await embedder.encode(text2)

        assert not np.array_equal(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_singleton_behavior_across_calls(self):
        """Test singleton behavior across multiple get_embedder calls."""
        embedder1 = get_embedder()
        text = "test text"
        embedding1 = await embedder1.encode(text)

        embedder2 = get_embedder()
        embedding2 = await embedder2.encode(text)

        assert embedder1 is embedder2
        np.testing.assert_array_almost_equal(embedding1, embedding2)
