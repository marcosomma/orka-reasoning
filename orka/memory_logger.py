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
Memory Logger
============

The Memory Logger is a critical component of the OrKa framework that provides
persistent storage and retrieval capabilities for orchestration events, agent outputs,
and system state. It serves as both a runtime memory system and an audit trail for
agent workflows.

Key Features:
------------
1. Event Logging: Records all agent activities and system events
2. Data Persistence: Stores data in Redis streams for reliability
3. Serialization: Handles conversion of complex Python objects to JSON-serializable formats
4. Error Resilience: Implements fallback mechanisms for handling serialization errors
5. Querying: Provides methods to retrieve recent events and specific data points
6. File Export: Supports exporting memory logs to files for analysis

The Memory Logger is essential for:
- Enabling agents to access past context and outputs
- Debugging and auditing agent workflows
- Maintaining state across distributed components
- Supporting complex workflow patterns like fork/join

Implementation Notes:
-------------------
- Uses Redis streams as the primary storage backend
- Maintains an in-memory buffer for fast access to recent events
- Implements robust sanitization to handle non-serializable objects
- Provides helper methods for common Redis operations
- Includes a placeholder for future Kafka-based implementation
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import redis

logger = logging.getLogger(__name__)


class BaseMemoryLogger(ABC):
    """
    Abstract base class for memory loggers.
    Defines the interface that must be implemented by all memory backends.
    """

    def __init__(self, stream_key: str = "orka:memory") -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
        """
        self.stream_key = stream_key
        self.memory: List[Dict[str, Any]] = []  # Local memory buffer

    @abstractmethod
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
        """Log an event to the memory backend."""
        pass

    @abstractmethod
    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the most recent events."""
        pass

    @abstractmethod
    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """Set a field in a hash structure."""
        pass

    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a field from a hash structure."""
        pass

    @abstractmethod
    def hkeys(self, name: str) -> List[str]:
        """Get all keys in a hash structure."""
        pass

    @abstractmethod
    def hdel(self, name: str, *keys: str) -> int:
        """Delete fields from a hash structure."""
        pass

    @abstractmethod
    def smembers(self, name: str) -> List[str]:
        """Get all members of a set."""
        pass

    @abstractmethod
    def sadd(self, name: str, *values: str) -> int:
        """Add members to a set."""
        pass

    @abstractmethod
    def srem(self, name: str, *values: str) -> int:
        """Remove members from a set."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set a value by key."""
        pass

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """Delete keys."""
        pass

    def _sanitize_for_json(self, obj: Any, _seen: Optional[set] = None) -> Any:
        """
        Recursively sanitize an object to be JSON serializable, with circular reference detection.

        Args:
            obj: The object to sanitize.
            _seen: Set of already processed object IDs to detect cycles.

        Returns:
            A JSON-serializable version of the object.
        """
        if _seen is None:
            _seen = set()

        # Check for circular references
        obj_id = id(obj)
        if obj_id in _seen:
            return f"<circular-reference: {type(obj).__name__}>"

        try:
            if obj is None or isinstance(obj, (str, int, float, bool)):
                return obj
            elif isinstance(obj, bytes):
                # Convert bytes to base64-encoded string
                import base64

                return {
                    "__type": "bytes",
                    "data": base64.b64encode(obj).decode("utf-8"),
                }
            elif isinstance(obj, (list, tuple)):
                _seen.add(obj_id)
                try:
                    result = [self._sanitize_for_json(item, _seen) for item in obj]
                finally:
                    _seen.discard(obj_id)
                return result
            elif isinstance(obj, dict):
                _seen.add(obj_id)
                try:
                    result = {
                        str(k): self._sanitize_for_json(v, _seen)
                        for k, v in obj.items()
                    }
                finally:
                    _seen.discard(obj_id)
                return result
            elif hasattr(obj, "__dict__"):
                try:
                    _seen.add(obj_id)
                    try:
                        # Handle custom objects by converting to dict
                        return {
                            "__type": obj.__class__.__name__,
                            "data": self._sanitize_for_json(obj.__dict__, _seen),
                        }
                    finally:
                        _seen.discard(obj_id)
                except Exception as e:
                    return f"<non-serializable object: {obj.__class__.__name__}, error: {str(e)}>"
            elif hasattr(obj, "isoformat"):  # Handle datetime-like objects
                return obj.isoformat()
            else:
                # Last resort - convert to string
                return f"<non-serializable: {type(obj).__name__}>"
        except Exception as e:
            logger.warning(f"Failed to sanitize object for JSON: {str(e)}")
            return f"<sanitization-error: {str(e)}>"

    def save_to_file(self, file_path: str) -> None:
        """
        Save the logged events to a JSON file.

        Args:
            file_path: Path to the output JSON file.
        """
        try:
            # Pre-sanitize all memory entries
            sanitized_memory = self._sanitize_for_json(self.memory)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    sanitized_memory,
                    f,
                    indent=2,
                    default=lambda o: f"<non-serializable: {type(o).__name__}>",
                )
            logger.info(f"[MemoryLogger] Logs saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save logs to file: {str(e)}")
            # Try again with simplified content
            try:
                simplified_memory = [
                    {
                        "agent_id": entry.get("agent_id", "unknown"),
                        "event_type": entry.get("event_type", "unknown"),
                        "timestamp": entry.get(
                            "timestamp", datetime.utcnow().isoformat()
                        ),
                        "error": "Original entry contained non-serializable data",
                    }
                    for entry in self.memory
                ]
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(simplified_memory, f, indent=2)
                logger.info(f"[MemoryLogger] Simplified logs saved to {file_path}")
            except Exception as inner_e:
                logger.error(f"Failed to save simplified logs to file: {str(inner_e)}")


