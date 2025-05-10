# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
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

This module also provides retry functionality with exponential backoff for
handling potential transient Redis connection issues during initialization.

Usage example:
```python
import redis.asyncio as redis
from orka.utils.bootstrap_memory_index import ensure_memory_index

async def initialize_memory():
    client = redis.from_url("redis://localhost:6379")
    await ensure_memory_index(client)
    # Now the memory index is ready for use
```
"""

import asyncio

import redis.asyncio as redis


async def ensure_memory_index(client: redis.Redis):
    """
    Ensure the memory index exists in Redis Search.

    This function checks if the required RediSearch index for memory storage
    exists, and creates it if needed. The index enables both text-based and
    vector-based searches over memory entries.

    The index includes the following fields:
    - content: Full text content for text search
    - session: Tag field to filter by session ID
    - agent: Tag field to filter by agent ID
    - ts: Numeric timestamp for time-based queries
    - vector: 384-dimension embedding vector for semantic similarity search

    Args:
        client: Redis async client instance connected to the Redis server

    Raises:
        redis.RedisError: If there's an issue with Redis communication
            other than the index not existing
    """
    try:
        # Check if the index already exists
        await client.ft("memory_idx").info()
    except redis.ResponseError:
        # Index doesn't exist, create it with the required fields
        await client.ft("memory_idx").create_index(
            (
                # Text field for content-based search
                redis.commands.search.field.TextField("content"),
                # Tag fields for exact matching and filtering
                redis.commands.search.field.TagField("session"),
                redis.commands.search.field.TagField("agent"),
                # Numeric field for time-based queries
                redis.commands.search.field.NumericField("ts"),
                # Vector field for semantic similarity search
                redis.commands.search.field.VectorField(
                    "vector",
                    "FLAT",  # FLAT index type for smaller datasets
                    {"TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE"},
                ),
            ),
            # Define index properties
            definition=redis.commands.search.IndexDefinition(
                prefix=["mem:"],  # Only index keys with this prefix
                index_type="HASH",  # Index Redis hash structures
            ),
        )


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
