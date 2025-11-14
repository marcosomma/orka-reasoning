"""Unit tests for orka.utils.embedder."""

import numpy as np
from unittest.mock import Mock, patch

import pytest

from orka.utils.embedder import AsyncEmbedder, _ensure_numpy_array, to_bytes

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestEnsureNumpyArray:
    """Test suite for _ensure_numpy_array function."""

    def test_ensure_numpy_array_already_array(self):
        """Test _ensure_numpy_array with numpy array."""
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        result = _ensure_numpy_array(arr)
        
        assert isinstance(result, np.ndarray)
        assert np.array_equal(result, arr)

    def test_ensure_numpy_array_list(self):
        """Test _ensure_numpy_array with list."""
        result = _ensure_numpy_array([1.0, 2.0, 3.0])
        
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_ensure_numpy_array_empty(self):
        """Test _ensure_numpy_array with empty data."""
        result = _ensure_numpy_array([])
        
        assert isinstance(result, np.ndarray)
        assert result.size > 0  # Should return zero array


class TestAsyncEmbedder:
    """Test suite for AsyncEmbedder class."""

    def test_init(self):
        """Test AsyncEmbedder initialization."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            MockST.return_value.get_sentence_embedding_dimension.return_value = 384
            embedder = AsyncEmbedder()
            
            assert embedder.model_name is not None
            assert embedder.embedding_dim == 384  # Default dimension

    def test_init_custom_model(self):
        """Test AsyncEmbedder initialization with custom model."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            MockST.return_value.get_sentence_embedding_dimension.return_value = 768
            embedder = AsyncEmbedder(model_name="sentence-transformers/all-mpnet-base-v2")
            
            assert embedder.model_name == "sentence-transformers/all-mpnet-base-v2"
            assert embedder.embedding_dim == 768  # mpnet dimension

    @pytest.mark.asyncio
    async def test_encode_with_model(self):
        """Test encode method when model is loaded."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            mock_model = Mock()
            mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3] * 128])  # 384-dim
            MockST.return_value = mock_model
            
            embedder = AsyncEmbedder()
            embedder.model = mock_model
            embedder.model_loaded = True
            
            result = await embedder.encode("test text")
            
            assert isinstance(result, np.ndarray)
            mock_model.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_encode_fallback(self):
        """Test encode method uses fallback when model not loaded."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            MockST.return_value.get_sentence_embedding_dimension.return_value = 384
            embedder = AsyncEmbedder()
            embedder.model_loaded = False
            
            result = await embedder.encode("test text")
            
            assert isinstance(result, np.ndarray)
            assert result.shape[0] == embedder.embedding_dim

    def test_fallback_encode(self):
        """Test _fallback_encode method."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            MockST.return_value.get_sentence_embedding_dimension.return_value = 384
            embedder = AsyncEmbedder()
            
            result = embedder._fallback_encode("test text")
            
            assert isinstance(result, np.ndarray)
            assert result.shape[0] == embedder.embedding_dim

    def test_fallback_encode_deterministic(self):
        """Test _fallback_encode produces deterministic results."""
        with patch('orka.utils.embedder.SentenceTransformer') as MockST:
            embedder = AsyncEmbedder()
            
            result1 = embedder._fallback_encode("test text")
            result2 = embedder._fallback_encode("test text")
            
            # Should produce same result for same input
            assert np.array_equal(result1, result2)


class TestToBytes:
    """Test suite for to_bytes function."""

    def test_to_bytes(self):
        """Test to_bytes function."""
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        
        result = to_bytes(arr)
        
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_to_bytes_empty(self):
        """Test to_bytes with empty array."""
        arr = np.array([], dtype=np.float32)
        
        result = to_bytes(arr)
        
        assert isinstance(result, bytes)

