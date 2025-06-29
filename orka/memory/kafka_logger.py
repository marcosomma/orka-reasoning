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
Kafka Memory Logger Implementation
=================================

This file contains the hybrid KafkaMemoryLogger implementation that uses
Kafka topics for event streaming and Redis for memory operations.
This provides the best of both worlds: Kafka's event streaming capabilities
with Redis's fast memory operations.
"""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis

from .base_logger import BaseMemoryLogger

logger = logging.getLogger(__name__)


class KafkaMemoryLogger(BaseMemoryLogger):
    """
    A hybrid memory logger that uses Kafka for event streaming and Redis for memory operations.

    This implementation combines:
    - Kafka topics for persistent event streaming and audit trails
    - Redis for fast memory operations (hset, hget, sadd, etc.) and fork/join coordination

    This approach provides both the scalability of Kafka and the performance of Redis.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        redis_url: Optional[str] = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[Dict[str, Any]] = None,
        enable_hnsw: bool = True,
        vector_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the hybrid Kafka + RedisStack memory logger.

        Args:
            bootstrap_servers: Kafka bootstrap servers. Defaults to "localhost:9092".
            redis_url: RedisStack connection URL. Defaults to environment variable REDIS_URL.
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
            decay_config: Configuration for memory decay functionality.
            enable_hnsw: Enable HNSW vector indexing in RedisStack backend.
            vector_params: HNSW configuration parameters.
        """
        super().__init__(stream_key, debug_keep_previous_outputs, decay_config)

        # Kafka setup
        self.bootstrap_servers = bootstrap_servers
        self.main_topic = "orka-memory-events"
        self.producer = None
        self.consumer = None

        # ✅ CRITICAL: Use RedisStack for memory operations instead of basic Redis
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6380/0")

        # Initialize Redis client variables
        self.redis_client = None
        self._redis_memory_logger = None

        # Create RedisStack logger for enhanced memory operations
        try:
            from .redisstack_logger import RedisStackMemoryLogger

            self._redis_memory_logger = RedisStackMemoryLogger(
                redis_url=self.redis_url,
                stream_key=stream_key,
                debug_keep_previous_outputs=debug_keep_previous_outputs,
                decay_config=decay_config,
                enable_hnsw=enable_hnsw,
                vector_params=vector_params,
            )

            # Ensure enhanced index is ready
            self._redis_memory_logger.ensure_index()
            logger.info("✅ Kafka backend using RedisStack for memory operations")

        except ImportError:
            # Fallback to basic Redis
            self.redis_client = redis.from_url(self.redis_url)
            self._redis_memory_logger = None
            logger.warning("⚠️ RedisStack not available, using basic Redis for memory operations")
        except Exception as e:
            # If RedisStack creation fails for any other reason, fall back to basic Redis
            logger.warning(
                f"⚠️ RedisStack initialization failed ({e}), using basic Redis for memory operations",
            )
            self._redis_memory_logger = None

        # Initialize basic Redis client as fallback
        self.redis_client = redis.from_url(self.redis_url)

    @property
    def redis(self) -> redis.Redis:
        """Return Redis client - prefer RedisStack client if available."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.redis
        return self.redis_client

    def _store_in_redis(self, event: dict, **kwargs):
        """Store event using RedisStack logger if available."""
        if self._redis_memory_logger:
            # ✅ Use RedisStack logger for enhanced storage
            self._redis_memory_logger.log(
                agent_id=event["agent_id"],
                event_type=event["event_type"],
                payload=event["payload"],
                step=kwargs.get("step"),
                run_id=kwargs.get("run_id"),
                fork_group=kwargs.get("fork_group"),
                parent=kwargs.get("parent"),
                previous_outputs=kwargs.get("previous_outputs"),
                agent_decay_config=kwargs.get("agent_decay_config"),
            )
        else:
            # Fallback to basic Redis streams
            try:
                # Prepare the Redis entry
                redis_entry = {
                    "agent_id": event["agent_id"],
                    "event_type": event["event_type"],
                    "timestamp": event.get("timestamp"),
                    "run_id": kwargs.get("run_id", "default"),
                    "step": str(kwargs.get("step", -1)),
                    "payload": json.dumps(event["payload"]),
                }

                # Add decay metadata if available
                if hasattr(self, "decay_config") and self.decay_config:
                    decay_metadata = self._generate_decay_metadata(event)
                    redis_entry.update(decay_metadata)

                # Write to Redis stream
                self.redis_client.xadd(self.stream_key, redis_entry)
                logger.debug(f"Stored event in basic Redis stream: {self.stream_key}")

            except Exception as e:
                logger.error(f"Failed to store event in basic Redis: {e}")

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
    ) -> None:
        """
        Log an event to both Kafka (for streaming) and Redis (for memory operations).

        This hybrid approach ensures events are durably stored in Kafka while also
        being available in Redis for fast memory operations and coordination.
        """
        # Sanitize payload
        safe_payload = self._sanitize_for_json(payload)

        # Handle decay configuration
        decay_metadata = {}
        if self.decay_config.get("enabled", False):
            # Temporarily merge agent-specific decay config
            old_config = self.decay_config
            try:
                if agent_decay_config:
                    # Create temporary merged config
                    merged_config = {**self.decay_config}
                    merged_config.update(agent_decay_config)
                    self.decay_config = merged_config

                # Calculate importance score and memory type
                importance_score = self._calculate_importance_score(
                    agent_id,
                    event_type,
                    safe_payload,
                )
                memory_type = self._classify_memory_type(
                    event_type,
                    importance_score,
                    self._classify_memory_category(event_type, agent_id, safe_payload),
                )
                memory_category = self._classify_memory_category(event_type, agent_id, safe_payload)

                # Calculate expiration time
                current_time = datetime.now(UTC)
                if memory_type == "short_term":
                    # Check agent-level config first, then fall back to global config
                    expire_hours = self.decay_config.get(
                        "short_term_hours",
                    ) or self.decay_config.get("default_short_term_hours", 1.0)
                    expire_time = current_time + timedelta(hours=expire_hours)
                else:  # long_term
                    # Check agent-level config first, then fall back to global config
                    expire_hours = self.decay_config.get(
                        "long_term_hours",
                    ) or self.decay_config.get("default_long_term_hours", 24.0)
                    expire_time = current_time + timedelta(hours=expire_hours)

                decay_metadata = {
                    "orka_importance_score": str(importance_score),
                    "orka_memory_type": memory_type,
                    "orka_memory_category": memory_category,
                    "orka_expire_time": expire_time.isoformat(),
                    "orka_created_time": current_time.isoformat(),
                }
            finally:
                # Restore original config
                self.decay_config = old_config

        # Create event record with decay metadata
        event = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": safe_payload,
            "step": step,
            "run_id": run_id,
            "fork_group": fork_group,
            "parent": parent,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add decay metadata to the event
        event.update(decay_metadata)

        # CRITICAL: Add event to local memory buffer for file operations
        # This ensures events are included in the JSON trace files
        self.memory.append(event)

        # Store in Redis for memory operations (similar to RedisMemoryLogger)
        self._store_in_redis(
            event,
            step=step,
            run_id=run_id,
            fork_group=fork_group,
            parent=parent,
            previous_outputs=previous_outputs,
            agent_decay_config=agent_decay_config,
        )

    def _send_to_kafka(self, event: dict, run_id: Optional[str], agent_id: str):
        """Send event to Kafka for streaming."""
        try:
            message_key = f"{run_id}:{agent_id}" if run_id else agent_id

            # Use schema serialization if available
            if self.use_schema_registry and self.serializer:
                try:
                    # Use confluent-kafka with schema serialization
                    from confluent_kafka.serialization import MessageField, SerializationContext

                    serialized_value = self.serializer(
                        event,
                        SerializationContext(self.main_topic, MessageField.VALUE),
                    )

                    self.producer.produce(
                        topic=self.main_topic,
                        key=message_key,
                        value=serialized_value,
                    )

                    if self.synchronous_send:
                        self.producer.flush()

                    logger.debug(
                        f"Sent event to Kafka with schema: {agent_id}:{event['event_type']}",
                    )

                except Exception as schema_error:
                    logger.warning(
                        f"Schema serialization failed: {schema_error}, using JSON fallback",
                    )
                    # Fall back to JSON serialization
                    self._send_json_message(message_key, event)
            else:
                # Use JSON serialization
                self._send_json_message(message_key, event)

        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            # Event is still stored in Redis, so we can continue

    def _send_json_message(self, message_key: str, event: dict):
        """Send message using JSON serialization (fallback)."""
        # Handle different producer types
        if hasattr(self.producer, "produce"):  # confluent-kafka
            self.producer.produce(
                topic=self.main_topic,
                key=message_key,
                value=json.dumps(event).encode("utf-8"),
            )
            if self.synchronous_send:
                self.producer.flush()
        else:  # kafka-python
            future = self.producer.send(
                topic=self.main_topic,
                key=message_key,
                value=event,
            )
            if self.synchronous_send:
                future.get(timeout=10)

        logger.debug(f"Sent event to Kafka with JSON: {event['agent_id']}:{event['event_type']}")

    def _sanitize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize payload to ensure JSON serialization."""
        if not isinstance(payload, dict):
            return {"value": str(payload)}

        sanitized = {}
        for key, value in payload.items():
            try:
                json.dumps(value)  # Test if serializable
                sanitized[key] = value
            except (TypeError, ValueError):
                sanitized[key] = str(value)

        return sanitized

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent events from memory buffer."""
        return self.memory[-count:] if self.memory else []

    # Redis operations - delegate to actual Redis client
    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a hash field using Redis."""
        return self.redis_client.hset(name, key, value)

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field using Redis."""
        result = self.redis_client.hget(name, key)
        return result.decode() if result else None

    def hkeys(self, name: str) -> List[str]:
        """Get hash keys using Redis."""
        return [key.decode() for key in self.redis_client.hkeys(name)]

    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields using Redis."""
        return self.redis_client.hdel(name, *keys)

    def smembers(self, name: str) -> List[str]:
        """Get set members using Redis."""
        return [member.decode() for member in self.redis_client.smembers(name)]

    def sadd(self, name: str, *values: str) -> int:
        """Add to set using Redis."""
        return self.redis_client.sadd(name, *values)

    def srem(self, name: str, *values: str) -> int:
        """Remove from set using Redis."""
        return self.redis_client.srem(name, *values)

    def get(self, key: str) -> Optional[str]:
        """Get a value using Redis."""
        result = self.redis_client.get(key)
        return result.decode() if result else None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a value using Redis."""
        return self.redis_client.set(key, value)

    def delete(self, *keys: str) -> int:
        """Delete keys using Redis."""
        return self.redis_client.delete(*keys)

    # 🎯 NEW: Enhanced memory operations - delegate to RedisStack logger
    def search_memories(
        self,
        query: str,
        num_results: int = 10,
        trace_id: Optional[str] = None,
        node_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        log_type: str = "memory",
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search memories using RedisStack logger if available, otherwise return empty list."""
        logger.debug(
            f"🔍 KafkaMemoryLogger.search_memories: _redis_memory_logger={self._redis_memory_logger is not None}, namespace='{namespace}'",
        )

        if self._redis_memory_logger and hasattr(self._redis_memory_logger, "search_memories"):
            logger.debug(f"🔍 Delegating to RedisStackMemoryLogger with namespace='{namespace}'")
            results = self._redis_memory_logger.search_memories(
                query=query,
                num_results=num_results,
                trace_id=trace_id,
                node_id=node_id,
                memory_type=memory_type,
                min_importance=min_importance,
                log_type=log_type,
                namespace=namespace,
            )
            logger.debug(f"🔍 RedisStack search returned {len(results)} results")
            return results
        else:
            logger.warning("RedisStack not available for memory search, returning empty results")
            return []

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
        """Log memory using RedisStack logger if available."""
        if self._redis_memory_logger and hasattr(self._redis_memory_logger, "log_memory"):
            return self._redis_memory_logger.log_memory(
                content=content,
                node_id=node_id,
                trace_id=trace_id,
                metadata=metadata,
                importance_score=importance_score,
                memory_type=memory_type,
                expiry_hours=expiry_hours,
            )
        else:
            logger.warning("RedisStack not available for memory logging")
            return f"fallback_memory_{datetime.now(UTC).timestamp()}"

    def ensure_index(self) -> bool:
        """Ensure memory index exists using RedisStack logger if available."""
        if self._redis_memory_logger and hasattr(self._redis_memory_logger, "ensure_index"):
            return self._redis_memory_logger.ensure_index()
        return False

    def close(self) -> None:
        """Close both Kafka producer and Redis connection."""
        # Close Kafka producer
        if self.producer:
            try:
                if hasattr(self.producer, "close"):  # kafka-python
                    self.producer.close()
                elif hasattr(self.producer, "flush"):  # confluent-kafka
                    self.producer.flush()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")

        # Close Redis connection
        try:
            if self._redis_memory_logger:
                # Close RedisStack logger if available
                if hasattr(self._redis_memory_logger, "close"):
                    self._redis_memory_logger.close()
                elif hasattr(self._redis_memory_logger, "client") and hasattr(
                    self._redis_memory_logger.client,
                    "close",
                ):
                    self._redis_memory_logger.client.close()
                logger.info("RedisStack memory logger closed")
            elif self.redis_client:
                # Close basic Redis client
                self.redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

    def __del__(self):
        """Cleanup on object deletion."""
        self.close()

    def cleanup_expired_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up expired memory entries using Redis-based approach.

        This delegates to Redis for cleanup while also cleaning the in-memory buffer.
        """
        try:
            # Import Redis memory logger for cleanup logic
            from .redis_logger import RedisMemoryLogger

            # Create a temporary Redis logger to reuse cleanup logic
            temp_redis_logger = RedisMemoryLogger(
                redis_url=self.redis_url,
                stream_key=self.stream_key,
                decay_config=self.decay_config,
            )

            # Use Redis cleanup logic
            stats = temp_redis_logger.cleanup_expired_memories(dry_run=dry_run)
            stats["backend"] = "kafka+redis"

            # Also clean up in-memory buffer if decay is enabled and not dry run
            if not dry_run and self.decay_config.get("enabled", False):
                current_time = datetime.now(UTC)
                expired_indices = []

                for i, entry in enumerate(self.memory):
                    expire_time_str = entry.get("orka_expire_time")
                    if expire_time_str:
                        try:
                            expire_time = datetime.fromisoformat(expire_time_str)
                            if current_time > expire_time:
                                expired_indices.append(i)
                        except (ValueError, TypeError):
                            continue

                # Remove expired entries from memory buffer
                for i in reversed(expired_indices):
                    del self.memory[i]

                logger.info(f"Cleaned up {len(expired_indices)} expired entries from memory buffer")

            return stats

        except Exception as e:
            logger.error(f"Error during hybrid memory cleanup: {e}")
            return {
                "error": str(e),
                "backend": "kafka+redis",
                "timestamp": datetime.now(UTC).isoformat(),
                "deleted_count": 0,
            }

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics from both Redis backend and local memory buffer.
        """
        try:
            current_time = datetime.now(UTC)
            stats = {
                "timestamp": current_time.isoformat(),
                "backend": "kafka+redis",
                "kafka_topic": self.main_topic,
                "memory_buffer_size": len(self.memory),
                "decay_enabled": self.decay_config.get("enabled", False),
                "total_streams": 0,
                "total_entries": 0,
                "entries_by_type": {},
                "entries_by_memory_type": {"short_term": 0, "long_term": 0, "unknown": 0},
                "entries_by_category": {"stored": 0, "log": 0, "unknown": 0},
                "expired_entries": 0,
                "streams_detail": [],
            }

            # Use the actual Redis client from the Kafka backend
            redis_client = self.redis

            # Get all stream keys that match OrKa patterns
            stream_patterns = [
                "orka:memory:*",  # All OrKa memory streams (this is what Kafka backend creates)
                self.stream_key,  # Base stream key
                f"{self.stream_key}:*",  # Namespace-specific streams
            ]

            processed_streams = set()
            for pattern in stream_patterns:
                try:
                    stream_keys = redis_client.keys(pattern)

                    for stream_key in stream_keys:
                        stream_key_str = (
                            stream_key.decode() if isinstance(stream_key, bytes) else stream_key
                        )

                        if stream_key_str in processed_streams:
                            continue
                        processed_streams.add(stream_key_str)

                        try:
                            # Check if it's actually a stream
                            key_type = redis_client.type(stream_key)
                            if key_type != b"stream" and key_type != "stream":
                                continue

                            # Get stream info and entries
                            stream_info = redis_client.xinfo_stream(stream_key)
                            entries = redis_client.xrange(stream_key)

                            stream_stats = {
                                "stream": stream_key_str,
                                "length": stream_info.get("length", 0),
                                "entries_by_type": {},
                                "entries_by_memory_type": {
                                    "short_term": 0,
                                    "long_term": 0,
                                    "unknown": 0,
                                },
                                "entries_by_category": {
                                    "stored": 0,
                                    "log": 0,
                                    "unknown": 0,
                                },
                                "expired_entries": 0,
                                "active_entries": 0,
                            }

                            stats["total_streams"] += 1

                            for entry_id, entry_data in entries:
                                # Check if expired first
                                is_expired = False
                                expire_time_field = entry_data.get(
                                    b"orka_expire_time",
                                ) or entry_data.get("orka_expire_time")
                                if expire_time_field:
                                    try:
                                        expire_time_str = (
                                            expire_time_field.decode()
                                            if isinstance(expire_time_field, bytes)
                                            else expire_time_field
                                        )
                                        expire_time = datetime.fromisoformat(expire_time_str)
                                        if current_time > expire_time:
                                            is_expired = True
                                            stream_stats["expired_entries"] += 1
                                            stats["expired_entries"] += 1
                                    except (ValueError, TypeError):
                                        pass  # Skip invalid dates

                                # Only count non-expired entries in the main statistics
                                if not is_expired:
                                    stream_stats["active_entries"] += 1
                                    stats["total_entries"] += 1

                                    # Count by event type
                                    event_type_field = entry_data.get(
                                        b"event_type",
                                    ) or entry_data.get("event_type")
                                    event_type = "unknown"
                                    if event_type_field:
                                        event_type = (
                                            event_type_field.decode()
                                            if isinstance(event_type_field, bytes)
                                            else event_type_field
                                        )

                                    stream_stats["entries_by_type"][event_type] = (
                                        stream_stats["entries_by_type"].get(event_type, 0) + 1
                                    )
                                    stats["entries_by_type"][event_type] = (
                                        stats["entries_by_type"].get(event_type, 0) + 1
                                    )

                                    # Count by memory category
                                    memory_category_field = entry_data.get(
                                        b"orka_memory_category",
                                    ) or entry_data.get("orka_memory_category")
                                    memory_category = "unknown"
                                    if memory_category_field:
                                        memory_category = (
                                            memory_category_field.decode()
                                            if isinstance(memory_category_field, bytes)
                                            else memory_category_field
                                        )

                                    if memory_category in stream_stats["entries_by_category"]:
                                        stream_stats["entries_by_category"][memory_category] += 1
                                        stats["entries_by_category"][memory_category] += 1
                                    else:
                                        stream_stats["entries_by_category"]["unknown"] += 1
                                        stats["entries_by_category"]["unknown"] += 1

                                    # Count by memory type ONLY for non-log entries
                                    if memory_category != "log":
                                        memory_type_field = entry_data.get(
                                            b"orka_memory_type",
                                        ) or entry_data.get("orka_memory_type")
                                        memory_type = "unknown"
                                        if memory_type_field:
                                            memory_type = (
                                                memory_type_field.decode()
                                                if isinstance(memory_type_field, bytes)
                                                else memory_type_field
                                            )

                                        if memory_type in stream_stats["entries_by_memory_type"]:
                                            stream_stats["entries_by_memory_type"][memory_type] += 1
                                            stats["entries_by_memory_type"][memory_type] += 1
                                        else:
                                            stream_stats["entries_by_memory_type"]["unknown"] += 1
                                            stats["entries_by_memory_type"]["unknown"] += 1

                            stats["streams_detail"].append(stream_stats)

                        except Exception as e:
                            logger.error(f"Error getting stats for stream {stream_key_str}: {e}")

                except Exception as e:
                    logger.error(f"Error getting keys for pattern {pattern}: {e}")

            # Add decay configuration info
            if self.decay_config.get("enabled", False):
                stats["decay_config"] = {
                    "short_term_hours": self.decay_config["default_short_term_hours"],
                    "long_term_hours": self.decay_config["default_long_term_hours"],
                    "check_interval_minutes": self.decay_config["check_interval_minutes"],
                    "last_decay_check": self._last_decay_check.isoformat()
                    if hasattr(self, "_last_decay_check") and self._last_decay_check
                    else None,
                }

            # Enhance stats with local memory buffer analysis
            # This provides more accurate decay metadata since local buffer has proper field names
            local_stats = {
                "entries_by_memory_type": {"short_term": 0, "long_term": 0, "unknown": 0},
                "entries_by_category": {"stored": 0, "log": 0, "unknown": 0},
            }

            for entry in self.memory:
                # Memory type distribution
                memory_type = entry.get("orka_memory_type", "unknown")
                if memory_type in local_stats["entries_by_memory_type"]:
                    local_stats["entries_by_memory_type"][memory_type] += 1
                else:
                    local_stats["entries_by_memory_type"]["unknown"] += 1

                # Memory category distribution
                memory_category = entry.get("orka_memory_category", "unknown")
                if memory_category in local_stats["entries_by_category"]:
                    local_stats["entries_by_category"][memory_category] += 1
                else:
                    local_stats["entries_by_category"]["unknown"] += 1

            # If local buffer has meaningful data, use it to enhance Redis stats
            if len(self.memory) > 0:
                # Combine Redis stats with local buffer insights
                if local_stats["entries_by_memory_type"]["unknown"] < len(self.memory):
                    # Local buffer has better memory type data
                    stats["entries_by_memory_type"] = local_stats["entries_by_memory_type"]

                if local_stats["entries_by_category"]["unknown"] < len(self.memory):
                    # Local buffer has better category data
                    stats["entries_by_category"] = local_stats["entries_by_category"]

                # Add local buffer specific metrics
                stats["local_buffer_insights"] = {
                    "total_entries": len(self.memory),
                    "entries_with_decay_metadata": sum(
                        1
                        for entry in self.memory
                        if entry.get("orka_memory_type") and entry.get("orka_memory_category")
                    ),
                    "memory_types": local_stats["entries_by_memory_type"],
                    "categories": local_stats["entries_by_category"],
                }

            return stats

        except Exception as e:
            logger.error(f"Error getting hybrid memory statistics: {e}")
            return {
                "error": str(e),
                "backend": "kafka+redis",
                "timestamp": datetime.now(UTC).isoformat(),
            }
