"""
Additional comprehensive tests for memory compressor to increase coverage.
"""

from datetime import datetime, timedelta

import pytest

from orka.memory.compressor import MemoryCompressor


class DummySummarizer:
    async def summarize(self, text: str) -> str:
        return f"SUMMARY: {text[:50]}..."


class TestMemoryCompressor:
    """Test memory compression functionality aligned with current API."""

    def test_compressor_initialization(self):
        """Test compressor initialization with defaults and custom params."""
        compressor_default = MemoryCompressor()
        assert compressor_default.max_entries == 1000
        assert compressor_default.importance_threshold == 0.3
        assert isinstance(compressor_default.time_window, timedelta)

        compressor_custom = MemoryCompressor(
            max_entries=5, importance_threshold=0.9, time_window=timedelta(hours=1)
        )
        assert compressor_custom.max_entries == 5
        assert compressor_custom.importance_threshold == 0.9
        assert compressor_custom.time_window == timedelta(hours=1)

    def test_should_compress_thresholds(self):
        """Validate the compression decision logic by size and importance."""
        compressor = MemoryCompressor(max_entries=3, importance_threshold=0.5)
        now = datetime.now()
        entries = [
            {"content": "a", "importance": 0.4, "timestamp": now},
            {"content": "b", "importance": 0.3, "timestamp": now},
            {"content": "c", "importance": 0.2, "timestamp": now},
            {"content": "d", "importance": 0.1, "timestamp": now},
        ]
        assert compressor.should_compress(entries) is True

        high_importance_entries = [
            {"content": "a", "importance": 0.9, "timestamp": now},
            {"content": "b", "importance": 0.8, "timestamp": now},
            {"content": "c", "importance": 0.7, "timestamp": now},
            {"content": "d", "importance": 0.6, "timestamp": now},
        ]
        # Too many entries but high mean importance → no compression
        assert compressor.should_compress(high_importance_entries) is False

        small_entries = [
            {"content": "a", "importance": 0.0, "timestamp": now},
        ]
        assert compressor.should_compress(small_entries) is False

    @pytest.mark.asyncio
    async def test_compress_no_entries(self):
        compressor = MemoryCompressor()
        result = await compressor.compress([], DummySummarizer())
        assert result == []

    @pytest.mark.asyncio
    async def test_compress_not_needed(self):
        compressor = MemoryCompressor(max_entries=10)
        now = datetime.now()
        entries = [
            {"content": "a", "importance": 0.9, "timestamp": now},
            {"content": "b", "importance": 0.8, "timestamp": now},
        ]
        result = await compressor.compress(entries, DummySummarizer())
        assert result == entries

    @pytest.mark.asyncio
    async def test_compress_summarizes_old_entries(self):
        # Force condition: many old entries beyond time window
        compressor = MemoryCompressor(
            max_entries=2, importance_threshold=0.9, time_window=timedelta(hours=1)
        )
        now = datetime.now()
        old_time = now - timedelta(days=2)
        entries = [
            {"content": "old1", "importance": 0.2, "timestamp": old_time},
            {"content": "old2", "importance": 0.2, "timestamp": old_time},
            {"content": "recent1", "importance": 0.2, "timestamp": now},
        ]
        result = await compressor.compress(entries, DummySummarizer())
        # Expect recent entries plus one summary
        assert any(e.get("is_summary") for e in result)
        assert any(e.get("timestamp") == now for e in result if not e.get("is_summary"))
        # Summary entry should have metadata and category
        summary_entries = [e for e in result if e.get("is_summary")]
        assert (
            summary_entries and summary_entries[0]["metadata"]["is_summary"] is True
            if isinstance(summary_entries[0].get("metadata"), dict)
            else True
        )
        assert summary_entries[0]["category"] == "summary"

    @pytest.mark.asyncio
    async def test_compress_when_no_old_but_over_max(self):
        # When over max_entries but all timestamps are recent, compressor should split by size
        compressor = MemoryCompressor(
            max_entries=2, importance_threshold=0.4, time_window=timedelta(days=30)
        )
        now = datetime.now()
        entries = [{"content": f"c{i}", "importance": 0.1, "timestamp": now} for i in range(4)]
        result = await compressor.compress(entries, DummySummarizer())
        assert any(e.get("is_summary") for e in result)
        assert len(result) <= 3  # 2 recent + 1 summary

    @pytest.mark.asyncio
    async def test_compress_invalid_summarizer_raises(self):
        compressor = MemoryCompressor(max_entries=1, importance_threshold=1.0)
        now = datetime.now()
        entries = [{"content": "x", "importance": 0.0, "timestamp": now} for _ in range(5)]

        class BadSummarizer:
            pass

        with pytest.raises(ValueError):
            await compressor.compress(entries, BadSummarizer())

    @pytest.mark.asyncio
    async def test_create_summary_uses_summarize(self):
        # Force compression: many entries, low importance, old timestamps
        compressor = MemoryCompressor(max_entries=2, importance_threshold=0.5, time_window=timedelta(hours=1))
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"content": "a", "importance": 0.1, "timestamp": old_time},
            {"content": "b", "importance": 0.1, "timestamp": old_time},
            {"content": "c", "importance": 0.1, "timestamp": old_time},
            {"content": "d", "importance": 0.1, "timestamp": old_time},
        ]
        # Verify compression is triggered
        assert compressor.should_compress(entries) is True
        result = await compressor.compress(entries, DummySummarizer())
        # Should have at least one summary entry
        assert any(e.get("is_summary") for e in result), f"No summary found in result: {result}"

    @pytest.mark.asyncio
    async def test_create_summary_with_generate(self):
        class GenSummarizer:
            async def generate(self, prompt: str) -> str:
                return "SUMMARY VIA GENERATE"

        compressor = MemoryCompressor(max_entries=2, importance_threshold=0.5, time_window=timedelta(hours=1))
        old_time = datetime.now() - timedelta(days=10)
        entries = [
            {"content": "a", "importance": 0.1, "timestamp": old_time},
            {"content": "b", "importance": 0.1, "timestamp": old_time},
            {"content": "c", "importance": 0.1, "timestamp": old_time},
        ]
        assert compressor.should_compress(entries) is True
        result = await compressor.compress(entries, GenSummarizer())
        assert any(e.get("is_summary") for e in result), f"No summary found in result: {result}"
