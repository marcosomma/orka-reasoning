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
Bootstrap Memory Index
=====================

This module contains utility functions for initializing and ensuring the
existence of the memory index in Redis, which is a critical component of
the OrKa framework's memory persistence system.

The memory index enables semantic search across agent memory entries using:
- Text fields for content matching
- Tag fields for filtering by session and agent
- Timestamp fields for time-based queries
- Vector fields for semantic similarity search

Enhanced RedisStack Features:
- HNSW vector indexing for sub-millisecond search
- Hybrid search combining vector similarity with metadata filtering
- Advanced filtering and namespace isolation
- Automatic index optimization

This module also provides retry functionality with exponential backoff for
handling potential transient Redis connection issues during initialization.

Usage example:
```python
import redis.asyncio as redis
from orka.utils.bootstrap_memory_index import ensure_memory_index, ensure_enhanced_memory_index

async def initialize_memory():
    client = redis.from_url("redis://localhost:6380")

    # Legacy FLAT indexing
    await ensure_memory_index(client)

    # Enhanced HNSW indexing
    await ensure_enhanced_memory_index(client)

    # Now the memory index is ready for use
```
"""

import asyncio
import logging
from typing import Any, cast

import numpy as np
import redis

# Handle different Redis versions and search field imports
try:
    from redis.commands.search.field import NumericField, TextField, VectorField
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    from redis.commands.search.query import Query

    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    try:
        # Fallback for older Redis versions
        from redisearch import IndexDefinition  # type: ignore[no-redef]
        from redisearch import IndexType  # type: ignore[no-redef]
        from redisearch import NumericField  # type: ignore[no-redef]
        from redisearch import Query  # type: ignore[no-redef]
        from redisearch import TextField  # type: ignore[no-redef]

        VECTOR_SEARCH_AVAILABLE = False
    except ImportError:
        # Minimal stubs for when Redis search is not available


        logger = logging.getLogger(__name__)
        logger.warning("Redis search modules not available - vector search disabled")

        class NumericField:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

        class TextField:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

        class VectorField:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

        class IndexDefinition:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

        class IndexType:  # type: ignore[no-redef]
            HASH = "HASH"

        class Query:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

        VECTOR_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)


def ensure_memory_index(redis_client: redis.Redis, index_name: str = "memory_entries") -> bool:
    try:
        # Check if index exists
        try:
            redis_client.ft(index_name).info()
            logger.info(f"Basic memory index '{index_name}' already exists")
            return True
        except redis.ResponseError as e:
            if "Unknown index name" in str(e):
                logger.info(f"Creating basic memory index '{index_name}'")
                # Create basic index for memory entries
                redis_client.ft(index_name).create_index(
                    [
                        TextField("content"),
                        TextField("node_id"),
                        NumericField("orka_expire_time"),
                    ],
                )
                logger.info(f"✅ Basic memory index '{index_name}' created successfully")
                return True
            else:
                raise
    except Exception as e:
        logger.error(f"❌ Failed to ensure basic memory index: {e}")
        if "unknown command" in str(e).lower() or "ft.create" in str(e).lower():
            logger.warning(
                "⚠️  Redis instance does not support RediSearch. Please install RedisStack or enable RediSearch module.",
            )
            logger.info(
                "🔧 For RedisStack setup: https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/",
            )
        return False


def ensure_enhanced_memory_index(
    redis_client: redis.Redis,
    index_name: str = "orka_enhanced_memory",
    vector_dim: int = 384,
    vector_field_name: str = "content_vector",
    vector_params: dict[str, Any] | None = None,
    force_recreate: bool = False,
    format_params: dict[str, Any] | None = None,
) -> bool:
    """
    Ensure that the enhanced memory index with vector search exists.
    This creates an index with vector search capabilities for semantic search.

    Args:
        redis_client: Redis client instance
        index_name: Name of the index to create or verify
        vector_dim: Dimension of the vector field
        vector_field_name: Name of the vector field
        vector_params: Additional parameters for vector field configuration
        force_recreate: If True, drop and recreate the index if it exists but has issues

    Returns:
        bool: True if index exists and is properly configured, False otherwise
    """
    if not VECTOR_SEARCH_AVAILABLE:
        logger.warning(
            "Vector search not available in this Redis version. Using basic index instead."
        )
        return ensure_memory_index(redis_client, index_name)

    # Default vector parameters
    default_vector_params = {
        "TYPE": "FLOAT32",
        "DIM": vector_dim,
        "DISTANCE_METRIC": "COSINE",
        "EF_CONSTRUCTION": 200,
        "M": 16,
    }

    # Merge with user-provided params if any
    if vector_params:
        default_vector_params.update(vector_params)

    try:
        # Check if index exists and verify its configuration
        try:
            # First verify if the index exists and has the correct configuration
            index_info = verify_memory_index(redis_client, index_name)

            if index_info["exists"]:
                logger.info(f"Enhanced memory index '{index_name}' exists, verifying configuration")

                # Check if vector field exists and is properly configured
                if not index_info["vector_field_exists"]:
                    logger.warning(
                        f"Memory index {index_name} missing vector field. Available fields: {index_info['fields']}"
                    )

                    if force_recreate:
                        logger.info(
                            f"Dropping and recreating index {index_name} with proper vector configuration"
                        )
                        try:
                            # Drop the existing index
                            redis_client.ft(index_name).dropindex()
                            logger.info(f"Successfully dropped index {index_name}")
                        except Exception as drop_error:
                            logger.error(f"Failed to drop index {index_name}: {drop_error}")
                            return False
                    else:
                        # Index exists but is missing vector field, and we're not forcing recreation
                        logger.warning(
                            f"Index {index_name} exists but is missing vector field configuration. Set force_recreate=True to fix."
                        )
                        return False
                else:
                    # Index exists and has vector field, we're good
                    logger.info(
                        f"Enhanced memory index '{index_name}' already exists with vector field"
                    )
                    return True

            # If we get here, either the index doesn't exist or we're recreating it
            logger.info(
                f"Creating enhanced memory index '{index_name}' with vector dimension {vector_dim}",
            )

            # Create enhanced index with vector field
            redis_client.ft(index_name).create_index(
                [
                    TextField(
                        "content", weight=5.0, sortable=True
                    ),  # Increase weight and make sortable
                    TextField("node_id", sortable=True),
                    TextField("trace_id", sortable=True),
                    NumericField("orka_expire_time", sortable=True),
                    VectorField(
                        vector_field_name,
                        "HNSW",
                        default_vector_params,
                    ),
                ],
                definition=IndexDefinition(prefix=["orka_memory:"], index_type=IndexType.HASH),
            )

            logger.info(f"✅ Enhanced memory index '{index_name}' created successfully")
            return True

        except redis.ResponseError as e:
            if "Unknown index name" in str(e):
                logger.info(
                    f"Creating enhanced memory index '{index_name}' with vector dimension {vector_dim}",
                )

                # Create enhanced index with vector field
                redis_client.ft(index_name).create_index(
                    [
                        TextField(
                            "content", weight=5.0, sortable=True
                        ),  # Increase weight and make sortable
                        TextField("node_id", sortable=True),
                        TextField("trace_id", sortable=True),
                        NumericField("orka_expire_time", sortable=True),
                        VectorField(
                            vector_field_name,
                            "HNSW",
                            default_vector_params,
                        ),
                    ],
                    definition=IndexDefinition(prefix=["orka_memory:"], index_type=IndexType.HASH),
                )

                logger.info(f"✅ Enhanced memory index '{index_name}' created successfully")
                return True
            else:
                raise
        except Exception as e:
            logger.error(f"❌ Failed to ensure enhanced memory index: {e}")
            if "unknown command" in str(e).lower() or "ft.create" in str(e).lower():
                logger.warning(
                    "⚠️  Redis instance does not support RediSearch. Please install RedisStack or enable RediSearch module.",
                )
                logger.info(
                    "🔧 For RedisStack setup: https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/",
                )
            elif "vector" in str(e).lower():
                logger.warning(
                    "⚠️  Redis instance does not support vector search. Please upgrade to RedisStack 7.2+ for vector capabilities.",
                )
            index_created = False
    except Exception as e:
        logger.error(f"Error checking enhanced memory index: {e}")
        index_created = False
    return index_created


def hybrid_vector_search(
    redis_client,
    query_text: str,
    query_vector: np.ndarray,
    num_results: int = 5,
    index_name: str = "orka_enhanced_memory",
    trace_id: str | None = None,
    format_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform hybrid vector search using RedisStack.
    Combines semantic vector search with text search and filtering.
    """
    results = []

    try:
        # Import Query from the correct location


        # Convert numpy array to bytes for Redis
        if hasattr(query_vector, "astype") and hasattr(query_vector, "tobytes"):
            vector_bytes = query_vector.astype(np.float32).tobytes()
        else:
            logger.error("Query vector must be a numpy array")
            return []

        # Construct the vector search query using correct RedisStack syntax
        base_query = f"*=>[KNN {num_results} @content_vector $query_vector AS vector_score]"

        logger.debug(f"- Vector search query: {base_query}")
        logger.debug(f"- Vector bytes length: {len(vector_bytes)}")
        logger.debug(
            f"Query vector shape: {query_vector.shape if hasattr(query_vector, 'shape') else 'No shape'}",
        )

        # Execute the search with proper parameters
        try:
            search_results = redis_client.ft(index_name).search(
                Query(base_query)
                .sort_by("vector_score")
                .paging(0, num_results)
                .return_fields("content", "node_id", "trace_id", "vector_score")
                .dialect(2),
                query_params={"query_vector": vector_bytes},
            )

            logger.debug(f"- Vector search returned {len(search_results.docs)} results")

            # Process results
            for doc in search_results.docs:
                try:
                    # Safely extract and validate the similarity score
                    # Redis returns the score with the alias we defined in the search query
                    # Try multiple possible field names for the score
                    raw_score = None
                    for score_field in ["vector_score", "__vector_score", "score", "similarity"]:
                        if hasattr(doc, score_field):
                            raw_score = getattr(doc, score_field)
                            logger.debug(
                                f"Found score field '{score_field}' with value: {raw_score}",
                            )
                            break

                    if raw_score is None:
                        # If no score field found, log available fields for debugging
                        available_fields = [attr for attr in dir(doc) if not attr.startswith("_")]
                        logger.debug(
                            f"- No score field found. Available fields: {available_fields}"
                        )
                        raw_score = 0.0

                    try:
                        score = float(raw_score)
                        import math

                        if math.isnan(score) or math.isinf(score):
                            score = 0.0
                        # This maps distance [0, 2] to similarity [1, 0]
                        if score < 0:
                            score = 1.0  # Treat negative as perfect similarity
                        elif score > 2:
                            score = 0.0  # Treat > 2 as no similarity

                        # Ensure final score is in [0, 1] range
                        score = max(0.0, min(1.0, score))
                        logger.debug(
                            f"- Converted cosine distance {raw_score} -> similarity {score}"
                        )
                    except (ValueError, TypeError) as e:
                        logger.debug(f"- Error converting score {raw_score}: {e}")
                        score = 0.0

                    result = {
                        "content": getattr(doc, "content", ""),
                        "node_id": getattr(doc, "node_id", ""),
                        "trace_id": getattr(doc, "trace_id", ""),
                        "score": score,
                        "key": doc.id,
                    }
                    results.append(result)
                except Exception as e:
                    # logger.warning(f"Error processing search result: {e}")
                    continue

        except Exception as search_error:
            logger.error(f"Vector search failed: {search_error}")
            logger.error(f"Search query was: {base_query}")
            logger.error(f"Vector bytes length: {len(vector_bytes)}")
            logger.error(f"Index name: {index_name}")
            # If vector search fails, try fallback to basic text search
            try:
                # logger.info("Falling back to basic text search")
                basic_query = f"@content:{query_text}"
                search_results = redis_client.ft(index_name).search(
                    Query(basic_query).paging(0, num_results),
                )

                for doc in search_results.docs:
                    try:
                        result = {
                            "content": getattr(doc, "content", ""),
                            "node_id": getattr(doc, "node_id", ""),
                            "trace_id": getattr(doc, "trace_id", ""),
                            "score": 0.5,  # Default score for text search (not perfect match)
                            "key": doc.id,
                        }
                        results.append(result)
                    except Exception as e:
                        # logger.warning(f"Error processing fallback result: {e}")
                        continue

            except Exception as fallback_error:
                logger.error(f"Both vector and fallback search failed: {fallback_error}")
                logger.error(f"Fallback query was: {basic_query}")

    except Exception as e:
        logger.error(f"Hybrid vector search failed: {e}")
        logger.debug(
            f"Query details - text: {query_text}, vector shape: {query_vector.shape if hasattr(query_vector, 'shape') else 'No shape'}",
        )

    # Apply trace filtering if specified
    if trace_id and results:
        results = [r for r in results if r.get("trace_id") == trace_id]

    logger.debug(f"- Returning {len(results)} search results")
    return results


