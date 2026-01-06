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

"""
Data management for TUI interface - statistics, caching, and data fetching.
"""

import json
import os
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Protocol, TypeVar, Union, cast

from ..memory_logger import BaseMemoryLogger, create_memory_logger

# Type aliases for clarity
MemoryEntry = Dict[str, Any]
MemoryList = List[MemoryEntry]
StatsDict = Dict[str, Union[str, int, float, bool, Dict[str, Any]]]


# Protocol for memory logger to help with type checking
class MemoryLoggerProtocol(Protocol):
    def get_memory_stats(self) -> Dict[str, Any]: ...
    def get_recent_stored_memories(self, limit: int) -> List[MemoryEntry]: ...
    def search_memories(self, query: str, num_results: int, log_type: str) -> List[MemoryEntry]: ...
    def get_performance_metrics(self) -> Dict[str, Any]: ...


class MemoryStats:
    """Container for memory statistics with historical tracking."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: Deque[StatsDict] = deque(maxlen=max_history)
        self.current: StatsDict = {}

    def update(self, stats: StatsDict) -> None:
        """Update current stats and add to history."""
        self.current = stats.copy()
        self.current["timestamp"] = time.time()
        self.history.append(self.current.copy())

    def get_trend(self, key: str, window: int = 10) -> str:
        """Get trend direction for a metric."""
        if len(self.history) < 2:
            return "->"

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return "->"

        try:
            values = []
            for item in recent:
                if key in item:
                    val = item[key]
                    if isinstance(val, (int, float)):
                        values.append(float(val))
                    elif isinstance(val, str) and val.replace(".", "").isdigit():
                        values.append(float(val))

            if len(values) < 2:
                return "->"

            if values[-1] > values[0]:
                return "^"
            elif values[-1] < values[0]:
                return "v"
            else:
                return "->"
        except (ValueError, TypeError):
            return "->"

    def get_rate(self, key: str, window: int = 5) -> float:
        """Get rate of change for a metric (per second)."""
        if len(self.history) < 2:
            return 0.0

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return 0.0

        try:
            # Calculate rate between first and last points
            first = recent[0]
            last = recent[-1]

            if key not in first or key not in last:
                return 0.0

            first_val = first[key]
            last_val = last[key]
            first_time = first["timestamp"]
            last_time = last["timestamp"]

            if not all(
                isinstance(x, (int, float, str))
                for x in [first_val, last_val, first_time, last_time]
            ):
                return 0.0

            value_diff = float(str(last_val)) - float(str(first_val))
            time_diff = float(str(last_time)) - float(str(first_time))

            if time_diff <= 0:
                return 0.0

            return value_diff / time_diff
        except (ValueError, TypeError, KeyError):
            return 0.0


class DataManager:
    """Manages data fetching and caching for the TUI interface."""

    def __init__(self):
        self.memory_logger: Optional[MemoryLoggerProtocol] = None
        self.backend: Optional[str] = None
        self.stats = MemoryStats()
        self.memory_data: MemoryList = []
        self.performance_history: Deque[StatsDict] = deque(maxlen=60)  # 1 minute at 1s intervals

    def init_memory_logger(self, args: Any) -> None:
        """Initialize the memory logger."""
        backend = cast(
            str,
            getattr(args, "backend", None)
            or os.getenv(
                "ORKA_MEMORY_BACKEND",
                "redisstack",
            ),
        )
        self.backend = backend

        # Provide proper Redis URL based on backend
        if self.backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")

        self.memory_logger = cast(
            MemoryLoggerProtocol, create_memory_logger(backend=backend, redis_url=redis_url)
        )

    def update_data(self) -> None:
        """Update all monitoring data."""
        if not self.memory_logger:
            return

        try:
            # Get memory statistics
            stats = self.memory_logger.get_memory_stats()
            self.stats.update(cast(StatsDict, stats))

            # [TARGET] FIX: Collect memories with deduplication by key
            memory_dict: Dict[str, MemoryEntry] = {}  # Use dict to deduplicate by key

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
                        log_type="log",  # [TARGET] FIX: Use "log" instead of "orchestration"
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
                if isinstance(perf_metrics, dict):
                    metrics_dict = cast(StatsDict, perf_metrics.copy())
                    metrics_dict["timestamp"] = time.time()
                    self.performance_history.append(metrics_dict)

        except Exception:
            # Log error but continue
            pass

    def is_short_term_memory(self, memory: dict[str, Any]) -> bool:
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

    def _get_memory_type(self, memory: dict[str, Any]) -> str:
        """Get the actual memory_type field from memory entry."""
        # First check direct memory_type field
        memory_type = memory.get("memory_type")
        if memory_type:
            # [TARGET] FIX: Handle bytes values from Redis
            if isinstance(memory_type, bytes):
                memory_type = memory_type.decode("utf-8", errors="ignore")
            if memory_type in ["short_term", "long_term"]:
                return str(memory_type)

        # Check in metadata
        metadata = memory.get("metadata", {})
        memory_type = metadata.get("memory_type")
        if memory_type:
            # [TARGET] FIX: Handle bytes values from Redis
            if isinstance(memory_type, bytes):
                memory_type = memory_type.decode("utf-8", errors="ignore")
            if memory_type in ["short_term", "long_term"]:
                return str(memory_type)

        # Default fallback
        return "unknown"

    def get_filtered_memories(self, memory_type: str = "all") -> list[dict[str, Any]]:
        if memory_type == "short":
            # [TARGET] FIX: Use actual memory_type field instead of TTL
            return [
                m
                for m in self.memory_data
                if self._get_log_type(m) == "memory" and self._get_memory_type(m) == "short_term"
            ]

        elif memory_type == "long":
            # [TARGET] FIX: Use actual memory_type field instead of TTL
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
                in ["log", "system"]  # [TARGET] FIX: Use "log" instead of "orchestration"
            ]
        else:
            return self.memory_data

    def _get_log_type(self, memory: dict[str, Any]) -> str:
        """Extract log type from memory entry."""
        metadata = memory.get("metadata", {})
        return (
            self._safe_decode(metadata.get("log_type"))
            or self._safe_decode(memory.get("log_type"))
            or self._safe_decode(memory.get("type"))
            or "unknown"
        )

    def _get_content(self, memory: dict[str, Any]) -> str:
        """Extract and decode content from memory entry."""
        content = memory.get("content") or memory.get("message") or memory.get("data") or ""
        return self._safe_decode(content)

    def _get_key(self, memory: dict[str, Any]) -> str:
        """Extract and decode key from memory entry."""
        key = memory.get("key") or memory.get("id") or memory.get("node_id") or "unknown"
        return self._safe_decode(key)

    def _get_node_id(self, memory: dict[str, Any]) -> str:
        """Extract and decode node_id from memory entry."""
        return self._get_safe_field(memory, "node_id", "node", "id", default="unknown")

    def _get_timestamp(self, memory: dict[str, Any]) -> int:
        """Extract timestamp from memory entry."""
        timestamp = memory.get("timestamp", 0)
        if isinstance(timestamp, bytes):
            try:
                return int(timestamp.decode())
            except Exception:
                return 0
        return int(timestamp) if timestamp else 0

    def _get_importance_score(self, memory: dict[str, Any]) -> float:
        """Extract importance score from memory entry."""
        score = memory.get("importance_score", 0)
        if isinstance(score, bytes):
            try:
                return float(score.decode())
            except Exception:
                return 0.0
        return float(score) if score else 0.0

    def _get_ttl_formatted(self, memory: dict[str, Any]) -> str:
        """Extract formatted TTL from memory entry."""
        return self._get_safe_field(memory, "ttl_formatted", "ttl", default="?")

    def get_memory_distribution(self) -> Dict[str, Any]:
        """Get distribution of memory types and log types for diagnostic purposes."""
        distribution: Dict[str, Any] = {
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
            if "by_log_type" not in distribution:
                distribution["by_log_type"] = {}
            distribution["by_log_type"][log_type] = distribution["by_log_type"].get(log_type, 0) + 1

            # Count by memory type for stored memories
            if log_type == "memory":
                distribution["stored_memories"]["total"] += 1
                if memory_type in distribution["stored_memories"]:
                    distribution["stored_memories"][memory_type] += 1
            else:
                distribution["log_entries"]["total"] += 1
                if "by_type" not in distribution["log_entries"]:
                    distribution["log_entries"]["by_type"] = {}
                distribution["log_entries"]["by_type"][log_type] = (
                    distribution["log_entries"]["by_type"].get(log_type, 0) + 1
                )

            # Overall memory type distribution
            if "by_memory_type" not in distribution:
                distribution["by_memory_type"] = {}
            distribution["by_memory_type"][memory_type] = (
                distribution["by_memory_type"].get(memory_type, 0) + 1
            )

        return distribution

    # [TARGET] NEW: Unified Data Calculation System
    def get_unified_stats(self) -> Dict[str, Any]:
        """
        Get unified, comprehensive statistics for all TUI components.
        This replaces scattered calculations throughout the TUI system.
        """
        # Calculate distribution once
        distribution = self.get_memory_distribution()

        # Get backend stats
        backend_stats = self.stats.current

        # Get latest performance metrics
        latest_perf = {}
        search_time = 0.0
        if self.performance_history:
            latest = self.performance_history[-1]
            latest_perf = dict(latest)
            search_time = self._safe_float(latest.get("average_search_time", 0))

        # [TARGET] UNIFIED: Calculate all core metrics consistently
        unified_stats: Dict[str, Any] = {
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
                "latest": latest_perf,
                "search_time": search_time,
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
            "raw_distribution": dict(distribution),
        }

        return unified_stats

    def _calculate_overall_health(self) -> Dict[str, str]:
        """Calculate overall system health status."""
        if not self.memory_logger:
            return {"status": "critical", "icon": "[R]", "message": "No Connection"}

        stats = self.stats.current
        total = self._safe_float(stats.get("total_entries", 0))
        expired = self._safe_float(stats.get("expired_entries", 0))

        if total == 0:
            return {"status": "warning", "icon": "[Y]", "message": "No Data"}

        expired_ratio = expired / total if total > 0 else 0

        if expired_ratio < 0.1:
            return {"status": "healthy", "icon": "[G]", "message": "Healthy"}
        elif expired_ratio < 0.3:
            return {"status": "degraded", "icon": "[Y]", "message": "Degraded"}
        else:
            return {"status": "critical", "icon": "[R]", "message": "Critical"}

    def _calculate_memory_health(self) -> Dict[str, str]:
        """Calculate memory system health."""
        stats = self.stats.current
        total = self._safe_float(stats.get("total_entries", 0))
        active = self._safe_float(stats.get("active_entries", 0))
        expired = self._safe_float(stats.get("expired_entries", 0))

        if total == 0:
            return {"status": "warning", "icon": "[Y]", "message": "No Data"}

        expired_ratio = expired / total if total > 0 else 0
        active_ratio = active / total if total > 0 else 0

        if expired_ratio < 0.1 and active_ratio > 0.8:
            return {"status": "healthy", "icon": "[G]", "message": "Healthy"}
        elif expired_ratio < 0.3:
            return {"status": "degraded", "icon": "[Y]", "message": "Degraded"}
        else:
            return {"status": "critical", "icon": "[R]", "message": "Critical"}

    def _calculate_backend_health(self) -> dict[str, Any]:
        """Calculate backend connection health."""
        if not self.memory_logger:
            return {"status": "critical", "icon": "[R]", "message": "Disconnected"}

        try:
            # Get the Redis client - use 'client' property which handles lazy initialization
            redis_client = None
            
            # Try 'client' property first (triggers lazy init for RedisStack)
            if hasattr(self.memory_logger, "client"):
                redis_client = self.memory_logger.client
            # Fall back to direct redis_client attribute
            elif hasattr(self.memory_logger, "redis_client"):
                redis_client = self.memory_logger.redis_client
            
            if redis_client is None:
                return {"status": "warning", "icon": "[Y]", "message": "No Client"}
            
            # Test actual connectivity with ping
            try:
                ping_result = redis_client.ping()
                if ping_result:
                    return {"status": "healthy", "icon": "[G]", "message": "Connected"}
                else:
                    return {"status": "warning", "icon": "[Y]", "message": "Limited"}
            except Exception:
                return {"status": "warning", "icon": "[Y]", "message": "Limited"}
                
        except Exception:
            return {"status": "critical", "icon": "[R]", "message": "Error"}

    def _calculate_performance_health(self) -> Dict[str, str]:
        """Calculate performance health."""
        if not self.performance_history:
            return {"status": "unknown", "icon": "[?]", "message": "No Data"}

        latest = self.performance_history[-1]
        search_time = self._safe_float(latest.get("average_search_time", 0))

        if search_time < 0.1:
            return {"status": "excellent", "icon": "[FAST]", "message": "Fast"}
        elif search_time < 0.5:
            return {"status": "good", "icon": "[OK]", "message": "Good"}
        elif search_time < 1.0:
            return {"status": "moderate", "icon": "[WARN]️", "message": "Moderate"}
        else:
            return {"status": "slow", "icon": "[SLOW]", "message": "Slow"}

    # [TARGET] UNIFIED: Centralized data extraction methods (handle bytes consistently)
    def _safe_decode(self, value: Any) -> str:
        """Safely decode bytes values to strings."""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value)

    def _safe_float(self, value: Any) -> float:
        """Safely convert any value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.replace(".", "").isdigit():
            return float(value)
        return 0.0

    def _get_metadata(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format metadata from memory entry."""
        metadata = memory.get("metadata", {})

        # Handle bytes values from Redis
        if isinstance(metadata, bytes):
            try:


                metadata = json.loads(metadata.decode("utf-8"))
            except Exception:
                metadata = {}
        elif not isinstance(metadata, dict):
            metadata = {}

        return cast(Dict[str, Any], metadata)

    def _format_metadata_for_display(self, memory: Dict[str, Any]) -> str:
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

    def _get_safe_field(
        self, memory: MemoryEntry, *field_names: str, default: str = "unknown"
    ) -> str:
        """Get a field from memory with safe handling of bytes values."""
        for field_name in field_names:
            value = memory.get(field_name)
            if value is not None:
                return self._safe_decode(value)
        return default

    def debug_memory_data(self) -> None:
        """Debug method to inspect memory data structure."""
        for i, memory in enumerate(self.memory_data[:3]):
            # logger.debug is not defined, so this line is removed.
            # If logger is intended to be used, it needs to be initialized.
            # For now, commenting out the line as per the original file.
            # logger.debug(
            #     f"  {i + 1}. log_type={self._get_log_type(memory)}, memory_type={self._get_memory_type(memory)}, key={self._get_key(memory)[:20]}...",
            # )
            pass
