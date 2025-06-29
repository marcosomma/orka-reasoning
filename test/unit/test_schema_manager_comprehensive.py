"""Tests for orka.memory.schema_manager module."""

import os
from unittest.mock import Mock, mock_open, patch

import pytest

# Import the components we're testing
from orka.memory.schema_manager import (
    SchemaConfig,
    SchemaFormat,
    SchemaManager,
    create_schema_manager,
    migrate_from_json,
)


class TestSchemaFormat:
    """Test the SchemaFormat enum."""

    def test_schema_format_values(self):
        """Test SchemaFormat enum values."""
        assert SchemaFormat.AVRO.value == "avro"
        assert SchemaFormat.PROTOBUF.value == "protobuf"
        assert SchemaFormat.JSON.value == "json"


class TestSchemaConfig:
    """Test the SchemaConfig dataclass."""

    def test_schema_config_default_values(self):
        """Test SchemaConfig initialization with default values."""
        config = SchemaConfig(registry_url="http://localhost:8081")

        assert config.registry_url == "http://localhost:8081"
        assert config.format == SchemaFormat.AVRO
        assert config.schemas_dir == "orka/schemas"
        assert config.subject_name_strategy == "TopicNameStrategy"

    def test_schema_config_custom_values(self):
        """Test SchemaConfig initialization with custom values."""
        config = SchemaConfig(
            registry_url="http://custom:9092",
            format=SchemaFormat.PROTOBUF,
            schemas_dir="custom/schemas",
            subject_name_strategy="RecordNameStrategy",
        )

        assert config.registry_url == "http://custom:9092"
        assert config.format == SchemaFormat.PROTOBUF
        assert config.schemas_dir == "custom/schemas"
        assert config.subject_name_strategy == "RecordNameStrategy"


