# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for input helper functions."""

import pytest

from orka.orchestrator.prompt_rendering.input_helpers import create_input_helpers


class TestInputHelpers:
    """Tests for input helper functions."""

    def test_get_input_simple(self):
        """Test get_input with simple string."""
        helpers = create_input_helpers({"input": "test input"})
        assert helpers["get_input"]() == "test input"

    def test_get_input_dict(self):
        """Test get_input with dict input."""
        helpers = create_input_helpers({"input": {"input": "nested", "other": "data"}})
        assert helpers["get_input"]() == "nested"

    def test_get_input_dict_no_input_key(self):
        """Test get_input with dict without input key."""
        helpers = create_input_helpers({"input": {"key": "value"}})
        result = helpers["get_input"]()
        assert "key" in result

    def test_get_input_missing(self):
        """Test get_input with missing input."""
        helpers = create_input_helpers({})
        assert helpers["get_input"]() == ""

    def test_get_current_topic(self):
        """Test get_current_topic returns get_input result."""
        helpers = create_input_helpers({"input": "topic"})
        assert helpers["get_current_topic"]() == "topic"

    def test_get_input_field_dict(self):
        """Test get_input_field with dict."""
        helpers = create_input_helpers({})
        result = helpers["get_input_field"]({"field1": "value1"}, "field1")
        assert result == "value1"

    def test_get_input_field_default(self):
        """Test get_input_field with default."""
        helpers = create_input_helpers({})
        result = helpers["get_input_field"]({"field1": "value1"}, "missing", "default")
        assert result == "default"

    def test_get_input_field_non_dict(self):
        """Test get_input_field with non-dict."""
        helpers = create_input_helpers({})
        result = helpers["get_input_field"]("string", "field", "default")
        assert result == "default"

