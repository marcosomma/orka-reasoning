"""Provide memory compression by summarizing older entries."""

import logging
from datetime import datetime, timedelta
from typing import List, Protocol

import numpy as np

from ..contracts import MemoryEntry

logger = logging.getLogger(__name__)


class Summarizer(Protocol):
    """Protocol for summarizer objects."""

    async def summarize(self, text: str) -> str:
        """Summarize text."""
        ...

    async def generate(self, prompt: str) -> str:
        """Generate text from prompt."""
        ...


# Default time window for memory compression
DEFAULT_TIME_WINDOW = timedelta(days=7)


class MemoryCompressor:
    """Compress memory by summarizing older entries."""

    def __init__(
        self,
        max_entries: int = 1000,
        importance_threshold: float = 0.3,
        time_window: timedelta = DEFAULT_TIME_WINDOW,
    ) -> None:
        """
        Initialize memory compressor.

        Args:
            max_entries: Maximum number of entries before compression. Defaults to 1000.
            importance_threshold: Threshold for mean importance before compression. Defaults to 0.3.
            time_window: Time window for recent entries. Defaults to 7 days.
        """
        self.max_entries = max_entries
        self.importance_threshold = importance_threshold
        self.time_window = time_window

    def should_compress(self, entries: List[MemoryEntry]) -> bool:
        """
        Check if compression is needed.

        Args:
            entries: List of memory entries to check

        Returns:
            True if compression is needed, False otherwise
        """
        if len(entries) <= self.max_entries:
            return False

        # Check if mean importance is below threshold
        importances = [float(entry["importance"]) for entry in entries]
        if np.mean(importances) < self.importance_threshold:
            return True

        return False

    async def compress(
        self,
        entries: List[MemoryEntry],
        summarizer: Summarizer,  # LLM or summarization model
    ) -> List[MemoryEntry]:
        """
        Compress memory by summarizing older entries.

        Args:
            entries: List of memory entries to compress
            summarizer: Model to use for summarization

        Returns:
            List of compressed memory entries
        """
        if not self.should_compress(entries):
            return entries

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda x: x["timestamp"])

        # Split into recent and old entries
        cutoff_time = datetime.now() - self.time_window
        recent_entries = [e for e in sorted_entries if e["timestamp"] > cutoff_time]
        old_entries = [e for e in sorted_entries if e["timestamp"] <= cutoff_time]

        if not old_entries:
            return entries

        # Create summary of old entries
        try:
            summary = await self._create_summary(old_entries, summarizer)
            summary_entry: MemoryEntry = {
                "content": summary,
                "importance": 1.0,  # High importance for summaries
                "timestamp": datetime.now(),
                "metadata": {"is_summary": True, "summarized_entries": len(old_entries)},
                "is_summary": True,
                "category": "summary",  # Required by MemoryEntry type
            }

            # Return recent entries + summary
            return recent_entries + [summary_entry]

        except Exception as e:
            logger.error(f"Error during memory compression: {e}")
            return entries

    async def _create_summary(self, entries: List[MemoryEntry], summarizer: Summarizer) -> str:
        """
        Create a summary of multiple memory entries.

        Args:
            entries: List of memory entries to summarize
            summarizer: Model to use for summarization

        Returns:
            Summary text

        Raises:
            ValueError: If summarizer lacks required methods
        """
        # Combine all content
        combined_content = "\n".join(str(entry["content"]) for entry in entries)

        # Use summarizer to create summary
        if hasattr(summarizer, "summarize"):
            return await summarizer.summarize(combined_content)
        elif hasattr(summarizer, "generate"):
            return await summarizer.generate(
                f"Summarize the following text concisely:\n\n{combined_content}",
            )
        else:
            raise ValueError("Summarizer must have summarize() or generate() method")
