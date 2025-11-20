"""Unit tests for orka.memory_logger."""

import os
from unittest.mock import ANY, Mock, patch

import pytest

from orka.memory_logger import MemoryLogger, apply_memory_preset_to_config, create_memory_logger

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestApplyMemoryPresetToConfig:
    """Test suite for apply_memory_preset_to_config function."""

    def test_no_preset(self):
        """Test with no preset specified."""
        config = {"key": "value"}
        result = apply_memory_preset_to_config(config, memory_preset=None, operation="read")
        
        assert result == config

    def test_no_operation(self):
        """Test with no operation specified."""
        config = {"key": "value"}
        result = apply_memory_preset_to_config(config, memory_preset="episodic", operation=None)
        
        assert result == config

    def test_both_none(self):
        """Test with both preset and operation as None."""
        config = {"key": "value"}
        result = apply_memory_preset_to_config(config, memory_preset=None, operation=None)
        
        assert result == config

    @patch("orka.memory.presets.get_operation_defaults")
    def test_with_valid_preset_and_operation(self, mock_get_defaults):
        """Test with valid preset and operation."""
        mock_get_defaults.return_value = {"similarity_threshold": 0.7, "vector_weight": 0.6}
        
        config = {"namespace": "test"}
        result = apply_memory_preset_to_config(config, memory_preset="episodic", operation="read")
        
        assert "namespace" in result
        assert result["namespace"] == "test"
        mock_get_defaults.assert_called_once_with("episodic", "read")

    @patch("orka.memory.presets.get_operation_defaults")
    def test_config_overrides_defaults(self, mock_get_defaults):
        """Test that existing config values override defaults."""
        mock_get_defaults.return_value = {"similarity_threshold": 0.7, "namespace": "default"}
        
        config = {"namespace": "custom"}
        result = apply_memory_preset_to_config(config, memory_preset="semantic", operation="write")
        
        # Existing config should not be overridden
        assert result["namespace"] == "custom"

    @patch("orka.memory.presets.get_operation_defaults", side_effect=ImportError("Module not found"))
    def test_import_error_handling(self, mock_get_defaults):
        """Test handling of ImportError for presets."""
        config = {"key": "value"}
        result = apply_memory_preset_to_config(config, memory_preset="working", operation="read")
        
        # Should return config unchanged
        assert result == config

    @patch("orka.memory.presets.get_operation_defaults", side_effect=Exception("Unexpected error"))
    def test_exception_handling(self, mock_get_defaults):
        """Test handling of general exceptions."""
        config = {"key": "value"}
        result = apply_memory_preset_to_config(config, memory_preset="procedural", operation="write")
        
        # Should return config unchanged
        assert result == config

    @patch("orka.memory.presets.get_operation_defaults")
    def test_empty_config_with_defaults(self, mock_get_defaults):
        """Test empty config gets populated with defaults."""
        mock_get_defaults.return_value = {"key1": "value1", "key2": "value2"}
        
        config = {}
        result = apply_memory_preset_to_config(config, memory_preset="sensory", operation="read")
        
        assert len(result) == 2


