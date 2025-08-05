"""
Unit tests for the orka.registry module.
Tests the ResourceRegistry functionality and resource management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.registry import ResourceRegistry, init_registry


class TestResourceRegistry:
    """Test the ResourceRegistry class functionality."""

    def test_resource_registry_init(self):
        """Test ResourceRegistry initialization."""
        config = {
            "test_resource": {
                "type": "custom",
                "config": {"module": "test.module", "class": "TestClass"},
            },
        }

        registry = ResourceRegistry(config)

        assert registry._config == config
        assert not registry._initialized
        assert len(registry._resources) == 0

    def test_init_registry_function(self):
        """Test init_registry function."""
        config = {
            "redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
        }

        registry = init_registry(config)

        assert isinstance(registry, ResourceRegistry)
        assert registry._config == config

    @pytest.mark.asyncio
    async def test_registry_initialization_empty_config(self):
        """Test registry initialization with empty config."""
        registry = ResourceRegistry({})

        await registry.initialize()

        assert registry._initialized
        assert len(registry._resources) == 0

    @pytest.mark.asyncio
    @patch("orka.registry.redis.from_url")
    async def test_init_redis_resource(self, mock_redis):
        """Test initializing Redis resource."""
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        config = {
            "redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
        }

        registry = ResourceRegistry(config)
        await registry.initialize()

        assert registry._initialized
        assert "redis" in registry._resources
        assert registry._resources["redis"] == mock_redis_client
        mock_redis.assert_called_once_with("redis://localhost:6379")

    @pytest.mark.asyncio
    @patch("orka.registry.AsyncOpenAI")
    async def test_init_openai_resource(self, mock_openai):
        """Test initializing OpenAI resource."""
        mock_openai_client = MagicMock()
        mock_openai.return_value = mock_openai_client

        config = {
            "openai": {
                "type": "openai",
                "config": {"api_key": "test-key"},
            },
        }

        registry = ResourceRegistry(config)
        await registry.initialize()

        assert registry._initialized
        assert "openai" in registry._resources
        assert registry._resources["openai"] == mock_openai_client
        mock_openai.assert_called_once_with(api_key="test-key")

    @pytest.mark.asyncio
    async def test_init_unknown_resource_type(self):
        """Test initializing unknown resource type."""
        config = {
            "unknown": {
                "type": "unknown_type",
                "config": {},
            },
        }

        registry = ResourceRegistry(config)

        with pytest.raises(ValueError, match="Unknown resource type: unknown_type"):
            await registry.initialize()

    @pytest.mark.asyncio
    async def test_get_resource_success(self):
        """Test successful resource retrieval."""
        mock_resource = MagicMock()

        config = {}
        registry = ResourceRegistry(config)
        registry._initialized = True
        registry._resources["test"] = mock_resource

        result = registry.get("test")

        assert result == mock_resource

    def test_get_resource_not_initialized(self):
        """Test getting resource when registry not initialized."""
        registry = ResourceRegistry({})

        with pytest.raises(RuntimeError, match="Registry not initialized"):
            registry.get("test")

    @pytest.mark.asyncio
    async def test_get_resource_not_found(self):
        """Test getting non-existent resource."""
        registry = ResourceRegistry({})
        await registry.initialize()

        with pytest.raises(KeyError, match="Resource not found: nonexistent"):
            registry.get("nonexistent")

    @pytest.mark.asyncio
    async def test_close_resources(self):
        """Test closing resources."""
        mock_resource1 = MagicMock()
        mock_close = AsyncMock()
        mock_resource1.close = mock_close

        mock_resource2 = MagicMock()
        # Only test close method for simplicity

        mock_resource3 = MagicMock()  # No close method

        registry = ResourceRegistry({})
        registry._resources = {
            "res1": mock_resource1,
            "res2": mock_resource2,
            "res3": mock_resource3,
        }

        await registry.close()

        mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        registry = ResourceRegistry({})

        await registry.initialize()
        assert registry._initialized

        # Should not raise error when called again
        await registry.initialize()
        assert registry._initialized

    def test_registry_imports(self):
        """Test that registry components can be imported."""
        from orka.registry import ResourceRegistry, init_registry

        assert ResourceRegistry is not None
        assert callable(init_registry)
