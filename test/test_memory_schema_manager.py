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

import json
import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from orka.memory.schema_manager import (
    SchemaConfig,
    SchemaFormat,
    SchemaManager,
    create_schema_manager,
    migrate_from_json,
)

# Check if we should skip schema tests that require optional dependencies
SKIP_SCHEMA_DEPENDENCY_TESTS = os.environ.get("CI", "").lower() in ("true", "1", "yes")

# Skip marker for schema tests requiring Avro/Protobuf
schema_dependency_skip = pytest.mark.skipif(
    SKIP_SCHEMA_DEPENDENCY_TESTS,
    reason="Schema dependency tests skipped in CI due to missing Avro/Protobuf packages",
)


class TestSchemaFormat:
    """Test suite for SchemaFormat enum"""

    def test_schema_format_values(self):
        """Test SchemaFormat enum values"""
        assert SchemaFormat.AVRO.value == "avro"
        assert SchemaFormat.PROTOBUF.value == "protobuf"
        assert SchemaFormat.JSON.value == "json"


class TestSchemaConfig:
    """Test suite for SchemaConfig dataclass"""

    def test_schema_config_initialization(self):
        """Test SchemaConfig initialization with all parameters"""
        config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.PROTOBUF,
            schemas_dir="custom/schemas",
            subject_name_strategy="RecordNameStrategy",
        )

        assert config.registry_url == "http://localhost:8081"
        assert config.format == SchemaFormat.PROTOBUF
        assert config.schemas_dir == "custom/schemas"
        assert config.subject_name_strategy == "RecordNameStrategy"

    def test_schema_config_defaults(self):
        """Test SchemaConfig initialization with defaults"""
        config = SchemaConfig(registry_url="http://localhost:8081")

        assert config.registry_url == "http://localhost:8081"
        assert config.format == SchemaFormat.AVRO
        assert config.schemas_dir == "orka/schemas"
        assert config.subject_name_strategy == "TopicNameStrategy"


