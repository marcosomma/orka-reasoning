"""
Schema management for OrKa memory entries.
Provides Avro and Protobuf serialization with Schema Registry integration.
"""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

# Always import SerializationContext for type hints
if TYPE_CHECKING:
    from confluent_kafka.serialization import MessageField, SerializationContext

try:
    import avro.io
    import avro.schema
    from confluent_kafka.schema_registry import SchemaRegistryClient
    from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
    from confluent_kafka.serialization import MessageField, SerializationContext

    AVRO_AVAILABLE = True
except ImportError:
    AVRO_AVAILABLE = False
    logging.warning(
        "Avro dependencies not available. Install with: pip install confluent-kafka[avro]",
    )

try:
    import google.protobuf
    from confluent_kafka.schema_registry.protobuf import (
        ProtobufDeserializer,
        ProtobufSerializer,
    )

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    logging.warning(
        "Protobuf dependencies not available. Install with: pip install confluent-kafka[protobuf]",
    )

logger = logging.getLogger(__name__)


class SchemaFormat(Enum):
    AVRO = "avro"
    PROTOBUF = "protobuf"
    JSON = "json"  # Fallback for development


@dataclass
class SchemaConfig:
    registry_url: str | None
    format: SchemaFormat = SchemaFormat.AVRO
    schemas_dir: str = "orka/schemas"
    subject_name_strategy: str = (
        "TopicNameStrategy"  # TopicNameStrategy, RecordNameStrategy, TopicRecordNameStrategy
    )


class SchemaManager:
    """Manages schema serialization/deserialization for OrKa memory entries."""

    def __init__(self, config: SchemaConfig):
        self.config = config
        self.registry_client = None
        self.serializers: dict[str, Any] = {}
        self.deserializers: dict[str, Any] = {}
        self.schema_cache: dict[str, str] = {}  # Cache for loaded schemas

        if config.format != SchemaFormat.JSON:
            self._init_schema_registry()

    def _init_schema_registry(self):
        """Initialize connection to Schema Registry."""
        if not AVRO_AVAILABLE and not PROTOBUF_AVAILABLE:
            raise RuntimeError(
                "Neither Avro nor Protobuf dependencies are available. Please install: pip install orka-reasoning[schema]",
            )

        try:
            # Import here to avoid issues when dependencies aren't available
            from confluent_kafka.schema_registry import SchemaRegistryClient

            self.registry_client = SchemaRegistryClient(
                {"url": self.config.registry_url},
            )
            logger.info(f"Connected to Schema Registry at {self.config.registry_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Schema Registry: {e}")
            raise

    def _load_avro_schema(self, schema_name: str) -> str:
        """Load Avro schema from file."""
        if schema_name in self.schema_cache:
            return self.schema_cache[schema_name]

        schema_path = os.path.join(
            self.config.schemas_dir,
            "avro",
            f"{schema_name}.avsc",
        )
        try:
            with open(schema_path) as f:
                schema_str = f.read()
                self.schema_cache[schema_name] = schema_str
                return schema_str
        except FileNotFoundError:
            raise FileNotFoundError(f"Avro schema not found: {schema_path}")

    def _load_protobuf_schema(self, schema_name: str) -> str:
        """Load Protobuf schema from file."""
        if schema_name in self.schema_cache:
            return self.schema_cache[schema_name]

        schema_path = os.path.join(
            self.config.schemas_dir,
            "protobuf",
            f"{schema_name}.proto",
        )
        try:
            with open(schema_path) as f:
                schema_str = f.read()
                self.schema_cache[schema_name] = schema_str
                return schema_str
        except FileNotFoundError:
            raise FileNotFoundError(f"Protobuf schema not found: {schema_path}")

    def get_serializer(self, topic: str, schema_name: str = "memory_entry") -> Any:
        """Get serializer for a topic."""
        cache_key = f"{topic}_{schema_name}_serializer"

        if cache_key in self.serializers:
            return self.serializers[cache_key]

        if self.config.format == SchemaFormat.AVRO:
            if not AVRO_AVAILABLE:
                raise RuntimeError("Avro dependencies not available")

            schema_str = self._load_avro_schema(schema_name)
            from confluent_kafka.schema_registry.avro import AvroSerializer

            serializer = AvroSerializer(
                self.registry_client,
                schema_str,
                self._memory_to_dict,
            )

        elif self.config.format == SchemaFormat.PROTOBUF:
            if not PROTOBUF_AVAILABLE:
                raise RuntimeError("Protobuf dependencies not available")

            # For Protobuf, we'd need the compiled proto class
            # This is a placeholder - you'd import your generated proto classes
            raise NotImplementedError("Protobuf serializer not fully implemented yet")

        else:  # JSON fallback
            serializer = self._json_serializer

        self.serializers[cache_key] = serializer
        return serializer

    def get_deserializer(self, topic: str, schema_name: str = "memory_entry") -> Any:
        """Get deserializer for a topic."""
        cache_key = f"{topic}_{schema_name}_deserializer"

        if cache_key in self.deserializers:
            return self.deserializers[cache_key]

        if self.config.format == SchemaFormat.AVRO:
            if not AVRO_AVAILABLE:
                raise RuntimeError("Avro dependencies not available")

            schema_str = self._load_avro_schema(schema_name)
            from confluent_kafka.schema_registry.avro import AvroDeserializer

            deserializer = AvroDeserializer(
                self.registry_client,
                schema_str,
                self._dict_to_memory,
            )

        elif self.config.format == SchemaFormat.PROTOBUF:
            if not PROTOBUF_AVAILABLE:
                raise RuntimeError("Protobuf dependencies not available")

            raise NotImplementedError("Protobuf deserializer not fully implemented yet")

        else:  # JSON fallback
            deserializer = self._json_deserializer

        self.deserializers[cache_key] = deserializer
        return deserializer

    def _memory_to_dict(self, obj: dict[str, Any], ctx: "SerializationContext") -> dict[str, Any]:
        """Convert memory object to dict for serialization."""
        # Ensure metadata field exists with default values
        if "metadata" not in obj:
            obj["metadata"] = {
                "source": "",
                "timestamp": "",
                "category": "",
                "tags": [],
                "confidence": 0.0,  # Default confidence score
                "reason": "",
                "fact": "",
                "agent_id": "",
                "query": "",
                "vector_embedding": [],
            }
        return obj

    def _dict_to_memory(self, obj: dict[str, Any], ctx: "SerializationContext") -> dict[str, Any]:
        """Convert dict to memory object after deserialization."""
        return obj

    def _json_serializer(
        self,
        obj: dict[str, Any],
        ctx: "SerializationContext",
    ) -> bytes:
        """Fallback JSON serializer."""
        return json.dumps(obj).encode("utf-8")

    def _json_deserializer(
        self,
        data: bytes,
        ctx: "SerializationContext",
    ) -> dict[str, Any]:
        """Fallback JSON deserializer."""
        result: dict[str, Any] = json.loads(data.decode("utf-8"))
        return result

    def _check_registry(self) -> None:
        """Check if registry client is initialized."""
        if self.registry_client is None:
            logger.error("Schema Registry not initialized")
            raise RuntimeError("Schema Registry not initialized")

    def register_schema(self, subject: str, schema_name: str) -> int:
        """Register a schema with the Schema Registry."""
        self._check_registry()
        registry = self.registry_client
        assert registry is not None  # Help mypy understand registry can't be None

        try:  # type: ignore[unreachable]
            if self.config.format == SchemaFormat.AVRO:
                schema_str = self._load_avro_schema(schema_name)
                from confluent_kafka.schema_registry import Schema

                schema = Schema(schema_str, schema_type="AVRO")
            elif self.config.format == SchemaFormat.PROTOBUF:
                schema_str = self._load_protobuf_schema(schema_name)
                from confluent_kafka.schema_registry import Schema

                schema = Schema(schema_str, schema_type="PROTOBUF")
            else:
                raise ValueError("Cannot register JSON schemas")

            schema_id = registry.register_schema(subject, schema)
            logger.info(
                f"Registered schema {schema_name} for subject {subject} with ID {schema_id}"
            )
            return schema_id
        except Exception as e:
            logger.error(f"Failed to register schema: {e}")
            raise


