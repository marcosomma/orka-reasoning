# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""Provide utilities for initializing and managing Redis memory indices.

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
    client = redis.from_url("redis://localhost:6379")

    # Legacy FLAT indexing
    await ensure_memory_index(client)

    # Enhanced HNSW indexing
    await ensure_enhanced_memory_index(client)

    # Now the memory index is ready for use
```
"""

import asyncio
import logging
from typing import Any, Coroutine, Dict, List, Optional, TypeVar, Union

import numpy as np
import redis
from redis.commands.search.field import NumericField, TextField, VectorField

# Support both redis-py 4.x and 5.x versions
try:
    # redis-py <5 (camelCase)
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
except ModuleNotFoundError:
    # redis-py ≥5 (snake_case)
    from redis.commands.search.index_definition import IndexDefinition, IndexType

logger = logging.getLogger(__name__)

T = TypeVar("T")


def ensure_memory_index(redis_client: redis.Redis, index_name: str = "memory_entries") -> bool:
    """
    Ensure that the basic memory index exists.

    This creates a basic text search index for memory entries.

    Args:
        redis_client: Redis client instance
        index_name: Name of the index to create/check

    Returns:
        True if index exists or was created successfully, False otherwise
    """
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
    redis_client: redis.Redis, index_name: str = "orka_enhanced_memory", vector_dim: int = 384
) -> bool:
    """
    Ensure that the enhanced memory index with vector search exists.

    This creates an index with vector search capabilities for semantic search.

    Args:
        redis_client: Redis client instance
        index_name: Name of the index to create/check
        vector_dim: Dimension of the vector field

    Returns:
        True if index exists or was created successfully, False otherwise
    """
    try:
        # Check if index exists
        try:
            redis_client.ft(index_name).info()
            logger.info(f"Enhanced memory index '{index_name}' already exists")
            return True
        except redis.ResponseError as e:
            if "Unknown index name" in str(e):
                logger.info(
                    f"Creating enhanced memory index '{index_name}' with vector dimension {vector_dim}",
                )

                # Create enhanced index with vector field
                redis_client.ft(index_name).create_index(
                    [
                        TextField("content"),
                        TextField("node_id"),
                        TextField("trace_id"),
                        NumericField("orka_expire_time"),
                        VectorField(
                            "content_vector",
                            "HNSW",
                            {
                                "TYPE": "FLOAT32",
                                "DIM": vector_dim,
                                "DISTANCE_METRIC": "COSINE",
                                "EF_CONSTRUCTION": 200,
                                "M": 16,
                            },
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
            return False
    except Exception as e:
        logger.error(f"Error checking enhanced memory index: {e}")
        return False


def hybrid_vector_search(
    redis_client: redis.Redis,
    query_text: str,
    query_vector: np.ndarray,
    num_results: int = 5,
    index_name: str = "orka_enhanced_memory",
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid vector search using RedisStack.

    Combines semantic vector search with text search and filtering.

    Args:
        redis_client: Redis client instance
        query_text: Text query to search for
        query_vector: Vector representation of the query
        num_results: Maximum number of results to return
        index_name: Name of the index to search
        trace_id: Optional trace ID to filter results

    Returns:
        List of dictionaries containing search results
    """
    results = []

    try:
        # Import Query from the correct location
        from redis.commands.search.query import Query

        # Convert numpy array to bytes for Redis
        if isinstance(query_vector, np.ndarray):
            vector_bytes = query_vector.astype(np.float32).tobytes()
        else:
            logger.error("Query vector must be a numpy array")
            return []

        # Construct the vector search query using correct RedisStack syntax
        base_query = f"*=>[KNN {num_results} @content_vector $query_vector AS vector_score]"

        logger.debug(f"Vector search query: {base_query}")
        logger.debug(f"Vector bytes length: {len(vector_bytes)}")
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
                query_params={"query_vector": vector_bytes.decode("latin1")},
            )

            logger.debug(f"Vector search returned {len(search_results.docs)} results")

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
                        logger.debug(f"No score field found. Available fields: {available_fields}")
                        raw_score = 0.0

                    try:
                        score = float(raw_score)
                        # Check for NaN, infinity, or invalid values
                        import math

                        if math.isnan(score) or math.isinf(score):
                            score = 0.0
                        # For cosine distance: 0 = identical, 2 = opposite
                        # Convert to similarity: similarity = 1 - (distance / 2)
                        similarity = 1 - (score / 2)

                        # Add result to list
                        result = {
                            "content": getattr(doc, "content", ""),
                            "node_id": getattr(doc, "node_id", ""),
                            "trace_id": getattr(doc, "trace_id", ""),
                            "similarity": similarity,
                        }
                        results.append(result)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error converting score: {e}")
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")

        except Exception as e:
            logger.error(f"Error executing vector search: {e}")

    except Exception as e:
        logger.error(f"Error in hybrid vector search: {e}")

    return results


def legacy_vector_search(
    client: redis.Redis,
    query_vector: Union[List[float], np.ndarray],
    namespace: Optional[str] = None,
    session: Optional[str] = None,
    agent: Optional[str] = None,
    similarity_threshold: float = 0.7,
    num_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Legacy vector search implementation using FLAT index.

    This function provides backward compatibility for older Redis installations.

    Args:
        client: Redis client instance
        query_vector: Vector to search for
        namespace: Optional namespace to filter results
        session: Optional session ID to filter results
        agent: Optional agent ID to filter results
        similarity_threshold: Minimum similarity score to include in results
        num_results: Maximum number of results to return

    Returns:
        List of dictionaries containing search results
    """
    results = []

    try:
        # Convert query vector to bytes
        if isinstance(query_vector, np.ndarray):
            vector_bytes = query_vector.astype(np.float32).tobytes()
        else:
            vector_bytes = np.array(query_vector, dtype=np.float32).tobytes()

        # Build search query
        base_query = "*=>[KNN 10 @vector $vector AS score]"
        if namespace:
            base_query = f"@namespace:{{{namespace}}} {base_query}"
        if session:
            base_query = f"@session:{{{session}}} {base_query}"
        if agent:
            base_query = f"@agent:{{{agent}}} {base_query}"

        # Execute search
        from redis.commands.search.query import Query

        search_results = client.ft("memory_entries").search(
            Query(base_query)
            .sort_by("score")
            .paging(0, num_results)
            .return_fields("content", "vector", "score"),
            {"vector": vector_bytes.decode("latin1")},
        )

        # Process results
        for doc in search_results.docs:
            try:
                score = float(doc.score)
                similarity = 1 - (score / 2)  # Convert cosine distance to similarity
                if similarity >= similarity_threshold:
                    results.append(
                        {
                            "content": doc.content,
                            "similarity": similarity,
                        }
                    )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Error processing search result: {e}")

    except Exception as e:
        logger.error(f"Error in legacy vector search: {e}")

    return results


async def retry(coro: Coroutine[Any, Any, T], attempts: int = 3, backoff: float = 0.2) -> T:
    """
    Retry a coroutine with exponential backoff.

    This function helps handle transient failures by retrying operations.

    Args:
        coro: Coroutine to retry
        attempts: Maximum number of attempts
        backoff: Initial backoff time in seconds

    Returns:
        Result of the coroutine

    Raises:
        The last exception encountered if all attempts fail
    """
    last_error = None
    for attempt in range(attempts):
        try:
            return await coro
        except Exception as e:
            last_error = e
            if attempt < attempts - 1:  # Don't sleep on the last attempt
                await asyncio.sleep(backoff * (2**attempt))
    if last_error is not None:
        raise last_error
    raise RuntimeError("Retry failed with no error")
