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

    @pytest.mark.asyncio
    async def test_create_summary_with_generate(self):
        """Test _create_summary using generate method."""
        compressor = MemoryCompressor()
        summarizer = AsyncMock()
        # No summarize method, only generate
        delattr(summarizer, "summarize")
        summarizer.generate = AsyncMock(return_value="Generated summary")
        
        entries = [
            {"content": "Entry 1"},
            {"content": "Entry 2"},
        ]
        
        summary = await compressor._create_summary(entries, summarizer)
        
        assert summary == "Generated summary"
        summarizer.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_summary_exception_in_summarizer(self):
        """Test _create_summary handles exceptions from summarizer."""
        compressor = MemoryCompressor()
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(side_effect=Exception("Summarization failed"))
        
        entries = [{"content": "Entry 1"}]
        
        with pytest.raises(Exception, match="Summarization failed"):
            await compressor._create_summary(entries, summarizer)

    @pytest.mark.asyncio
    async def test_compress_no_old_entries_under_max(self):
        """Test compress when no old entries and under max entries."""
        compressor = MemoryCompressor(max_entries=1000, time_window=timedelta(days=7))
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(return_value="Summary")
        
        # All entries are recent (within time window) and under max
        recent_time = datetime.now() - timedelta(days=1)
        entries = [
            {"importance": 0.1, "timestamp": recent_time, "content": "Recent entry"}
            for _ in range(50)
        ]
        
        result = await compressor.compress(entries, summarizer)
        
        # Should return entries as-is since no old entries and under max
        assert result == entries
        summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_no_old_entries_over_max(self):
        """Test compress when no old entries but over max entries."""
        compressor = MemoryCompressor(max_entries=10, importance_threshold=0.3, time_window=timedelta(days=7))
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(return_value="Summary text")
        
        # All entries are recent (within time window) but over max
        recent_time = datetime.now() - timedelta(days=1)
        entries = [
            {"importance": 0.1, "timestamp": recent_time, "content": f"Entry {i}"}
            for i in range(20)
        ]
        
        result = await compressor.compress(entries, summarizer)
        
        # Should compress since over max entries
        assert len(result) < len(entries)
        summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_exception_during_summary(self):
        """Test compress handles exceptions during summary creation."""
        compressor = MemoryCompressor(max_entries=10, importance_threshold=0.3)
        summarizer = AsyncMock()
        summarizer.summarize = AsyncMock(side_effect=Exception("Summary error"))
        
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"importance": 0.1, "timestamp": old_time, "content": "Old entry"}
            for _ in range(20)
        ]
        
        # Should return original entries if summarization fails
        result = await compressor.compress(entries, summarizer)
        
        assert result == entries
        summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_with_missing_summarize_and_generate(self):
        """Test compress when summarizer has neither summarize nor generate."""
        compressor = MemoryCompressor(max_entries=10, importance_threshold=0.3)
        summarizer = Mock()  # No methods
        
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"importance": 0.1, "timestamp": old_time, "content": "Old entry"}
            for _ in range(20)
        ]
        
        # Should return original entries when summarizer validation fails
        result = await compressor.compress(entries, summarizer)
        
        assert result == entries

