# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory Metrics Mixin
====================

Provides statistics and performance metrics for memory operations.
"""

import json
import logging
import time
from typing import Any, cast

logger = logging.getLogger(__name__)


class MetricsMixin:
    """Mixin providing statistics and performance metrics for memory storage."""

    def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory storage statistics."""
        try:
            client = self._get_thread_safe_client()
            pattern = "orka_memory:*"
            keys = client.keys(pattern)

            total_memories = len(keys)
            expired_count = 0
            log_count = 0
            stored_count = 0
            memory_types: dict[str, int] = {}
            categories: dict[str, int] = {}

            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if not memory_data:
                        continue

                    if self._is_expired(memory_data):
                        expired_count += 1
                        continue

                    try:
                        metadata_value = self._safe_get_redis_value(
                            memory_data, "metadata", "{}"
                        )
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                    log_type = metadata.get("log_type", "log")
                    category = metadata.get("category", "log")

                    if log_type == "memory" or category == "stored":
                        stored_count += 1
                        categories["stored"] = categories.get("stored", 0) + 1
                    else:
                        log_count += 1
                        categories["log"] = categories.get("log", 0) + 1

                    memory_type = self._safe_get_redis_value(
                        memory_data, "memory_type", "unknown"
                    )
                    memory_types[memory_type] = memory_types.get(memory_type, 0) + 1

                except Exception as e:
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.warning(f"Error analyzing memory {key}: {error_msg}")
                    continue

            return {
                "total_entries": total_memories,
                "active_entries": total_memories - expired_count,
                "expired_entries": expired_count,
                "stored_memories": stored_count,
                "orchestration_logs": log_count,
                "entries_by_memory_type": memory_types,
                "entries_by_category": categories,
                "backend": "redisstack",
                "index_name": self.index_name,
                "vector_search_enabled": self.embedder is not None,
                "decay_enabled": bool(
                    self.memory_decay_config
                    and self.memory_decay_config.get("enabled", True)
                ),
                "timestamp": int(time.time() * 1000),
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get RedisStack performance metrics including vector search status."""
        try:
            metrics: dict[str, Any] = {
                "vector_searches": 0,
                "hybrid_searches": 0,
                "memory_writes": 0,
                "cache_hits": 0,
                "average_search_time": 0.0,
                "vector_search_enabled": self.embedder is not None,
                "embedder_model": (
                    getattr(self.embedder, "model_name", "Unknown")
                    if self.embedder
                    else None
                ),
                "embedding_dimension": (
                    getattr(self.embedder, "embedding_dim", 0) if self.embedder else 0
                ),
                "index_status": {"status": "unknown"},
            }

            try:
                client = self._get_thread_safe_client()
                index_info = client.ft(self.index_name).info()

                metrics["index_status"] = {
                    "status": "available",
                    "index_name": self.index_name,
                    "num_docs": index_info.get("num_docs", 0),
                    "indexing": index_info.get("indexing", False),
                    "percent_indexed": index_info.get("percent_indexed", 100),
                }

                if index_info:
                    metrics["index_status"]["index_options"] = cast(
                        dict[str, Any], index_info.get("index_options", {})
                    )

            except Exception as e:
                logger.debug(f"Could not get index info: {e}")
                metrics["index_status"] = {"status": "unavailable", "error": str(e)}

            try:
                client = self._get_thread_safe_client()
                pattern = "orka_memory:*"
                keys = client.keys(pattern)

                namespace_dist: dict[str, int] = {}
                for key in keys[:100]:
                    try:
                        memory_data = client.hgetall(key)
                        raw_trace_id = self._safe_get_redis_value(
                            memory_data, "trace_id", "unknown"
                        )
                        if raw_trace_id is not None:
                            trace_id = str(raw_trace_id)
                            namespace_dist[trace_id] = namespace_dist.get(trace_id, 0) + 1
                    except Exception:
                        continue

                metrics["namespace_distribution"] = namespace_dist

            except Exception as e:
                logger.debug(f"Could not get namespace distribution: {e}")
                metrics["namespace_distribution"] = {}

            try:
                recent_memories = self.get_recent_stored_memories(20)
                if recent_memories:
                    importance_scores = [
                        m.get("importance_score", 0) for m in recent_memories
                    ]
                    long_term_count = sum(
                        1 for m in recent_memories if m.get("memory_type") == "long_term"
                    )

                    metrics["memory_quality"] = {
                        "avg_importance_score": (
                            sum(importance_scores) / len(importance_scores)
                            if importance_scores
                            else 0
                        ),
                        "long_term_percentage": (
                            (long_term_count / len(recent_memories)) * 100
                            if recent_memories
                            else 0
                        ),
                    }
                else:
                    metrics["memory_quality"] = {
                        "avg_importance_score": 0,
                        "long_term_percentage": 0,
                    }

            except Exception as e:
                logger.debug(f"Could not get memory quality metrics: {e}")
                metrics["memory_quality"] = {}

            return metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                "error": str(e),
                "vector_search_enabled": self.embedder is not None,
            }