class RedisMemoryLogger(BaseMemoryLogger):
    """
    A memory logger that uses Redis to store and retrieve orchestration events.
    Supports logging events, saving logs to files, and querying recent events.
    """

    def __init__(
        self, redis_url: Optional[str] = None, stream_key: str = "orka:memory"
    ) -> None:
        """
        Initialize the Redis memory logger.

        Args:
            redis_url: URL for the Redis server. Defaults to environment variable REDIS_URL or redis service name.
            stream_key: Key for the Redis stream. Defaults to "orka:memory".
        """
        super().__init__(stream_key)
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client = redis.from_url(self.redis_url)

    @property
    def redis(self) -> redis.Redis:
        """
        Return the Redis client for backward compatibility.
        This property exists for compatibility with existing code.
        """
        return self.client

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
        """
        Log an event to Redis and local memory.

        Args:
            agent_id: ID of the agent generating the event.
            event_type: Type of the event.
            payload: Event payload.
            step: Step number in the orchestration.
            run_id: ID of the orchestration run.
            fork_group: ID of the fork group.
            parent: ID of the parent event.
            previous_outputs: Previous outputs from agents.

        Raises:
            ValueError: If agent_id is missing.
            Exception: If Redis operation fails.
        """
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": safe_payload,
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = self._sanitize_for_json(previous_outputs)

        self.memory.append(event)

        try:
            # Sanitize previous outputs if present
            safe_previous_outputs = None
            if previous_outputs:
                try:
                    safe_previous_outputs = json.dumps(
                        self._sanitize_for_json(previous_outputs)
                    )
                except Exception as e:
                    logger.error(f"Failed to serialize previous_outputs: {str(e)}")
                    safe_previous_outputs = json.dumps(
                        {"error": f"Serialization error: {str(e)}"}
                    )

            # Prepare the Redis entry
            redis_entry = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": str(step or -1),
            }

            # Safely serialize the payload
            try:
                redis_entry["payload"] = json.dumps(safe_payload)
            except Exception as e:
                logger.error(f"Failed to serialize payload: {str(e)}")
                redis_entry["payload"] = json.dumps(
                    {"error": "Original payload contained non-serializable objects"}
                )

            # Only add previous_outputs if it exists and is not None
            if safe_previous_outputs:
                redis_entry["previous_outputs"] = safe_previous_outputs

            # Add the entry to Redis
            self.client.xadd(self.stream_key, redis_entry)

        except Exception as e:
            logger.error(f"Failed to log event to Redis: {str(e)}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {str(e)}"
                }
                self.client.xadd(
                    self.stream_key,
                    {
                        "agent_id": agent_id,
                        "event_type": event_type,
                        "timestamp": event["timestamp"],
                        "payload": json.dumps(simplified_payload),
                        "run_id": run_id or "default",
                        "step": str(step or -1),
                    },
                )
                logger.info("Logged simplified error payload instead")
            except Exception as inner_e:
                logger.error(
                    f"Failed to log event to Redis: {str(e)} and fallback also failed: {str(inner_e)}"
                )

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from the Redis stream.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        try:
            results = self.client.xrevrange(self.stream_key, count=count)
            # Sanitize results for JSON serialization before returning
            return self._sanitize_for_json(results)
        except Exception as e:
            logger.error(f"Failed to retrieve events from Redis: {str(e)}")
            return []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a field in a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added.
        """
        try:
            # Convert non-string values to strings if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(self._sanitize_for_json(value))
            return self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {str(e)}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a Redis hash.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        try:
            return self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {str(e)}")
            return None

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a Redis hash.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        try:
            return self.client.hkeys(name)
        except Exception as e:
            logger.error(f"Failed to get hash keys from {name}: {str(e)}")
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a Redis hash.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Failed to delete hash fields from {name}: {str(e)}")
            return 0

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a Redis set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        try:
            return self.client.smembers(name)
        except Exception as e:
            logger.error(f"Failed to get set members from {name}: {str(e)}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """
        Add members to a Redis set.

        Args:
            name: Name of the set.
            *values: Values to add.

        Returns:
            Number of new members added.
        """
        try:
            return self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Failed to add members to set {name}: {str(e)}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """
        Remove members from a Redis set.

        Args:
            name: Name of the set.
            *values: Values to remove.

        Returns:
            Number of members removed.
        """
        try:
            return self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Failed to remove members from set {name}: {str(e)}")
            return 0

    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key from Redis.

        Args:
            key: The key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            result = self.client.get(key)
            return result.decode() if isinstance(result, bytes) else result
        except Exception as e:
            logger.error(f"Failed to get key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set a value by key in Redis.

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Failed to set key {key}: {str(e)}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {str(e)}")
            return 0

    def close(self) -> None:
        """Close the Redis client connection."""
        try:
            self.client.close()
            # Only log if logging system is still available
            try:
                logger.info("[RedisMemoryLogger] Redis client closed")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass
        except Exception as e:
            try:
                logger.error(f"Error closing Redis client: {str(e)}")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            # Ignore all errors during cleanup
            pass


# Future stub
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
    ) -> None:
        """
        Initialize the Kafka memory logger.

        Args:
            bootstrap_servers: Kafka bootstrap servers. Defaults to environment variable KAFKA_BOOTSTRAP_SERVERS.
            topic_prefix: Prefix for Kafka topics. Defaults to "orka-memory".
            stream_key: Key for the memory stream. Defaults to "orka:memory".
        """
        super().__init__(stream_key)
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.topic_prefix = topic_prefix
        self.main_topic = f"{topic_prefix}-events"

        # In-memory storage for hash and set operations (since Kafka doesn't have these concepts)
        self._hash_storage: Dict[str, Dict[str, Any]] = {}
        self._set_storage: Dict[str, set] = {}

        # Initialize Kafka producer
        try:
            from kafka import KafkaProducer

            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            logger.info(
                f"[KafkaMemoryLogger] Connected to Kafka at {self.bootstrap_servers}"
            )
        except ImportError:
            logger.error(
                "kafka-python package is required for KafkaMemoryLogger. Install with: pip install kafka-python"
            )
            raise ImportError("kafka-python package is required")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
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
        """
        Log an event to Kafka and local memory.

        Args:
            agent_id: ID of the agent generating the event.
            event_type: Type of the event.
            payload: Event payload.
            step: Step number in the orchestration.
            run_id: ID of the orchestration run.
            fork_group: ID of the fork group.
            parent: ID of the parent event.
            previous_outputs: Previous outputs from agents.

        Raises:
            ValueError: If agent_id is missing.
            Exception: If Kafka operation fails.
        """
        if not agent_id:
            raise ValueError("Event must contain 'agent_id'")

        # Create a copy of the payload to avoid modifying the original
        safe_payload = self._sanitize_for_json(payload)

        event: Dict[str, Any] = {
            "agent_id": agent_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": safe_payload,
        }
        if step is not None:
            event["step"] = step
        if run_id:
            event["run_id"] = run_id
        if fork_group:
            event["fork_group"] = fork_group
        if parent:
            event["parent"] = parent
        if previous_outputs:
            event["previous_outputs"] = self._sanitize_for_json(previous_outputs)

        self.memory.append(event)

        try:
            # Prepare the Kafka message
            kafka_message = {
                "agent_id": agent_id,
                "event_type": event_type,
                "timestamp": event["timestamp"],
                "run_id": run_id or "default",
                "step": step or -1,
                "payload": safe_payload,
            }

            if previous_outputs:
                kafka_message["previous_outputs"] = self._sanitize_for_json(
                    previous_outputs
                )

            # Send to Kafka topic
            key = f"{run_id or 'default'}:{agent_id}"
            future = self.producer.send(self.main_topic, value=kafka_message, key=key)

            # Optional: Wait for the message to be sent (for reliability)
            # future.get(timeout=10)

            logger.debug(f"[KafkaMemoryLogger] Sent event to topic {self.main_topic}")

        except Exception as e:
            logger.error(f"Failed to log event to Kafka: {str(e)}")
            logger.error(f"Problematic payload: {str(payload)[:200]}")
            # Try again with a simplified payload
            try:
                simplified_payload = {
                    "error": f"Original payload contained non-serializable objects: {str(e)}"
                }
                simplified_message = {
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "timestamp": event["timestamp"],
                    "run_id": run_id or "default",
                    "step": step or -1,
                    "payload": simplified_payload,
                }

                key = f"{run_id or 'default'}:{agent_id}"
                self.producer.send(self.main_topic, value=simplified_message, key=key)
                logger.info("Logged simplified error payload to Kafka instead")
            except Exception as inner_e:
                logger.error(
                    f"Failed to log event to Kafka: {str(e)} and fallback also failed: {str(inner_e)}"
                )

    def tail(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent events from local memory.
        Note: Kafka doesn't naturally support tail operations like Redis streams,
        so we use the local memory buffer for this functionality.

        Args:
            count: Number of events to retrieve.

        Returns:
            List of recent events.
        """
        try:
            # Return the last 'count' events from local memory
            recent_events = (
                self.memory[-count:] if count <= len(self.memory) else self.memory
            )
            return self._sanitize_for_json(recent_events)
        except Exception as e:
            logger.error(f"Failed to retrieve recent events: {str(e)}")
            return []

    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a field in a hash structure (stored in memory).

        Args:
            name: Name of the hash.
            key: Field key.
            value: Field value.

        Returns:
            Number of fields added (1 if new, 0 if updated).
        """
        try:
            if name not in self._hash_storage:
                self._hash_storage[name] = {}

            is_new_field = key not in self._hash_storage[name]

            # Convert non-string values to strings if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(self._sanitize_for_json(value))

            self._hash_storage[name][key] = value
            return 1 if is_new_field else 0
        except Exception as e:
            logger.error(f"Failed to set hash field {key} in {name}: {str(e)}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get a field from a hash structure.

        Args:
            name: Name of the hash.
            key: Field key.

        Returns:
            Field value.
        """
        try:
            hash_data = self._hash_storage.get(name, {})
            value = hash_data.get(key)
            return str(value) if value is not None else None
        except Exception as e:
            logger.error(f"Failed to get hash field {key} from {name}: {str(e)}")
            return None

    def hkeys(self, name: str) -> List[str]:
        """
        Get all keys in a hash structure.

        Args:
            name: Name of the hash.

        Returns:
            List of keys.
        """
        try:
            hash_data = self._hash_storage.get(name, {})
            return list(hash_data.keys())
        except Exception as e:
            logger.error(f"Failed to get hash keys from {name}: {str(e)}")
            return []

    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a hash structure.

        Args:
            name: Name of the hash.
            *keys: Keys to delete.

        Returns:
            Number of fields deleted.
        """
        try:
            if name not in self._hash_storage:
                return 0

            deleted_count = 0
            for key in keys:
                if key in self._hash_storage[name]:
                    del self._hash_storage[name][key]
                    deleted_count += 1

            # Clean up empty hash
            if not self._hash_storage[name]:
                del self._hash_storage[name]

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete hash fields from {name}: {str(e)}")
            return 0

    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a set.

        Args:
            name: Name of the set.

        Returns:
            Set of members.
        """
        try:
            set_data = self._set_storage.get(name, set())
            return list(set_data)
        except Exception as e:
            logger.error(f"Failed to get set members from {name}: {str(e)}")
            return []

    def sadd(self, name: str, *values: str) -> int:
        """
        Add members to a set.

        Args:
            name: Name of the set.
            *values: Values to add.

        Returns:
            Number of new members added.
        """
        try:
            if name not in self._set_storage:
                self._set_storage[name] = set()

            initial_size = len(self._set_storage[name])
            self._set_storage[name].update(values)
            final_size = len(self._set_storage[name])

            return final_size - initial_size
        except Exception as e:
            logger.error(f"Failed to add members to set {name}: {str(e)}")
            return 0

    def srem(self, name: str, *values: str) -> int:
        """
        Remove members from a set.

        Args:
            name: Name of the set.
            *values: Values to remove.

        Returns:
            Number of members removed.
        """
        try:
            if name not in self._set_storage:
                return 0

            removed_count = 0
            for value in values:
                if value in self._set_storage[name]:
                    self._set_storage[name].discard(value)
                    removed_count += 1

            # Clean up empty set
            if not self._set_storage[name]:
                del self._set_storage[name]

            return removed_count
        except Exception as e:
            logger.error(f"Failed to remove members from set {name}: {str(e)}")
            return 0

    def get(self, key: str) -> Optional[str]:
        """
        Get a value by key (stored in memory).

        Args:
            key: The key to get.

        Returns:
            Value if found, None otherwise.
        """
        try:
            # Store simple key-value pairs in a special hash
            return self.hget("simple_kv_storage", key)
        except Exception as e:
            logger.error(f"Failed to get key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set a value by key (stored in memory).

        Args:
            key: The key to set.
            value: The value to set.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Store simple key-value pairs in a special hash
            self.hset("simple_kv_storage", key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {str(e)}")
            return False

    def delete(self, *keys: str) -> int:
        """
        Delete keys (from memory storage).

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        try:
            # Delete from the simple key-value storage hash
            return self.hdel("simple_kv_storage", *keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {str(e)}")
            return 0

    def close(self) -> None:
        """Close the Kafka producer connection."""
        try:
            if hasattr(self, "producer"):
                self.producer.flush()
                self.producer.close()
                # Only log if logging system is still available
                try:
                    logger.info("[KafkaMemoryLogger] Kafka producer closed")
                except (ValueError, OSError):
                    # Logging system might be shut down, ignore
                    pass
        except Exception as e:
            try:
                logger.error(f"Error closing Kafka producer: {str(e)}")
            except (ValueError, OSError):
                # Logging system might be shut down, ignore
                pass

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            # Ignore all errors during cleanup
            pass

    @property
    def redis(self):
        """
        Kafka backend doesn't have a redis client.
        This property exists for compatibility but will raise an error if accessed.
        """
        raise AttributeError(
            "KafkaMemoryLogger does not have a Redis client. "
            "Use the appropriate Kafka-compatible methods or switch to RedisMemoryLogger."
        )


def create_memory_logger(backend: str = "redis", **kwargs) -> BaseMemoryLogger:
    """
    Factory function to create a memory logger based on backend type.

    Args:
        backend: Backend type ("redis" or "kafka")
        **kwargs: Backend-specific configuration

    Returns:
        Memory logger instance

    Raises:
        ValueError: If backend type is not supported
    """
    backend = backend.lower()

    if backend == "redis":
        return RedisMemoryLogger(**kwargs)
    elif backend == "kafka":
        return KafkaMemoryLogger(**kwargs)
    else:
        raise ValueError(
            f"Unsupported memory backend: {backend}. Supported backends: redis, kafka"
        )


# Add MemoryLogger alias for backward compatibility with tests
MemoryLogger = RedisMemoryLogger
