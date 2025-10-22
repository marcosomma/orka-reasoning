"""
Additional comprehensive tests for memory presets to increase coverage.
"""
import pytest
from unittest.mock import MagicMock, patch
from orka.memory.presets import (
    MemoryPreset,
    get_preset,
    list_presets,
    create_custom_preset,
    DEFAULT_PRESETS
)


class TestMemoryPresets:
    """Test memory preset functionality."""

    def test_memory_preset_creation(self):
        """Test creating a memory preset."""
        preset = MemoryPreset(
            name="test_preset",
            decay_rate=0.1,
            importance_threshold=0.5
        )
        assert preset.name == "test_preset"
        assert preset.decay_rate == 0.1

    def test_get_default_preset(self):
        """Test getting default preset."""
        preset = get_preset("default")
        assert preset is not None
        assert preset.name == "default"

    def test_get_fast_preset(self):
        """Test getting fast preset."""
        preset = get_preset("fast")
        assert preset is not None
        assert preset.decay_rate > 0

    def test_get_balanced_preset(self):
        """Test getting balanced preset."""
        preset = get_preset("balanced")
        assert preset is not None

    def test_get_thorough_preset(self):
        """Test getting thorough preset."""
        preset = get_preset("thorough")
        assert preset is not None
        assert preset.importance_threshold < 0.5

    def test_get_nonexistent_preset(self):
        """Test getting nonexistent preset returns default."""
        preset = get_preset("nonexistent")
        assert preset is not None

    def test_list_all_presets(self):
        """Test listing all available presets."""
        presets = list_presets()
        assert len(presets) > 0
        assert "default" in presets

    def test_create_custom_preset(self):
        """Test creating custom preset."""
        custom = create_custom_preset(
            name="custom",
            decay_rate=0.05,
            importance_threshold=0.7,
            max_memories=500
        )
        assert custom.name == "custom"
        assert custom.decay_rate == 0.05
        assert custom.max_memories == 500

    def test_preset_validation(self):
        """Test preset parameter validation."""
        with pytest.raises(ValueError):
            MemoryPreset(
                name="invalid",
                decay_rate=-0.1,  # Invalid negative rate
                importance_threshold=0.5
            )

    def test_preset_to_dict(self):
        """Test converting preset to dictionary."""
        preset = MemoryPreset(
            name="test",
            decay_rate=0.1,
            importance_threshold=0.5
        )
        preset_dict = preset.to_dict()
        assert preset_dict["name"] == "test"
        assert preset_dict["decay_rate"] == 0.1

    def test_preset_from_dict(self):
        """Test creating preset from dictionary."""
        preset_dict = {
            "name": "test",
            "decay_rate": 0.1,
            "importance_threshold": 0.5
        }
        preset = MemoryPreset.from_dict(preset_dict)
        assert preset.name == "test"

    def test_preset_equality(self):
        """Test preset equality comparison."""
        preset1 = MemoryPreset("test", 0.1, 0.5)
        preset2 = MemoryPreset("test", 0.1, 0.5)
        assert preset1 == preset2

    def test_preset_copy(self):
        """Test copying preset."""
        original = MemoryPreset("test", 0.1, 0.5)
        copy = original.copy()
        assert copy.name == original.name
        assert copy.decay_rate == original.decay_rate

    def test_preset_merge(self):
        """Test merging presets."""
        preset1 = MemoryPreset("test1", 0.1, 0.5)
        preset2 = MemoryPreset("test2", 0.2, 0.6)
        merged = preset1.merge(preset2)
        assert merged is not None

    def test_apply_preset_to_memory_config(self):
        """Test applying preset to memory configuration."""
        preset = get_preset("default")
        config = {}
        updated_config = preset.apply_to_config(config)
        assert "decay_rate" in updated_config
