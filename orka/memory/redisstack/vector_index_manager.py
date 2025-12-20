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
Vector Index Manager for RedisStack
===================================

HNSW vector index creation, verification, and management for RedisStack.

Features
--------
- HNSW index creation with configurable parameters
- Index verification and health checks
- Automatic index recreation on schema mismatch
- Thread-safe index operations

Usage
-----
```python
from orka.memory.redisstack.vector_index_manager import VectorIndexManager
from orka.memory.redisstack.connection_manager import ConnectionManager

conn_mgr = ConnectionManager(redis_url="redis://localhost:6380/0")
index_mgr = VectorIndexManager(conn_mgr, index_name="orka_memory")
index_mgr.ensure_index(vector_dim=384)
```
"""

import logging
import queue
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orka.memory.redisstack.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class VectorIndexManager:
    """
    Manages HNSW vector indexes for RedisStack memory search.

    Handles index creation, verification, and maintenance for
    high-performance vector similarity search.

    Attributes:
        conn_mgr: Connection manager for Redis access
        index_name: Name of the RedisStack index
        enable_hnsw: Whether HNSW indexing is enabled
        vector_params: HNSW configuration parameters
    """

    def __init__(
        self,
        conn_mgr: "ConnectionManager",
        index_name: str = "orka_enhanced_memory",
        enable_hnsw: bool = True,
        vector_params: dict[str, Any] | None = None,
        embedder: Any = None,
    ):
        """
        Initialize the vector index manager.

        Args:
            conn_mgr: Connection manager for Redis access.
            index_name: Name of the RedisStack index.
            enable_hnsw: Whether to enable HNSW indexing.
            vector_params: HNSW configuration parameters.
            embedder: Optional embedder for dimension detection.
        """
        self.conn_mgr = conn_mgr
        self.index_name = index_name
        self.enable_hnsw = enable_hnsw
        self.vector_params = vector_params or {}
        self.embedder = embedder

        logger.debug(f"VectorIndexManager initialized with index_name={index_name}")

    def ensure_index(
        self,
        vector_dim: int | None = None,
        force_recreate: bool = False,
    ) -> bool:
        """
        Ensure the enhanced memory index exists with vector search capabilities.

        Args:
            vector_dim: Vector embedding dimension (default: 384 or from embedder).
            force_recreate: Force recreation of the index.

        Returns:
            True if index is ready, False otherwise.
        """
        try:
            # Try to get Redis client with timeout
            try:
                result_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

                def try_redis_connection():
                    try:
                        redis_client = self.conn_mgr.get_client()
                        result_queue.put(("success", redis_client))
                    except Exception as e:
                        result_queue.put(("error", e))

                connection_thread = threading.Thread(
                    target=try_redis_connection, daemon=True
                )
                connection_thread.start()

                try:
                    result_type, result_value = result_queue.get(timeout=5)
                    if result_type == "error":
                        raise result_value
                    redis_client = result_value
                except queue.Empty:
                    logger.warning(
                        "Redis connection timeout during init, skipping index setup"
                    )
                    return False

            except Exception as e:
                logger.warning(
                    f"Redis not available during init, skipping index setup: {e}"
                )
                return False

            from orka.utils.bootstrap_memory_index import (
                ensure_enhanced_memory_index,
                verify_memory_index,
            )

            # Get vector dimension from embedder if available
            if vector_dim is None:
                vector_dim = 384  # Default dimension
                if self.embedder and hasattr(self.embedder, "embedding_dim"):
                    vector_dim = self.embedder.embedding_dim

            # Check if we should force recreate
            local_force_recreate = force_recreate or self.vector_params.get(
                "force_recreate", False
            )
            vector_field_name = self.vector_params.get(
                "vector_field_name", "content_vector"
            )

            # Extract vector parameters for HNSW configuration
            hnsw_params = {
                "TYPE": self.vector_params.get("type", "FLOAT32"),
                "DIM": vector_dim,
                "DISTANCE_METRIC": self.vector_params.get("distance_metric", "COSINE"),
                "EF_CONSTRUCTION": self.vector_params.get("ef_construction", 200),
                "M": self.vector_params.get("m", 16),
            }

            # Verify index and check for issues
            if self.enable_hnsw:
                index_info = verify_memory_index(
                    redis_client=redis_client,
                    index_name=self.index_name,
                )

                if index_info["exists"] and not index_info["vector_field_exists"]:
                    logger.warning(
                        f"Memory index {self.index_name} missing vector field. "
                        f"Available fields: {index_info['fields']}. "
                        f"Will attempt to fix based on configuration."
                    )
                    local_force_recreate = True

                if index_info["exists"] and not index_info["content_field_exists"]:
                    logger.warning(
                        f"Memory index {self.index_name} missing content field. "
                        f"Available fields: {index_info['fields']}. "
                        f"Will attempt to fix based on configuration."
                    )
                    local_force_recreate = True

            # Try multiple times with increasing force_recreate if needed
            max_attempts = 2
            success = False
            for attempt in range(max_attempts):
                success = ensure_enhanced_memory_index(
                    redis_client=redis_client,
                    index_name=self.index_name,
                    vector_dim=vector_dim,
                    vector_field_name=vector_field_name,
                    vector_params=hnsw_params,
                    force_recreate=(local_force_recreate or attempt > 0),
                )

                if success:
                    # Verify the index was created correctly
                    index_info = verify_memory_index(
                        redis_client=redis_client,
                        index_name=self.index_name,
                    )

                    if (
                        index_info["exists"]
                        and index_info["vector_field_exists"]
                        and index_info["content_field_exists"]
                    ):
                        logger.info(f"Index verification successful after attempt {attempt + 1}")
                        break
                    elif attempt < max_attempts - 1:
                        logger.warning(
                            f"Index verification failed after attempt {attempt + 1}, "
                            "retrying with force_recreate=True"
                        )
                        local_force_recreate = True
                    else:
                        logger.error("Index verification failed after all attempts")
                else:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Index creation failed on attempt {attempt + 1}, "
                            "retrying with force_recreate=True"
                        )
                        local_force_recreate = True
                    else:
                        logger.error("Index creation failed after all attempts")

            if success:
                logger.info(
                    f"Enhanced HNSW memory index ready with dimension {vector_dim}"
                )
                return True
            else:
                logger.warning(
                    f"Enhanced memory index creation failed for {self.index_name}, "
                    "some features may be limited."
                )
                return False

        except Exception as e:
            logger.error(f"Failed to ensure enhanced memory index: {e}")
            return False

    def verify_index(self) -> dict[str, Any]:
        """
        Verify the current state of the memory index.

        Returns:
            Dictionary with index status information.
        """
        try:
            from orka.utils.bootstrap_memory_index import verify_memory_index

            redis_client = self.conn_mgr.get_client()
            return verify_memory_index(
                redis_client=redis_client,
                index_name=self.index_name,
            )
        except Exception as e:
            logger.error(f"Failed to verify index: {e}")
            return {
                "exists": False,
                "error": str(e),
                "vector_field_exists": False,
                "content_field_exists": False,
                "fields": [],
            }

