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
Tests for Resource Registry
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.registry import HAS_SENTENCE_TRANSFORMERS, ResourceRegistry, init_registry


class TestResourceRegistry:
    """Test cases for ResourceRegistry"""

    @pytest.fixture
    def basic_config(self):
        """Basic configuration for testing"""
        return {
            "test_redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
            "test_openai": {"type": "openai", "config": {"api_key": "test-key"}},
        }

    def test_init(self, basic_config):
        """Test ResourceRegistry initialization"""
        registry = ResourceRegistry(basic_config)
        assert registry._config == basic_config
        assert registry._resources == {}
        assert not registry._initialized

    @pytest.mark.asyncio
    async def test_initialize_redis_resource(self):
        """Test initializing Redis resource"""
        config = {
            "redis_client": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            }
        }

        with patch("orka.registry.redis.from_url") as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance

            registry = ResourceRegistry(config)
            await registry.initialize()

            assert registry._initialized
            assert "redis_client" in registry._resources
            assert registry._resources["redis_client"] == mock_redis_instance
            mock_redis.assert_called_once_with("redis://localhost:6379")

    @pytest.mark.asyncio
    async def test_initialize_openai_resource(self):
        """Test initializing OpenAI resource"""
        config = {
            "openai_client": {"type": "openai", "config": {"api_key": "test-api-key"}}
        }

        with patch("orka.registry.AsyncOpenAI") as mock_openai:
            mock_openai_instance = MagicMock()
            mock_openai.return_value = mock_openai_instance

            registry = ResourceRegistry(config)
            await registry.initialize()

            assert registry._initialized
            assert "openai_client" in registry._resources
            assert registry._resources["openai_client"] == mock_openai_instance
            mock_openai.assert_called_once_with(api_key="test-api-key")

    @pytest.mark.asyncio
    async def test_initialize_sentence_transformer_resource_available(self):
        """Test initializing SentenceTransformer resource when available"""
        config = {
            "embedder": {
                "type": "sentence_transformer",
                "config": {"model_name": "all-MiniLM-L6-v2"},
            }
        }

        with patch("orka.registry.HAS_SENTENCE_TRANSFORMERS", True):
            with patch("orka.registry.SentenceTransformer") as mock_st:
                mock_st_instance = MagicMock()
                mock_st.return_value = mock_st_instance

                registry = ResourceRegistry(config)
                await registry.initialize()

                assert registry._initialized
                assert "embedder" in registry._resources
                assert registry._resources["embedder"] == mock_st_instance
                mock_st.assert_called_once_with("all-MiniLM-L6-v2")

    @pytest.mark.asyncio
    async def test_initialize_sentence_transformer_resource_unavailable(self):
        """Test initializing SentenceTransformer resource when unavailable"""
        config = {
            "embedder": {
                "type": "sentence_transformer",
                "config": {"model_name": "all-MiniLM-L6-v2"},
            }
        }

        with patch("orka.registry.HAS_SENTENCE_TRANSFORMERS", False):
            registry = ResourceRegistry(config)

            with pytest.raises(ImportError, match="sentence_transformers is required"):
                await registry.initialize()

    @pytest.mark.asyncio
    async def test_initialize_custom_resource(self):
        """Test initializing custom resource"""
        config = {
            "custom_tool": {
                "type": "custom",
                "config": {
                    "module": "test.mock_module",
                    "class": "MockClass",
                    "init_args": {"param1": "value1", "param2": "value2"},
                },
            }
        }

        # Create a mock module and class
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_module.MockClass = mock_class

        with patch("orka.registry.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            registry = ResourceRegistry(config)
            await registry.initialize()

            assert registry._initialized
            assert "custom_tool" in registry._resources
            assert registry._resources["custom_tool"] == mock_instance
            mock_import.assert_called_once_with("test.mock_module")
            mock_class.assert_called_once_with(param1="value1", param2="value2")

    @pytest.mark.asyncio
    async def test_initialize_custom_resource_no_init_args(self):
        """Test initializing custom resource without init_args"""
        config = {
            "custom_tool": {
                "type": "custom",
                "config": {"module": "test.mock_module", "class": "MockClass"},
            }
        }

        # Create a mock module and class
        mock_module = MagicMock()
        mock_class = MagicMock()
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_module.MockClass = mock_class

        with patch("orka.registry.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            registry = ResourceRegistry(config)
            await registry.initialize()

            assert registry._initialized
            assert "custom_tool" in registry._resources
            mock_class.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_initialize_unknown_resource_type(self):
        """Test error handling for unknown resource type"""
        config = {"unknown": {"type": "unknown_type", "config": {}}}

        registry = ResourceRegistry(config)

        with pytest.raises(ValueError, match="Unknown resource type: unknown_type"):
            await registry.initialize()

    @pytest.mark.asyncio
    async def test_initialize_resource_init_failure(self):
        """Test error handling when resource initialization fails"""
        config = {
            "failing_redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            }
        }

        with patch("orka.registry.redis.from_url") as mock_redis:
            mock_redis.side_effect = Exception("Connection failed")

            registry = ResourceRegistry(config)

            with pytest.raises(Exception, match="Connection failed"):
                await registry.initialize()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, basic_config):
        """Test that initialize() is idempotent"""
        with patch("orka.registry.redis.from_url") as mock_redis:
            with patch("orka.registry.AsyncOpenAI") as mock_openai:
                registry = ResourceRegistry(basic_config)

                # First initialization
                await registry.initialize()
                assert registry._initialized

                # Second initialization should not re-initialize
                await registry.initialize()

                # Should only be called once each
                mock_redis.assert_called_once()
                mock_openai.assert_called_once()

    def test_get_resource_success(self, basic_config):
        """Test successfully getting a resource"""
        registry = ResourceRegistry(basic_config)
        registry._initialized = True
        mock_resource = MagicMock()
        registry._resources["test_resource"] = mock_resource

        result = registry.get("test_resource")
        assert result == mock_resource

    def test_get_resource_not_initialized(self, basic_config):
        """Test error when getting resource from non-initialized registry"""
        registry = ResourceRegistry(basic_config)

        with pytest.raises(RuntimeError, match="Registry not initialized"):
            registry.get("test_resource")

    def test_get_resource_not_found(self, basic_config):
        """Test error when getting non-existent resource"""
        registry = ResourceRegistry(basic_config)
        registry._initialized = True

        with pytest.raises(KeyError, match="Resource not found: nonexistent"):
            registry.get("nonexistent")

    @pytest.mark.asyncio
    async def test_close_resources_with_close_method(self):
        """Test closing resources that have close() method"""
        registry = ResourceRegistry({})
        registry._initialized = True

        # Mock resource with close method
        mock_resource = AsyncMock()
        mock_resource.close = AsyncMock()
        registry._resources["test_resource"] = mock_resource

        await registry.close()
        mock_resource.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_resources_with_aexit_method(self):
        """Test closing resources that have __aexit__ method"""
        registry = ResourceRegistry({})
        registry._initialized = True

        # Mock resource with __aexit__ method but no close method
        mock_resource = MagicMock()
        mock_resource.__aexit__ = AsyncMock()
        # Make sure hasattr(resource, "close") returns False
        del mock_resource.close  # Remove close attribute if it exists
        registry._resources["test_resource"] = mock_resource

        await registry.close()
        mock_resource.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_close_resources_with_no_close_method(self):
        """Test closing resources that have no close method"""
        registry = ResourceRegistry({})
        registry._initialized = True

        # Mock resource with no close method
        mock_resource = MagicMock()
        registry._resources["test_resource"] = mock_resource

        # Should not raise any error
        await registry.close()

    @pytest.mark.asyncio
    async def test_close_resources_error_handling(self):
        """Test error handling during resource closing"""
        registry = ResourceRegistry({})
        registry._initialized = True

        # Mock resource that raises error on close
        mock_resource = AsyncMock()
        mock_resource.close = AsyncMock(side_effect=Exception("Close failed"))
        registry._resources["failing_resource"] = mock_resource

        # Should not raise error but log it
        await registry.close()
        mock_resource.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_resources_initialization(self):
        """Test initializing multiple different resource types"""
        config = {
            "redis_client": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
            "openai_client": {"type": "openai", "config": {"api_key": "test-key"}},
        }

        with patch("orka.registry.redis.from_url") as mock_redis:
            with patch("orka.registry.AsyncOpenAI") as mock_openai:
                mock_redis_instance = MagicMock()
                mock_openai_instance = MagicMock()
                mock_redis.return_value = mock_redis_instance
                mock_openai.return_value = mock_openai_instance

                registry = ResourceRegistry(config)
                await registry.initialize()

                assert registry._initialized
                assert len(registry._resources) == 2
                assert registry.get("redis_client") == mock_redis_instance
                assert registry.get("openai_client") == mock_openai_instance


class TestInitRegistry:
    """Test cases for init_registry function"""

    def test_init_registry(self):
        """Test init_registry function"""
        config = {
            "test_resource": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            }
        }

        registry = init_registry(config)

        assert isinstance(registry, ResourceRegistry)
        assert registry._config == config
        assert not registry._initialized


class TestHasSentenceTransformers:
    """Test cases for HAS_SENTENCE_TRANSFORMERS flag"""

    def test_has_sentence_transformers_flag(self):
        """Test that HAS_SENTENCE_TRANSFORMERS flag is boolean"""
        assert isinstance(HAS_SENTENCE_TRANSFORMERS, bool)
