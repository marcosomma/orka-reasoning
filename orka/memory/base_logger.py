"""Base memory logger for the OrKa framework.

Abstract base class for memory loggers that defines the interface that must be
implemented by all memory backends.
"""

import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Union

from .file_operations import FileOperationsMixin
from .serialization import SerializationMixin

logger = logging.getLogger(__name__)

# Type aliases
MemoryEntry = Dict[str, Any]
DecayConfig = Dict[str, Any]
BlobStore = Dict[str, Any]
BlobUsage = Dict[str, int]
BlobReference = Dict[str, Any]
MemoryStats = Dict[str, Any]


class BaseMemoryLogger(ABC, SerializationMixin, FileOperationsMixin):
    """Base memory logger that defines the interface for all memory backends."""

    def __init__(
        self,
        stream_key: str = "orka:memory",
        debug_keep_previous_outputs: bool = False,
        decay_config: Optional[DecayConfig] = None,
    ) -> None:
        """
        Initialize the memory logger.

        Args:
            stream_key: Key for the memory stream. Defaults to "orka:memory".
            debug_keep_previous_outputs: If True, keeps previous_outputs in log files for debugging.
            decay_config: Configuration for memory decay functionality.
        """
        self.stream_key = stream_key
        self.memory: List[MemoryEntry] = []  # Local memory buffer
        self.debug_keep_previous_outputs = debug_keep_previous_outputs

        # Initialize decay configuration
        self.decay_config = self._init_decay_config(decay_config or {})

        # Decay state management
        self._decay_thread: Optional[threading.Thread] = None
        self._decay_stop_event = threading.Event()
        self._last_decay_check = datetime.now(UTC)

        # Initialize automatic decay if enabled
        if self.decay_config.get("enabled", False):
            self._start_decay_scheduler()

        # Blob deduplication storage: SHA256 -> actual blob content
        self._blob_store: BlobStore = {}
        # Track blob usage count for potential cleanup
        self._blob_usage: BlobUsage = {}
        # Minimum size threshold for blob deduplication (in chars)
        self._blob_threshold = 200

    def _init_decay_config(self, decay_config: DecayConfig) -> DecayConfig:
        """
        Initialize decay configuration with defaults.

        Args:
            decay_config: Raw decay configuration

        Returns:
            Processed decay configuration with defaults applied
        """
        default_config: DecayConfig = {
            "enabled": False,  # Disable by default to prevent logs from disappearing
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
            "memory_type_rules": {
                "long_term_events": ["success", "completion", "write", "result"],
                "short_term_events": ["debug", "processing", "start", "progress"],
            },
            "importance_rules": {
                "base_score": 0.5,
                "event_type_boosts": {
                    "write": 0.3,
                    "success": 0.2,
                    "completion": 0.2,
                    "result": 0.1,
                },
                "agent_type_boosts": {
                    "memory": 0.2,
                    "openai-answer": 0.1,
                },
            },
        }

        # Deep merge with defaults
        merged_config = default_config.copy()
        for key, value in decay_config.items():
            if isinstance(value, dict) and key in merged_config:
                merged_config[key].update(value)
            else:
                merged_config[key] = value

        return merged_config

    def _calculate_importance_score(
        self,
        event_type: str,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> float:
        """
        Calculate importance score for a memory entry.

        Args:
            event_type: Type of event
            agent_id: ID of the agent
            payload: Event payload

        Returns:
            Importance score between 0.0 and 1.0
        """
        if not self.decay_config:
            return 0.5  # Default score if no decay config

        rules = self.decay_config.get("importance_rules", {})
        base_score = float(rules.get("base_score", 0.5))

        # Apply event type boosts
        event_boosts = rules.get("event_type_boosts", {})
        event_boost = float(event_boosts.get(event_type, 0.0))

        # Apply agent type boosts
        agent_boosts = rules.get("agent_type_boosts", {})
        agent_type = agent_id.split("-")[0] if "-" in agent_id else agent_id
        agent_boost = float(agent_boosts.get(agent_type, 0.0))

        # Calculate final score
        score = base_score + event_boost + agent_boost

        # Ensure score is between 0.0 and 1.0
        return max(0.0, min(1.0, score))

    def _classify_memory_type(
        self,
        event_type: str,
        importance_score: float,
        category: str = "log",
    ) -> str:
        """
        Classify memory as short-term or long-term.

        Args:
            event_type: Type of event
            importance_score: Calculated importance score
            category: Memory category (log or memory)

        Returns:
            Memory type (short_term or long_term)
        """
        # Orchestration logs are always short-term
        if category == "log":
            return "short_term"

        # Check memory type rules
        rules = self.decay_config.get("memory_type_rules", {})
        long_term_events = rules.get("long_term_events", [])
        short_term_events = rules.get("short_term_events", [])

        # Event type based classification
        if event_type in long_term_events:
            return "long_term"
        if event_type in short_term_events:
            return "short_term"

        # Importance score based classification
        return "long_term" if importance_score >= 0.7 else "short_term"

    def _classify_memory_category(
        self,
        event_type: str,
        agent_id: str,
        payload: Dict[str, Any],
        log_type: str = "log",
    ) -> str:
        """
        Classify memory entry into a category.

        Args:
            event_type: Type of event
            agent_id: ID of the agent
            payload: Event payload
            log_type: Type of log entry

        Returns:
            Memory category
        """
        # Use log_type as primary category
        return log_type

    def _start_decay_scheduler(self) -> None:
        """Start the background thread for memory decay."""
        if self._decay_thread is not None:
            return

        def decay_scheduler() -> None:
            """Run memory decay checks periodically."""
            while not self._decay_stop_event.is_set():
                try:
                    self.cleanup_expired_memories()
                except Exception as e:
                    logger.error(f"Error in decay scheduler: {e}")
                self._decay_stop_event.wait(
                    self.decay_config.get("check_interval_minutes", 30) * 60
                )

        self._decay_thread = threading.Thread(target=decay_scheduler, daemon=True)
        self._decay_thread.start()

    def stop_decay_scheduler(self) -> None:
        """Stop the decay scheduler thread."""
        if self._decay_thread is not None:
            self._decay_stop_event.set()
            self._decay_thread.join(timeout=5.0)
            self._decay_thread = None

    @abstractmethod
    def cleanup_expired_memories(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Clean up expired memories based on decay configuration.

        Args:
            dry_run: If True, only simulate cleanup without making changes

        Returns:
            Statistics about the cleanup operation
        """
        pass

    @abstractmethod
    def get_memory_stats(self) -> MemoryStats:
        """
        Get statistics about the memory store.

        Returns:
            Dictionary containing memory statistics
        """
        pass

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
        agent_decay_config: Optional[Dict[str, Any]] = None,
        log_type: str = "log",  # "log" for orchestration, "memory" for stored memories
    ) -> None:
        """
        Log a memory entry.

        Args:
            agent_id: ID of the agent
            event_type: Type of event
            payload: Event payload
            step: Step number in the workflow
            run_id: ID of the current run
            fork_group: ID of the fork group
            parent: ID of the parent node
            previous_outputs: Previous outputs from other nodes
            agent_decay_config: Agent-specific decay configuration
            log_type: Type of log entry (log or memory)
        """
        pass

    @abstractmethod
    def tail(self, count: int = 10) -> List[MemoryEntry]:
        """
        Get the most recent memory entries.

        Args:
            count: Number of entries to return

        Returns:
            List of recent memory entries
        """
        pass

    @abstractmethod
    def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> int:
        """
        Set a hash field to a value.

        Args:
            name: Name of the hash
            key: Field name
            value: Field value

        Returns:
            1 if field is new, 0 if field was updated
        """
        pass

    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[str]:
        """
        Get the value of a hash field.

        Args:
            name: Name of the hash
            key: Field name

        Returns:
            Field value if it exists, None otherwise
        """
        pass

    @abstractmethod
    def hkeys(self, name: str) -> List[str]:
        """
        Get all field names in a hash.

        Args:
            name: Name of the hash

        Returns:
            List of field names
        """
        pass

    @abstractmethod
    def hdel(self, name: str, *keys: str) -> int:
        """
        Delete one or more hash fields.

        Args:
            name: Name of the hash
            *keys: Field names to delete

        Returns:
            Number of fields that were removed
        """
        pass

    @abstractmethod
    def smembers(self, name: str) -> List[str]:
        """
        Get all members of a set.

        Args:
            name: Name of the set

        Returns:
            List of set members
        """
        pass

    @abstractmethod
    def sadd(self, name: str, *values: str) -> int:
        """
        Add one or more members to a set.

        Args:
            name: Name of the set
            *values: Values to add

        Returns:
            Number of elements added to the set
        """
        pass

    @abstractmethod
    def srem(self, name: str, *values: str) -> int:
        """
        Remove one or more members from a set.

        Args:
            name: Name of the set
            *values: Values to remove

        Returns:
            Number of elements removed from the set
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """
        Get the value of a key.

        Args:
            key: Key name

        Returns:
            Value if key exists, None otherwise
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Union[str, bytes, int, float]) -> bool:
        """
        Set the value of a key.

        Args:
            key: Key name
            value: Value to set

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys that were removed
        """
        pass

    def _compute_blob_hash(self, obj: Any) -> str:
        """
        Compute SHA256 hash of an object.

        Args:
            obj: Object to hash

        Returns:
            SHA256 hash of the object
        """
        if isinstance(obj, (str, bytes)):
            content = obj.encode() if isinstance(obj, str) else obj
        else:
            content = json.dumps(obj, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()

    def _should_deduplicate_blob(self, obj: Any) -> bool:
        """
        Check if an object should be deduplicated.

        Args:
            obj: Object to check

        Returns:
            True if object should be deduplicated
        """
        if isinstance(obj, str):
            return len(obj) > self._blob_threshold
        if isinstance(obj, bytes):
            return len(obj) > self._blob_threshold
        if isinstance(obj, dict):
            # Check if any value is large enough for deduplication
            return any(
                isinstance(v, (str, bytes)) and len(v) > self._blob_threshold for v in obj.values()
            )
        return False

    def _store_blob(self, obj: Any) -> str:
        """
        Store an object in the blob store.

        Args:
            obj: Object to store

        Returns:
            Hash of the stored object
        """
        blob_hash = self._compute_blob_hash(obj)
        if blob_hash not in self._blob_store:
            self._blob_store[blob_hash] = obj
            self._blob_usage[blob_hash] = 0
        self._blob_usage[blob_hash] += 1
        return blob_hash

    def _create_blob_reference(
        self,
        blob_hash: str,
        original_keys: Optional[List[str]] = None,
    ) -> BlobReference:
        """
        Create a reference to a stored blob.

        Args:
            blob_hash: Hash of the blob
            original_keys: Original keys from the object

        Returns:
            Reference object
        """
        return {
            "_blob_ref": blob_hash,
            "_original_keys": original_keys or [],
            "_type": "blob_reference",
        }

    def _deduplicate_object(self, obj: Any) -> Any:
        """
        Deduplicate an object by storing large values in the blob store.

        Args:
            obj: Object to deduplicate

        Returns:
            Deduplicated object
        """
        if not self._should_deduplicate_blob(obj):
            return obj

        if isinstance(obj, (str, bytes)):
            blob_hash = self._store_blob(obj)
            return self._create_blob_reference(blob_hash)

        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if isinstance(value, (str, bytes)) and len(value) > self._blob_threshold:
                    blob_hash = self._store_blob(value)
                    result[key] = self._create_blob_reference(blob_hash, [key])
                else:
                    result[key] = value
            return result

        return obj
