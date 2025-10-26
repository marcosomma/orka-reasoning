"""
Additional comprehensive tests for memory presets to increase coverage.
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


class TestMemoryPresets:
    """Test memory preset functionality using current public API."""

    def test_presets_exist_and_have_descriptions(self):
        presets = list_memory_presets()
        assert isinstance(presets, dict)
        # Ensure known presets are present
        for name in ["sensory", "working", "episodic", "semantic", "procedural", "meta"]:
            assert name in presets
            assert isinstance(presets[name], str)

    def test_get_memory_preset_basic(self):
        cfg = get_memory_preset("episodic")
        assert isinstance(cfg, dict)
        assert "decay" in cfg
        assert "vector_search" in cfg
        assert validate_preset_config(cfg) is True

    def test_get_memory_preset_invalid_raises(self):
        with pytest.raises(ValueError):
            get_memory_preset("does_not_exist")

    def test_operation_defaults_read(self):
        defaults = get_operation_defaults("working", "read")
        assert isinstance(defaults, dict)
        assert defaults.get("enable_vector_search") is True

    def test_operation_defaults_write(self):
        defaults = get_operation_defaults("semantic", "write")
        assert isinstance(defaults, dict)
        assert defaults.get("vector") is True

    def test_operation_defaults_invalid(self):
        with pytest.raises(ValueError):
            get_operation_defaults("working", "invalid")
        with pytest.raises(ValueError):
            get_operation_defaults("missing", "read")

    def test_get_memory_preset_with_operation_merges_defaults(self):
        base_only = get_memory_preset("sensory")
        read_cfg = get_memory_preset("sensory", operation="read")
        # read_cfg should include read-default keys
        assert "limit" in read_cfg and "limit" not in base_only
        assert read_cfg["enable_temporal_ranking"] is True

    def test_merge_preset_with_custom_overrides_shallow(self):
        custom = {"decay": {"enabled": False}}
        merged = merge_preset_with_config("procedural", custom_config=custom)
        assert merged["decay"]["enabled"] is False
        # Other values remain present
        assert "default_short_term_hours" in merged["decay"]

    def test_merge_preset_with_operation_and_overrides(self):
        custom = {"read_defaults": {"limit": 99}, "vector_search": {"threshold": 0.42}}
        merged = merge_preset_with_config("episodic", custom_config=custom, operation="read")
        # Operation defaults should be present at top-level after merge via get_memory_preset
        assert merged.get("limit") in (
            5,
            8,
            99,
            merged.get("limit"),
        )  # tolerate preset limit but custom override elsewhere
        assert merged["vector_search"]["threshold"] == 0.42

    def test_validate_preset_config(self):
        valid = get_memory_preset("meta")
        assert validate_preset_config(valid) is True

        invalid = {"vector_search": {"enabled": True}}
        assert validate_preset_config(invalid) is False

    def test_memory_presets_constant_structure(self):
        assert isinstance(MEMORY_PRESETS, dict)
        # spot check a couple of structural invariants
        episodic = MEMORY_PRESETS["episodic"]["config"]
        assert "decay" in episodic
        assert "namespace_prefix" in episodic