class TestSchemaManager:
    """Test the SchemaManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = SchemaConfig(registry_url="http://localhost:8081")

    def test_init_json_format(self):
        """Test SchemaManager initialization with JSON format."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        assert manager.config == config
        assert manager.registry_client is None
        assert manager.serializers == {}
        assert manager.deserializers == {}

    @patch("orka.memory.schema_manager.AVRO_AVAILABLE", False)
    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", False)
    def test_init_schema_registry_no_dependencies(self):
        """Test Schema Registry initialization without dependencies."""
        with pytest.raises(
            RuntimeError,
            match="Neither Avro nor Protobuf dependencies are available",
        ):
            SchemaManager(self.config)

    @patch("builtins.open", mock_open(read_data='{"type": "record", "name": "TestSchema"}'))
    def test_load_avro_schema_success(self):
        """Test successful Avro schema loading."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,  # Use JSON to avoid registry initialization
        )
        manager = SchemaManager(config)

        result = manager._load_avro_schema("test_schema")
        assert result == '{"type": "record", "name": "TestSchema"}'

    @patch("builtins.open", mock_open(read_data='syntax = "proto3"; message TestMessage {}'))
    def test_load_protobuf_schema_success(self):
        """Test successful Protobuf schema loading."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        result = manager._load_protobuf_schema("test_schema")
        assert result == 'syntax = "proto3"; message TestMessage {}'

    def test_get_serializer_json_format(self):
        """Test get_serializer with JSON format."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        serializer = manager.get_serializer("test_topic")

        # Should return the JSON serializer function
        assert serializer == manager._json_serializer
        assert "test_topic_memory_entry_serializer" in manager.serializers

    def test_get_serializer_cached(self):
        """Test get_serializer returns cached serializer."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        # First call
        serializer1 = manager.get_serializer("test_topic")
        # Second call should return cached version
        serializer2 = manager.get_serializer("test_topic")

        assert serializer1 == serializer2

    @patch("orka.memory.schema_manager.AVRO_AVAILABLE", False)
    def test_get_serializer_avro_unavailable(self):
        """Test get_serializer with Avro format but Avro unavailable."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,  # JSON to avoid registry init
            ),
        )
        manager.config.format = SchemaFormat.AVRO  # Change after init

        with pytest.raises(RuntimeError, match="Avro dependencies not available"):
            manager.get_serializer("test_topic")

    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", False)
    def test_get_serializer_protobuf_unavailable(self):
        """Test get_serializer with Protobuf format but Protobuf unavailable."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,
            ),
        )
        manager.config.format = SchemaFormat.PROTOBUF

        with pytest.raises(RuntimeError, match="Protobuf dependencies not available"):
            manager.get_serializer("test_topic")

    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", True)
    def test_get_serializer_protobuf_not_implemented(self):
        """Test get_serializer with Protobuf format raises NotImplementedError."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,
            ),
        )
        manager.config.format = SchemaFormat.PROTOBUF

        with pytest.raises(
            NotImplementedError,
            match="Protobuf serializer not fully implemented yet",
        ):
            manager.get_serializer("test_topic")

    def test_get_deserializer_json_format(self):
        """Test get_deserializer with JSON format."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        deserializer = manager.get_deserializer("test_topic")

        assert deserializer == manager._json_deserializer
        assert "test_topic_memory_entry_deserializer" in manager.deserializers

    def test_get_deserializer_cached(self):
        """Test get_deserializer returns cached deserializer."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        deserializer1 = manager.get_deserializer("test_topic")
        deserializer2 = manager.get_deserializer("test_topic")

        assert deserializer1 == deserializer2

    @patch("orka.memory.schema_manager.AVRO_AVAILABLE", False)
    def test_get_deserializer_avro_unavailable(self):
        """Test get_deserializer with Avro format but Avro unavailable."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,
            ),
        )
        manager.config.format = SchemaFormat.AVRO

        with pytest.raises(RuntimeError, match="Avro dependencies not available"):
            manager.get_deserializer("test_topic")

    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", False)
    def test_get_deserializer_protobuf_unavailable(self):
        """Test get_deserializer with Protobuf format but Protobuf unavailable."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,
            ),
        )
        manager.config.format = SchemaFormat.PROTOBUF

        with pytest.raises(RuntimeError, match="Protobuf dependencies not available"):
            manager.get_deserializer("test_topic")

    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", True)
    def test_get_deserializer_protobuf_not_implemented(self):
        """Test get_deserializer with Protobuf format raises NotImplementedError."""
        manager = SchemaManager(
            SchemaConfig(
                registry_url="http://localhost:8081",
                format=SchemaFormat.JSON,
            ),
        )
        manager.config.format = SchemaFormat.PROTOBUF

        with pytest.raises(
            NotImplementedError,
            match="Protobuf deserializer not fully implemented yet",
        ):
            manager.get_deserializer("test_topic")

    def test_memory_to_dict(self):
        """Test _memory_to_dict conversion."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        memory_obj = {
            "id": "test_id",
            "content": "test content",
            "metadata": {
                "source": "test_source",
                "confidence": 0.95,
                "reason": "test_reason",
                "fact": "test_fact",
                "timestamp": 1234567890.0,
                "agent_id": "test_agent",
                "query": "test_query",
                "tags": ["tag1", "tag2"],
                "vector_embedding": [0.1, 0.2, 0.3],
            },
            "similarity": 0.85,
            "ts": 1234567890,
            "match_type": "semantic",
            "stream_key": "test_stream",
        }

        mock_ctx = Mock()
        result = manager._memory_to_dict(memory_obj, mock_ctx)

        assert result["id"] == "test_id"
        assert result["content"] == "test content"
        assert result["metadata"]["source"] == "test_source"
        assert result["metadata"]["confidence"] == 0.95
        assert result["similarity"] == 0.85
        assert result["ts"] == 1234567890
        assert result["match_type"] == "semantic"
        assert result["stream_key"] == "test_stream"

    def test_memory_to_dict_empty_metadata(self):
        """Test _memory_to_dict with empty metadata."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        memory_obj = {"id": "test", "content": "content"}
        mock_ctx = Mock()

        result = manager._memory_to_dict(memory_obj, mock_ctx)

        assert result["id"] == "test"
        assert result["content"] == "content"
        assert result["metadata"]["source"] == ""
        assert result["metadata"]["confidence"] == 0.0

    def test_dict_to_memory(self):
        """Test _dict_to_memory conversion."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        avro_dict = {"id": "test", "content": "content"}
        mock_ctx = Mock()

        result = manager._dict_to_memory(avro_dict, mock_ctx)
        assert result == avro_dict

    def test_json_serializer(self):
        """Test _json_serializer."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        obj = {"test": "data"}
        mock_ctx = Mock()

        result = manager._json_serializer(obj, mock_ctx)
        assert result == b'{"test": "data"}'

    def test_json_deserializer(self):
        """Test _json_deserializer."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        data = b'{"test": "data"}'
        mock_ctx = Mock()

        result = manager._json_deserializer(data, mock_ctx)
        assert result == {"test": "data"}

    def test_register_schema_no_registry_client(self):
        """Test register_schema without registry client."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)

        with pytest.raises(RuntimeError, match="Schema Registry not initialized"):
            manager.register_schema("test_subject", "test_schema")

    def test_register_schema_json_format_error(self):
        """Test register_schema with JSON format raises ValueError."""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(config)
        manager.registry_client = Mock()  # Set a mock client

        with pytest.raises(ValueError, match="Cannot register JSON schemas"):
            manager.register_schema("test_subject", "test_schema")


class TestUtilityFunctions:
    """Test utility functions."""

    @patch.dict(os.environ, {}, clear=True)
    def test_create_schema_manager_default(self):
        """Test create_schema_manager with default values."""
        manager = create_schema_manager()

        assert manager.config.registry_url == "http://localhost:8081"
        assert manager.config.format == SchemaFormat.AVRO

    @patch.dict(os.environ, {"KAFKA_SCHEMA_REGISTRY_URL": "http://env:9092"})
    def test_create_schema_manager_from_env(self):
        """Test create_schema_manager with environment variable."""
        manager = create_schema_manager()

        assert manager.config.registry_url == "http://env:9092"

    def test_create_schema_manager_custom_params(self):
        """Test create_schema_manager with custom parameters."""
        manager = create_schema_manager(
            registry_url="http://custom:8081",
            format=SchemaFormat.PROTOBUF,
        )

        assert manager.config.registry_url == "http://custom:8081"
        assert manager.config.format == SchemaFormat.PROTOBUF

    @patch("builtins.print")
    def test_migrate_from_json(self, mock_print):
        """Test migrate_from_json prints migration instructions."""
        migrate_from_json()

        # Should print migration instructions
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Migration Steps" in call_args
        assert "pip install confluent-kafka" in call_args
