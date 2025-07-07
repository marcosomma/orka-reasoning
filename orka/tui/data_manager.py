"""
Data management for TUI interface - statistics, caching, and data fetching.
"""

import os
import time
from collections import deque
from typing import Any

from ..memory_logger import create_memory_logger


class MemoryStats:
    """Container for memory statistics with historical tracking."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.current: dict[str, Any] = {}

    def update(self, stats: dict[str, Any]):
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

            # 🎯 FIX: Collect memories with deduplication by key
            memory_dict = {}  # Use dict to deduplicate by key

            # Get stored memories
            if hasattr(self.memory_logger, "get_recent_stored_memories"):
                stored_memories = self.memory_logger.get_recent_stored_memories(20)
                if stored_memories:
                    for memory in stored_memories:
                        key = self._get_key(memory)
                        memory_dict[key] = memory

            # Only add search results if we didn't get stored memories above
            elif hasattr(self.memory_logger, "search_memories"):
                stored_memories = self.memory_logger.search_memories(
                    query=" ",
                    num_results=20,
                    log_type="memory",
                )
                if stored_memories:
                    for memory in stored_memories:
                        key = self._get_key(memory)
                        memory_dict[key] = memory

            # Get orchestration logs (separate search, different log_type)
            if hasattr(self.memory_logger, "search_memories"):
                try:
                    orchestration_logs = self.memory_logger.search_memories(
                        query=" ",
                        num_results=20,
                        log_type="log",  # 🎯 FIX: Use "log" instead of "orchestration"
                    )
                    if orchestration_logs:
                        for memory in orchestration_logs:
                            key = self._get_key(memory)
                            # Only add if not already present (avoid duplicates)
                            if key not in memory_dict:
                                memory_dict[key] = memory
                except Exception:
                    # Some backends might not support this
                    pass

            # Convert back to list
            self.memory_data = list(memory_dict.values())

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

    def _get_memory_type(self, memory):
        """Get the actual memory_type field from memory entry."""
        # First check direct memory_type field
        memory_type = memory.get("memory_type")
        if memory_type:
            # 🎯 FIX: Handle bytes values from Redis
            if isinstance(memory_type, bytes):
                memory_type = memory_type.decode("utf-8", errors="ignore")
            if memory_type in ["short_term", "long_term"]:
                return memory_type

        # Check in metadata
        metadata = memory.get("metadata", {})
        memory_type = metadata.get("memory_type")
        if memory_type:
            # 🎯 FIX: Handle bytes values from Redis
            if isinstance(memory_type, bytes):
                memory_type = memory_type.decode("utf-8", errors="ignore")
            if memory_type in ["short_term", "long_term"]:
                return memory_type

        # Default fallback
        return "unknown"

    def get_filtered_memories(self, memory_type="all"):
        """Get memories filtered by type using actual memory_type field."""
        if memory_type == "short":
            # 🎯 FIX: Use actual memory_type field instead of TTL
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) == "memory" and self._get_memory_type(m) == "short_term"
            ]

        elif memory_type == "long":
            # 🎯 FIX: Use actual memory_type field instead of TTL
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) == "memory" and self._get_memory_type(m) == "long_term"
            ]

        elif memory_type == "logs":
            # All log entries (not memory type)
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m)
                in ["log", "system"]  # 🎯 FIX: Use "log" instead of "orchestration"
            ]
        else:
            return self.memory_data

    def _get_log_type(self, memory):
        """Extract log type from memory entry."""
        metadata = memory.get("metadata", {})
        return (
            self._safe_decode(metadata.get("log_type"))
            or self._safe_decode(memory.get("log_type"))
            or self._safe_decode(memory.get("type"))
            or "unknown"
        )

    def _get_content(self, memory):
        """Extract and decode content from memory entry."""
        content = memory.get("content") or memory.get("message") or memory.get("data") or ""
        return self._safe_decode(content)

    def _get_key(self, memory):
        """Extract and decode key from memory entry."""
        key = memory.get("key") or memory.get("id") or memory.get("node_id") or "unknown"
        return self._safe_decode(key)

    def _get_node_id(self, memory):
        """Extract and decode node_id from memory entry."""
        return self._get_safe_field(memory, "node_id", "node", "id", default="unknown")

    def _get_timestamp(self, memory):
        """Extract timestamp from memory entry."""
        timestamp = memory.get("timestamp", 0)
        if isinstance(timestamp, bytes):
            try:
                return int(timestamp.decode())
            except:
                return 0
        return int(timestamp) if timestamp else 0

    def _get_importance_score(self, memory):
        """Extract importance score from memory entry."""
        score = memory.get("importance_score", 0)
        if isinstance(score, bytes):
            try:
                return float(score.decode())
            except:
                return 0.0
        return float(score) if score else 0.0

    def _get_ttl_formatted(self, memory):
        """Extract formatted TTL from memory entry."""
        return self._get_safe_field(memory, "ttl_formatted", "ttl", default="?")

    def get_memory_distribution(self):
        """Get distribution of memory types and log types for diagnostic purposes."""
        distribution = {
            "total_entries": len(self.memory_data),
            "by_log_type": {},
            "by_memory_type": {},
            "stored_memories": {
                "total": 0,
                "short_term": 0,
                "long_term": 0,
                "unknown": 0,
            },
            "log_entries": {
                "total": 0,
                "by_type": {},
            },
        }

        for memory in self.memory_data:
            log_type = self._get_log_type(memory)
            memory_type = self._get_memory_type(memory)

            # Count by log type
            distribution["by_log_type"][log_type] = distribution["by_log_type"].get(log_type, 0) + 1

            # Count by memory type for stored memories
            if log_type == "memory":
                distribution["stored_memories"]["total"] += 1
                distribution["stored_memories"][memory_type] += 1
            else:
                distribution["log_entries"]["total"] += 1
                distribution["log_entries"]["by_type"][log_type] = (
                    distribution["log_entries"]["by_type"].get(log_type, 0) + 1
                )

            # Overall memory type distribution
            distribution["by_memory_type"][memory_type] = (
                distribution["by_memory_type"].get(memory_type, 0) + 1
            )

        return distribution

    # 🎯 NEW: Unified Data Calculation System
    def get_unified_stats(self):
        """
        Get unified, comprehensive statistics for all TUI components.
        This replaces scattered calculations throughout the TUI system.
        """
        # Calculate distribution once
        distribution = self.get_memory_distribution()

        # Get backend stats
        backend_stats = self.stats.current

        # 🎯 UNIFIED: Calculate all core metrics consistently
        unified_stats = {
            # === CORE COUNTS ===
            "total_entries": distribution["total_entries"],
            "stored_memories": {
                "total": distribution["stored_memories"]["total"],
                "short_term": distribution["stored_memories"]["short_term"],
                "long_term": distribution["stored_memories"]["long_term"],
                "unknown": distribution["stored_memories"]["unknown"],
            },
            "log_entries": {
                "total": distribution["log_entries"]["total"],
                "orchestration": distribution["by_log_type"].get("log", 0),
                "system": distribution["by_log_type"].get("system", 0),
                "by_type": distribution["log_entries"]["by_type"],
            },
            # === BACKEND METRICS ===
            "backend": {
                "type": self.backend,
                "connected": self.memory_logger is not None,
                "active_entries": backend_stats.get("active_entries", 0),
                "expired_entries": backend_stats.get("expired_entries", 0),
                "total_streams": backend_stats.get("total_streams", 0),
                "decay_enabled": backend_stats.get("decay_enabled", False),
            },
            # === PERFORMANCE METRICS ===
            "performance": {
                "has_data": len(self.performance_history) > 0,
                "latest": self.performance_history[-1] if self.performance_history else {},
                "search_time": self.performance_history[-1].get("average_search_time", 0)
                if self.performance_history
                else 0,
            },
            # === HEALTH INDICATORS ===
            "health": {
                "overall": self._calculate_overall_health(),
                "memory": self._calculate_memory_health(),
                "backend": self._calculate_backend_health(),
                "performance": self._calculate_performance_health(),
            },
            # === TRENDS (based on historical data) ===
            "trends": {
                "total_entries": self.stats.get_trend("total_entries"),
                "stored_memories": self.stats.get_trend("stored_memories"),
                "orchestration_logs": self.stats.get_trend("orchestration_logs"),
                "active_entries": self.stats.get_trend("active_entries"),
            },
            # === RATES (items per second) ===
            "rates": {
                "total_entries": self.stats.get_rate("total_entries"),
                "stored_memories": self.stats.get_rate("stored_memories"),
                "orchestration_logs": self.stats.get_rate("orchestration_logs"),
            },
            # === RAW DISTRIBUTION (for debugging) ===
            "raw_distribution": distribution,
        }

        return unified_stats

    def _calculate_overall_health(self):
        """Calculate overall system health status."""
        if not self.memory_logger:
            return {"status": "critical", "icon": "🔴", "message": "No Connection"}

        stats = self.stats.current
        total = stats.get("total_entries", 0)
        expired = stats.get("expired_entries", 0)

        if total == 0:
            return {"status": "warning", "icon": "🟡", "message": "No Data"}

        expired_ratio = expired / total if total > 0 else 0

        if expired_ratio < 0.1:
            return {"status": "healthy", "icon": "🟢", "message": "Healthy"}
        elif expired_ratio < 0.3:
            return {"status": "degraded", "icon": "🟡", "message": "Degraded"}
        else:
            return {"status": "critical", "icon": "🔴", "message": "Critical"}

    def _calculate_memory_health(self):
        """Calculate memory system health."""
        stats = self.stats.current
        total = stats.get("total_entries", 0)
        active = stats.get("active_entries", 0)
        expired = stats.get("expired_entries", 0)

        if total == 0:
            return {"status": "warning", "icon": "🟡", "message": "No Data"}

        expired_ratio = expired / total if total > 0 else 0
        active_ratio = active / total if total > 0 else 0

        if expired_ratio < 0.1 and active_ratio > 0.8:
            return {"status": "healthy", "icon": "🟢", "message": "Healthy"}
        elif expired_ratio < 0.3:
            return {"status": "degraded", "icon": "🟡", "message": "Degraded"}
        else:
            return {"status": "critical", "icon": "🔴", "message": "Critical"}

    def _calculate_backend_health(self):
        """Calculate backend connection health."""
        if not self.memory_logger:
            return {"status": "critical", "icon": "🔴", "message": "Disconnected"}

        try:
            # Test basic connectivity - check for different client attribute names
            if hasattr(self.memory_logger, "redis_client"):
                # RedisStack and Redis loggers use redis_client
                try:
                    # Test actual connectivity with ping
                    ping_result = self.memory_logger.redis_client.ping()
                    if ping_result:
                        return {"status": "healthy", "icon": "🟢", "message": "Connected"}
                    else:
                        return {"status": "warning", "icon": "🟡", "message": "Limited"}
                except:
                    return {"status": "warning", "icon": "🟡", "message": "Limited"}
            elif hasattr(self.memory_logger, "client"):
                # Other memory loggers might use client
                return {"status": "healthy", "icon": "🟢", "message": "Connected"}
            else:
                # Memory logger exists but no known client attribute
                return {"status": "warning", "icon": "🟡", "message": "Limited"}
        except:
            return {"status": "critical", "icon": "🔴", "message": "Error"}

    def _calculate_performance_health(self):
        """Calculate performance health."""
        if not self.performance_history:
            return {"status": "unknown", "icon": "❓", "message": "No Data"}

        latest = self.performance_history[-1]
        search_time = latest.get("average_search_time", 0)

        if search_time < 0.1:
            return {"status": "excellent", "icon": "⚡", "message": "Fast"}
        elif search_time < 0.5:
            return {"status": "good", "icon": "✅", "message": "Good"}
        elif search_time < 1.0:
            return {"status": "moderate", "icon": "⚠️", "message": "Moderate"}
        else:
            return {"status": "slow", "icon": "🐌", "message": "Slow"}

    # 🎯 UNIFIED: Centralized data extraction methods (handle bytes consistently)
    def _safe_decode(self, value):
        """Safely decode bytes values to strings."""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    def _get_metadata(self, memory):
        """Extract and format metadata from memory entry."""
        metadata = memory.get("metadata", {})

        # Handle bytes values from Redis
        if isinstance(metadata, bytes):
            try:
                import json

                metadata = json.loads(metadata.decode("utf-8"))
            except:
                metadata = {}

        return metadata

    def _format_metadata_for_display(self, memory):
        """Format metadata for TUI display."""
        metadata = self._get_metadata(memory)

        if not metadata:
            return "[dim]No metadata available[/dim]"

        # Format metadata as readable text
        formatted_lines = []
        for key, value in metadata.items():
            # Handle nested dictionaries
            if isinstance(value, dict):
                formatted_lines.append(f"[cyan]{key}:[/cyan]")
                for sub_key, sub_value in value.items():
                    formatted_lines.append(f"  [dim]{sub_key}:[/dim] {sub_value!s}")
            else:
                # Handle bytes values
                if isinstance(value, bytes):
                    value = value.decode("utf-8", errors="ignore")
                formatted_lines.append(f"[cyan]{key}:[/cyan] {value!s}")

        return "\n".join(formatted_lines)

    def _get_safe_field(self, memory, *field_names, default="unknown"):
        """Get a field from memory with safe handling of bytes values."""
        for field_name in field_names:
            value = memory.get(field_name)
            if value is not None:
                return self._safe_decode(value)
        return default

    def debug_memory_data(self):
        """Debug method to inspect memory data structure."""
        for i, memory in enumerate(self.memory_data[:3]):
            print(
                f"  {i + 1}. log_type={self._get_log_type(memory)}, memory_type={self._get_memory_type(memory)}, key={self._get_key(memory)[:20]}...",
            )
