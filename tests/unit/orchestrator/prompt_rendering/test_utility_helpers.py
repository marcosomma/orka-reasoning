# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for utility helper functions."""

import pytest

from orka.orchestrator.prompt_rendering.utility_helpers import (
    create_utility_helpers,
    normalize_bool,
)


class TestUtilityHelpers:
    """Tests for utility helper functions."""

    def test_safe_get_dict(self):
        """Test safe_get with dict."""
        helpers = create_utility_helpers({})
        result = helpers["safe_get"]({"key": "value"}, "key")
        assert result == "value"

    def test_safe_get_default(self):
        """Test safe_get with default."""
        helpers = create_utility_helpers({})
        result = helpers["safe_get"]({"key": "value"}, "missing", "default")
        assert result == "default"

    def test_safe_get_non_dict(self):
        """Test safe_get with non-dict."""
        helpers = create_utility_helpers({})
        result = helpers["safe_get"]("string", "key", "default")
        assert result == "default"

    def test_safe_str_none(self):
        """Test safe_str with None."""
        helpers = create_utility_helpers({})
        assert helpers["safe_str"](None) == ""

    def test_safe_str_value(self):
        """Test safe_str with value."""
        helpers = create_utility_helpers({})
        assert helpers["safe_str"](42) == "42"

    def test_has_context_in_previous_outputs(self):
        """Test has_context with agent in previous_outputs."""
        helpers = create_utility_helpers({
            "previous_outputs": {"agent1": {"result": "test"}}
        })
        assert helpers["has_context"]("agent1") is True

    def test_has_context_empty_value(self):
        """Test has_context with empty value."""
        helpers = create_utility_helpers({
            "previous_outputs": {"agent1": None}
        })
        assert helpers["has_context"]("agent1") is False

    def test_has_context_conversation_context(self):
        """Test has_context with conversation_context."""
        helpers = create_utility_helpers({
            "input": {"conversation_context": "some context"}
        })
        assert helpers["has_context"]("any_agent") is True

    def test_has_context_in_memories(self):
        """Test has_context in memories."""
        helpers = create_utility_helpers({
            "memories": [{"agent_name": "agent1", "content": "memory"}]
        })
        assert helpers["has_context"]("agent1") is True

    def test_has_context_false(self):
        """Test has_context returns False."""
        helpers = create_utility_helpers({})
        assert helpers["has_context"]("missing") is False


class TestNormalizeBool:
    """Tests for normalize_bool function."""

    def test_normalize_bool_true(self):
        """Test normalize_bool with True."""
        assert normalize_bool(True) is True

    def test_normalize_bool_false(self):
        """Test normalize_bool with False."""
        assert normalize_bool(False) is False

    def test_normalize_bool_string_true(self):
        """Test normalize_bool with 'true' string."""
        assert normalize_bool("true") is True
        assert normalize_bool("True") is True
        assert normalize_bool("TRUE") is True

    def test_normalize_bool_string_yes(self):
        """Test normalize_bool with 'yes' string."""
        assert normalize_bool("yes") is True
        assert normalize_bool("Yes") is True

    def test_normalize_bool_string_false(self):
        """Test normalize_bool with other strings."""
        assert normalize_bool("false") is False
        assert normalize_bool("no") is False
        assert normalize_bool("anything") is False

    def test_normalize_bool_dict_result(self):
        """Test normalize_bool with dict containing result."""
        assert normalize_bool({"result": True}) is True
        assert normalize_bool({"result": "yes"}) is True

    def test_normalize_bool_dict_nested_result(self):
        """Test normalize_bool with nested result."""
        assert normalize_bool({"result": {"result": True}}) is True
        assert normalize_bool({"result": {"response": "true"}}) is True

    def test_normalize_bool_dict_response(self):
        """Test normalize_bool with dict containing response."""
        assert normalize_bool({"response": True}) is True
        assert normalize_bool({"response": "yes"}) is True

    def test_normalize_bool_other(self):
        """Test normalize_bool with other types."""
        assert normalize_bool(123) is False
        assert normalize_bool([]) is False
        assert normalize_bool(None) is False

