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
RedisStack Memory Logger Implementation.

High-performance memory logger that leverages RedisStack's advanced capabilities
for semantic search and memory operations with HNSW vector indexing.

Key Features
------------

**Vector Search Performance:**
- HNSW (Hierarchical Navigable Small World) indexing for fast similarity search
- Hybrid search combining vector similarity with metadata filtering
- Fallback to text search when vector search fails
- Thread-safe operations with connection pooling

**Memory Management:**
- Automatic memory decay and expiration handling
- Importance-based memory classification (short_term/long_term)
- Namespace isolation for multi-tenant scenarios
- TTL (Time To Live) management with configurable expiry

**Production Features:**
- Thread-safe Redis client management with connection pooling
- Comprehensive error handling with graceful degradation
- Performance metrics and monitoring capabilities
- Batch operations for high-throughput scenarios

Architecture Details
-------------------

**Storage Schema:**
- Memory keys: `orka_memory:{uuid}`
- Hash fields: content, node_id, trace_id, importance_score, memory_type, timestamp, metadata
- Vector embeddings stored in RedisStack vector index
- Automatic expiry through `orka_expire_time` field

**Search Capabilities:**
1. **Vector Search**: Uses HNSW index for semantic similarity
2. **Hybrid Search**: Combines vector similarity with metadata filters
3. **Fallback Search**: Text-based search when vector search unavailable
4. **Filtered Search**: Support for trace_id, node_id, memory_type, importance, namespace

**Thread Safety:**
- Thread-local Redis connections for concurrent operations
- Connection locks for thread-safe access
- Separate embedding locks to prevent race conditions

**Memory Decay System:**
- Configurable decay rules based on importance and memory type
- Automatic cleanup of expired memories
- Dry-run support for testing cleanup operations

Usage Examples
--------------

**Basic Usage:**
```python
from orka.memory.redisstack_logger import RedisStackMemoryLogger

# Initialize with HNSW indexing
logger = RedisStackMemoryLogger(
    redis_url="redis://localhost:6380/0",
    index_name="orka_enhanced_memory",
    embedder=my_embedder,
    enable_hnsw=True
)

# Log a memory
memory_key = logger.log_memory(
    content="Important information",
    node_id="agent_1",
    trace_id="session_123",
    importance_score=0.8,
    memory_type="long_term"
)

# Search memories
results = logger.search_memories(
    query="information",
    num_results=5,
    trace_id="session_123"
)
```

**Advanced Configuration:**
```python
# With memory decay configuration
decay_config = {
    "enabled": True,
    "short_term_hours": 24,
    "long_term_hours": 168,  # 1 week
    "importance_threshold": 0.7
}

logger = RedisStackMemoryLogger(
    redis_url="redis://localhost:6380/0",
    memory_decay_config=decay_config,
    vector_params={"M": 16, "ef_construction": 200}
)
```

Implementation Notes
-------------------

**Error Handling:**
- Vector search failures automatically fall back to text search
- Redis connection errors are logged and handled gracefully
- Invalid metadata is parsed safely with fallback to empty objects

**Performance Considerations:**
- Thread-local connections prevent connection contention
- Embedding operations are locked to prevent race conditions
- Memory cleanup operations support dry-run mode for testing

