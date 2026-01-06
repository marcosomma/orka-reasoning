# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

import logging
from datetime import datetime, timedelta
from typing import Any, List

import numpy as np

from ..contracts import MemoryEntry

logger = logging.getLogger(__name__)


class MemoryCompressor:
    """Compresses memory by summarizing older entries."""

    def __init__(
        self,
        max_entries: int = 1000,
        importance_threshold: float = 0.3,
        time_window: timedelta = timedelta(days=7),
    ):
        self.max_entries = max_entries
        self.importance_threshold = importance_threshold
        self.time_window = time_window

    def should_compress(self, entries: List[MemoryEntry]) -> bool:
        """Check if compression is needed."""
        if len(entries) <= self.max_entries:
            return False

        # Check if mean importance is below threshold
        importances = [entry.get("importance", 0.0) for entry in entries]
        mean_importance = np.mean(importances) if importances else 0.0

        # Compress only if both conditions are met:
        # 1. Too many entries
        # 2. Low average importance
        return bool(len(entries) > self.max_entries and mean_importance < self.importance_threshold)

    async def compress(
        self,
        entries: List[MemoryEntry],
        summarizer: Any,  # LLM or summarization model
    ) -> List[MemoryEntry]:
        """Compress memory by summarizing older entries."""
        if not entries:
            return entries

        if not self.should_compress(entries):
            return entries

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda x: x.get("timestamp", datetime.min))

        # Split into recent and old entries
        cutoff_time = datetime.now() - self.time_window
        recent_entries = [
            e for e in sorted_entries if e.get("timestamp", datetime.min) > cutoff_time
        ]
        old_entries = [e for e in sorted_entries if e.get("timestamp", datetime.min) <= cutoff_time]

        # If no old entries, try to compress based on max entries
        if not old_entries and len(entries) > self.max_entries:
            split_point = len(entries) - self.max_entries
            old_entries = sorted_entries[:split_point]
            recent_entries = sorted_entries[split_point:]
        elif not old_entries:
            # No old entries and not over max entries, return as is
            return entries

        # Check summarizer type first
        if not (hasattr(summarizer, "summarize") or hasattr(summarizer, "generate")):
            msg = "Summarizer must have summarize() or generate() method"
            logger.error(f"Error during memory compression: {msg}")
            raise ValueError(msg)

        # Create summary of old entries
        try:
            summary = await self._create_summary(old_entries, summarizer)
            summary_entry: MemoryEntry = {
                "content": summary,
                "importance": 1.0,  # High importance for summaries
                "timestamp": datetime.now(),
                "metadata": {"is_summary": True, "summarized_entries": len(old_entries)},
                "is_summary": True,
                "category": "summary",  # Add a category for summaries
            }

            # Return recent entries + summary
            return recent_entries + [summary_entry]

        except Exception as e:
            logger.error(f"Error during memory compression: {e}")
            return entries

    async def _create_summary(self, entries: List[MemoryEntry], summarizer: Any) -> str:
        """Create a summary of multiple memory entries."""
        # Combine all content
        combined_content = "\n".join(entry.get("content", "") for entry in entries)

        # Check summarizer type first to avoid unnecessary try/except
        if not (hasattr(summarizer, "summarize") or hasattr(summarizer, "generate")):
            msg = "Summarizer must have summarize() or generate() method"
            logger.error(f"Error during memory compression: {msg}")
            raise ValueError(msg)

        # Use summarizer to create summary
        try:
            if hasattr(summarizer, "summarize"):
                result = await summarizer.summarize(combined_content)
                return str(result)
            else:  # Must have generate() method
                result = await summarizer.generate(
                    f"Summarize the following text concisely:\n\n{combined_content}",
                )
                return str(result)
        except Exception as e:
            logger.error(f"Error during memory compression: {e}")
            raise
