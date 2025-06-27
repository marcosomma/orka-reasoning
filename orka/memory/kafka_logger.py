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
        bootstrap_servers: Optional[str] = None,
        topic_prefix: str = "orka-memory",
        stream_key: str = "orka:memory",
        synchronous_send: bool = False,
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[Dict[str, Any]] = None,
        redis_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the hybrid Kafka + Redis memory logger.

        Args:
            bootstrap_servers: Kafka bootstrap servers. Defaults to environment variable KAFKA_BOOTSTRAP_SERVERS.
            topic_prefix: Prefix for Kafka topics. Defaults to "orka-memory".
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            synchronous_send: Whether to wait for message confirmation. Defaults to False for performance.
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
            decay_config: Configuration for memory decay functionality.
            redis_url: Redis connection URL. Defaults to environment variable REDIS_URL.
        """
        super().__init__(stream_key, debug_keep_previous_outputs, decay_config)

        # Kafka configuration
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        )
        self.topic_prefix = topic_prefix
        self.main_topic = f"{topic_prefix}-events"
        self.synchronous_send = synchronous_send

        # Schema Registry configuration
        self.use_schema_registry = os.getenv("KAFKA_USE_SCHEMA_REGISTRY", "false").lower() == "true"
        self.schema_registry_url = os.getenv("KAFKA_SCHEMA_REGISTRY_URL", "http://localhost:8081")

        # Redis configuration for memory operations
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(self.redis_url)

        # In-memory storage for recent events (for tail operations)
        self.memory: List[Dict[str, Any]] = []

        # Initialize schema manager and producer
        self.schema_manager = None
        self.serializer = None
        if self.use_schema_registry:
            self._init_schema_registry()

        self.producer = self._init_kafka_producer()

    @property
    def redis(self) -> redis.Redis:
        """
        Return the Redis client for compatibility.
        This allows the KafkaMemoryLogger to work with Redis-based fork managers.
        """
        return self.redis_client

    def _init_schema_registry(self):
        """Initialize schema registry and register schemas."""
        try:
            logger.info("🔧 Initializing schema registry integration...")

            # Import schema manager
            from .schema_manager import create_schema_manager

            # Create schema manager
            self.schema_manager = create_schema_manager(
                registry_url=self.schema_registry_url,
            )

            # Register schemas
            subject = f"{self.main_topic}-value"
            schema_id = self.schema_manager.register_schema(subject, "memory_entry")
            logger.info(f"✅ Schema registered: {subject} (ID: {schema_id})")

            # Get serializer
            self.serializer = self.schema_manager.get_serializer(self.main_topic)
            logger.info("✅ Schema registry integration ready")

        except Exception as e:
            logger.warning(f"Schema registry initialization failed: {e}")
            logger.warning("Falling back to JSON serialization")
            self.use_schema_registry = False

    def _init_kafka_producer(self):
        """Initialize Kafka producer with proper error handling."""
        try:
            # Check if schema registry is enabled
            use_schema_registry = os.getenv("KAFKA_USE_SCHEMA_REGISTRY", "false").lower() == "true"

            if use_schema_registry:
                # Use confluent-kafka with schema registry
                try:
                    from confluent_kafka import Producer

                    config = {
                        "bootstrap.servers": self.bootstrap_servers,
                        "client.id": "orka-memory-logger",
                        "acks": "all" if self.synchronous_send else "1",
                        "retries": 3,
                        "retry.backoff.ms": 100,
                    }

                    producer = Producer(config)
                    logger.info("Initialized Confluent Kafka producer with schema registry support")
                    return producer

                except ImportError:
                    logger.warning("confluent-kafka not available, falling back to kafka-python")

            # Use kafka-python as fallback
            try:
                from kafka import KafkaProducer

                producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(","),
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks="all" if self.synchronous_send else 1,
                    retries=3,
                    retry_backoff_ms=100,
                )

                logger.info("Initialized kafka-python producer")
                return producer

            except ImportError:
                raise ImportError("kafka-python package is required for Kafka backend")

        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

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
                    expire_time = current_time + timedelta(
                        hours=self.decay_config["default_short_term_hours"],
                    )
                else:  # long_term
                    expire_time = current_time + timedelta(
                        hours=self.decay_config["default_long_term_hours"],
                    )

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

        # Store in memory buffer for tail operations
        self.memory.append(event)

        # Send to Kafka for event streaming
        self._send_to_kafka(event, run_id, agent_id)

        # Store in Redis for memory operations (similar to RedisMemoryLogger)
        self._store_in_redis(
            event,
            step,
            run_id,
            fork_group,
            parent,
            previous_outputs,
            decay_metadata,
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

    def _store_in_redis(
        self,
        event: dict,
        step: Optional[int],
        run_id: Optional[str],
        fork_group: Optional[str],
        parent: Optional[str],
        previous_outputs: Optional[Dict[str, Any]],
        decay_metadata: dict,
    ):
        """Store event in Redis streams (similar to RedisMemoryLogger)."""
        try:
            # Determine which stream(s) to write to based on memory category
            streams_to_write = []
            memory_category = decay_metadata.get("orka_memory_category", "log")

            if (
                memory_category == "stored"
                and event["event_type"] == "write"
                and isinstance(event["payload"], dict)
            ):
                # For stored memories, only write to namespace-specific stream
                namespace = event["payload"].get("namespace")
                session = event["payload"].get("session", "default")
                if namespace:
                    namespace_stream = f"orka:memory:{namespace}:{session}"
                    streams_to_write.append(namespace_stream)
                    logger.info(
                        f"Writing stored memory to namespace-specific stream: {namespace_stream}",
                    )
                else:
                    # Fallback to general stream if no namespace
                    streams_to_write.append(self.stream_key)
            else:
                # For orchestration logs and other events, write to general stream
                streams_to_write.append(self.stream_key)

            # Sanitize previous outputs if present
            safe_previous_outputs = None
            if previous_outputs:
                try:
                    safe_previous_outputs = json.dumps(
                        self._sanitize_for_json(previous_outputs),
                    )
                except Exception as e:
                    logger.error(f"Failed to serialize previous_outputs: {e!s}")
                    safe_previous_outputs = json.dumps(
                        {"error": f"Serialization error: {e!s}"},
                    )

            # Prepare the Redis entry
            redis_entry = {
                "agent_id": event["agent_id"],
                "event_type": event["event_type"],
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": str(step or -1),
            }

            # Add decay metadata if decay is enabled
            redis_entry.update(decay_metadata)

            # Safely serialize the payload
            try:
                redis_entry["payload"] = json.dumps(event["payload"])
            except Exception as e:
                logger.error(f"Failed to serialize payload: {e!s}")
                redis_entry["payload"] = json.dumps(
                    {"error": "Original payload contained non-serializable objects"},
                )

            # Only add previous_outputs if it exists and is not None
            if safe_previous_outputs:
                redis_entry["previous_outputs"] = safe_previous_outputs

            # Write to all determined streams
            for stream_key in streams_to_write:
                try:
                    self.redis_client.xadd(stream_key, redis_entry)
                    logger.debug(f"Successfully wrote to Redis stream: {stream_key}")
                except Exception as stream_e:
                    logger.error(f"Failed to write to Redis stream {stream_key}: {stream_e!s}")

        except Exception as e:
            logger.error(f"Failed to store event in Redis: {e}")
            # Continue execution since event is still in Kafka

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
        Get memory usage statistics from Redis backend.
        """
        try:
            # Import Redis memory logger for stats logic
            from .redis_logger import RedisMemoryLogger

            # Create a temporary Redis logger to reuse stats logic
            temp_redis_logger = RedisMemoryLogger(
                redis_url=self.redis_url,
                stream_key=self.stream_key,
                decay_config=self.decay_config,
            )

            # Use Redis stats logic
            stats = temp_redis_logger.get_memory_stats()
            stats["backend"] = "kafka+redis"
            stats["kafka_topic"] = self.main_topic
            stats["memory_buffer_size"] = len(self.memory)

            return stats

        except Exception as e:
            logger.error(f"Error getting hybrid memory statistics: {e}")
            return {
                "error": str(e),
                "backend": "kafka+redis",
                "timestamp": datetime.now(UTC).isoformat(),
            }
