"""Test suite for memory compressor."""

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from orka.contracts import MemoryEntry
from orka.memory.compressor import MemoryCompressor


@pytest.fixture
def mock_summarizer():
    """Create a mock summarizer."""
    summarizer = AsyncMock()
    summarizer.summarize = AsyncMock(return_value="Summary of entries")
    return summarizer


@pytest.fixture
def mock_generator():
    """Create a mock generator."""
    generator = AsyncMock()
    generator.generate = AsyncMock(return_value="Generated summary")
    return generator


@pytest.fixture
def sample_entries():
    """Create sample memory entries."""
    now = datetime.now()
    return [
        {
            "content": f"Entry {i}",
            "importance": 0.1 * i,
            "timestamp": now - timedelta(days=i),
            "metadata": {},
        }
        for i in range(1, 11)
    ]


class TestMemoryCompressorInitialization:
    """Test initialization of MemoryCompressor."""

    def test_default_initialization(self):
        """Test initialization with default parameters."""
        compressor = MemoryCompressor()

        assert compressor.max_entries == 1000
        assert compressor.importance_threshold == 0.3
        assert compressor.time_window == timedelta(days=7)

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        compressor = MemoryCompressor(
            max_entries=500,
            importance_threshold=0.5,
            time_window=timedelta(days=14),
        )

        assert compressor.max_entries == 500
        assert compressor.importance_threshold == 0.5
        assert compressor.time_window == timedelta(days=14)


