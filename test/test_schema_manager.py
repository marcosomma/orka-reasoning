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
from unittest.mock import MagicMock, patch

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

    def test_schema_manager_json_initialization(self, json_config):
        """Test SchemaManager initialization with JSON format"""
        manager = SchemaManager(json_config)

        assert manager.config == json_config
        assert manager.registry_client is None
        assert manager.serializers == {}
        assert manager.deserializers == {}

    def test_get_serializer_json_format(self, json_config):
        """Test get_serializer with JSON format"""
        manager = SchemaManager(json_config)

        serializer = manager.get_serializer("test_topic")

        # Should return the JSON serializer method
        assert callable(serializer)
        assert serializer == manager._json_serializer

    def test_json_serializer(self, json_config):
        """Test _json_serializer method"""
        manager = SchemaManager(json_config)

        obj = {"test": "data"}
        mock_ctx = MagicMock()

        result = manager._json_serializer(obj, mock_ctx)

        assert isinstance(result, bytes)
        assert json.loads(result.decode()) == obj

    def test_json_deserializer(self, json_config):
        """Test _json_deserializer method"""
        manager = SchemaManager(json_config)

        data = json.dumps({"test": "data"}).encode()
        mock_ctx = MagicMock()

        result = manager._json_deserializer(data, mock_ctx)

        assert result == {"test": "data"}

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

    @schema_dependency_skip
    def test_create_schema_manager_no_registry_url(self):
        """Test create_schema_manager without registry URL"""
        with patch.dict("os.environ", {}, clear=True):
            # Should use default URL when no environment variable is set
            schema_manager = create_schema_manager()
            assert schema_manager.config.registry_url == "http://localhost:8081"
