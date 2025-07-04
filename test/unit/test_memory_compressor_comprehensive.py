"""Test Memory Compressor Comprehensive."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.memory.compressor import MemoryCompressor


class TestMemoryCompressor:
    """Test cases for MemoryCompressor."""

    def test_init_default_values(self):
        """Test MemoryCompressor initialization with default values."""
        compressor = MemoryCompressor()

        assert compressor.max_entries == 1000
        assert compressor.importance_threshold == 0.3
        assert compressor.time_window == timedelta(days=7)

    def test_init_custom_values(self):
        """Test MemoryCompressor initialization with custom values."""
        compressor = MemoryCompressor(
            max_entries=500,
            importance_threshold=0.5,
            time_window=timedelta(days=3),
        )

        assert compressor.max_entries == 500
        assert compressor.importance_threshold == 0.5
        assert compressor.time_window == timedelta(days=3)

    def test_should_compress_false_entries_below_max(self):
        """Test should_compress returns False when entries below max."""
        compressor = MemoryCompressor(max_entries=1000)

        entries = [{"importance": 0.5, "content": "test"} for _ in range(500)]

        assert not compressor.should_compress(entries)

    def test_should_compress_false_entries_at_max(self):
        """Test should_compress returns False when entries equal max."""
        compressor = MemoryCompressor(max_entries=1000)

        entries = [{"importance": 0.5, "content": "test"} for _ in range(1000)]

        assert not compressor.should_compress(entries)

    def test_should_compress_true_entries_above_max_low_importance(self):
        """Test should_compress returns True when entries above max and low importance."""
        compressor = MemoryCompressor(max_entries=100, importance_threshold=0.5)

        entries = [{"importance": 0.2, "content": "test"} for _ in range(150)]

        assert compressor.should_compress(entries)

    def test_should_compress_false_entries_above_max_high_importance(self):
        """Test should_compress returns False when entries above max but high importance."""
        compressor = MemoryCompressor(max_entries=100, importance_threshold=0.5)

        entries = [{"importance": 0.8, "content": "test"} for _ in range(150)]

        assert not compressor.should_compress(entries)

    def test_should_compress_mixed_importance(self):
        """Test should_compress with mixed importance values."""
        compressor = MemoryCompressor(max_entries=100, importance_threshold=0.5)

        entries = [
            {"importance": 0.2, "content": "test1"},
            {"importance": 0.3, "content": "test2"},
            {"importance": 0.4, "content": "test3"},
            {"importance": 0.6, "content": "test4"},
        ] * 30  # 120 entries with mean importance 0.375

        assert compressor.should_compress(entries)

    @pytest.mark.asyncio
    async def test_compress_no_compression_needed(self):
        """Test compress returns original entries when compression not needed."""
        compressor = MemoryCompressor(max_entries=1000)
        summarizer = MagicMock()

        entries = [
            {"importance": 0.5, "content": "test", "timestamp": datetime.now()} for _ in range(100)
        ]

        result = await compressor.compress(entries, summarizer)

        assert result == entries
        summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_no_old_entries(self):
        """Test compress with all recent entries."""
        compressor = MemoryCompressor(max_entries=10, time_window=timedelta(days=1))
        summarizer = MagicMock()

        # All entries are recent (within 1 day)
        now = datetime.now()
        entries = [
            {"importance": 0.2, "content": f"test{i}", "timestamp": now - timedelta(hours=i)}
            for i in range(15)
        ]

        result = await compressor.compress(entries, summarizer)

        assert result == entries
        summarizer.summarize.assert_not_called()

    @pytest.mark.asyncio
    async def test_compress_with_old_entries_summarize_method(self):
        """Test compress with old entries using summarize method."""
        compressor = MemoryCompressor(max_entries=10, time_window=timedelta(days=1))
        summarizer = AsyncMock()
        summarizer.summarize.return_value = "Summary of old entries"

        now = datetime.now()
        recent_entries = [
            {"importance": 0.2, "content": f"recent{i}", "timestamp": now - timedelta(hours=i)}
            for i in range(5)
        ]
        old_entries = [
            {"importance": 0.2, "content": f"old{i}", "timestamp": now - timedelta(days=i + 2)}
            for i in range(10)
        ]

        entries = recent_entries + old_entries

        with patch("orka.memory.compressor.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = await compressor.compress(entries, summarizer)

        # Should have recent entries + 1 summary entry
        assert len(result) == 6

        # Check summary entry
        summary_entry = result[-1]
        assert summary_entry["content"] == "Summary of old entries"
        assert summary_entry["importance"] == 1.0
        assert summary_entry["metadata"]["is_summary"] is True
        assert summary_entry["metadata"]["summarized_entries"] == 10
        assert summary_entry["is_summary"] is True

        # Verify summarizer was called correctly
        summarizer.summarize.assert_called_once()
        call_args = summarizer.summarize.call_args[0][0]
        assert "old0" in call_args
        assert "old9" in call_args

    @pytest.mark.asyncio
    async def test_compress_with_old_entries_generate_method(self):
        """Test compress with old entries using generate method."""
        compressor = MemoryCompressor(max_entries=10, time_window=timedelta(days=1))
        summarizer = AsyncMock()
        summarizer.generate.return_value = "Generated summary"
        # Remove summarize method to force use of generate
        del summarizer.summarize

        now = datetime.now()
        recent_entries = [
            {"importance": 0.2, "content": f"recent{i}", "timestamp": now - timedelta(hours=i)}
            for i in range(3)
        ]
        old_entries = [
            {"importance": 0.2, "content": f"old{i}", "timestamp": now - timedelta(days=i + 2)}
            for i in range(8)
        ]

        entries = recent_entries + old_entries

        with patch("orka.memory.compressor.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = await compressor.compress(entries, summarizer)

        # Should have recent entries + 1 summary entry
        assert len(result) == 4

        # Check summary entry
        summary_entry = result[-1]
        assert summary_entry["content"] == "Generated summary"
        assert summary_entry["importance"] == 1.0

        # Verify generate was called with correct prompt
        summarizer.generate.assert_called_once()
        call_args = summarizer.generate.call_args[0][0]
        assert "Summarize the following text concisely:" in call_args
        assert "old0" in call_args

    @pytest.mark.asyncio
    async def test_compress_summarizer_error(self):
        """Test compress handles summarizer errors gracefully."""
        compressor = MemoryCompressor(max_entries=10, time_window=timedelta(days=1))
        summarizer = AsyncMock()
        summarizer.summarize.side_effect = Exception("Summarizer failed")

        now = datetime.now()
        recent_entries = [
            {"importance": 0.2, "content": f"recent{i}", "timestamp": now - timedelta(hours=i)}
            for i in range(5)
        ]
        old_entries = [
            {"importance": 0.2, "content": f"old{i}", "timestamp": now - timedelta(days=i + 2)}
            for i in range(10)
        ]

        entries = recent_entries + old_entries

        with patch("orka.memory.compressor.logger") as mock_logger:
            result = await compressor.compress(entries, summarizer)

        # Should return original entries on error
        assert result == entries

        # Should log the error
        mock_logger.error.assert_called_once()
        assert "Error during memory compression" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_create_summary_with_summarize_method(self):
        """Test _create_summary with summarize method."""
        compressor = MemoryCompressor()
        summarizer = AsyncMock()
        summarizer.summarize.return_value = "Test summary"

        entries = [
            {"content": "First entry"},
            {"content": "Second entry"},
            {"content": "Third entry"},
        ]

        result = await compressor._create_summary(entries, summarizer)

        assert result == "Test summary"
        summarizer.summarize.assert_called_once_with("First entry\nSecond entry\nThird entry")

    @pytest.mark.asyncio
    async def test_create_summary_with_generate_method(self):
        """Test _create_summary with generate method."""
        compressor = MemoryCompressor()
        summarizer = AsyncMock()
        summarizer.generate.return_value = "Generated summary"
        # Remove summarize method
        del summarizer.summarize

        entries = [
            {"content": "Entry one"},
            {"content": "Entry two"},
        ]

        result = await compressor._create_summary(entries, summarizer)

        assert result == "Generated summary"
        expected_prompt = "Summarize the following text concisely:\n\nEntry one\nEntry two"
        summarizer.generate.assert_called_once_with(expected_prompt)

    @pytest.mark.asyncio
    async def test_create_summary_invalid_summarizer(self):
        """Test _create_summary with invalid summarizer."""
        compressor = MemoryCompressor()

        # Create a mock without summarize or generate methods
        class InvalidSummarizer:
            pass

        summarizer = InvalidSummarizer()
        entries = [{"content": "Test entry"}]

        with pytest.raises(
            ValueError,
            match="Summarizer must have summarize\\(\\) or generate\\(\\) method",
        ):
            await compressor._create_summary(entries, summarizer)

    @pytest.mark.asyncio
    async def test_compress_entry_sorting(self):
        """Test that compress sorts entries by timestamp correctly."""
        compressor = MemoryCompressor(max_entries=5, time_window=timedelta(days=1))
        summarizer = AsyncMock()
        summarizer.summarize.return_value = "Sorted summary"

        now = datetime.now()

        # Create entries with timestamps out of order
        entries = [
            {"importance": 0.2, "content": "newest", "timestamp": now - timedelta(hours=1)},
            {"importance": 0.2, "content": "oldest", "timestamp": now - timedelta(days=5)},
            {"importance": 0.2, "content": "middle", "timestamp": now - timedelta(hours=12)},
            {"importance": 0.2, "content": "old", "timestamp": now - timedelta(days=3)},
        ] * 2  # 8 entries total

        with patch("orka.memory.compressor.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = await compressor.compress(entries, summarizer)

        # Should have recent entries (within 1 day) + summary
        recent_contents = [entry["content"] for entry in result[:-1]]
        assert "newest" in recent_contents
        assert "middle" in recent_contents

        # Check that old entries were summarized
        summarizer.summarize.assert_called_once()
        summarized_content = summarizer.summarize.call_args[0][0]
        assert "oldest" in summarized_content
        assert "old" in summarized_content

    def test_should_compress_edge_case_empty_entries(self):
        """Test should_compress with empty entries list."""
        compressor = MemoryCompressor(max_entries=100)

        assert not compressor.should_compress([])

    def test_should_compress_edge_case_single_entry(self):
        """Test should_compress with single entry."""
        compressor = MemoryCompressor(max_entries=0, importance_threshold=0.5)

        entries = [{"importance": 0.2, "content": "single"}]

        assert compressor.should_compress(entries)

    @pytest.mark.asyncio
    async def test_compress_all_entries_old(self):
        """Test compress when all entries are old."""
        compressor = MemoryCompressor(max_entries=5, time_window=timedelta(days=1))
        summarizer = AsyncMock()
        summarizer.summarize.return_value = "All old summary"

        now = datetime.now()

        # All entries are older than 1 day
        entries = [
            {"importance": 0.2, "content": f"old{i}", "timestamp": now - timedelta(days=i + 2)}
            for i in range(10)
        ]

        with patch("orka.memory.compressor.datetime") as mock_dt:
            mock_dt.now.return_value = now
            result = await compressor.compress(entries, summarizer)

        # Should have only 1 summary entry
        assert len(result) == 1
        assert result[0]["content"] == "All old summary"
        assert result[0]["is_summary"] is True
        assert result[0]["metadata"]["summarized_entries"] == 10
