"""
Data management for TUI interface - statistics, caching, and data fetching.
"""

import os
import time
from collections import deque
from typing import Any, Dict

from ..memory_logger import create_memory_logger


class MemoryStats:
    """Container for memory statistics with historical tracking."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.current: Dict[str, Any] = {}

    def update(self, stats: Dict[str, Any]):
        """Update current stats and add to history."""
        self.current = stats.copy()
        self.current["timestamp"] = time.time()
        self.history.append(self.current.copy())

    def get_trend(self, key: str, window: int = 10) -> str:
        """Get trend direction for a metric."""
        if len(self.history) < 2:
            return "→"

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return "→"

        values = [item.get(key, 0) for item in recent if key in item]
        if len(values) < 2:
            return "→"

        if values[-1] > values[0]:
            return "↗"
        elif values[-1] < values[0]:
            return "↘"
        else:
            return "→"

    def get_rate(self, key: str, window: int = 5) -> float:
        """Get rate of change for a metric (per second)."""
        if len(self.history) < 2:
            return 0.0

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return 0.0

        # Calculate rate between first and last points
        first = recent[0]
        last = recent[-1]

        if key not in first or key not in last:
            return 0.0

        value_diff = last[key] - first[key]
        time_diff = last["timestamp"] - first["timestamp"]

        if time_diff <= 0:
            return 0.0

        return value_diff / time_diff


class DataManager:
    """Manages data fetching and caching for the TUI interface."""

    def __init__(self):
        self.memory_logger = None
        self.backend = None
        self.stats = MemoryStats()
        self.memory_data = []
        self.performance_history = deque(maxlen=60)  # 1 minute at 1s intervals

    def init_memory_logger(self, args):
        """Initialize the memory logger."""
        self.backend = getattr(args, "backend", None) or os.getenv(
            "ORKA_MEMORY_BACKEND",
            "redisstack",
        )

        # Provide proper Redis URL based on backend
        if self.backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.memory_logger = create_memory_logger(backend=self.backend, redis_url=redis_url)

    def update_data(self):
        """Update all monitoring data."""
        try:
            # Get memory statistics
            stats = self.memory_logger.get_memory_stats()
            self.stats.update(stats)

            # Get all memory data (both stored memories and logs)
            all_memories = []

            # Get stored memories
            if hasattr(self.memory_logger, "get_recent_stored_memories"):
                stored_memories = self.memory_logger.get_recent_stored_memories(20)
                all_memories.extend(stored_memories or [])
            elif hasattr(self.memory_logger, "search_memories"):
                stored_memories = self.memory_logger.search_memories(
                    query=" ",
                    num_results=20,
                    log_type="memory",
                )
                all_memories.extend(stored_memories or [])

            # Get orchestration logs
            if hasattr(self.memory_logger, "search_memories"):
                try:
                    orchestration_logs = self.memory_logger.search_memories(
                        query=" ",
                        num_results=20,
                        log_type="orchestration",
                    )
                    all_memories.extend(orchestration_logs or [])
                except Exception:
                    # Some backends might not support this
                    pass

            # Also try to get all entries if the method exists
            if hasattr(self.memory_logger, "get_recent_entries"):
                try:
                    recent_entries = self.memory_logger.get_recent_entries(30)
                    all_memories.extend(recent_entries or [])
                except Exception:
                    pass

            self.memory_data = all_memories

            # Get performance metrics if available
            if hasattr(self.memory_logger, "get_performance_metrics"):
                perf_metrics = self.memory_logger.get_performance_metrics()
                perf_metrics["timestamp"] = time.time()
                self.performance_history.append(perf_metrics)

        except Exception:
            # Log error but continue
            pass

    def is_short_term_memory(self, memory):
        """Check if a memory entry is short-term (TTL < 1 hour)."""
        ttl = (
            memory.get("ttl_seconds")
            or memory.get("ttl")
            or memory.get("expires_at")
            or memory.get("expiry")
        )
        if ttl is None or ttl == "" or ttl == -1:
            return False
        try:
            # Handle string TTL values
            if isinstance(ttl, str):
                if ttl.lower() in ["none", "null", "infinite", "∞", ""]:
                    return False
                ttl_val = int(float(ttl))
            else:
                ttl_val = int(ttl)

            if ttl_val <= 0:
                return False
            return ttl_val < 3600  # Less than 1 hour
        except (ValueError, TypeError):
            return False

    def get_filtered_memories(self, memory_type="all"):
        """Get memories filtered by type."""
        if memory_type == "short":
            # Only memory type entries that are short-term
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) == "memory" and self.is_short_term_memory(m)
            ]
        elif memory_type == "long":
            # Only memory type entries that are long-term
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) == "memory" and not self.is_short_term_memory(m)
            ]
        elif memory_type == "logs":
            # All log entries (not memory type)
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) in ["log", "orchestration", "system"]
            ]
        else:
            return self.memory_data

    def _get_log_type(self, memory):
        """Extract log type from memory entry."""
        metadata = memory.get("metadata", {})
        return metadata.get("log_type") or memory.get("log_type") or memory.get("type") or "unknown"

    def _get_content(self, memory):
        """Extract and decode content from memory entry."""
        content = memory.get("content") or memory.get("message") or memory.get("data") or ""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")
        return content

    def _get_key(self, memory):
        """Extract and decode key from memory entry."""
        key = memory.get("key") or memory.get("id") or memory.get("node_id") or "unknown"
        if isinstance(key, bytes):
            key = key.decode("utf-8", errors="ignore")
        return key

    def debug_memory_data(self):
        """Debug method to inspect memory data structure."""
        print(f"Total memories: {len(self.memory_data)}")
        for i, memory in enumerate(self.memory_data[:3]):  # Show first 3 entries
            print(f"Memory {i}: {memory}")

        # Count by type
        type_counts = {}
        for memory in self.memory_data:
            log_type = self._get_log_type(memory)
            type_counts[log_type] = type_counts.get(log_type, 0) + 1

        print(f"Type counts: {type_counts}")

        # Check TTL values
        ttl_values = [m.get("ttl") for m in self.memory_data if m.get("ttl") is not None]
        print(f"TTL values sample: {ttl_values[:5]}")

        return {
            "total": len(self.memory_data),
            "types": type_counts,
            "ttl_sample": ttl_values[:5],
        }