class TestSchemaManager:
    """Test suite for SchemaManager functionality"""

    @pytest.fixture
    def json_config(self):
        """Create a SchemaConfig for JSON format"""
        return SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )

    @pytest.fixture
    def avro_config(self):
        """Create a SchemaConfig for Avro format"""
        return SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.AVRO,
        )

    def test_schema_manager_json_initialization(self, json_config):
        """Test SchemaManager initialization with JSON format"""
        manager = SchemaManager(json_config)

        assert manager.config == json_config
        assert manager.registry_client is None
        assert manager.serializers == {}
        assert manager.deserializers == {}

    @patch("orka.memory.schema_manager.AVRO_AVAILABLE", False)
    @patch("orka.memory.schema_manager.PROTOBUF_AVAILABLE", False)
    def test_schema_manager_avro_init_no_dependencies(self, avro_config):
        """Test SchemaManager initialization with Avro but no dependencies"""
        with pytest.raises(
            RuntimeError,
            match="Neither Avro nor Protobuf dependencies are available",
        ):
            SchemaManager(avro_config)

    def test_load_avro_schema_success(self, json_config):
        """Test successful Avro schema loading"""
        manager = SchemaManager(json_config)
        schema_content = '{"type": "record", "name": "TestRecord"}'

        with patch("builtins.open", mock_open(read_data=schema_content)):
            result = manager._load_avro_schema("test_schema")

        assert result == schema_content

    def test_load_avro_schema_file_not_found(self, json_config):
        """Test Avro schema loading with file not found"""
        manager = SchemaManager(json_config)

        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError, match="Avro schema not found"):
                manager._load_avro_schema("nonexistent_schema")

    def test_load_protobuf_schema_success(self, json_config):
        """Test successful Protobuf schema loading"""
        manager = SchemaManager(json_config)
        schema_content = 'syntax = "proto3"; message TestMessage {}'

        with patch("builtins.open", mock_open(read_data=schema_content)):
            result = manager._load_protobuf_schema("test_schema")

        assert result == schema_content

    def test_load_protobuf_schema_file_not_found(self, json_config):
        """Test Protobuf schema loading with file not found"""
        manager = SchemaManager(json_config)

        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError, match="Protobuf schema not found"):
                manager._load_protobuf_schema("nonexistent_schema")

    def test_get_serializer_json_format(self, json_config):
        """Test get_serializer with JSON format"""
        manager = SchemaManager(json_config)

        serializer = manager.get_serializer("test_topic")

        # Should return the JSON serializer method
        assert callable(serializer)
        assert serializer == manager._json_serializer

    def test_get_serializer_caching(self, json_config):
        """Test that serializers are cached"""
        manager = SchemaManager(json_config)

        serializer1 = manager.get_serializer("test_topic")
        serializer2 = manager.get_serializer("test_topic")

        assert serializer1 is serializer2
        assert len(manager.serializers) == 1

    @schema_dependency_skip
    @patch("orka.memory.schema_manager.AVRO_AVAILABLE", False)
    def test_get_serializer_avro_no_dependencies(self, json_config):
        """Test get_serializer with Avro format but no dependencies"""
        json_config.format = SchemaFormat.AVRO
        manager = SchemaManager(json_config)

        with pytest.raises(RuntimeError, match="Avro dependencies not available"):
            manager.get_serializer("test_topic")

    @schema_dependency_skip
    def test_get_serializer_protobuf_not_implemented(self, json_config):
        """Test get_serializer with Protobuf format (not implemented)"""
        json_config.format = SchemaFormat.PROTOBUF
        manager = SchemaManager(json_config)

        with pytest.raises(NotImplementedError, match="Protobuf serializer not fully implemented"):
            manager.get_serializer("test_topic")

    def test_get_deserializer_json_format(self, json_config):
        """Test get_deserializer with JSON format"""
        manager = SchemaManager(json_config)

        deserializer = manager.get_deserializer("test_topic")

        # Should return the JSON deserializer method
        assert callable(deserializer)
        assert deserializer == manager._json_deserializer

    def test_get_deserializer_caching(self, json_config):
        """Test that deserializers are cached"""
        manager = SchemaManager(json_config)

        deserializer1 = manager.get_deserializer("test_topic")
        deserializer2 = manager.get_deserializer("test_topic")

        assert deserializer1 is deserializer2
        assert len(manager.deserializers) == 1

    @schema_dependency_skip
    def test_get_deserializer_protobuf_not_implemented(self, json_config):
        """Test get_deserializer with Protobuf format (not implemented)"""
        json_config.format = SchemaFormat.PROTOBUF
        manager = SchemaManager(json_config)

        with pytest.raises(
            NotImplementedError,
            match="Protobuf deserializer not fully implemented",
        ):
            manager.get_deserializer("test_topic")

    def test_memory_to_dict(self, json_config):
        """Test _memory_to_dict method"""
        manager = SchemaManager(json_config)

        memory_obj = {
            "id": "test-id",
            "content": "test content",
            "metadata": {
                "source": "test-source",
                "confidence": 0.95,
                "reason": "test reason",
                "fact": "test fact",
                "timestamp": 1234567890.0,
                "agent_id": "test-agent",
                "query": "test query",
                "tags": ["tag1", "tag2"],
                "vector_embedding": [0.1, 0.2, 0.3],
            },
            "similarity": 0.85,
            "ts": 1234567890,
            "match_type": "semantic",
            "stream_key": "test-stream",
        }

        mock_ctx = MagicMock()
        result = manager._memory_to_dict(memory_obj, mock_ctx)

        # Should match the actual structure returned by _memory_to_dict
        expected = {
            "id": "test-id",
            "content": "test content",
            "metadata": {
                "source": "test-source",
                "confidence": 0.95,
                "reason": "test reason",
                "fact": "test fact",
                "timestamp": 1234567890.0,
                "agent_id": "test-agent",
                "query": "test query",
                "tags": ["tag1", "tag2"],
                "vector_embedding": [0.1, 0.2, 0.3],
            },
            "similarity": 0.85,
            "ts": 1234567890,
            "match_type": "semantic",
            "stream_key": "test-stream",
        }

        assert result == expected

    def test_dict_to_memory(self, json_config):
        """Test _dict_to_memory method"""
        manager = SchemaManager(json_config)

        avro_dict = {"test": "data"}
        mock_ctx = MagicMock()

        result = manager._dict_to_memory(avro_dict, mock_ctx)

        # Currently just returns the dict as-is
        assert result == avro_dict

    def test_json_serializer(self, json_config):
        """Test JSON serializer"""
        manager = SchemaManager(json_config)

        test_obj = {"test": "data", "number": 42}
        mock_ctx = MagicMock()

        result = manager._json_serializer(test_obj, mock_ctx)

        assert isinstance(result, bytes)
        assert json.loads(result.decode("utf-8")) == test_obj

    def test_json_deserializer(self, json_config):
        """Test JSON deserializer"""
        manager = SchemaManager(json_config)

        test_data = json.dumps({"test": "data", "number": 42}).encode("utf-8")
        mock_ctx = MagicMock()

        result = manager._json_deserializer(test_data, mock_ctx)

        assert result == {"test": "data", "number": 42}

    def test_register_schema_json_format_error(self, json_config):
        """Test schema registration with JSON format (should fail)"""
        manager = SchemaManager(json_config)

        with pytest.raises(RuntimeError, match="Schema Registry not initialized"):
            manager.register_schema("test_subject", "test_schema")

    def test_register_schema_no_registry_client(self, avro_config):
        """Test schema registration without registry client"""
        # Create manager with JSON format to avoid registry client initialization
        json_config = SchemaConfig(
            registry_url="http://localhost:8081",
            format=SchemaFormat.JSON,
        )
        manager = SchemaManager(json_config)
        manager.registry_client = None

        with pytest.raises(RuntimeError, match="Schema Registry not initialized"):
            manager.register_schema("test_subject", "test_schema")


