"""Tests for orka.memory.compressor module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from orka.memory.compressor import MemoryCompressor


class TestMemoryCompressor:
    """Test the MemoryCompressor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.compressor = MemoryCompressor()

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        compressor = MemoryCompressor()

        assert compressor.max_entries == 1000
        assert compressor.importance_threshold == 0.3
        assert compressor.time_window == timedelta(days=7)

    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        compressor = MemoryCompressor(
            max_entries=500,
            importance_threshold=0.5,
            time_window=timedelta(days=3),
        )

        assert compressor.max_entries == 500
        assert compressor.importance_threshold == 0.5
        assert compressor.time_window == timedelta(days=3)

    def test_should_compress_false_few_entries(self):
        """Test should_compress returns False when entries are under max."""
        entries = [
            {"importance": 0.8, "content": "test1"},
            {"importance": 0.7, "content": "test2"},
        ]

        result = self.compressor.should_compress(entries)
        assert result is False

    def test_should_compress_false_high_importance(self):
        """Test should_compress returns False when mean importance is high."""
        # Create entries that exceed max_entries but have high importance
        entries = []
        for i in range(1001):  # Exceeds default max_entries of 1000
            entries.append({"importance": 0.8, "content": f"test{i}"})

        result = self.compressor.should_compress(entries)
        assert result is False

    def test_should_compress_true_low_importance(self):
        """Test should_compress returns True when entries exceed max and have low importance."""
        # Create entries that exceed max_entries with low importance
        entries = []
        for i in range(1001):  # Exceeds default max_entries of 1000
            entries.append({"importance": 0.1, "content": f"test{i}"})  # Below threshold of 0.3

        result = self.compressor.should_compress(entries)
        assert result is True

    @pytest.mark.asyncio
    async def test_compress_no_compression_needed(self):
        """Test compress returns original entries when compression not needed."""
        entries = [
            {"importance": 0.8, "content": "test1"},
            {"importance": 0.7, "content": "test2"},
        ]

        result = await self.compressor.compress(entries, Mock())
        assert result == entries

    @pytest.mark.asyncio
    async def test_compress_no_old_entries(self):
        """Test compress returns original entries when no old entries exist."""
        # All entries are recent (within time window)
        recent_time = datetime.now() - timedelta(hours=1)
        entries = []
        for i in range(1001):  # Exceeds max_entries
            entries.append(
                {
                    "importance": 0.1,  # Low importance to trigger compression
                    "content": f"test{i}",
                    "timestamp": recent_time,
                },
            )

        result = await self.compressor.compress(entries, Mock())
        assert result == entries

    @pytest.mark.asyncio
    async def test_compress_successful_compression(self):
        """Test successful compression with old entries."""
        # Create old entries (outside time window)
        old_time = datetime.now() - timedelta(days=10)
        recent_time = datetime.now() - timedelta(hours=1)

        entries = []
        # Add old entries with low importance
        for i in range(500):
            entries.append(
                {
                    "importance": 0.1,
                    "content": f"old_test{i}",
                    "timestamp": old_time,
                },
            )

        # Add recent entries with low importance
        for i in range(501):  # Total > 1000 to trigger compression
            entries.append(
                {
                    "importance": 0.1,
                    "content": f"recent_test{i}",
                    "timestamp": recent_time,
                },
            )

        # Mock summarizer
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "This is a summary of old entries"

        result = await self.compressor.compress(entries, mock_summarizer)

        # Should have recent entries + 1 summary entry
        assert len(result) == 502  # 501 recent + 1 summary

        # Check summary entry
        summary_entry = result[-1]
        assert summary_entry["content"] == "This is a summary of old entries"
        assert summary_entry["importance"] == 1.0
        assert summary_entry["metadata"]["is_summary"] is True
        assert summary_entry["metadata"]["summarized_entries"] == 500
        assert summary_entry["is_summary"] is True

    @pytest.mark.asyncio
    async def test_compress_summarizer_error(self):
        """Test compress handles summarizer errors gracefully."""
        # Create old entries
        old_time = datetime.now() - timedelta(days=10)
        entries = []
        for i in range(1001):  # Exceeds max_entries
            entries.append(
                {
                    "importance": 0.1,  # Low importance to trigger compression
                    "content": f"test{i}",
                    "timestamp": old_time,
                },
            )

        # Mock summarizer that raises an error
        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.side_effect = Exception("Summarizer error")

        result = await self.compressor.compress(entries, mock_summarizer)

        # Should return original entries when error occurs
        assert result == entries

    @pytest.mark.asyncio
    async def test_create_summary_with_summarize_method(self):
        """Test _create_summary with summarizer that has summarize method."""
        entries = [
            {"content": "First entry content"},
            {"content": "Second entry content"},
            {"content": "Third entry content"},
        ]

        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Combined summary"

        result = await self.compressor._create_summary(entries, mock_summarizer)

        assert result == "Combined summary"
        mock_summarizer.summarize.assert_called_once_with(
            "First entry content\nSecond entry content\nThird entry content",
        )

    @pytest.mark.asyncio
    async def test_create_summary_with_generate_method(self):
        """Test _create_summary with summarizer that has generate method."""
        entries = [
            {"content": "Entry one"},
            {"content": "Entry two"},
        ]

        mock_summarizer = AsyncMock()
        # Remove summarize method to force use of generate
        del mock_summarizer.summarize
        mock_summarizer.generate.return_value = "Generated summary"

        result = await self.compressor._create_summary(entries, mock_summarizer)

        assert result == "Generated summary"
        expected_prompt = "Summarize the following text concisely:\n\nEntry one\nEntry two"
        mock_summarizer.generate.assert_called_once_with(expected_prompt)

    @pytest.mark.asyncio
    async def test_create_summary_invalid_summarizer(self):
        """Test _create_summary raises ValueError with invalid summarizer."""
        entries = [{"content": "Test content"}]

        # Create a mock object without summarize or generate methods
        class InvalidSummarizer:
            pass

        mock_summarizer = InvalidSummarizer()

        with pytest.raises(
            ValueError,
            match="Summarizer must have summarize\\(\\) or generate\\(\\) method",
        ):
            await self.compressor._create_summary(entries, mock_summarizer)

    def test_should_compress_edge_cases(self):
        """Test should_compress with edge cases."""
        # Test with empty entries
        assert self.compressor.should_compress([]) is False

        # Test with exactly max_entries
        entries = []
        for i in range(1000):  # Exactly max_entries
            entries.append({"importance": 0.1, "content": f"test{i}"})

        assert self.compressor.should_compress(entries) is False

    @pytest.mark.asyncio
    async def test_compress_with_mixed_timestamps(self):
        """Test compress with mixed old and recent timestamps."""
        now = datetime.now()
        old_time = now - timedelta(days=10)
        recent_time = now - timedelta(hours=1)

        entries = [
            {"importance": 0.1, "content": "old1", "timestamp": old_time},
            {"importance": 0.1, "content": "recent1", "timestamp": recent_time},
            {"importance": 0.1, "content": "old2", "timestamp": old_time},
            {"importance": 0.1, "content": "recent2", "timestamp": recent_time},
        ]

        # Need more entries to trigger compression
        for i in range(997):
            entries.append(
                {
                    "importance": 0.1,
                    "content": f"filler{i}",
                    "timestamp": old_time,
                },
            )

        mock_summarizer = AsyncMock()
        mock_summarizer.summarize.return_value = "Mixed summary"

        result = await self.compressor.compress(entries, mock_summarizer)

        # Should have recent entries + summary
        recent_count = sum(1 for e in result if not e.get("is_summary", False))
        summary_count = sum(1 for e in result if e.get("is_summary", False))

        assert recent_count == 2  # Only the 2 recent entries
        assert summary_count == 1  # One summary entry