class TestMemoryCompressorCompression:
    """Test compression functionality."""

    def test_should_compress_below_max_entries(self, sample_entries):
        """Test compression check when entries are below max."""
        compressor = MemoryCompressor(max_entries=20)
        assert not compressor.should_compress(sample_entries)

    def test_should_compress_above_max_entries(self, sample_entries):
        """Test compression check when entries are above max."""
        compressor = MemoryCompressor(max_entries=5)
        # Current implementation requires both max_entries exceeded AND low average importance
        # Sample entries have average importance around 0.55 > default threshold 0.3
        assert not compressor.should_compress(sample_entries)

    def test_should_compress_low_importance(self, sample_entries):
        """Test compression check with low importance."""
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)
        assert compressor.should_compress(sample_entries)

    def test_should_compress_high_importance(self, sample_entries):
        """Test compression check with high importance."""
        # Modify entries to have high importance
        for entry in sample_entries:
            entry["importance"] = 0.9

        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.3)
        # High importance (0.9) > threshold (0.3), so compression should not happen
        assert not compressor.should_compress(sample_entries)

    @pytest.mark.asyncio
    async def test_compress_no_compression_needed(self, sample_entries, mock_summarizer):
        """Test compression when no compression is needed."""
        compressor = MemoryCompressor(max_entries=20)
        result = await compressor.compress(sample_entries, mock_summarizer)

        assert result == sample_entries
        mock_summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_with_summarizer(self, sample_entries, mock_summarizer):
        """Test compression with summarizer."""
        # Use high importance threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)
        result = await compressor.compress(sample_entries, mock_summarizer)

        assert len(result) < len(sample_entries)
        mock_summarizer.summarize.assert_called_once()

        # Check summary entry
        summary_entry = next(e for e in result if e.get("is_summary", False))
        assert summary_entry["content"] == "Summary of entries"
        assert summary_entry["importance"] == 1.0
        assert summary_entry["category"] == "summary"
        assert summary_entry["metadata"]["is_summary"]

    @pytest.mark.asyncio
    async def test_compress_with_generator(self, sample_entries, mock_generator):
        """Test compression with generator."""
        # Use high importance threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)
        delattr(mock_generator, "summarize")  # Remove summarize method to force using generate
        result = await compressor.compress(sample_entries, mock_generator)

        assert len(result) < len(sample_entries)
        mock_generator.generate.assert_called_once()

        # Check summary entry
        summary_entry = next(e for e in result if e.get("is_summary", False))
        assert summary_entry["content"] == "Generated summary"

    @pytest.mark.asyncio
    async def test_compress_error_handling(self, sample_entries, mock_summarizer, caplog):
        """Test compression error handling."""
        mock_summarizer.summarize.side_effect = Exception("Test error")
        # Use high importance threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)

        with caplog.at_level(logging.ERROR):
            result = await compressor.compress(sample_entries, mock_summarizer)

        assert result == sample_entries  # Should return original entries on error
        assert "Error during memory compression: Test error" in caplog.text

    @pytest.mark.asyncio
    async def test_compress_invalid_summarizer(self, sample_entries):
        """Test compression with invalid summarizer."""
        invalid_summarizer = Mock()  # No summarize or generate method
        delattr(invalid_summarizer, "summarize")  # Remove summarize method
        delattr(invalid_summarizer, "generate")  # Remove generate method
        # Use high importance threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)

        with pytest.raises(
            ValueError, match=r"Summarizer must have summarize\(\) or generate\(\) method"
        ):
            await compressor.compress(sample_entries, invalid_summarizer)

    @pytest.mark.asyncio
    async def test_compress_empty_entries(self, mock_summarizer):
        """Test compression with empty entries list."""
        compressor = MemoryCompressor()
        result = await compressor.compress([], mock_summarizer)

        assert result == []
        mock_summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_no_old_entries(self, mock_summarizer):
        """Test compression when all entries are recent."""
        now = datetime.now()
        recent_entries = [
            {
                "content": f"Recent entry {i}",
                "importance": 0.9,  # High importance to avoid compression
                "timestamp": now - timedelta(hours=i),
                "metadata": {},
            }
            for i in range(1, 11)
        ]

        compressor = MemoryCompressor(max_entries=20)  # Higher max entries to avoid compression
        result = await compressor.compress(recent_entries, mock_summarizer)

        assert len(result) == len(recent_entries)
        mock_summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_missing_timestamps(self, mock_summarizer):
        """Test compression with entries missing timestamps."""
        entries = [
            {"content": f"Entry {i}", "importance": 0.2, "metadata": {}} for i in range(1, 11)
        ]

        # Use low importance entries and high threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)
        result = await compressor.compress(entries, mock_summarizer)

        assert len(result) < len(entries)
        mock_summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_missing_importance(self, mock_summarizer):
        """Test compression with entries missing importance values."""
        now = datetime.now()
        entries = [
            {
                "content": f"Entry {i}",
                "timestamp": now - timedelta(days=i),
                "metadata": {},
            }
            for i in range(1, 11)
        ]

        compressor = MemoryCompressor(max_entries=5)
        result = await compressor.compress(entries, mock_summarizer)

        assert len(result) < len(entries)
        mock_summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_missing_content(self, mock_summarizer):
        """Test compression with entries missing content."""
        now = datetime.now()
        entries = [
            {
                "importance": 0.2,
                "timestamp": now - timedelta(days=i),
                "metadata": {},
            }
            for i in range(1, 11)
        ]

        # Use low importance entries and high threshold to enable compression
        compressor = MemoryCompressor(max_entries=5, importance_threshold=0.8)
        result = await compressor.compress(entries, mock_summarizer)

        assert len(result) < len(entries)
        mock_summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_time_window(self, mock_summarizer):
        """Test compression with custom time window."""
        now = datetime.now()
        entries = [
            {
                "content": f"Entry {i}",
                "importance": 0.2,  # Low importance to enable compression
                "timestamp": now - timedelta(days=i),
                "metadata": {},
            }
            for i in range(1, 31)  # 30 days of entries
        ]

        # Use high threshold to enable compression
        compressor = MemoryCompressor(
            max_entries=5, time_window=timedelta(days=14), importance_threshold=0.8
        )
        result = await compressor.compress(entries, mock_summarizer)

        # Should have recent entries (14 days) + 1 summary
        recent_count = sum(1 for e in entries if e["timestamp"] > now - timedelta(days=14))
        assert len(result) == recent_count + 1
