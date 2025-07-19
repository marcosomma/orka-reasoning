"""Kafka memory logger implementation."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import redis

from .base_logger import BaseMemoryLogger

logger = logging.getLogger(__name__)


class KafkaMemoryLogger(BaseMemoryLogger):
    """Memory logger implementation using Kafka."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        redis_url: str | None = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: dict[str, Any] | None = None,
        enable_hnsw: bool = True,
        vector_params: dict[str, Any] | None = None,
        topic_prefix: str = "orka-memory",
        schema_registry_url: str | None = None,
        use_schema_registry: bool = True,
    ) -> None:
        """Initialize the Kafka memory logger."""
        super().__init__(stream_key, debug_keep_previous_outputs, decay_config)

        self.bootstrap_servers = bootstrap_servers
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6380/0")
        self.stream_key = stream_key
        self.debug_keep_previous_outputs = debug_keep_previous_outputs
        self.main_topic = f"{topic_prefix}-events"
        self.memory = []
        self.decay_config = decay_config or {}
        self.schema_registry_url = schema_registry_url or os.getenv(
            "KAFKA_SCHEMA_REGISTRY_URL",
            "http://localhost:8081",
        )
        self.use_schema_registry = use_schema_registry

        # Initialize Kafka producer
        self._init_kafka_producer()

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

    def _init_kafka_producer(self):
        """Initialize the Kafka producer with proper configuration."""
        try:
            from confluent_kafka import Producer
            from confluent_kafka.serialization import StringSerializer

            # Configure producer with reliability settings
            producer_config = {
                "bootstrap.servers": self.bootstrap_servers,
                "acks": "all",  # Wait for all replicas
                "enable.idempotence": True,  # Prevent duplicates
                "max.in.flight.requests.per.connection": 5,
                "retries": 5,
                "retry.backoff.ms": 500,
                "compression.type": "lz4",
                "queue.buffering.max.messages": 100000,
                "queue.buffering.max.ms": 100,
                "batch.size": 16384,
                "linger.ms": 5,
            }

            self.producer = Producer(producer_config)
            self.string_serializer = StringSerializer("utf_8")
            logger.info("✅ Kafka producer initialized with reliability settings")

        except ImportError:
            logger.error(
                "❌ confluent-kafka not installed. Please install it to use Kafka backend.",
            )
            raise

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
                log_type=kwargs.get("log_type", "log"),
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

    def _generate_decay_metadata(self, event: dict[str, Any]) -> dict[str, Any]:
        """Generate decay metadata for an event."""
        if not self.decay_config or not self.decay_config.get("enabled"):
            return {}

        current_time = int(datetime.now(UTC).timestamp() * 1000)
        decay_hours = self.decay_config.get("default_long_term_hours", 24.0)

        return {
            "orka_memory_type": "long_term",
            "orka_memory_category": "stored",
            "orka_expire_time": current_time + int(decay_hours * 3600 * 1000),
            "orka_importance_score": 1.0,
        }

    def log(
        self,
        agent_id: str,
        event_type: str,
        payload: dict[str, Any],
        step: int | None = None,
        run_id: str | None = None,
        fork_group: str | None = None,
        parent: str | None = None,
        previous_outputs: dict[str, Any] | None = None,
        agent_decay_config: dict[str, Any] | None = None,
        log_type: str = "log",
    ) -> None:
        """Log an event to both Kafka and Redis."""
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        # Determine which decay config to use
        effective_decay_config = self.decay_config.copy() if self.decay_config else {}
        if agent_decay_config:
            # Merge agent-specific decay config with global config
            effective_decay_config.update(agent_decay_config)

        # Calculate decay metadata if decay is enabled
        decay_metadata = {}
        decay_enabled = effective_decay_config.get("enabled", False)

        if decay_enabled:
            decay_metadata = self._generate_decay_metadata(
                {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "payload": safe_payload,
                    "timestamp": int(datetime.now(UTC).timestamp() * 1000),
                },
            )

        # Store in memory buffer
        event_data = {
            "agent_id": agent_id,
            "event_type": event_type,
            "payload": safe_payload,
            "timestamp": int(datetime.now(UTC).timestamp() * 1000),
            "run_id": run_id or "default",
            "step": step or -1,
        }
        event_data.update(decay_metadata)
        self.memory.append(event_data)

        # Store in Redis first
        self._store_in_redis(
            event_data,
            step=step,
            run_id=run_id,
            fork_group=fork_group,
            parent=parent,
            previous_outputs=previous_outputs,
            agent_decay_config=agent_decay_config,
            log_type=log_type,
        )

        # Then send to Kafka
        self._send_to_kafka(event_data)

    def _send_to_kafka(self, event_data: dict[str, Any]) -> None:
        """Send event data to Kafka."""
        try:
            # Prepare Kafka message
            kafka_message = event_data.copy()

            # Serialize and send
            message_str = json.dumps(kafka_message)
            self.producer.produce(
                self.main_topic,
                value=self.string_serializer(message_str),
                on_delivery=self._delivery_callback,
            )
            self.producer.poll(0)  # Trigger delivery reports

        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
            # Continue execution - Redis storage is our source of truth

    def _delivery_callback(self, err, msg):
        """Handle Kafka message delivery confirmation."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def tail(self, n: int = 10, run_id: str | None = None) -> list[dict[str, Any]]:
        """Get the last n events from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.tail(n, run_id)

        try:
            # Get stream entries
            entries = self.redis_client.xrevrange(self.stream_key, count=n)
            result = []

            for _, data in entries:
                if run_id and data.get(b"run_id", b"").decode() != run_id:
                    continue

                entry = {
                    "agent_id": data.get(b"agent_id", b"").decode(),
                    "event_type": data.get(b"event_type", b"").decode(),
                    "timestamp": int(data.get(b"timestamp", b"0").decode()),
                    "run_id": data.get(b"run_id", b"default").decode(),
                    "step": int(data.get(b"step", b"-1").decode()),
                }

                try:
                    entry["payload"] = json.loads(data.get(b"payload", b"{}").decode())
                except json.JSONDecodeError:
                    entry["payload"] = {}

                result.append(entry)

            return result

        except Exception as e:
            logger.error(f"Failed to tail Redis stream: {e}")
            return []

    def get(self, key: str) -> str | None:
        """Get a value from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.get(key)
        try:
            value = self.redis_client.get(key)
            return value.decode() if value else None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    def set(self, key: str, value: str) -> bool:
        """Set a value in Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.set(key, value)
        try:
            return bool(self.redis_client.set(key, value))
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.delete(key)
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    def hset(self, key: str, field: str, value: str) -> int:
        """Set a hash field in Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.hset(key, field, value)
        try:
            return self.redis_client.hset(key, field, value)
        except Exception as e:
            logger.error(f"Failed to hset {key}.{field}: {e}")
            return 0

    def hget(self, key: str, field: str) -> str | None:
        """Get a hash field from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.hget(key, field)
        try:
            value = self.redis_client.hget(key, field)
            return value.decode() if value else None
        except Exception as e:
            logger.error(f"Failed to hget {key}.{field}: {e}")
            return None

    def hdel(self, key: str, field: str) -> bool:
        """Delete a hash field from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.hdel(key, field)
        try:
            return bool(self.redis_client.hdel(key, field))
        except Exception as e:
            logger.error(f"Failed to hdel {key}.{field}: {e}")
            return False

    def hkeys(self, key: str) -> list[str]:
        """Get all hash fields from Redis."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.hkeys(key)
        try:
            keys = self.redis_client.hkeys(key)
            return [k.decode() for k in keys]
        except Exception as e:
            logger.error(f"Failed to get hkeys for {key}: {e}")
            return []

    def sadd(self, key: str, value: str) -> bool:
        """Add a value to a Redis set."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.sadd(key, value)
        try:
            return bool(self.redis_client.sadd(key, value))
        except Exception as e:
            logger.error(f"Failed to sadd to {key}: {e}")
            return False

    def srem(self, key: str, value: str) -> bool:
        """Remove a value from a Redis set."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.srem(key, value)
        try:
            return bool(self.redis_client.srem(key, value))
        except Exception as e:
            logger.error(f"Failed to srem from {key}: {e}")
            return False

    def smembers(self, key: str) -> list[str]:
        """Get all members of a Redis set."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.smembers(key)
        try:
            members = self.redis_client.smembers(key)
            return [m.decode() for m in members]
        except Exception as e:
            logger.error(f"Failed to get smembers for {key}: {e}")
            return []

    def cleanup_expired_memories(self, dry_run: bool = False) -> int:
        """Clean up expired memories."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.cleanup_expired_memories(dry_run=dry_run)
        try:
            # Get all memory keys
            memory_pattern = "orka_memory:*"
            keys = self.redis_client.keys(memory_pattern)
            cleaned = 0

            for key in keys:
                try:
                    # Get expiry time if set
                    expire_time = self.redis_client.hget(key, "orka_expire_time")
                    if expire_time:
                        expire_time = int(expire_time.decode())
                        current_time = int(datetime.now(UTC).timestamp() * 1000)

                        if current_time > expire_time:
                            if not dry_run:
                                self.redis_client.delete(key)
                            cleaned += 1

                except Exception as e:
                    logger.warning(f"Error checking expiry for key {key}: {e}")
                    continue

            return cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.get_memory_stats()
        try:
            memory_pattern = "orka_memory:*"
            keys = self.redis_client.keys(memory_pattern)
            total_memories = len(keys)

            # Count memories by type
            memory_types = {}
            expired_count = 0
            current_time = int(datetime.now(UTC).timestamp() * 1000)

            for key in keys:
                try:
                    memory_data = self.redis_client.hgetall(key)

                    # Count by memory type
                    memory_type = memory_data.get(b"memory_type", b"unknown").decode()
                    memory_types[memory_type] = memory_types.get(memory_type, 0) + 1

                    # Check expiry
                    expire_time = memory_data.get(b"orka_expire_time")
                    if expire_time:
                        expire_time = int(expire_time.decode())
                        if current_time > expire_time:
                            expired_count += 1

                except Exception as e:
                    logger.warning(f"Error processing memory stats for key {key}: {e}")
                    continue

            return {
                "total_memories": total_memories,
                "memory_types": memory_types,
                "expired_count": expired_count,
                "backend": "kafka+redis",
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                "error": str(e),
                "backend": "kafka+redis",
                "timestamp": int(datetime.now(UTC).timestamp() * 1000),
            }

    def close(self):
        """Close all connections."""
        try:
            if hasattr(self, "producer"):
                self.producer.flush()  # Ensure all messages are delivered
            if self._redis_memory_logger:
                self._redis_memory_logger.close()
            else:
                self.redis_client.close()
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

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
        """Search memories using RedisStack if available."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.search_memories(
                query=query,
                num_results=num_results,
                trace_id=trace_id,
                node_id=node_id,
                memory_type=memory_type,
                min_importance=min_importance,
                log_type=log_type,
                namespace=namespace,
            )
        return []  # Return empty list when RedisStack is not available

    def log_memory(
        self,
        content: str,
        node_id: str,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 1.0,
        memory_type: str = "short_term",
        expiry_hours: float | None = None,
    ) -> str:
        """Store memory with vector embedding."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.log_memory(
                content=content,
                node_id=node_id,
                trace_id=trace_id,
                metadata=metadata,
                importance_score=importance_score,
                memory_type=memory_type,
                expiry_hours=expiry_hours,
            )
        return ""

    def ensure_index(self) -> bool:
        """Ensure the enhanced memory index exists."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.ensure_index()
        return False