def verify_memory_index(
    redis_client,
    index_name: str = "orka_enhanced_memory",
    format_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Verify that the memory index exists and has the correct schema.

    Returns:
        dict: Status information about the index
    """
    try:
        # Check if index exists
        info = redis_client.ft(index_name).info()

        # Parse index info
        index_info = {
            "exists": True,
            "num_docs": info.get("num_docs", 0),
            "fields": {},
            "vector_field_exists": False,
            "content_field_exists": False,
            "vector_field_name": None,
            "vector_field_type": None,
            "vector_field_dim": None,
        }

        # Extract field information
        if "attributes" in info:
            for attr in info["attributes"]:
                if isinstance(attr, list) and len(attr) >= 2:
                    # Handle both bytes and string field names
                    field_name = attr[1]
                    if isinstance(field_name, bytes):
                        field_name = field_name.decode("utf-8")

                    field_type = attr[3] if len(attr) > 3 else "UNKNOWN"
                    if isinstance(field_type, bytes):
                        field_type = field_type.decode("utf-8")

                    index_info["fields"][field_name] = field_type

                    # Check for vector field with more detailed inspection
                    if field_type == "VECTOR" or (
                        isinstance(attr, list) and len(attr) > 5 and "VECTOR" in str(attr)
                    ):
                        index_info["vector_field_exists"] = True
                        index_info["vector_field_name"] = field_name
                        index_info["vector_field_type"] = field_type

                        # Try to extract vector dimension if available
                        for i, item in enumerate(attr):
                            if (
                                isinstance(item, bytes)
                                and item.decode("utf-8", errors="ignore") == "DIM"
                                and i + 1 < len(attr)
                                and isinstance(attr[i + 1], int)
                            ):
                                index_info["vector_field_dim"] = attr[i + 1]

                    # Check for content field with more flexible type checking
                    if field_name == "content":
                        index_info["content_field_exists"] = True
                        logger.debug(f"Found content field with type: {field_type}")

        logger.info(f"Index {index_name} verification: {index_info}")
        return index_info

    except Exception as e:
        logger.error(f"Failed to verify index {index_name}: {e}")
        return {
            "exists": False,
            "error": str(e),
            "num_docs": 0,
            "fields": {},
            "vector_field_exists": False,
            "content_field_exists": False,
            "vector_field_name": None,
            "vector_field_type": None,
            "vector_field_dim": None,
        }


def legacy_vector_search(
    client: redis.Redis,
    query_vector: list[float] | np.ndarray,
    namespace: str | None = None,
    session: str | None = None,
    agent: str | None = None,
    similarity_threshold: float = 0.7,
    num_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Fallback vector search using legacy FLAT indexing.

    Args:
        client: Redis async client instance
        query_vector: Query vector for semantic similarity search
        namespace: Filter by namespace (legacy support)
        session: Filter by session ID
        agent: Filter by agent ID
        similarity_threshold: Minimum cosine similarity threshold
        num_results: Maximum number of results to return

    Returns:
        List of memory dictionaries with metadata and similarity scores
    """
    try:
        # Convert query vector to bytes if needed
        if isinstance(query_vector, np.ndarray):
            query_vector_bytes = query_vector.astype(np.float32).tobytes()
        else:
            query_vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()

        # Build search query with legacy filters
        query_parts = []

        if session:
            query_parts.append(f"@session:{{{session}}}")
        if agent:
            query_parts.append(f"@agent:{{{agent}}}")

        # Combine filters
        base_query = " ".join(query_parts) if query_parts else "*"

        # Build vector search query for legacy index with correct syntax
        if base_query == "*":
            vector_query = f"*=>[KNN {num_results} @vector $query_vector AS similarity]"
        else:
            vector_query = f"{base_query}=>[KNN {num_results} @vector $query_vector AS similarity]"

        # Execute legacy search with proper LIMIT syntax
        search_result = client.ft("memory_idx").search(
            Query(f"{vector_query} LIMIT 0 {num_results}").limit_fields(2),
            query_params={"query_vector": query_vector_bytes.decode("latin-1")},
        )

        # Process results
        results = []
        for doc in search_result.docs:
            try:
                # Extract memory data (legacy format)
                memory_data = {
                    "key": doc.id,
                    "content": doc.content,
                    "session": getattr(doc, "session", "default"),
                    "agent": getattr(doc, "agent", "unknown"),
                    "timestamp": float(getattr(doc, "ts", 0)),
                    "similarity": float(doc.similarity),
                }

                # Apply similarity threshold
                if memory_data["similarity"] >= similarity_threshold:
                    results.append(memory_data)

            except Exception as e:
                logger.error(f"Error processing legacy search result {doc.id}: {e}")
                continue

        # Sort by similarity score (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Legacy vector search returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Legacy vector search error: {e}")
        return []


async def retry(coro: Any, attempts: int = 3, backoff: float = 0.2) -> Any:
    """
    Retry a coroutine with exponential backoff on connection errors.

    This utility function helps handle transient connection issues with
    Redis by implementing a retry mechanism with exponential backoff.

    Args:
        coro: The coroutine to execute and potentially retry
        attempts: Maximum number of attempts before giving up (default: 3)
        backoff: Initial backoff time in seconds, doubles with each retry (default: 0.2)

    Returns:
        The result of the successful coroutine execution

    Raises:
        redis.ConnectionError: If all retry attempts fail
        Exception: Any other exceptions raised by the coroutine
        RuntimeError: If attempts <= 0

    Example:
        ```python
        # Retry a Redis operation up to 5 times with initial 0.5s backoff
        result = await retry(redis_client.get("key"), attempts=5, backoff=0.5)
        ```
    """
    if attempts <= 0:
        raise RuntimeError("Invalid number of attempts")

    last_error: redis.ConnectionError | None = None

    # Try first attempt without delay
    try:
        return await coro
    except redis.ConnectionError as e:
        if attempts == 1:
            raise
        last_error = e

    for attempt in range(1, attempts):
        try:
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))
            return await coro
        except redis.ConnectionError as e:
            if attempt == attempts - 1:
                raise
            last_error = e

    assert last_error is not None  # for mypy
    raise last_error
