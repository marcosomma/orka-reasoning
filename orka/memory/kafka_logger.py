"""Kafka memory logger implementation."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

import redis
from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer

from .base_logger import BaseMemoryLogger
from .redisstack_logger import RedisStackMemoryLogger

logger = logging.getLogger(__name__)


class KafkaMemoryLogger(BaseMemoryLogger):
    """Memory logger implementation using Kafka."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        redis_url: Optional[str] = None,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[Dict[str, Any]] = None,
        enable_hnsw: bool = True,
        vector_params: Optional[Dict[str, Any]] = None,
        topic_prefix: str = "orka-memory",
        schema_registry_url: Optional[str] = None,
        use_schema_registry: bool = True,
    ) -> None:
        """Initialize the Kafka memory logger."""
        super().__init__(
            stream_key=stream_key,
            debug_keep_previous_outputs=debug_keep_previous_outputs,
            decay_config=decay_config,
        )

        self.bootstrap_servers: str = bootstrap_servers
        self.redis_url: str = (
            redis_url
            or os.environ.get("REDIS_URL", "redis://localhost:6380/0")
            or "redis://localhost:6380/0"
        )
        self.stream_key: str = stream_key
        self.debug_keep_previous_outputs: bool = debug_keep_previous_outputs
        self.main_topic: str = f"{topic_prefix}-events"
        self.memory: List[Dict[str, Any]] = []
        self.decay_config: Dict[str, Any] = decay_config or {}
        self.schema_registry_url: str = (
            schema_registry_url
            or os.getenv(
                "KAFKA_SCHEMA_REGISTRY_URL",
                "http://localhost:8081",
            )
            or "http://localhost:8081"
        )
        self.use_schema_registry: bool = use_schema_registry
        self.producer: Optional[Producer] = None
        self.string_serializer: Optional[StringSerializer] = None
        self._redis_memory_logger: Optional[RedisStackMemoryLogger] = None
        self.redis_client: redis.Redis[Any] = redis.from_url(self.redis_url)

        # Initialize Kafka producer
        self._init_kafka_producer()

        # Create RedisStack logger for enhanced memory operations
        try:
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

    def _init_kafka_producer(self) -> None:
        """Initialize the Kafka producer with proper configuration."""
        try:
            # Configure producer with reliability settings
            producer_config: Dict[str, Any] = {
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
    def redis(self) -> redis.Redis[Any]:
        """Return Redis client - prefer RedisStack client if available."""
        if self._redis_memory_logger:
            return self._redis_memory_logger.redis
        return self.redis_client

    def _store_in_redis(self, event: Dict[str, Any], **kwargs: Any) -> None:
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
                redis_entry: Dict[str, Any] = {
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

    def _generate_decay_metadata(self, event: Dict[str, Any]) -> Dict[str, Any]:
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
        payload: Dict[str, Any],
        step: Optional[int] = None,
        run_id: Optional[str] = None,
        fork_group: Optional[str] = None,
        parent: Optional[str] = None,
        previous_outputs: Optional[Dict[str, Any]] = None,
        agent_decay_config: Optional[Dict[str, Any]] = None,
        log_type: str = "memory",
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
        decay_metadata: Dict[str, Any] = {}
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
        event_data: Dict[str, Any] = {
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
        )

        # Then send to Kafka
        self._send_to_kafka(event_data)

    def _send_to_kafka(self, event_data: Dict[str, Any]) -> None:
        """Send event data to Kafka."""
        try:
            # Prepare Kafka message
            kafka_message = event_data.copy()

            # Serialize and send
            message_str = json.dumps(kafka_message)

            if self.producer is not None and self.string_serializer is not None:
                self.producer.produce(
                    topic=self.main_topic,
                    key=self.string_serializer(event_data["agent_id"]),
                    value=message_str,
                    on_delivery=self._delivery_callback,
                )
                self.producer.poll(0)  # Trigger delivery reports
            else:
                logger.error("Kafka producer not initialized")

        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")

    def _delivery_callback(self, err: Optional[Exception], msg: Any) -> None:
        """Handle Kafka message delivery reports."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def tail(self, n: int = 10, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get the last N events from memory.

        Args:
            n: Number of events to retrieve.
            run_id: Optional run ID to filter by.

        Returns:
            List of events.
        """
        if self._redis_memory_logger:
            return self._redis_memory_logger.tail(n)

        try:
            events = self.redis_client.xrevrange(self.stream_key, count=n)
            result: List[Dict[str, Any]] = []
            for event_id, event_data in events:
                try:
                    event = {
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in event_data.items()
                    }
                    if "payload" in event:
                        event["payload"] = json.loads(event["payload"])
                    if run_id is None or event.get("run_id") == run_id:
                        result.append(event)
                except Exception as e:
                    logger.error(f"Failed to process event {event_id}: {e}")
            return result
        except Exception as e:
            logger.error(f"Failed to tail Redis stream: {e}")
            return []

    def get(self, key: str) -> Optional[str]:
        """
        Get a value from Redis.

        Args:
            key: Key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            value = self.redis_client.get(key)
            return value.decode() if value else None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    def set(self, name: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a key-value pair in Redis."""
        try:
            if self._redis_memory_logger:
                return bool(self._redis_memory_logger.set(name, value))
            return bool(self.redis_client.set(name, value))
        except Exception as e:
            logger.error(f"Failed to set key {name}: {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys from Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.delete(*keys)
            return self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a hash field to a value in Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.hset(name, key, value)
            return bool(self.redis_client.hset(name, key, value))
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {e}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """Get the value of a hash field in Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.hget(name, key)
            value = self.redis_client.hget(name, key)
            return value.decode("utf-8") if value else None
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {e}")
            return None

    def hdel(self, name: str, *keys: str) -> int:
        """Delete one or more hash fields in Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.hdel(name, *keys)
            return self.redis_client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Failed to delete hash fields {keys} from {name}: {e}")
            return 0

    def hkeys(self, key: str) -> List[str]:
        """
        Get all hash field names.

        Args:
            key: Hash key.

        Returns:
            List of field names.
        """
        try:
            keys = self.redis_client.hkeys(key)
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logger.error(f"Failed to get hash keys from {key}: {e}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """Add one or more members to a set in Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.sadd(name, *values)
            return self.redis_client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Failed to add values {values} to set {name}: {e}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """Remove one or more members from a set in Redis."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.srem(name, *values)
            return self.redis_client.srem(name, *values)
        except Exception as e:
            logger.error(f"Failed to remove values {values} from set {name}: {e}")
            return 0

    def smembers(self, key: str) -> List[str]:
        """
        Get all members of a set.

        Args:
            key: Set key.

        Returns:
            List of set members.
        """
        try:
            members = self.redis_client.smembers(key)
            return [m.decode() if isinstance(m, bytes) else m for m in members]
        except Exception as e:
            logger.error(f"Failed to get members from set {key}: {e}")
            return []

    def cleanup_expired_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up expired memories."""
        try:
            if self._redis_memory_logger:
                return self._redis_memory_logger.cleanup_expired_memories(dry_run)
            # Basic Redis implementation doesn't support expiry cleanup
            return {"cleaned": 0, "dry_run": dry_run}
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return {"error": str(e), "cleaned": 0, "dry_run": dry_run}

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary containing memory statistics.
        """
        if self._redis_memory_logger:
            return self._redis_memory_logger.get_memory_stats()

        return {
            "total_memories": len(self.memory),
            "backend": "kafka",
            "redis_available": bool(self.redis_client),
            "kafka_producer_ready": bool(self.producer),
        }

    def close(self) -> None:
        """Close all connections."""
        try:
            if self.producer:
                self.producer.flush()
                self.producer.close()
            if self.redis_client:
                self.redis_client.close()
            if self._redis_memory_logger:
                self._redis_memory_logger.close()
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

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
        """
        Search memories using vector similarity.

        Args:
            query: Search query.
            num_results: Maximum number of results to return.
            trace_id: Optional trace ID to filter by.
            node_id: Optional node ID to filter by.
            memory_type: Optional memory type to filter by.
            min_importance: Optional minimum importance score.
            log_type: Type of log to search.
            namespace: Optional namespace to search in.

        Returns:
            List of matching memories.
        """
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
        """
        Log a memory entry.

        Args:
            content: Memory content.
            node_id: Node ID.
            trace_id: Trace ID.
            metadata: Optional metadata.
            importance_score: Importance score.
            memory_type: Memory type.
            expiry_hours: Optional expiry time in hours.

        Returns:
            Memory ID.
        """
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
        """
        Ensure the memory index exists.

        Returns:
            True if successful, False otherwise.
        """
        if self._redis_memory_logger:
            return self._redis_memory_logger.ensure_index()
        return False
