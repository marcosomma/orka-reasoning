# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Memory Search Mixin for RedisStack
==================================

Search operations including vector, text, and basic Redis search.

Features
--------
- Vector similarity search with HNSW
- Fallback text search using FT.SEARCH
- Basic Redis SCAN search for non-RedisStack deployments
- Query escaping for special characters
- Similarity score validation

Usage
-----
This mixin is intended to be used with RedisStackMemoryLogger:

```python
class RedisStackMemoryLogger(BaseMemoryLogger, MemorySearchMixin):
    pass
```
"""

import json
import logging
import math
import time
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)


class MemorySearchMixin:
    """
    Mixin providing memory search functionality.

    Requires the host class to provide:
    - `_get_thread_safe_client()` method
    - `_safe_get_redis_value()` method
    - `_get_embedding_sync()` method
    - `_is_expired()` method
    - `_get_ttl_info()` method
    - `_ensure_index()` method
    - `embedder` attribute
    - `index_name` attribute
    - `vector_params` attribute
    """

    # Type hints for attributes provided by the host class
    embedder: Any
    index_name: str
    vector_params: dict[str, Any]

    # Methods expected from host class (via other mixins or main class):
    # - _get_thread_safe_client() -> redis.Redis
    # - _safe_get_redis_value(memory_data, key, default) -> Any
    # - _get_embedding_sync(text) -> np.ndarray | None
    # - _is_expired(memory_data) -> bool
    # - _get_ttl_info(key, memory_data, current_time_ms) -> dict | None
    # - _ensure_index() -> None

    def _escape_redis_search_query(
        self, query: str, include_underscores: bool = False
    ) -> str:
        """
        Escape special characters in Redis search query.

        Args:
            query: The query string to escape
            include_underscores: Whether to also escape underscores

        Returns:
            Escaped query string safe for Redis FT.SEARCH
        """
        if not query:
            return ""

        special_chars = [
            "\\",
            ":",
            '"',
            "'",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "|",
            "@",
            "~",
            "-",
            "&",
            "!",
            "*",
            ",",
            ".",
            "?",
            "^",
            "+",
            "/",
            "<",
            ">",
            "=",
        ]

        if include_underscores:
            special_chars.append("_")

        escaped_query = query
        for char in special_chars:
            escaped_query = escaped_query.replace(char, f"\\{char}")

        return escaped_query

    def _escape_redis_search_phrase(self, phrase: str) -> str:
        """
        Escape a quoted phrase for RedisSearch.

        Only escapes characters that can break the quoted string itself.
        """
        if not phrase:
            return ""

        normalized = " ".join(str(phrase).split())
        normalized = normalized.replace("\\", "\\\\").replace('"', '\\"')
        return normalized

    def _validate_similarity_score(self, score: Any) -> float:
        """Validate and sanitize similarity scores to prevent NaN values."""
        try:
            score_float = float(score)
            if math.isnan(score_float) or math.isinf(score_float) or score_float < 0:
                return 0.0
            return max(0.0, min(1.0, score_float))
        except (ValueError, TypeError):
            return 0.0

    def search_memories(
        self,
        query: str,
        num_results: int = 10,
        trace_id: str | None = None,
        node_id: str | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
        log_type: str = "memory",
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search memories using enhanced vector search with filtering.

        Args:
            query: Search query text
            num_results: Maximum number of results
            trace_id: Filter by trace ID
            node_id: Filter by node ID
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            log_type: Filter by log type (default: only memories)
            namespace: Filter by namespace

        Returns:
            List of matching memory entries with scores
        """
        try:
            # Try vector search if embedder is available and query is not empty
            if self.embedder and query.strip():
                try:
                    query_vector = self._get_embedding_sync(query)
                    if query_vector is None:
                        logger.warning(
                            "Failed to get embedding, falling back to text search"
                        )
                        return self._fallback_text_search(
                            query,
                            num_results,
                            trace_id,
                            node_id,
                            memory_type,
                            min_importance,
                            log_type,
                            namespace,
                        )

                    from orka.utils.bootstrap_memory_index import (
                        hybrid_vector_search,
                        verify_memory_index,
                    )

                    logger.debug(f"Performing vector search for: {query}")

                    client = self._get_thread_safe_client()

                    # Verify index exists
                    index_status = verify_memory_index(client, self.index_name)
                    if not index_status["exists"]:
                        logger.error(
                            f"Memory index {self.index_name} does not exist: "
                            f"{index_status.get('error', 'Unknown error')}"
                        )
                        try:
                            logger.info(
                                f"Attempting to recreate missing index {self.index_name}"
                            )
                            self._ensure_index()
                            index_status = verify_memory_index(client, self.index_name)
                            if (
                                not index_status["exists"]
                                or not index_status["vector_field_exists"]
                            ):
                                return self._fallback_text_search(
                                    query,
                                    num_results,
                                    trace_id,
                                    node_id,
                                    memory_type,
                                    min_importance,
                                    log_type,
                                    namespace,
                                )
                        except Exception as recreate_error:
                            logger.error(f"Failed to recreate index: {recreate_error}")
                            return self._fallback_text_search(
                                query,
                                num_results,
                                trace_id,
                                node_id,
                                memory_type,
                                min_importance,
                                log_type,
                                namespace,
                            )

                    if not index_status["vector_field_exists"]:
                        logger.error(
                            f"Memory index {self.index_name} missing vector field"
                        )
                        try:
                            original_force_recreate = self.vector_params.get(
                                "force_recreate", False
                            )
                            self.vector_params["force_recreate"] = True
                            self._ensure_index()
                            self.vector_params["force_recreate"] = original_force_recreate

                            index_status = verify_memory_index(client, self.index_name)
                            if not index_status["vector_field_exists"]:
                                return self._fallback_text_search(
                                    query,
                                    num_results,
                                    trace_id,
                                    node_id,
                                    memory_type,
                                    min_importance,
                                    log_type,
                                    namespace,
                                )
                        except Exception as recreate_error:
                            logger.error(
                                f"Failed to recreate index with vector field: "
                                f"{recreate_error}"
                            )
                            return self._fallback_text_search(
                                query,
                                num_results,
                                trace_id,
                                node_id,
                                memory_type,
                                min_importance,
                                log_type,
                                namespace,
                            )

                    logger.debug(
                        f"Index verification passed: {index_status['num_docs']} docs"
                    )

                    results = hybrid_vector_search(
                        redis_client=client,
                        query_text=query,
                        query_vector=query_vector,
                        num_results=num_results,
                        index_name=self.index_name,
                        trace_id=trace_id,
                    )

                    logger.debug(f"Vector search returned {len(results)} results")

                    if len(results) == 0:
                        logger.warning(
                            f"Vector search found no results for query: '{query}'"
                        )

                    # Convert and filter results
                    formatted_results = self._process_search_results(
                        results,
                        node_id,
                        memory_type,
                        min_importance,
                        log_type,
                        namespace,
                    )

                    logger.debug(f"Returning {len(formatted_results)} filtered results")

                    # Fall back to text search if no results
                    if len(formatted_results) == 0 and query.strip():
                        logger.info(
                            "Vector search returned 0 results, falling back to text search"
                        )
                        return self._fallback_text_search(
                            query,
                            num_results,
                            trace_id,
                            node_id,
                            memory_type,
                            min_importance,
                            log_type,
                            namespace,
                        )

                    return formatted_results

                except Exception as e:
                    logger.warning(
                        f"Vector search failed, falling back to text search: {e}"
                    )

            else:
                logger.debug(
                    "Using text search for empty query or no embedder available"
                )

            # Fallback to basic text search
            return self._fallback_text_search(
                query,
                num_results,
                trace_id,
                node_id,
                memory_type,
                min_importance,
                log_type,
                namespace,
            )

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def _process_search_results(
        self,
        results: list[dict[str, Any]],
        node_id: str | None,
        memory_type: str | None,
        min_importance: float | None,
        log_type: str,
        namespace: str | None,
    ) -> list[dict[str, Any]]:
        """Process and filter search results."""
        formatted_results = []

        for result in results:
            try:
                memory_data = self._get_thread_safe_client().hgetall(result["key"])
                if not memory_data:
                    continue

                # Apply filters
                if (
                    node_id
                    and self._safe_get_redis_value(memory_data, "node_id") != node_id
                ):
                    continue
                if (
                    memory_type
                    and self._safe_get_redis_value(memory_data, "memory_type")
                    != memory_type
                ):
                    continue

                importance_str = self._safe_get_redis_value(
                    memory_data,
                    "importance_score",
                    "0",
                )
                if min_importance and float(importance_str) < min_importance:
                    continue

                if self._is_expired(memory_data):
                    continue

                # Parse metadata
                try:
                    metadata_value = self._safe_get_redis_value(
                        memory_data,
                        "metadata",
                        "{}",
                    )
                    metadata = json.loads(metadata_value)
                except Exception as e:
                    logger.debug(f"Error parsing metadata for key {result['key']}: {e}")
                    metadata = {}

                # Check log type
                memory_log_type = metadata.get("log_type", "log")
                memory_category = metadata.get("category", "log")
                is_stored_memory = (
                    memory_log_type == "memory" or memory_category == "stored"
                )

                if log_type == "memory" and not is_stored_memory:
                    continue
                if log_type == "log" and is_stored_memory:
                    continue

                # Filter by namespace
                if namespace:
                    memory_namespace = metadata.get("namespace")
                    if memory_namespace is not None and memory_namespace != namespace:
                        continue

                # Calculate TTL information
                current_time_ms = int(time.time() * 1000)
                expiry_info = self._get_ttl_info(
                    result["key"],
                    memory_data,
                    current_time_ms,
                )

                formatted_result = {
                    "content": self._safe_get_redis_value(memory_data, "content", ""),
                    "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                    "trace_id": self._safe_get_redis_value(memory_data, "trace_id", ""),
                    "importance_score": float(
                        self._safe_get_redis_value(
                            memory_data,
                            "importance_score",
                            "0",
                        ),
                    ),
                    "memory_type": self._safe_get_redis_value(
                        memory_data,
                        "memory_type",
                        "",
                    ),
                    "timestamp": int(
                        self._safe_get_redis_value(memory_data, "timestamp", "0"),
                    ),
                    "metadata": metadata,
                    "similarity_score": self._validate_similarity_score(
                        result.get("score", 0.0),
                    ),
                    "key": result["key"],
                    "ttl_seconds": (
                        expiry_info.get("ttl_seconds", -1) if expiry_info else -1
                    ),
                    "ttl_formatted": (
                        expiry_info.get("ttl_formatted", "N/A") if expiry_info else "N/A"
                    ),
                    "expires_at": (
                        expiry_info.get("expires_at") if expiry_info else None
                    ),
                    "expires_at_formatted": (
                        expiry_info.get("expires_at_formatted", "N/A")
                        if expiry_info
                        else "N/A"
                    ),
                    "has_expiry": (
                        expiry_info.get("has_expiry", False) if expiry_info else False
                    ),
                }
                formatted_results.append(formatted_result)

            except Exception as e:
                logger.warning(f"Error processing search result: {e}")
                continue

        return formatted_results

    def _fallback_text_search(
        self,
        query: str,
        num_results: int,
        trace_id: str | None = None,
        node_id: str | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
        log_type: str = "memory",
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback text search using basic Redis search capabilities."""
        try:
            logger.debug("Using fallback text search")

            from redis.commands.search.query import Query

            # Build search query
            if query.strip():
                escaped_query = self._escape_redis_search_phrase(query)
                search_query = f'@content:"{escaped_query}"'
            else:
                search_query = "*"

            # Add filters
            filters = []
            if trace_id and trace_id.strip():
                escaped_trace_id = self._escape_redis_search_query(
                    trace_id, include_underscores=True
                )
                if escaped_trace_id:
                    filters.append(f"@trace_id:{escaped_trace_id}")

            if node_id and node_id.strip():
                escaped_node_id = self._escape_redis_search_query(
                    node_id, include_underscores=True
                )
                if escaped_node_id:
                    filters.append(f"@node_id:{escaped_node_id}")

            if filters:
                if search_query and search_query.strip() and search_query != "*":
                    search_query = f"({search_query}) " + " ".join(filters)
                else:
                    search_query = " ".join(filters)

            logger.debug(f"FT.SEARCH query: '{search_query}'")

            if not search_query or not search_query.strip():
                logger.warning("Empty search query, falling back to basic Redis scan")
                return self._basic_redis_search(
                    query,
                    num_results,
                    trace_id,
                    node_id,
                    memory_type,
                    min_importance,
                    log_type,
                    namespace,
                )

            try:
                client = self._get_thread_safe_client()
                search_results = client.ft(self.index_name).search(
                    Query(search_query).paging(0, num_results),
                )
            except Exception as ft_error:
                logger.debug(
                    f"RedisStack FT.SEARCH failed: {ft_error}, using basic Redis scan"
                )
                return self._basic_redis_search(
                    query,
                    num_results,
                    trace_id,
                    node_id,
                    memory_type,
                    min_importance,
                    log_type,
                    namespace,
                )

            results: list[dict[str, Any]] = []
            for doc in search_results.docs:
                try:
                    memory_data = client.hgetall(doc.id)
                    if not memory_data:
                        continue

                    if (
                        memory_type
                        and self._safe_get_redis_value(memory_data, "memory_type")
                        != memory_type
                    ):
                        continue

                    importance_str = self._safe_get_redis_value(
                        memory_data,
                        "importance_score",
                        "0",
                    )
                    if min_importance and float(importance_str) < min_importance:
                        continue

                    if self._is_expired(memory_data):
                        continue

                    try:
                        metadata_value = self._safe_get_redis_value(
                            memory_data, "metadata", "{}"
                        )
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {doc.id}: {e}")
                        metadata = {}

                    memory_log_type = metadata.get("log_type", "log")
                    memory_category = metadata.get("category", "log")
                    is_stored_memory = (
                        memory_log_type == "memory" or memory_category == "stored"
                    )

                    if log_type == "memory" and not is_stored_memory:
                        continue
                    if log_type == "log" and is_stored_memory:
                        continue

                    if namespace:
                        memory_namespace = metadata.get("namespace")
                        if memory_namespace != namespace:
                            continue

                    current_time_ms = int(time.time() * 1000)
                    expiry_info = self._get_ttl_info(doc.id, memory_data, current_time_ms)
                    if not expiry_info:
                        continue

                    result = {
                        "content": self._safe_get_redis_value(memory_data, "content", ""),
                        "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                        "trace_id": self._safe_get_redis_value(
                            memory_data, "trace_id", ""
                        ),
                        "importance_score": float(
                            self._safe_get_redis_value(
                                memory_data, "importance_score", "0"
                            ),
                        ),
                        "memory_type": self._safe_get_redis_value(
                            memory_data, "memory_type", ""
                        ),
                        "timestamp": int(
                            self._safe_get_redis_value(memory_data, "timestamp", "0")
                        ),
                        "metadata": metadata,
                        "similarity_score": 0.5,
                        "key": doc.id,
                        "ttl_seconds": expiry_info["ttl_seconds"],
                        "ttl_formatted": expiry_info["ttl_formatted"],
                        "expires_at": expiry_info["expires_at"],
                        "expires_at_formatted": expiry_info["expires_at_formatted"],
                        "has_expiry": expiry_info["has_expiry"],
                    }
                    results.append(result)

                except Exception as e:
                    error_msg = str(e) if str(e) else type(e).__name__
                    logger.warning(f"Error processing fallback result: {error_msg}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            return []

    def _basic_redis_search(
        self,
        query: str,
        num_results: int,
        trace_id: str | None = None,
        node_id: str | None = None,
        memory_type: str | None = None,
        min_importance: float | None = None,
        log_type: str = "memory",
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Basic Redis search using SCAN when RedisStack modules are not available."""
        try:
            logger.debug("Using basic Redis SCAN for search")

            client = self._get_thread_safe_client()
            pattern = "orka_memory:*"
            keys = client.keys(pattern)

            results: list[dict[str, Any]] = []
            current_time_ms = int(time.time() * 1000)

            for key in keys:
                if len(results) >= num_results:
                    break

                try:
                    memory_data = client.hgetall(key)
                    if not memory_data:
                        continue

                    if self._is_expired(memory_data):
                        continue

                    try:
                        metadata_value = self._safe_get_redis_value(
                            memory_data, "metadata", "{}"
                        )
                        metadata = json.loads(metadata_value)
                    except Exception:
                        metadata = {}

                    memory_log_type = metadata.get("log_type", "log")
                    memory_category = metadata.get("category", "log")
                    is_stored_memory = (
                        memory_log_type == "memory" or memory_category == "stored"
                    )

                    if log_type == "memory" and not is_stored_memory:
                        continue
                    if log_type == "log" and is_stored_memory:
                        continue

                    if (
                        trace_id
                        and self._safe_get_redis_value(memory_data, "trace_id")
                        != trace_id
                    ):
                        continue
                    if (
                        node_id
                        and self._safe_get_redis_value(memory_data, "node_id") != node_id
                    ):
                        continue
                    if (
                        memory_type
                        and self._safe_get_redis_value(memory_data, "memory_type")
                        != memory_type
                    ):
                        continue

                    importance_str = self._safe_get_redis_value(
                        memory_data, "importance_score", "0"
                    )
                    if min_importance and float(importance_str) < min_importance:
                        continue

                    if namespace:
                        memory_namespace = metadata.get("namespace")
                        if memory_namespace is not None and memory_namespace != namespace:
                            continue

                    # Basic content matching
                    if query.strip():
                        content = self._safe_get_redis_value(memory_data, "content", "")
                        if query.lower() not in content.lower():
                            continue

                    expiry_info = self._get_ttl_info(key, memory_data, current_time_ms)

                    result = {
                        "content": self._safe_get_redis_value(memory_data, "content", ""),
                        "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                        "trace_id": self._safe_get_redis_value(
                            memory_data, "trace_id", ""
                        ),
                        "importance_score": float(
                            self._safe_get_redis_value(
                                memory_data, "importance_score", "0"
                            )
                        ),
                        "memory_type": self._safe_get_redis_value(
                            memory_data, "memory_type", "unknown"
                        ),
                        "timestamp": int(
                            self._safe_get_redis_value(memory_data, "timestamp", "0")
                        ),
                        "metadata": metadata,
                        "similarity_score": 0.5,
                        "key": key.decode() if isinstance(key, bytes) else key,
                    }

                    if expiry_info:
                        result.update(expiry_info)

                    results.append(result)

                except Exception as e:
                    logger.debug(f"Error processing key {key}: {e}")
                    continue

            logger.debug(f"Basic Redis search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Basic Redis search failed: {e}")
            return []

