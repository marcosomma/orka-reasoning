"""Unit tests for orka.memory.presets."""

import pytest

from orka.memory.presets import (
    MEMORY_PRESETS,
    get_memory_preset,
    get_operation_defaults,
    list_memory_presets,
    merge_preset_with_config,
    validate_preset_config,
)

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestMemoryPresets:
    """Test suite for memory presets."""

    def test_memory_presets_structure(self):
        """Test that MEMORY_PRESETS has expected structure."""
        assert "sensory" in MEMORY_PRESETS
        assert "working" in MEMORY_PRESETS
        assert "episodic" in MEMORY_PRESETS
        assert "semantic" in MEMORY_PRESETS
        assert "procedural" in MEMORY_PRESETS
        assert "meta" in MEMORY_PRESETS
        
        for preset_name, preset_data in MEMORY_PRESETS.items():
            assert "description" in preset_data
            assert "config" in preset_data

    def test_get_memory_preset(self):
        """Test get_memory_preset function."""
        preset = get_memory_preset("sensory")
        
        assert isinstance(preset, dict)
        assert "decay" in preset

    def test_get_memory_preset_with_operation(self):
        """Test get_memory_preset with operation parameter."""
        preset = get_memory_preset("working", operation="read")
        
        assert isinstance(preset, dict)
        assert "limit" in preset  # From read_defaults

    def test_get_memory_preset_invalid(self):
        """Test get_memory_preset with invalid preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown memory preset"):
            get_memory_preset("invalid_preset")

    def test_list_memory_presets(self):
        """Test list_memory_presets function."""
        presets = list_memory_presets()
        
        assert isinstance(presets, dict)
        assert "sensory" in presets
        assert len(presets) == 6

    def test_merge_preset_with_config(self):
        """Test merge_preset_with_config function."""
        custom_config = {
            "decay": {
                "default_short_term_hours": 48.0
            }
        }
        
        merged = merge_preset_with_config("sensory", custom_config)
        
        assert merged["decay"]["default_short_term_hours"] == 48.0

    def test_merge_preset_with_config_no_custom(self):
        """Test merge_preset_with_config without custom config."""
        merged = merge_preset_with_config("sensory")
        
        assert isinstance(merged, dict)
        assert "decay" in merged

    def test_get_operation_defaults(self):
        """Test get_operation_defaults function."""
        defaults = get_operation_defaults("working", "read")
        
        assert isinstance(defaults, dict)
        assert "limit" in defaults

    def test_get_operation_defaults_write(self):
        """Test get_operation_defaults for write operation."""
        defaults = get_operation_defaults("working", "write")
        
        assert isinstance(defaults, dict)
        assert "vector" in defaults

    def test_get_operation_defaults_invalid_preset(self):
        """Test get_operation_defaults with invalid preset."""
        with pytest.raises(ValueError, match="Unknown memory preset"):
            get_operation_defaults("invalid", "read")

    def test_get_operation_defaults_invalid_operation(self):
        """Test get_operation_defaults with invalid operation."""
        with pytest.raises(ValueError, match="Invalid operation"):
            get_operation_defaults("sensory", "invalid")

    def test_validate_preset_config_valid(self):
        """Test validate_preset_config with valid config."""
        config = {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 1.0,
                "default_long_term_hours": 24.0,
            }
        }
        
        assert validate_preset_config(config) is True

    def test_validate_preset_config_invalid(self):
        """Test validate_preset_config with invalid config."""
        config = {
            "decay": {
                "enabled": True,
                # Missing required fields
            }
        }
        
        assert validate_preset_config(config) is False

    def test_validate_preset_config_missing_decay(self):
        """Test validate_preset_config with missing decay section."""
        config = {
            # Missing decay section
        }
        
        assert validate_preset_config(config) is False

