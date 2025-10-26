"""
Comprehensive tests for memory presets module.
"""

import pytest

from orka.memory.presets import (
    MEMORY_PRESETS,
    get_memory_preset,
    get_operation_defaults,
    list_memory_presets,
    merge_preset_with_config,
    validate_preset_config,
)


class TestMemoryPresetsComprehensive:
    """Comprehensive tests for memory presets."""

    def test_memory_presets_constant_exists(self):
        """Test that MEMORY_PRESETS constant exists and has expected structure."""
        assert isinstance(MEMORY_PRESETS, dict)
        assert len(MEMORY_PRESETS) == 6
        expected_presets = ["sensory", "working", "episodic", "semantic", "procedural", "meta"]
        for preset_name in expected_presets:
            assert preset_name in MEMORY_PRESETS
            assert "description" in MEMORY_PRESETS[preset_name]
            assert "config" in MEMORY_PRESETS[preset_name]

    def test_list_memory_presets(self):
        """Test listing all memory presets."""
        presets = list_memory_presets()
        assert isinstance(presets, dict)
        assert len(presets) == 6
        for name, description in presets.items():
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_get_memory_preset_sensory(self):
        """Test getting sensory preset."""
        config = get_memory_preset("sensory")
        assert isinstance(config, dict)
        assert "decay" in config
        assert config["decay"]["enabled"] is True
        assert config["decay"]["default_short_term_hours"] == 0.25
        assert config["vector_search"]["enabled"] is False

    def test_get_memory_preset_working(self):
        """Test getting working preset."""
        config = get_memory_preset("working")
        assert isinstance(config, dict)
        assert config["decay"]["default_short_term_hours"] == 2.0
        assert config["vector_search"]["enabled"] is True

    def test_get_memory_preset_episodic(self):
        """Test getting episodic preset."""
        config = get_memory_preset("episodic")
        assert isinstance(config, dict)
        assert config["decay"]["default_short_term_hours"] == 24.0
        assert config["vector_search"]["enabled"] is True

    def test_get_memory_preset_semantic(self):
        """Test getting semantic preset."""
        config = get_memory_preset("semantic")
        assert isinstance(config, dict)
        assert config["decay"]["default_long_term_hours"] == 2160.0
        assert config["vector_search"]["threshold"] == 0.65

    def test_get_memory_preset_procedural(self):
        """Test getting procedural preset."""
        config = get_memory_preset("procedural")
        assert isinstance(config, dict)
        assert config["decay"]["default_short_term_hours"] == 168.0

    def test_get_memory_preset_meta(self):
        """Test getting meta preset."""
        config = get_memory_preset("meta")
        assert isinstance(config, dict)
        assert config["decay"]["default_long_term_hours"] == 8760.0

    def test_get_memory_preset_invalid(self):
        """Test getting invalid preset raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_memory_preset("invalid_preset")
        assert "Unknown memory preset" in str(exc_info.value)
        assert "invalid_preset" in str(exc_info.value)

    def test_get_memory_preset_with_read_operation(self):
        """Test getting preset with read operation."""
        config = get_memory_preset("working", operation="read")
        assert "limit" in config
        assert "similarity_threshold" in config
        assert config["enable_vector_search"] is True

    def test_get_memory_preset_with_write_operation(self):
        """Test getting preset with write operation."""
        config = get_memory_preset("semantic", operation="write")
        assert "vector" in config
        assert config["vector"] is True
        assert "store_metadata" in config

    def test_get_operation_defaults_read(self):
        """Test getting read operation defaults."""
        defaults = get_operation_defaults("episodic", "read")
        assert isinstance(defaults, dict)
        assert "limit" in defaults
        assert "similarity_threshold" in defaults
        assert defaults["enable_vector_search"] is True

    def test_get_operation_defaults_write(self):
        """Test getting write operation defaults."""
        defaults = get_operation_defaults("working", "write")
        assert isinstance(defaults, dict)
        assert "vector" in defaults
        assert "force_recreate_index" in defaults

    def test_get_operation_defaults_invalid_preset(self):
        """Test getting operation defaults for invalid preset."""
        with pytest.raises(ValueError) as exc_info:
            get_operation_defaults("invalid", "read")
        assert "Unknown memory preset" in str(exc_info.value)

    def test_get_operation_defaults_invalid_operation(self):
        """Test getting operation defaults for invalid operation."""
        with pytest.raises(ValueError) as exc_info:
            get_operation_defaults("working", "invalid")
        assert "Invalid operation" in str(exc_info.value)

    def test_merge_preset_with_config_no_custom(self):
        """Test merging preset with no custom config."""
        merged = merge_preset_with_config("sensory")
        assert isinstance(merged, dict)
        assert "decay" in merged

    def test_merge_preset_with_config_custom_override(self):
        """Test merging preset with custom config override."""
        custom = {"decay": {"enabled": False}}
        merged = merge_preset_with_config("working", custom_config=custom)
        assert merged["decay"]["enabled"] is False
        # Other decay fields should still be present
        assert "default_short_term_hours" in merged["decay"]

    def test_merge_preset_with_config_deep_merge(self):
        """Test deep merging of nested configs."""
        custom = {
            "vector_search": {"threshold": 0.99},
            "decay": {"check_interval_minutes": 60},
        }
        merged = merge_preset_with_config("episodic", custom_config=custom)
        assert merged["vector_search"]["threshold"] == 0.99
        assert merged["vector_search"]["enabled"] is True  # Original value preserved
        assert merged["decay"]["check_interval_minutes"] == 60
        assert "default_short_term_hours" in merged["decay"]  # Original value preserved

    def test_merge_preset_with_operation(self):
        """Test merging preset with operation."""
        merged = merge_preset_with_config("semantic", operation="read")
        assert "limit" in merged
        assert "similarity_threshold" in merged

    def test_validate_preset_config_valid(self):
        """Test validating valid preset config."""
        config = get_memory_preset("working")
        assert validate_preset_config(config) is True

    def test_validate_preset_config_missing_decay(self):
        """Test validating config missing decay section."""
        config = {"vector_search": {"enabled": True}}
        assert validate_preset_config(config) is False

    def test_validate_preset_config_incomplete_decay(self):
        """Test validating config with incomplete decay section."""
        config = {"decay": {"enabled": True}}
        assert validate_preset_config(config) is False

    def test_validate_preset_config_complete(self):
        """Test validating complete config."""
        config = {
            "decay": {
                "enabled": True,
                "default_short_term_hours": 1.0,
                "default_long_term_hours": 24.0,
            }
        }
        assert validate_preset_config(config) is True

    def test_all_presets_have_required_fields(self):
        """Test that all presets have required fields."""
        for preset_name in MEMORY_PRESETS.keys():
            config = get_memory_preset(preset_name)
            assert validate_preset_config(config) is True
            assert "decay" in config
            assert "vector_search" in config
            assert "namespace_prefix" in config

    def test_all_presets_have_operation_defaults(self):
        """Test that all presets have read and write defaults."""
        for preset_name in MEMORY_PRESETS.keys():
            read_defaults = get_operation_defaults(preset_name, "read")
            write_defaults = get_operation_defaults(preset_name, "write")
            assert isinstance(read_defaults, dict)
            assert isinstance(write_defaults, dict)

    def test_preset_descriptions_are_meaningful(self):
        """Test that all preset descriptions are meaningful."""
        presets = list_memory_presets()
        for name, description in presets.items():
            assert len(description) > 20
            assert any(
                keyword in description.lower()
                for keyword in ["memory", "processing", "knowledge", "experience"]
            )


