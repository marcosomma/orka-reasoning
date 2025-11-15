"""Unit tests for orka.memory.compressor."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from orka.memory.compressor import MemoryCompressor

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryCompressor:
    """Test suite for MemoryCompressor class."""

    def test_init(self):
        """Test MemoryCompressor initialization."""
        compressor = MemoryCompressor()
        
        assert compressor.max_entries == 1000
        assert compressor.importance_threshold == 0.3
        assert isinstance(compressor.time_window, timedelta)

    def test_init_custom_params(self):
        """Test MemoryCompressor initialization with custom parameters."""
        compressor = MemoryCompressor(
            max_entries=500,
            importance_threshold=0.5,
            time_window=timedelta(days=14)
        )
        
        assert compressor.max_entries == 500
        assert compressor.importance_threshold == 0.5
        assert compressor.time_window == timedelta(days=14)

    def test_should_compress_false_under_limit(self):
        """Test should_compress returns False when under entry limit."""
        compressor = MemoryCompressor(max_entries=1000)
        
        entries = [{"importance": 0.1} for _ in range(500)]
        
        assert compressor.should_compress(entries) is False

    def test_should_compress_false_high_importance(self):
        """Test should_compress returns False when importance is high."""
        compressor = MemoryCompressor(max_entries=100, importance_threshold=0.3)
        
        entries = [{"importance": 0.8} for _ in range(200)]
        
        assert compressor.should_compress(entries) is False

    def test_should_compress_true(self):
        """Test should_compress returns True when conditions are met."""
        compressor = MemoryCompressor(max_entries=100, importance_threshold=0.3)
        
        entries = [{"importance": 0.1} for _ in range(200)]
        
        assert compressor.should_compress(entries) is True

    @pytest.mark.asyncio
    async def test_compress_empty(self):
        """Test compress with empty entries."""
        compressor = MemoryCompressor()
        summarizer = Mock()
        
        result = await compressor.compress([], summarizer)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_compress_no_compression_needed(self):
        """Test compress when compression is not needed."""
        compressor = MemoryCompressor(max_entries=1000)
        summarizer = Mock()
        
        entries = [{"importance": 0.8, "timestamp": datetime.now()} for _ in range(100)]
        
        result = await compressor.compress(entries, summarizer)
        
        assert result == entries

    @pytest.mark.asyncio
    async def test_compress_with_summarizer_summarize(self):
        """Test compress with summarizer that has summarize method."""
        compressor = MemoryCompressor(max_entries=10, importance_threshold=0.3)
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(return_value="Summary text")
        
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"importance": 0.1, "timestamp": old_time, "content": "Old entry"}
            for _ in range(20)
        ]
        
        result = await compressor.compress(entries, summarizer)
        
        assert len(result) < len(entries)
        summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_with_summarizer_generate(self):
        """Test compress with summarizer that has generate method."""
        compressor = MemoryCompressor(max_entries=10, importance_threshold=0.3)
        summarizer = AsyncMock()
        # Mock both summarize and generate, but expect summarize to be called
        summarizer.summarize = AsyncMock(return_value="Summary text")
        summarizer.generate = AsyncMock(return_value="Summary text")
        
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"importance": 0.1, "timestamp": old_time, "content": "Old entry"}
            for _ in range(20)
        ]
        
        result = await compressor.compress(entries, summarizer)
        
        assert len(result) < len(entries)
        summarizer.summarize.assert_called_once()
        summarizer.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_invalid_summarizer(self):
        """Test compress with invalid summarizer raises ValueError."""
        compressor = MemoryCompressor(max_entries=10)
        summarizer = Mock()  # No summarize or generate method
        
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"importance": 0.1, "timestamp": old_time, "content": "Old entry"}
            for _ in range(20)
        ]
        
        result = await compressor.compress(entries, summarizer)
        assert result == entries

    @pytest.mark.asyncio
    async def test_create_summary(self):
        """Test _create_summary method."""
        compressor = MemoryCompressor()
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(return_value="Summary")
        
        entries = [
            {"content": "Entry 1"},
            {"content": "Entry 2"},
        ]
        
        summary = await compressor._create_summary(entries, summarizer)
        
        assert summary == "Summary"
        summarizer.summarize.assert_called_once()

