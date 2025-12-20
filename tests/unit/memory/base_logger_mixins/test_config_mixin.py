# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for ConfigMixin."""

import pytest

from orka.memory.base_logger_mixins.config_mixin import ConfigMixin


class ConcreteConfigMixin(ConfigMixin):
    """Concrete implementation for testing."""

    pass


class TestConfigMixin:
    """Tests for ConfigMixin."""

    @pytest.fixture
    def config(self):
        return ConcreteConfigMixin()

    def test_init_decay_config_defaults(self, config):
        """Test default decay configuration."""
        result = config._init_decay_config({})

        assert result["enabled"] is False
        assert result["default_short_term_hours"] == 1.0
        assert result["default_long_term_hours"] == 24.0
        assert result["check_interval_minutes"] == 30

    def test_init_decay_config_override(self, config):
        """Test overriding decay configuration."""
        custom = {"enabled": True, "default_short_term_hours": 2.0}
        result = config._init_decay_config(custom)

        assert result["enabled"] is True
        assert result["default_short_term_hours"] == 2.0
        assert result["default_long_term_hours"] == 24.0

    def test_init_decay_config_nested_merge(self, config):
        """Test nested dict merging."""
        custom = {"importance_rules": {"base_score": 0.8}}
        result = config._init_decay_config(custom)

        assert result["importance_rules"]["base_score"] == 0.8
        assert "event_type_boosts" in result["importance_rules"]

    def test_resolve_memory_preset_none(self, config):
        """Test resolve with no preset."""
        result = config._resolve_memory_preset(None, {"enabled": True}, None)
        assert result == {"enabled": True}

    def test_resolve_memory_preset_missing_module(self, config):
        """Test resolve when presets module is missing."""
        # This will attempt to import presets and handle the error gracefully
        result = config._resolve_memory_preset("unknown_preset", {}, None)
        # Should return original config on error
        assert isinstance(result, dict)