class TestCreateMemoryLogger:
    """Test suite for create_memory_logger factory function."""

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_default_backend_redisstack(self, mock_get_embedder, MockRedisStack):
        """Test default backend is RedisStack."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger()
        
        MockRedisStack.assert_called_once()
        assert result == mock_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_redis_backend_fallback(self, mock_get_embedder, MockRedis, MockRedisStack):
        """Test fallback to Redis when RedisStack not available."""
        MockRedisStack.side_effect = ImportError("RedisStack not available")
        mock_redis_instance = Mock()
        MockRedis.return_value = mock_redis_instance
        
        result = create_memory_logger("redis")
        
        MockRedis.assert_called_once()
        assert result == mock_redis_instance

    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    def test_force_basic_redis(self, MockRedis):
        """Test force basic Redis via environment variable."""
        mock_instance = Mock()
        MockRedis.return_value = mock_instance
        
        with patch.dict(os.environ, {"ORKA_FORCE_BASIC_REDIS": "true"}):
            result = create_memory_logger("redis")
        
        MockRedis.assert_called_once()
        assert result == mock_instance

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_stream_key(self, mock_get_embedder, MockRedisStack):
        """Test custom stream key parameter."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(stream_key="custom:stream")
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["stream_key"] == "custom:stream"

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_debug_keep_previous_outputs(self, mock_get_embedder, MockRedisStack):
        """Test debug_keep_previous_outputs parameter."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(debug_keep_previous_outputs=True)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["debug_keep_previous_outputs"] is True

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_decay_config(self, mock_get_embedder, MockRedisStack):
        """Test custom decay configuration."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        custom_decay = {
            "enabled": False,
            "default_short_term_hours": 2.0,
            "default_long_term_hours": 48.0,
        }
        
        result = create_memory_logger(decay_config=custom_decay)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["decay_config"] == custom_decay

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_memory_preset_parameter(self, mock_get_embedder, MockRedisStack):
        """Test memory preset parameter."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(memory_preset="episodic")
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["memory_preset"] == "episodic"

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_enable_hnsw_parameter(self, mock_get_embedder, MockRedisStack):
        """Test enable_hnsw parameter."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(enable_hnsw=False)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["enable_hnsw"] is False

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_vector_params(self, mock_get_embedder, MockRedisStack):
        """Test custom vector parameters."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        custom_params = {"M": 32, "ef_construction": 400}
        
        result = create_memory_logger(vector_params=custom_params)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["vector_params"] == custom_params

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_format_params(self, mock_get_embedder, MockRedisStack):
        """Test format parameters."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        format_params = {"newline_handling": "strip"}
        
        result = create_memory_logger(format_params=format_params)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["format_params"] == format_params

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_index_name(self, mock_get_embedder, MockRedisStack):
        """Test custom index name."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(index_name="custom_index")
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["index_name"] == "custom_index"

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_vector_dim(self, mock_get_embedder, MockRedisStack):
        """Test custom vector dimension."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(vector_dim=512)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["vector_dim"] == 512

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_force_recreate_index(self, mock_get_embedder, MockRedisStack):
        """Test force recreate index parameter."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(force_recreate_index=True)
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["force_recreate_index"] is True
        assert call_kwargs["vector_params"]["force_recreate"] is True

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_embedder_initialization_failure(self, mock_get_embedder, MockRedisStack):
        """Test handling of embedder initialization failure."""
        mock_get_embedder.side_effect = Exception("Embedder init failed")
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        # Should still create logger despite embedder failure
        result = create_memory_logger()
        
        MockRedisStack.assert_called_once()
        # Embedder should be None
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["embedder"] is None

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_backend_normalization(self, mock_get_embedder, MockRedisStack):
        """Test backend name normalization."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        # Test uppercase
        result = create_memory_logger("REDISSTACK")
        MockRedisStack.assert_called()
        
        # Test mixed case
        MockRedisStack.reset_mock()
        result = create_memory_logger("RedisStack")
        MockRedisStack.assert_called()

    def test_invalid_backend(self):
        """Test invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            create_memory_logger("invalid_backend")

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.memory.redis_logger.RedisMemoryLogger")
    def test_no_backends_available(self, MockRedis, MockRedisStack):
        """Test error when no backends are available."""
        MockRedisStack.side_effect = ImportError("RedisStack not available")
        MockRedis.side_effect = ImportError("Redis not available")
        
        with pytest.raises(ImportError, match="No Redis backends available"):
            create_memory_logger("redis")

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_custom_redis_url(self, mock_get_embedder, MockRedisStack):
        """Test custom Redis URL."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger(redis_url="redis://custom:6379/1")
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["redis_url"] == "redis://custom:6379/1"

    @patch("orka.memory.redisstack_logger.RedisStackMemoryLogger")
    @patch("orka.utils.embedder.get_embedder")
    def test_default_redis_url(self, mock_get_embedder, MockRedisStack):
        """Test default Redis URL is applied."""
        mock_embedder = Mock()
        mock_get_embedder.return_value = mock_embedder
        mock_instance = Mock()
        MockRedisStack.return_value = mock_instance
        
        result = create_memory_logger()
        
        call_kwargs = MockRedisStack.call_args[1]
        assert call_kwargs["redis_url"] == "redis://localhost:6380/0"

    def test_memory_logger_alias(self):
        """Test MemoryLogger alias for backward compatibility."""
        from orka.memory_logger import MemoryLogger
        from orka.memory.redis_logger import RedisMemoryLogger
        
        assert MemoryLogger is RedisMemoryLogger