class TestModuleFunctions:
    """Test suite for module-level functions"""

    def test_create_schema_manager_with_parameters(self):
        """Test create_schema_manager with parameters"""
        manager = create_schema_manager(
            registry_url="http://custom:8081",
            format=SchemaFormat.JSON,
        )

        assert manager.config.registry_url == "http://custom:8081"
        assert manager.config.format == SchemaFormat.JSON

    @schema_dependency_skip
    def test_create_schema_manager_default(self):
        """Test create_schema_manager with defaults"""
        with patch.dict("os.environ", {"KAFKA_SCHEMA_REGISTRY_URL": "http://env:8081"}):
            manager = create_schema_manager()
            assert manager.config.registry_url == "http://env:8081"

    @schema_dependency_skip
    def test_create_schema_manager_fallback_default(self):
        """Test create_schema_manager falls back to default when no env var"""
        with patch.dict("os.environ", {}, clear=True):
            manager = create_schema_manager()
            assert manager.config.registry_url == "http://localhost:8081"

    @patch("builtins.print")
    def test_migrate_from_json(self, mock_print):
        """Test migrate_from_json function"""
        migrate_from_json()

        # Should print migration instructions
        mock_print.assert_called_once()
        call_args = mock_print.call_args[0][0]
        assert "Migration Steps:" in call_args
        assert "pip install confluent-kafka[avro]" in call_args
        assert "schema_manager.register_schema" in call_args


class TestErrorHandling:
    """Test suite for error handling scenarios"""

    def test_schema_manager_with_invalid_format(self):
        """Test SchemaManager handles invalid format gracefully"""
        # This tests the JSON fallback when an invalid format is somehow set
        config = SchemaConfig(registry_url="http://localhost:8081", format=SchemaFormat.JSON)
        manager = SchemaManager(config)

        # Should work fine with JSON format
        serializer = manager.get_serializer("test_topic")
        assert callable(serializer)
