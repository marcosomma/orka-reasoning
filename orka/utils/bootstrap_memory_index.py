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
from typing import Any, Dict, List, Optional, Union

import numpy as np
import redis
from redis.commands.search.field import NumericField, TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

logger = logging.getLogger(__name__)


def ensure_memory_index(redis_client, index_name="memory_entries"):
    """
    Ensure that the basic memory index exists.
    This creates a basic text search index for memory entries.
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


def ensure_enhanced_memory_index(redis_client, index_name="orka_enhanced_memory", vector_dim=384):
    """
    Ensure that the enhanced memory index with vector search exists.
    This creates an index with vector search capabilities for semantic search.
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
    redis_client,
    query_text: str,
    query_vector: np.ndarray,
    num_results: int = 5,
    index_name: str = "orka_enhanced_memory",
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid vector search using RedisStack.
    Combines semantic vector search with text search and filtering.
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
                query_params={"query_vector": vector_bytes},
            )

            logger.debug(f"Vector search returned {len(search_results.docs)} results")

            # Process results
            for doc in search_results.docs:
                try:
                    result = {
                        "content": getattr(doc, "content", ""),
                        "node_id": getattr(doc, "node_id", ""),
                        "trace_id": getattr(doc, "trace_id", ""),
                        "score": float(getattr(doc, "vector_score", 0.0)),
                        "key": doc.id,
                    }
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue

        except Exception as search_error:
            logger.warning(f"Vector search failed: {search_error}")

            # If vector search fails, try fallback to basic text search
            try:
                logger.info("Falling back to basic text search")
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
                            "score": 1.0,  # Default score for text search
                            "key": doc.id,
                        }
                        results.append(result)
                    except Exception as e:
                        logger.warning(f"Error processing fallback result: {e}")
                        continue

            except Exception as fallback_error:
                logger.error(f"Both vector and fallback search failed: {fallback_error}")

    except Exception as e:
        logger.error(f"Hybrid vector search failed: {e}")
        logger.debug(
            f"Query details - text: {query_text}, vector shape: {query_vector.shape if hasattr(query_vector, 'shape') else 'No shape'}",
        )

    # Apply trace filtering if specified
    if trace_id and results:
        results = [r for r in results if r.get("trace_id") == trace_id]

    logger.debug(f"Returning {len(results)} search results")
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
        if query_parts:
            base_query = " ".join(query_parts)
        else:
            base_query = "*"

        # Build vector search query for legacy index with correct syntax
        if base_query == "*":
            vector_query = f"*=>[KNN {num_results} @vector $query_vector AS similarity]"
        else:
            vector_query = f"{base_query}=>[KNN {num_results} @vector $query_vector AS similarity]"

        # Execute legacy search with proper LIMIT syntax
        search_result = client.ft("memory_idx").search(
            query=f"{vector_query} LIMIT 0 {num_results}",
            query_params={"query_vector": query_vector_bytes},
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


async def retry(coro, attempts=3, backoff=0.2):
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

    Example:
        ```python
        # Retry a Redis operation up to 5 times with initial 0.5s backoff
        result = await retry(redis_client.get("key"), attempts=5, backoff=0.5)
        ```
    """
    for i in range(attempts):
        try:
            # Attempt to execute the coroutine
            return await coro
        except redis.ConnectionError:
            # Only retry on connection errors, not other exceptions
            if i == attempts - 1:
                # Last attempt failed, propagate the exception
                raise
            # Wait with exponential backoff before next attempt
            # Example: backoff=0.2, i=0 → wait 0.2s; i=1 → wait 0.4s; i=2 → wait 0.8s
            await asyncio.sleep(backoff * (2**i))