def create_schema_manager(
    registry_url: str | None = None,
    format: SchemaFormat = SchemaFormat.AVRO,
) -> SchemaManager:
    """Create a schema manager with configuration from environment or parameters."""
    registry_url = registry_url or os.getenv(
        "KAFKA_SCHEMA_REGISTRY_URL",
        "http://localhost:8081",
    )

    config = SchemaConfig(registry_url=registry_url, format=format)
    return SchemaManager(config)


# Example usage and migration helper
def migrate_from_json():
    """
    Example of how to migrate existing JSON-based Kafka messages to schema-based.
    """
    logger.info(
        """
    Migration Steps:
    
    1. Install dependencies:
       pip install orka-reasoning[schema]  # Includes Avro and Protobuf support
    
    2. Update your Kafka producer:
       schema_manager = create_schema_manager()
       serializer = schema_manager.get_serializer('orka-memory-topic')
       
       # In your producer code:
       producer.produce(
           topic='orka-memory-topic',
           value=serializer(memory_object, SerializationContext('orka-memory-topic', MessageField.VALUE))
       )
    
    3. Update your Kafka consumer:
       deserializer = schema_manager.get_deserializer('orka-memory-topic')
       
       # In your consumer code:
       memory_object = deserializer(message.value(), SerializationContext('orka-memory-topic', MessageField.VALUE))
    
    4. Register schemas:
       schema_manager.register_schema('orka-memory-topic-value', 'memory_entry')
    """
    )


if __name__ == "__main__":
    # Demo the schema management
    migrate_from_json()
