# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning
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
        importances = [entry.importance for entry in entries]
        if np.mean(importances) < self.importance_threshold:
            return True

        return False

    async def compress(
        self,
        entries: List[MemoryEntry],
        summarizer: Any,  # LLM or summarization model
    ) -> List[MemoryEntry]:
        """Compress memory by summarizing older entries."""
        if not self.should_compress(entries):
            return entries

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda x: x.timestamp)

        # Split into recent and old entries
        cutoff_time = datetime.now() - self.time_window
        recent_entries = [e for e in sorted_entries if e.timestamp > cutoff_time]
        old_entries = [e for e in sorted_entries if e.timestamp <= cutoff_time]

        if not old_entries:
            return entries

        # Create summary of old entries
        try:
            summary = await self._create_summary(old_entries, summarizer)
            summary_entry = MemoryEntry(
                content=summary,
                importance=1.0,  # High importance for summaries
                timestamp=datetime.now(),
                metadata={"is_summary": True, "summarized_entries": len(old_entries)},
                is_summary=True,
            )

            # Return recent entries + summary
            return recent_entries + [summary_entry]

        except Exception as e:
            logger.error(f"Error during memory compression: {e}")
            return entries

    async def _create_summary(self, entries: List[MemoryEntry], summarizer: Any) -> str:
        """Create a summary of multiple memory entries."""
        # Combine all content
        combined_content = "\n".join(entry.content for entry in entries)

        # Use summarizer to create summary
        if hasattr(summarizer, "summarize"):
            return await summarizer.summarize(combined_content)
        elif hasattr(summarizer, "generate"):
            return await summarizer.generate(
                f"Summarize the following text concisely:\n\n{combined_content}"
            )
        else:
            raise ValueError("Summarizer must have summarize() or generate() method")