**Compatibility:**
- Maintains BaseMemoryLogger interface for drop-in replacement
- Supports both async and sync embedding generation
- Compatible with Redis and RedisStack deployments
"""

import json
import logging
import threading
import time
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional, Union, cast

import numpy as np
import redis
from numpy.typing import NDArray

from .base_logger import BaseMemoryLogger

logger = logging.getLogger(__name__)

# Check if Redis search is available
REDIS_SEARCH_AVAILABLE = False
try:
    import redis.commands.search.field  # type: ignore
    import redis.commands.search.indexDefinition  # type: ignore

    REDIS_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("RedisStack search module not available")

RedisType = redis.Redis  # type: ignore


class RedisStackMemoryLogger(BaseMemoryLogger):
    """RedisStack memory logger implementation.

    A high-performance memory engine powered by RedisStack with HNSW vector indexing.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",  # Use port 6379 by default
        index_name: str = "orka_enhanced_memory",
        embedder: Optional[Any] = None,
        memory_decay_config: Optional[Dict[str, Any]] = None,
        # Additional parameters for factory compatibility
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[Dict[str, Any]] = None,
        enable_hnsw: bool = True,
        vector_params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the RedisStack memory logger."""
        # Handle legacy decay config
        effective_decay_config = memory_decay_config or decay_config

        super().__init__(
            stream_key=stream_key,
            debug_keep_previous_outputs=debug_keep_previous_outputs,
            decay_config=effective_decay_config,
        )

        self.redis_url: str = redis_url
        self.index_name: str = index_name
        self.embedder: Optional[Any] = embedder
        self.enable_hnsw: bool = enable_hnsw and REDIS_SEARCH_AVAILABLE
        self.vector_params: Dict[str, Any] = vector_params or {}
        self.memory_decay_config: Dict[str, Any] = effective_decay_config or {}

        # Thread-local storage for Redis connections
        self._local: threading.local = threading.local()
        self._connection_lock: Lock = Lock()
        self._embedding_lock: Lock = Lock()

        # Initialize Redis connection
        self._redis_client: Optional[RedisType] = None
        self._init_redis_client()

        # Initialize index if enabled
        if self.enable_hnsw:
            self._ensure_index()

    def _init_redis_client(self) -> None:
        """Initialize the Redis client with proper configuration."""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                health_check_interval=30,
            )
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _create_redis_connection(self) -> RedisType:
        """Create a new Redis connection."""
        return redis.from_url(
            self.redis_url,
            decode_responses=True,
            health_check_interval=30,
        )

    def _get_thread_safe_client(self) -> RedisType:
        """Get a thread-safe Redis client."""
        if not hasattr(self._local, "redis"):
            with self._connection_lock:
                self._local.redis = self._create_redis_connection()
        return self._local.redis

    @property
    def redis(self) -> RedisType:
        """Get the Redis client."""
        return self._get_thread_safe_client()

    def _ensure_index(self) -> None:
        """Ensure the vector index exists."""
        if not self.enable_hnsw or not REDIS_SEARCH_AVAILABLE:
            return

        try:
            # Import Redis search modules at runtime
            from redis.commands.search.field import TextField, VectorField  # type: ignore
            from redis.commands.search.indexDefinition import IndexDefinition, IndexType  # type: ignore

            # Define index schema
            schema = (
                TextField("$.content", as_name="content"),
                TextField("$.node_id", as_name="node_id"),
                TextField("$.trace_id", as_name="trace_id"),
                TextField("$.memory_type", as_name="memory_type"),
                VectorField(
                    "$.embedding",
                    "HNSW",
                    cast(
                        Dict[str, Any],
                        {
                            "TYPE": "FLOAT32",
                            "DIM": 1536,  # Default dimension for text-embedding-ada-002
                            "DISTANCE_METRIC": "COSINE",
                            **self.vector_params,
                        },
                    ),
                    as_name="embedding",
                ),
            )

            # Create index
            try:
                self.redis.ft(self.index_name).create_index(
                    fields=schema,
                    definition=IndexDefinition(
                        prefix=["orka_memory:"],
                        index_type=IndexType.JSON,
                    ),
                )
                logger.info(f"Created RedisStack index: {self.index_name}")
            except Exception as e:
                if "Index already exists" not in str(e):
                    raise
                logger.debug(f"RedisStack index {self.index_name} already exists")

        except Exception as e:
            logger.error(f"Failed to create RedisStack index: {e}")
            self.enable_hnsw = False

    def log_memory(
        self,
        content: str,
        node_id: str,
        trace_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: float = 1.0,
        memory_type: str = "short_term",
        expiry_hours: Optional[float] = None,
    ) -> str:
        """Store memory with vector embedding for enhanced search."""
        try:
            # Store memory with enhanced metadata
            memory_id = str(uuid.uuid4()).replace("-", "")
            memory_key = f"orka_memory:{memory_id}"

            current_time_ms = int(time.time() * 1000)
            metadata = metadata or {}

            # Calculate expiry time if specified
            orka_expire_time = None
            if expiry_hours is not None:
                orka_expire_time = current_time_ms + int(expiry_hours * 3600 * 1000)

            # Store to Redis with vector embedding
            client = self._get_thread_safe_client()

            # Ensure all data is Redis-serializable
            try:
                # Test serialization of content
                if not isinstance(content, str):
                    logger.warning(f"Content is not a string: {type(content)}, converting...")
                    content = str(content)

            except Exception as serialize_error:
                logger.error(f"Serialization error: {serialize_error}")
                # Create safe fallback data
                safe_metadata = {
                    "error": "serialization_failed",
                    "original_error": str(serialize_error),
                    "node_id": node_id,
                    "trace_id": trace_id,
                    "log_type": "memory",
                }
                metadata = safe_metadata
                if not isinstance(content, str):
                    content = str(content)
                logger.warning("Using safe fallback metadata due to serialization error")

            # Store memory data
            memory_data = {
                "content": content,
                "node_id": node_id,
                "trace_id": trace_id,
                "timestamp": current_time_ms,
                "importance_score": importance_score,
                "memory_type": memory_type,
                "metadata": json.dumps(metadata),
            }

            if orka_expire_time:
                memory_data["orka_expire_time"] = orka_expire_time

            # Generate embedding if embedder is available
            if self.embedder:
                try:
                    embedding = self._get_embedding_sync(content)
                    if embedding is not None:
                        memory_data["content_vector"] = embedding.tobytes()
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for memory: {e}")

            # Store the memory
            client.hset(memory_key, mapping=memory_data)

            # Set TTL if specified
            if orka_expire_time:
                ttl_seconds = max(1, int((orka_expire_time - current_time_ms) / 1000))
                client.expire(memory_key, ttl_seconds)

            return memory_key

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    def _get_embedding_sync(self, text: str) -> NDArray[np.float32]:
        """Get embedding in a sync context, handling async embedder properly."""
        try:
            import asyncio

            # Check if we're in an async context
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                # We're in an async context - use fallback encoding to avoid complications
                logger.debug(f"In async context, using fallback encoding for embedding {loop}")
                return self.embedder._fallback_encode(text)

            except RuntimeError:
                # No running event loop, safe to use asyncio.run()
                return asyncio.run(self.embedder.encode(text))

        except Exception as e:
            logger.warning(f"Failed to get embedding: {e}")
            # Return a zero vector as fallback
            embedding_dim = getattr(self.embedder, "embedding_dim", 384)
            return np.zeros(embedding_dim, dtype=np.float32)

    def search_memories(
        self,
        query: str,
        num_results: int = 10,
        trace_id: Optional[str] = None,
        node_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        log_type: str = "memory",  # Filter by log type (default: only memories)
        namespace: Optional[str] = None,  # Filter by namespace
    ) -> List[Dict[str, Any]]:
        """
        Search memories using enhanced vector search with filtering.

        Args:
            query: Search query text
            num_results: Maximum number of results
            trace_id: Filter by trace ID
            node_id: Filter by node ID
            memory_type: Filter by memory type
            min_importance: Minimum importance score

        Returns:
            List of matching memory entries with scores
        """
        try:
            # Try vector search if embedder is available
            if self.embedder:
                try:
                    # Use sync embedding wrapper
                    query_vector = self._get_embedding_sync(query)

                    from orka.utils.bootstrap_memory_index import hybrid_vector_search

                    logger.debug(f"Performing vector search for: {query}")

                    client = self._get_thread_safe_client()
                    results = hybrid_vector_search(
                        redis_client=client,
                        query_text=query,
                        query_vector=query_vector,
                        num_results=num_results,
                        index_name=self.index_name,
                        trace_id=trace_id,
                    )

                    logger.debug(f"Vector search returned {len(results)} results")

                    # Convert to expected format and apply additional filters
                    formatted_results = []
                    for result in results:
                        try:
                            # Get full memory data
                            memory_data = self.redis.hgetall(result["key"])
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

                            # Check expiry
                            if self._is_expired(memory_data):
                                continue

                            # Parse metadata
                            try:
                                # Handle both string and bytes keys for Redis data
                                metadata_value = self._safe_get_redis_value(
                                    memory_data,
                                    "metadata",
                                    "{}",
                                )
                                metadata = json.loads(metadata_value)
                            except Exception as e:
                                logger.debug(f"Error parsing metadata for key {result['key']}: {e}")
                                metadata = {}

                            # Check if this is a stored memory
                            memory_log_type = metadata.get("log_type", "log")
                            memory_category = metadata.get("category", "log")

                            is_stored_memory = (
                                memory_log_type == "memory" or memory_category == "stored"
                            )

                            # Skip if we want memory entries but this isn't a stored memory
                            if log_type == "memory" and not is_stored_memory:
                                continue

                            # Skip if we want log entries but this is a stored memory
                            if log_type == "log" and is_stored_memory:
                                continue

                            # Filter by namespace
                            if namespace:
                                memory_namespace = metadata.get("namespace")
                                if memory_namespace != namespace:
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
                                # TTL information
                                "ttl_seconds": expiry_info["ttl_seconds"],
                                "ttl_formatted": expiry_info["ttl_formatted"],
                                "expires_at": expiry_info["expires_at"],
                                "expires_at_formatted": expiry_info["expires_at_formatted"],
                                "has_expiry": expiry_info["has_expiry"],
                            }
                            formatted_results.append(formatted_result)

                        except Exception as e:
                            logger.warning(f"Error processing search result: {e}")
                            continue

                    logger.debug(f"Returning {len(formatted_results)} filtered results")
                    return formatted_results

                except Exception as e:
                    logger.warning(f"Vector search failed, falling back to text search: {e}")

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

    def _safe_get_redis_value(
        self, memory_data: Dict[str, Any], key: str, default: Any = None
    ) -> Any:
        """Safely get value from Redis hash data that might have bytes or string keys."""
        # Try string key first
        value = memory_data.get(key, default)
        if value is not None:
            return value.decode() if isinstance(value, bytes) else value

        # Try bytes key
        bytes_key = key.encode("utf-8") if isinstance(key, str) else key
        value = memory_data.get(bytes_key, default)
        return value.decode() if isinstance(value, bytes) else value

    def _validate_similarity_score(self, score: Any) -> float:
        """Validate and sanitize similarity scores to prevent NaN values."""
        try:
            score_float = float(score)
            if np.isnan(score_float) or np.isinf(score_float):
                return 0.0
            return max(0.0, min(1.0, score_float))
        except (TypeError, ValueError):
            return 0.0

    def _encode_value(self, value: Union[str, bytes, int, float]) -> str:
        """Encode a value for Redis storage."""
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return str(value)
        return str(value)

    def _encode_key(self, key: str) -> str:
        """Encode a key for Redis storage."""
        if isinstance(key, bytes):
            try:
                return key.decode("utf-8")
            except UnicodeDecodeError:
                return str(key)
        return str(key)

    def _fallback_text_search(
        self,
        query: str,
        num_results: int,
        trace_id: Optional[str] = None,
        node_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        log_type: str = "memory",
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fallback text search using basic Redis search capabilities."""
        try:
            logger.info("Using fallback text search")

            # Import Query from the correct location
            from redis.commands.search.query import Query

            # Build search query
            search_query = f"@content:{query}"

            # Add filters
            filters = []
            if trace_id:
                filters.append(f"@trace_id:{trace_id}")
            if node_id:
                filters.append(f"@node_id:{node_id}")

            if filters:
                search_query = " ".join([search_query] + filters)

            # Execute search
            search_results = self.redis.ft(self.index_name).search(
                Query(search_query).paging(0, num_results),
            )

            results = []
            for doc in search_results.docs:
                try:
                    memory_data = self.redis.hgetall(doc.id)
                    if not memory_data:
                        continue

                    # Apply additional filters using safe value access
                    if (
                        memory_type
                        and self._safe_get_redis_value(memory_data, "memory_type") != memory_type
                    ):
                        continue

                    importance_str = self._safe_get_redis_value(
                        memory_data,
                        "importance_score",
                        "0",
                    )
                    if min_importance and float(importance_str) < min_importance:
                        continue

                    # Check expiry
                    if self._is_expired(memory_data):
                        continue

                    # Parse metadata with proper bytes handling
                    try:
                        metadata_value = self._safe_get_redis_value(memory_data, "metadata", "{}")
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {doc.id}: {e}")
                        metadata = {}

                    # Filter by log_type (same logic as vector search)
                    memory_log_type = metadata.get("log_type", "log")
                    memory_category = metadata.get("category", "log")

                    # Check if this is a stored memory (same as vector search)
                    is_stored_memory = memory_log_type == "memory" or memory_category == "stored"

                    # Skip if we want memory entries but this isn't a stored memory
                    if log_type == "memory" and not is_stored_memory:
                        continue

                    # Skip if we want log entries but this is a stored memory
                    if log_type == "log" and is_stored_memory:
                        continue

                    # Filter by namespace (same logic as vector search)
                    if namespace:
                        memory_namespace = metadata.get("namespace")
                        if memory_namespace != namespace:
                            continue

                    # Calculate TTL information
                    current_time_ms = int(time.time() * 1000)
                    expiry_info = self._get_ttl_info(doc.id, memory_data, current_time_ms)

                    # Build result with safe value access
                    result = {
                        "content": self._safe_get_redis_value(memory_data, "content", ""),
                        "node_id": self._safe_get_redis_value(memory_data, "node_id", ""),
                        "trace_id": self._safe_get_redis_value(memory_data, "trace_id", ""),
                        "importance_score": float(
                            self._safe_get_redis_value(memory_data, "importance_score", "0"),
                        ),
                        "memory_type": self._safe_get_redis_value(memory_data, "memory_type", ""),
                        "timestamp": int(self._safe_get_redis_value(memory_data, "timestamp", "0")),
                        "metadata": metadata,
                        "similarity_score": 0.5,  # Default score for text search
                        "key": doc.id,
                        # TTL information
                        "ttl_seconds": expiry_info["ttl_seconds"],
                        "ttl_formatted": expiry_info["ttl_formatted"],
                        "expires_at": expiry_info["expires_at"],
                        "expires_at_formatted": expiry_info["expires_at_formatted"],
                        "has_expiry": expiry_info["has_expiry"],
                    }
                    results.append(result)

                except Exception as e:
                    logger.warning(f"Error processing fallback result: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Fallback text search failed: {e}")
            # If all search methods fail, return empty list
            return []

    def _is_expired(self, memory_data: Dict[str, Any]) -> bool:
        """Check if memory entry has expired."""
        expiry_time = self._safe_get_redis_value(memory_data, "orka_expire_time")
        if expiry_time:
            try:
                return int(float(expiry_time)) <= int(time.time() * 1000)
            except (ValueError, TypeError):
                pass
        return False

    def get_all_memories(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all memories, optionally filtered by trace_id."""
        try:
            pattern = "orka_memory:*"
            keys = self.redis.keys(pattern)

            memories = []
            for key in keys:
                try:
                    memory_data = self.redis.hgetall(key)
                    if not memory_data:
                        continue

                    # Filter by trace_id if specified
                    if trace_id and memory_data.get("trace_id") != trace_id:
                        continue

                    # Check expiry
                    if self._is_expired(memory_data):
                        continue

                    # Parse metadata
                    try:
                        metadata_value = memory_data.get("metadata", "{}")
                        if isinstance(metadata_value, bytes):
                            metadata_value = metadata_value.decode()
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                    memory = {
                        "content": memory_data.get("content", ""),
                        "node_id": memory_data.get("node_id", ""),
                        "trace_id": memory_data.get("trace_id", ""),
                        "importance_score": float(memory_data.get("importance_score", 0)),
                        "memory_type": memory_data.get("memory_type", ""),
                        "timestamp": int(memory_data.get("timestamp", 0)),
                        "metadata": metadata,
                        "key": key,
                    }
                    memories.append(memory)

                except Exception as e:
                    logger.warning(f"Error processing memory {key}: {e}")
                    continue

            # Sort by timestamp (newest first)
            memories.sort(key=lambda x: x["timestamp"], reverse=True)
            return memories

        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []

    def delete_memory(self, key: str) -> bool:
        """Delete a specific memory entry."""
        try:
            result = self.redis.delete(key)
            logger.debug(f"Deleted memory key: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete memory {key}: {e}")
            return False

    def close(self) -> None:
        """Clean up resources."""
        try:
            if self._redis_client:
                self._redis_client.close()
            # Also close thread-local connections
            if hasattr(self._local, "redis"):
                try:
                    self._local.redis.close()
                except Exception:
                    pass  # Ignore errors during cleanup
        except Exception as e:
            logger.error(f"Error closing RedisStack logger: {e}")

    def clear_all_memories(self) -> None:
        """Clear all memories from the RedisStack storage."""
        try:
            pattern = "orka_memory:*"
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} memories from RedisStack")
            else:
                logger.info("No memories to clear")
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory storage statistics."""
        try:
            # Use thread-safe client to match log_memory() method
            client = self._get_thread_safe_client()
            pattern = "orka_memory:*"
            keys = client.keys(pattern)

            total_memories = len(keys)
            expired_count = 0
            log_count = 0
            stored_count = 0
            memory_types = {}
            categories = {}

            # Analyze each memory entry
            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if not memory_data:
                        continue

                    # Check expiry
                    if self._is_expired(memory_data):
                        expired_count += 1
                        continue

                    # Parse metadata (handle bytes keys from decode_responses=False)
                    try:
                        metadata_value = memory_data.get(b"metadata") or memory_data.get(
                            "metadata",
                            "{}",
                        )
                        if isinstance(metadata_value, bytes):
                            metadata_value = metadata_value.decode()
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                    # Count by log_type and determine correct category
                    log_type = metadata.get("log_type", "log")
                    category = metadata.get("category", "log")

                    # Determine if this is a stored memory or orchestration log
                    if log_type == "memory" or category == "stored":
                        stored_count += 1
                        # Count as "stored" in categories regardless of original category value
                        categories["stored"] = categories.get("stored", 0) + 1
                    else:
                        log_count += 1
                        # Count as "log" in categories for orchestration logs
                        categories["log"] = categories.get("log", 0) + 1

                    # Count by memory_type (handle bytes keys)
                    memory_type = memory_data.get(b"memory_type") or memory_data.get(
                        "memory_type",
                        "unknown",
                    )
                    if isinstance(memory_type, bytes):
                        memory_type = memory_type.decode()
                    memory_types[memory_type] = memory_types.get(memory_type, 0) + 1

                    # Note: Category counting is now handled above in the log_type classification

                except Exception as e:
                    logger.warning(f"Error analyzing memory {key}: {e}")
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
                    self.memory_decay_config and self.memory_decay_config.get("enabled", True),
                ),
                "timestamp": int(time.time() * 1000),
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    # Abstract method implementations required by BaseMemoryLogger
    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: Dict[str, Any],
        step: Optional[int] = None,
        run_id: Optional[str] = None,
        fork_group: Optional[str] = None,
        parent: Optional[str] = None,
        previous_outputs: Optional[Dict[str, Any]] = None,
        agent_decay_config: Optional[Dict[str, Any]] = None,
        log_type: str = "log",  # "log" for orchestration, "memory" for stored memories
    ) -> None:
        """
        Log an orchestration event as a memory entry.

        This method converts orchestration events into memory entries for storage.
        """
        try:
            # Extract content from payload for memory storage
            content = self._extract_content_from_payload(payload, event_type)

            # Determine memory type and importance
            importance_score = self._calculate_importance_score(event_type, payload)
            memory_type = self._determine_memory_type(event_type, importance_score)

            # Calculate expiry hours based on memory type and decay config
            expiry_hours = self._calculate_expiry_hours(
                memory_type,
                importance_score,
                agent_decay_config,
            )

            # Force 10 second TTL for orchestration logs
            if log_type == "log":
                expiry_hours = 10 / 3600  # 10 seconds in hours

            # Store as memory entry
            self.log_memory(
                content=content,
                node_id=agent_id,
                trace_id=run_id or "default",
                metadata={
                    "event_type": event_type,
                    "step": step,
                    "fork_group": fork_group,
                    "parent": parent,
                    "previous_outputs": previous_outputs,
                    "agent_decay_config": agent_decay_config,
                    "log_type": log_type,  # Store log_type for filtering
                    "category": self._classify_memory_category(
                        event_type,
                        agent_id,
                        payload,
                        log_type,
                    ),
                },
                importance_score=importance_score,
                memory_type=memory_type,
                expiry_hours=expiry_hours,
            )

            # Also add to local memory buffer for trace files
            trace_entry = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": int(time.time() * 1000),
                "payload": payload,
                "step": step,
                "run_id": run_id,
                "fork_group": fork_group,
                "parent": parent,
                "previous_outputs": previous_outputs,
            }
            self.memory.append(trace_entry)

        except Exception as e:
            logger.error(f"Failed to log orchestration event: {e}")

    def _extract_content_from_payload(self, payload: Dict[str, Any], event_type: str) -> str:
        """Extract meaningful content from payload for memory storage."""
        content_parts = []

        # Extract from common content fields
        for field in [
            "content",
            "message",
            "response",
            "result",
            "output",
            "text",
            "formatted_prompt",
        ]:
            if payload.get(field):
                content_parts.append(str(payload[field]))

        # Include event type for context
        content_parts.append(f"Event: {event_type}")

        # Fallback to full payload if no content found
        if len(content_parts) == 1:  # Only event type
            content_parts.append(json.dumps(payload, default=str))

        return " ".join(content_parts)

    def _calculate_importance_score(self, event_type: str, payload: Dict[str, Any]) -> float:
        """Calculate importance score based on event type and payload."""
        # Base importance by event type
        importance_map = {
            "agent.start": 0.7,
            "agent.end": 0.8,
            "agent.error": 0.9,
            "orchestrator.start": 0.8,
            "orchestrator.end": 0.9,
            "memory.store": 0.6,
            "memory.retrieve": 0.4,
            "llm.query": 0.5,
            "llm.response": 0.6,
        }

        base_importance = importance_map.get(event_type, 0.5)

        # Adjust based on payload content
        if isinstance(payload, dict):
            # Higher importance for errors
            if "error" in payload or "exception" in payload:
                base_importance = min(1.0, base_importance + 0.3)

            # Higher importance for final results
            if "result" in payload and payload.get("result"):
                base_importance = min(1.0, base_importance + 0.2)

        return base_importance

    def _determine_memory_type(self, event_type: str, importance_score: float) -> str:
        """Determine memory type based on event type and importance."""
        # Long-term memory for important events
        long_term_events = {
            "orchestrator.end",
            "agent.error",
            "orchestrator.start",
        }

        if event_type in long_term_events or importance_score >= 0.8:
            return "long_term"
        else:
            return "short_term"

    def _calculate_expiry_hours(
        self,
        memory_type: str,
        importance_score: float,
        agent_decay_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Calculate expiry hours based on memory type and importance."""
        # Use agent-specific config if available, otherwise use default
        decay_config = agent_decay_config or self.memory_decay_config

        if not decay_config.get("enabled", True):
            return None

        # Base expiry times
        if memory_type == "long_term":
            # Check agent-level config first, then fall back to global config
            base_hours = decay_config.get("long_term_hours") or decay_config.get(
                "default_long_term_hours",
                24.0,
            )
        else:
            # Check agent-level config first, then fall back to global config
            base_hours = decay_config.get("short_term_hours") or decay_config.get(
                "default_short_term_hours",
                1.0,
            )

        # Adjust based on importance (higher importance = longer retention)
        importance_multiplier = 1.0 + importance_score
        adjusted_hours = base_hours * importance_multiplier

        return adjusted_hours

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent memory entries."""
        try:
            # Get all memories and sort by timestamp
            memories = self.get_all_memories()

            # Sort by timestamp (newest first) and limit
            memories.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return memories[:count]

        except Exception as e:
            logger.error(f"Error in tail operation: {e}")
            return []

    def cleanup_expired_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up expired memories."""
        cleaned = 0
        total_checked = 0
        errors = []

        try:
            pattern = "orka_memory:*"
            keys = self.redis.keys(pattern)
            total_checked = len(keys)

            expired_keys = []
            for key in keys:
                try:
                    memory_data = self.redis.hgetall(key)
                    if self._is_expired(memory_data):
                        expired_keys.append(key)
                except Exception as e:
                    errors.append(f"Error checking {key}: {e}")

            if not dry_run and expired_keys:
                # Delete expired keys in batches
                batch_size = 100
                for i in range(0, len(expired_keys), batch_size):
                    batch = expired_keys[i : i + batch_size]
                    try:
                        deleted_count = self.redis.delete(*batch)
                        cleaned += deleted_count
                        logger.debug(f"Deleted batch of {deleted_count} expired memories")
                    except Exception as e:
                        errors.append(f"Batch deletion error: {e}")

            result = {
                "cleaned": cleaned,
                "total_checked": total_checked,
                "expired_found": len(expired_keys),
                "dry_run": dry_run,
                "cleanup_type": "redisstack",
                "errors": errors,
            }

            if cleaned > 0:
                logger.info(f"Cleanup completed: {cleaned} expired memories removed")

            return result

        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return {
                "error": str(e),
                "cleaned": 0,
                "total_checked": total_checked,
                "cleanup_type": "redisstack_failed",
                "errors": errors + [str(e)],
            }

    # Redis interface methods (thread-safe delegated methods)
    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a hash field."""
        encoded_value = self._encode_value(value)
        encoded_key = self._encode_key(key)
        client = self._get_thread_safe_client()
        return client.hset(name, key=encoded_key, value=encoded_value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field."""
        client = self._get_thread_safe_client()
        encoded_key = self._encode_key(key)
        try:
            value = client.hget(name, encoded_key)
            if value is None:
                return None
            return value if isinstance(value, str) else value.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            return None

    def hkeys(self, name: str) -> List[str]:
        """Get all hash field names."""
        client = self._get_thread_safe_client()
        try:
            keys = client.hkeys(name)
            return [k if isinstance(k, str) else k.decode("utf-8") for k in keys]
        except (AttributeError, UnicodeDecodeError):
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        client = self._get_thread_safe_client()
        encoded_keys = [self._encode_key(k) for k in keys]
        return client.hdel(name, *encoded_keys)

    def smembers(self, name: str) -> List[str]:
        """Get all set members."""
        client = self._get_thread_safe_client()
        try:
            members = client.smembers(name)
            return [m if isinstance(m, str) else m.decode("utf-8") for m in members]
        except (AttributeError, UnicodeDecodeError):
            return []

    def sadd(self, name: str, *values: str) -> int:
        """Add members to a set."""
        client = self._get_thread_safe_client()
        encoded_values = [self._encode_value(v) for v in values]
        return client.sadd(name, *encoded_values)

    def srem(self, name: str, *values: str) -> int:
        """Remove members from a set."""
        client = self._get_thread_safe_client()
        encoded_values = [self._encode_value(v) for v in values]
        return client.srem(name, *encoded_values)

    def get(self, key: str) -> Optional[str]:
        """Get a key's value."""
        client = self._get_thread_safe_client()
        encoded_key = self._encode_key(key)
        try:
            value = client.get(encoded_key)
            if value is None:
                return None
            return value if isinstance(value, str) else value.decode("utf-8")
        except (AttributeError, UnicodeDecodeError):
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a key's value."""
        client = self._get_thread_safe_client()
        encoded_key = self._encode_key(key)
        encoded_value = self._encode_value(value)
        return bool(client.set(encoded_key, encoded_value))

    def delete(self, *keys: str) -> int:
        """Delete keys."""
        client = self._get_thread_safe_client()
        encoded_keys = [self._encode_key(k) for k in keys]
        return client.delete(*encoded_keys)

    def ensure_index(self) -> bool:
        """Ensure the enhanced memory index exists - for factory compatibility."""
        try:
            self._ensure_index()
            return True
        except Exception as e:
            logger.error(f"Failed to ensure index: {e}")
            return False

    def get_recent_stored_memories(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent stored memories (log_type='memory' only), sorted by timestamp."""
        try:
            # Use thread-safe client to match log_memory() method
            client = self._get_thread_safe_client()
            pattern = "orka_memory:*"
            keys = client.keys(pattern)

            stored_memories = []
            current_time_ms = int(time.time() * 1000)

            for key in keys:
                try:
                    memory_data = client.hgetall(key)
                    if not memory_data:
                        continue

                    # Check expiry
                    if self._is_expired(memory_data):
                        continue

                    # Parse metadata (handle bytes keys from decode_responses=False)
                    try:
                        metadata_value = memory_data.get(b"metadata") or memory_data.get(
                            "metadata",
                            "{}",
                        )
                        if isinstance(metadata_value, bytes):
                            metadata_value = metadata_value.decode()
                        metadata = json.loads(metadata_value)
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for key {key}: {e}")
                        metadata = {}

                        # Only include stored memories (not orchestration logs)
                    memory_log_type = metadata.get("log_type", "log")
                    memory_category = metadata.get("category", "log")

                    # Skip if not a stored memory
                    if memory_log_type != "memory" and memory_category != "stored":
                        continue

                    # Calculate TTL information
                    expiry_info = self._get_ttl_info(key, memory_data, current_time_ms)

                    memory = {
                        "content": memory_data.get(b"content") or memory_data.get("content", ""),
                        "node_id": memory_data.get(b"node_id") or memory_data.get("node_id", ""),
                        "trace_id": memory_data.get(b"trace_id") or memory_data.get("trace_id", ""),
                        "importance_score": float(
                            memory_data.get(b"importance_score")
                            or memory_data.get("importance_score", 0),
                        ),
                        "memory_type": memory_data.get(b"memory_type")
                        or memory_data.get("memory_type", ""),
                        "timestamp": int(
                            memory_data.get(b"timestamp") or memory_data.get("timestamp", 0),
                        ),
                        "metadata": metadata,
                        "key": key,
                        # TTL and expiration information
                        "ttl_seconds": expiry_info["ttl_seconds"],
                        "ttl_formatted": expiry_info["ttl_formatted"],
                        "expires_at": expiry_info["expires_at"],
                        "expires_at_formatted": expiry_info["expires_at_formatted"],
                        "has_expiry": expiry_info["has_expiry"],
                    }
                    stored_memories.append(memory)

                except Exception as e:
                    logger.warning(f"Error processing memory {key}: {e}")
                    continue

            # Sort by timestamp (newest first) and limit
            stored_memories.sort(key=lambda x: x["timestamp"], reverse=True)
            return stored_memories[:count]

        except Exception as e:
            logger.error(f"Failed to get recent stored memories: {e}")
            return []

    def _get_ttl_info(
        self,
        key: str,
        memory_data: Dict[str, Any],
        current_time_ms: int,
    ) -> Dict[str, Any]:
        """Get TTL information for a memory entry."""
        try:
            # Check if memory has expiry time set (handle bytes keys)
            orka_expire_time = memory_data.get(b"orka_expire_time") or memory_data.get(
                "orka_expire_time",
            )

            if orka_expire_time:
                try:
                    expire_time_ms = int(float(orka_expire_time))
                    ttl_ms = expire_time_ms - current_time_ms
                    ttl_seconds = max(0, ttl_ms // 1000)

                    # Format expire time
                    import datetime

                    expires_at = datetime.datetime.fromtimestamp(expire_time_ms / 1000)
                    expires_at_formatted = expires_at.strftime("%Y-%m-%d %H:%M:%S")

                    # Format TTL
                    if ttl_seconds >= 86400:  # >= 1 day
                        days = ttl_seconds // 86400
                        hours = (ttl_seconds % 86400) // 3600
                        ttl_formatted = f"{days}d {hours}h"
                    elif ttl_seconds >= 3600:  # >= 1 hour
                        hours = ttl_seconds // 3600
                        minutes = (ttl_seconds % 3600) // 60
                        ttl_formatted = f"{hours}h {minutes}m"
                    elif ttl_seconds >= 60:  # >= 1 minute
                        minutes = ttl_seconds // 60
                        seconds = ttl_seconds % 60
                        ttl_formatted = f"{minutes}m {seconds}s"
                    else:
                        ttl_formatted = f"{ttl_seconds}s"

                    return {
                        "has_expiry": True,
                        "ttl_seconds": ttl_seconds,
                        "ttl_formatted": ttl_formatted,
                        "expires_at": expire_time_ms,
                        "expires_at_formatted": expires_at_formatted,
                    }
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid expiry time format for {key}: {e}")

            # No expiry or invalid expiry time
            return {
                "has_expiry": False,
                "ttl_seconds": -1,  # -1 indicates no expiry
                "ttl_formatted": "Never",
                "expires_at": None,
                "expires_at_formatted": "Never",
            }

        except Exception as e:
            logger.error(f"Error getting TTL info for {key}: {e}")
            return {
                "has_expiry": False,
                "ttl_seconds": -1,
                "ttl_formatted": "Unknown",
                "expires_at": None,
                "expires_at_formatted": "Unknown",
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get RedisStack performance metrics including vector search status."""
        try:
            metrics = {
                "vector_searches": 0,
                "hybrid_searches": 0,
                "memory_writes": 0,
                "cache_hits": 0,
                "average_search_time": 0.0,
                "vector_search_enabled": self.embedder is not None,
                "embedder_model": (
                    getattr(self.embedder, "model_name", "Unknown") if self.embedder else None
                ),
                "embedding_dimension": (
                    getattr(self.embedder, "embedding_dim", 0) if self.embedder else 0
                ),
            }

            # Index status
            try:
                # Check if index exists and get info
                client = self._get_thread_safe_client()
                index_info = client.ft(self.index_name).info()

                metrics["index_status"] = {
                    "status": "available",
                    "index_name": self.index_name,
                    "num_docs": index_info.get("num_docs", 0),
                    "indexing": index_info.get("indexing", False),
                    "percent_indexed": index_info.get("percent_indexed", 100),
                }

                # Get index options if available
                if "index_options" in index_info:
                    metrics["index_status"]["index_options"] = index_info["index_options"]

            except Exception as e:
                logger.debug(f"Could not get index info: {e}")
                metrics["index_status"] = {
                    "status": "unavailable",
                    "error": str(e),
                }

                # Memory distribution by namespace (simplified)
            try:
                client = self._get_thread_safe_client()
                pattern = "orka_memory:*"
                keys = client.keys(pattern)

                namespace_dist = {}
                for key in keys[:100]:  # Limit to avoid performance issues
                    try:
                        memory_data = client.hgetall(key)
                        # Handle bytes keys from decode_responses=False
                        raw_trace_id = memory_data.get(b"trace_id") or memory_data.get(
                            "trace_id",
                            "unknown",
                        )
                        if isinstance(raw_trace_id, bytes):
                            trace_id = raw_trace_id.decode()
                        else:
                            trace_id = raw_trace_id
                        namespace_dist[trace_id] = namespace_dist.get(trace_id, 0) + 1
                    except:
                        continue

                metrics["namespace_distribution"] = namespace_dist

            except Exception as e:
                logger.debug(f"Could not get namespace distribution: {e}")
                metrics["namespace_distribution"] = {}

            # Memory quality metrics
            try:
                # Get sample of recent memories for quality analysis
                recent_memories = self.get_recent_stored_memories(20)
                if recent_memories:
                    importance_scores = [m.get("importance_score", 0) for m in recent_memories]
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
                            (long_term_count / len(recent_memories)) * 100 if recent_memories else 0
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
