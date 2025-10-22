"""
Additional comprehensive tests for memory compressor to increase coverage.
"""
import pytest
from unittest.mock import MagicMock, patch
from orka.memory.compressor import MemoryCompressor, CompressionStrategy


class TestMemoryCompressor:
    """Test memory compression functionality."""

    def test_compressor_initialization(self):
        """Test compressor initialization."""
        compressor = MemoryCompressor()
        assert compressor is not None

    def test_compress_text_basic(self):
        """Test basic text compression."""
        compressor = MemoryCompressor()
        text = "This is a test text that should be compressed."
        compressed = compressor.compress(text)
        assert compressed is not None
        assert len(compressed) <= len(text)

    def test_compress_with_strategy(self):
        """Test compression with specific strategy."""
        compressor = MemoryCompressor(strategy=CompressionStrategy.AGGRESSIVE)
        text = "Test text for compression"
        compressed = compressor.compress(text)
        assert compressed is not None

    def test_decompress_text(self):
        """Test text decompression."""
        compressor = MemoryCompressor()
        original = "Test text"
        compressed = compressor.compress(original)
        decompressed = compressor.decompress(compressed)
        assert decompressed == original

    def test_compress_empty_text(self):
        """Test compressing empty text."""
        compressor = MemoryCompressor()
        compressed = compressor.compress("")
        assert compressed == ""

    def test_compress_large_text(self):
        """Test compressing large text."""
        compressor = MemoryCompressor()
        large_text = "test " * 10000
        compressed = compressor.compress(large_text)
        assert len(compressed) < len(large_text)

    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        compressor = MemoryCompressor()
        text = "test " * 100
        compressed = compressor.compress(text)
        ratio = compressor.get_compression_ratio(text, compressed)
        assert 0 < ratio <= 1

    def test_compress_with_metadata(self):
        """Test compression with metadata preservation."""
        compressor = MemoryCompressor()
        data = {
            "text": "test text",
            "metadata": {"importance": 0.8}
        }
        compressed = compressor.compress_with_metadata(data)
        assert "text" in compressed
        assert "metadata" in compressed

    def test_selective_compression(self):
        """Test selective compression based on importance."""
        compressor = MemoryCompressor()
        memories = [
            {"text": "important", "importance": 0.9},
            {"text": "less important", "importance": 0.3}
        ]
        compressed = compressor.compress_selective(memories, threshold=0.5)
        assert len(compressed) == 2

    def test_compression_strategies(self):
        """Test different compression strategies."""
        strategies = [
            CompressionStrategy.NONE,
            CompressionStrategy.LIGHT,
            CompressionStrategy.MODERATE,
            CompressionStrategy.AGGRESSIVE
        ]
        text = "Test text for compression"
        
        for strategy in strategies:
            compressor = MemoryCompressor(strategy=strategy)
            compressed = compressor.compress(text)
            assert compressed is not None
