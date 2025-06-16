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

This file contains the complete KafkaMemoryLogger implementation that was
working before the refactoring. It uses Kafka topics for event streaming
and in-memory storage for Redis-like operations.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .base_logger import BaseMemoryLogger

logger = logging.getLogger(__name__)


class KafkaMemoryLogger(BaseMemoryLogger):
    """
    A memory logger that uses Kafka to store and retrieve orchestration events.
    Uses Kafka topics for event streaming and in-memory storage for hash/set operations.
    """

    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic_prefix: str = "orka-memory",
        stream_key: str = "orka:memory",
        synchronous_send: bool = False,
        debug_keep_previous_outputs: bool = False,
    ) -> None:
        """
        Initialize the Kafka memory logger.

        Args:
            bootstrap_servers: Kafka bootstrap servers. Defaults to environment variable KAFKA_BOOTSTRAP_SERVERS.
            topic_prefix: Prefix for Kafka topics. Defaults to "orka-memory".
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            synchronous_send: Whether to wait for message confirmation. Defaults to False for performance.
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
        """
        super().__init__(stream_key, debug_keep_previous_outputs)

        # Configuration
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

        # In-memory storage for Redis-like operations
        self.memory: List[Dict[str, Any]] = []
        self._hash_storage: Dict[str, Dict[str, str]] = {}
        self._set_storage: Dict[str, set] = {}
        self._key_value_storage: Dict[str, str] = {}

        # Initialize schema manager and producer
        self.schema_manager = None
        self.serializer = None
        if self.use_schema_registry:
            self._init_schema_registry()

        self.producer = self._init_kafka_producer()

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
    ) -> None:
        """Log an event to Kafka and in-memory storage."""
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create event record
        event = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": self._sanitize_payload(payload),
            "step": step,
            "run_id": run_id,
            "fork_group": fork_group,
            "parent": parent,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in memory
        self.memory.append(event)

        # Send to Kafka
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

                    logger.debug(f"Sent event to Kafka with schema: {agent_id}:{event_type}")

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
            # Event is still stored in memory, so we can continue

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
        """Retrieve recent events from memory."""
        return self.memory[-count:] if self.memory else []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a hash field."""
        if name not in self._hash_storage:
            self._hash_storage[name] = {}

        is_new = key not in self._hash_storage[name]
        self._hash_storage[name][key] = str(value)
        return 1 if is_new else 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field."""
        return self._hash_storage.get(name, {}).get(key)

    def hkeys(self, name: str) -> List[str]:
        """Get hash keys."""
        return list(self._hash_storage.get(name, {}).keys())

    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if name not in self._hash_storage:
            return 0

        deleted_count = 0
        for key in keys:
            if key in self._hash_storage[name]:
                del self._hash_storage[name][key]
                deleted_count += 1

        return deleted_count

    def smembers(self, name: str) -> List[str]:
        """Get set members."""
        return list(self._set_storage.get(name, set()))

    def sadd(self, name: str, *values: str) -> int:
        """Add to set."""
        if name not in self._set_storage:
            self._set_storage[name] = set()

        added_count = 0
        for value in values:
            if value not in self._set_storage[name]:
                self._set_storage[name].add(value)
                added_count += 1

        return added_count

    def srem(self, name: str, *values: str) -> int:
        """Remove from set."""
        if name not in self._set_storage:
            return 0

        removed_count = 0
        for value in values:
            if value in self._set_storage[name]:
                self._set_storage[name].remove(value)
                removed_count += 1

        return removed_count

    def get(self, key: str) -> Optional[str]:
        """Get a value."""
        return self._key_value_storage.get(key)

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a value."""
        self._key_value_storage[key] = str(value)
        return True

    def delete(self, *keys: str) -> int:
        """Delete keys."""
        deleted_count = 0
        for key in keys:
            if key in self._key_value_storage:
                del self._key_value_storage[key]
                deleted_count += 1

        return deleted_count

    def close(self) -> None:
        """Close the Kafka producer."""
        if self.producer:
            try:
                if hasattr(self.producer, "close"):  # kafka-python
                    self.producer.close()
                elif hasattr(self.producer, "flush"):  # confluent-kafka
                    self.producer.flush()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")

    @property
    def redis(self):
        """Compatibility property - raises error since this is Kafka backend."""
        raise AttributeError("KafkaMemoryLogger does not have a 'redis' attribute")

    def __del__(self):
        """Cleanup on object deletion."""
        self.close()
