"""Unit tests for orka.registry - simplified version."""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from orka.registry import ResourceRegistry, init_registry


# Skip auto-mocking for this test since we need to control mocking manually
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestResourceRegistry:
    """Test suite for ResourceRegistry class."""

    def test_init_empty_config(self):
        """Test initialization with empty config."""
        registry = ResourceRegistry({})
        
        assert registry._resources == {}
        assert registry._config == {}
        assert registry._initialized is False

    def test_init_with_config(self):
        """Test initialization with config."""
        config = {
            "redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"}
            }
        }
        
        registry = ResourceRegistry(config)
        
        assert registry._resources == {}  # Not initialized yet
        assert registry._config == config
        assert registry._initialized is False

    def test_get_before_initialization(self):
        """Test get method before initialization raises error."""
        registry = ResourceRegistry({})
        
        with pytest.raises(RuntimeError, match="Registry not initialized"):
            registry.get("test_resource")

    @pytest.mark.asyncio
    async def test_initialize_empty_config(self):
        """Test initialize with empty config."""
        registry = ResourceRegistry({})
        
        await registry.initialize()
        
        assert registry._initialized is True
        assert registry._resources == {}

    @pytest.mark.asyncio
    async def test_get_nonexistent_resource(self):
        """Test getting nonexistent resource after initialization."""
        registry = ResourceRegistry({})
        await registry.initialize()
        
        with pytest.raises(KeyError, match="Resource not found: nonexistent"):
            registry.get("nonexistent")

    @pytest.mark.asyncio
    @patch('orka.registry.redis.from_url')
    async def test_initialize_redis_resource(self, mock_redis_from_url):
        """Test initializing Redis resource."""
        mock_redis_client = Mock()
        mock_redis_from_url.return_value = mock_redis_client
        
        config = {
            "redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"}
            }
        }
        
        registry = ResourceRegistry(config)
        await registry.initialize()
        
        assert registry._initialized is True
        assert registry.get("redis") is mock_redis_client
        mock_redis_from_url.assert_called_once_with("redis://localhost:6379")

    @pytest.mark.asyncio
    @patch('orka.registry.AsyncOpenAI')
    async def test_initialize_openai_resource(self, mock_openai_class):
        """Test initializing OpenAI resource."""
        mock_openai_client = Mock()
        mock_openai_class.return_value = mock_openai_client
        
        config = {
            "openai": {
                "type": "openai",
                "config": {"api_key": "test_key"}
            }
        }
        
        registry = ResourceRegistry(config)
        await registry.initialize()
        
        assert registry._initialized is True
        assert registry.get("openai") is mock_openai_client
        mock_openai_class.assert_called_once_with(api_key="test_key")

    @pytest.mark.asyncio
    @patch('orka.registry.HAS_SENTENCE_TRANSFORMERS', True)
    @patch('orka.registry.SentenceTransformer')
    async def test_initialize_sentence_transformer_resource(self, mock_st_class):
        """Test initializing SentenceTransformer resource."""
        mock_model = Mock()
        mock_st_class.return_value = mock_model
        
        config = {
            "embedder": {
                "type": "sentence_transformer",
                "config": {"model_name": "all-MiniLM-L6-v2"}
            }
        }
        
        registry = ResourceRegistry(config)
        await registry.initialize()
        
        assert registry._initialized is True
        assert registry.get("embedder") is mock_model
        mock_st_class.assert_called_once_with("all-MiniLM-L6-v2")

    @pytest.mark.asyncio
    @patch('orka.registry.HAS_SENTENCE_TRANSFORMERS', False)
    async def test_sentence_transformer_not_available(self):
        """Test SentenceTransformer when not available."""
        config = {
            "embedder": {
                "type": "sentence_transformer",
                "config": {"model_name": "test-model"}
            }
        }
        
        registry = ResourceRegistry(config)
        
        with pytest.raises(ImportError, match="sentence_transformers is required"):
            await registry.initialize()

    @pytest.mark.asyncio
    @patch('orka.registry.importlib.import_module')
    async def test_initialize_custom_resource(self, mock_import):
        """Test initializing custom resource."""
        mock_module = Mock()
        mock_class = Mock()
        mock_instance = Mock()
        mock_class.return_value = mock_instance
        mock_module.CustomClass = mock_class
        mock_import.return_value = mock_module
        
        config = {
            "custom": {
                "type": "custom",
                "config": {
                    "module": "custom.module",
                    "class": "CustomClass",
                    "init_args": {"arg1": "value1"}
                }
            }
        }
        
        registry = ResourceRegistry(config)
        await registry.initialize()
        
        assert registry._initialized is True
        assert registry.get("custom") is mock_instance
        mock_import.assert_called_once_with("custom.module")
        mock_class.assert_called_once_with(arg1="value1")

    @pytest.mark.asyncio
    async def test_initialize_unknown_resource_type(self):
        """Test initializing unknown resource type."""
        config = {
            "unknown": {
                "type": "unknown_type",
                "config": {}
            }
        }
        
        registry = ResourceRegistry(config)
        
        with pytest.raises(ValueError, match="Unknown resource type: unknown_type"):
            await registry.initialize()

    @pytest.mark.asyncio
    async def test_initialize_multiple_resources(self):
        """Test initializing multiple resources."""
        with patch('orka.registry.redis.from_url') as mock_redis, \
             patch('orka.registry.AsyncOpenAI') as mock_openai:
            
            mock_redis_client = Mock()
            mock_openai_client = Mock()
            mock_redis.return_value = mock_redis_client
            mock_openai.return_value = mock_openai_client
            
            config = {
                "redis": {
                    "type": "redis",
                    "config": {"url": "redis://localhost:6379"}
                },
                "openai": {
                    "type": "openai",
                    "config": {"api_key": "test_key"}
                }
            }
            
            registry = ResourceRegistry(config)
            await registry.initialize()
            
            assert registry._initialized is True
            assert registry.get("redis") is mock_redis_client
            assert registry.get("openai") is mock_openai_client

    @pytest.mark.asyncio
    async def test_initialize_twice(self):
        """Test that initialize can be called multiple times safely."""
        registry = ResourceRegistry({})
        
        await registry.initialize()
        assert registry._initialized is True
        
        # Should not raise error
        await registry.initialize()
        assert registry._initialized is True

    @pytest.mark.asyncio
    async def test_close_resources(self):
        """Test closing resources."""
        mock_resource1 = Mock()
        mock_resource1.close = AsyncMock()
        
        mock_resource2 = Mock()  # No close method
        
        registry = ResourceRegistry({})
        registry._resources = {
            "resource1": mock_resource1,
            "resource2": mock_resource2
        }
        registry._initialized = True
        
        # Should not raise any exceptions
        await registry.close()
        
        # Verify close was called on resource1
        mock_resource1.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_error(self):
        """Test closing resources when one raises an error."""
        mock_resource1 = Mock()
        mock_resource1.close = AsyncMock(side_effect=Exception("Close error"))
        
        mock_resource2 = Mock()
        mock_resource2.close = AsyncMock()
        
        registry = ResourceRegistry({})
        registry._resources = {
            "resource1": mock_resource1,
            "resource2": mock_resource2
        }
        registry._initialized = True
        
        # Should not raise error, just log it
        await registry.close()
        
        mock_resource1.close.assert_called_once()
        mock_resource2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_aexit(self):
        """Test closing resources with __aexit__ method."""
        mock_resource = Mock()
        mock_resource.__aexit__ = AsyncMock()
        # Remove close method so __aexit__ is used
        delattr(mock_resource, 'close') if hasattr(mock_resource, 'close') else None
        
        registry = ResourceRegistry({})
        registry._resources = {"resource": mock_resource}
        registry._initialized = True
        
        await registry.close()
        
        # Verify __aexit__ was called
        mock_resource.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_close_no_cleanup_method(self):
        """Test closing resources without close or __aexit__."""
        mock_resource = Mock(spec=[])  # No methods at all
        
        registry = ResourceRegistry({})
        registry._resources = {"resource": mock_resource}
        registry._initialized = True
        
        # Should complete without error
        await registry.close()


class TestInitRegistry:
    """Test suite for init_registry function."""

    def test_init_registry_empty_config(self):
        """Test init_registry with empty config."""
        config = {}
        
        registry = init_registry(config)
        
        assert isinstance(registry, ResourceRegistry)
        assert registry._config == config
        assert registry._initialized is False

    def test_init_registry_with_config(self):
        """Test init_registry with resource config."""
        config = {
            "redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"}
            }
        }
        
        registry = init_registry(config)
        
        assert isinstance(registry, ResourceRegistry)
        assert registry._config == config
        assert registry._initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
