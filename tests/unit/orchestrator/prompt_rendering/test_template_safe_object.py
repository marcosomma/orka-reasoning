# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for TemplateSafeObject."""

import pytest

from orka.orchestrator.prompt_rendering.template_safe_object import (
    TemplateSafeObject,
    unwrap_template_safe,
)


class TestTemplateSafeObject:
    """Tests for TemplateSafeObject class."""

    def test_init(self):
        """Test initialization."""
        obj = TemplateSafeObject({"key": "value"})
        assert obj._value == {"key": "value"}

    def test_getattr_dict(self):
        """Test attribute access for dict values."""
        obj = TemplateSafeObject({"name": "test", "count": 42})
        assert str(obj.name) == "test"

    def test_getattr_nested_result(self):
        """Test nested result lookup."""
        obj = TemplateSafeObject({"result": {"data": "nested"}})
        assert str(obj.data) == "nested"

    def test_getattr_missing(self):
        """Test attribute access for missing key."""
        obj = TemplateSafeObject({"key": "value"})
        with pytest.raises(AttributeError):
            _ = obj.missing

    def test_str_dict(self):
        """Test string conversion for dict."""
        obj = TemplateSafeObject({"key": "value"})
        assert "key" in str(obj)

    def test_str_simple(self):
        """Test string conversion for simple value."""
        obj = TemplateSafeObject("hello")
        assert str(obj) == "hello"

    def test_repr(self):
        """Test repr."""
        obj = TemplateSafeObject("test")
        assert "TemplateSafeObject" in repr(obj)

    def test_get(self):
        """Test get method."""
        obj = TemplateSafeObject({"key": "value"})
        assert obj.get("key") == "value"
        assert obj.get("missing", "default") == "default"

    def test_get_non_dict(self):
        """Test get on non-dict value."""
        obj = TemplateSafeObject("string")
        assert obj.get("key", "default") == "default"

    def test_raw(self):
        """Test raw method."""
        data = {"key": "value"}
        obj = TemplateSafeObject(data)
        assert obj.raw() == data

    def test_getitem(self):
        """Test item access."""
        obj = TemplateSafeObject({"key": "value"})
        assert obj["key"] == "value"

    def test_getitem_nested(self):
        """Test nested item access."""
        obj = TemplateSafeObject({"nested": {"inner": "value"}})
        inner = obj["nested"]
        assert isinstance(inner, TemplateSafeObject)

    def test_getitem_non_dict(self):
        """Test item access on non-dict."""
        obj = TemplateSafeObject("string")
        with pytest.raises(TypeError):
            _ = obj["key"]

    def test_startswith_string(self):
        """Test startswith for string value."""
        obj = TemplateSafeObject("hello world")
        assert obj.startswith("hello") is True
        assert obj.startswith("world") is False

    def test_startswith_non_string(self):
        """Test startswith for non-string value."""
        obj = TemplateSafeObject(123)
        assert obj.startswith("1") is False

    def test_items_dict(self):
        """Test items for dict value."""
        obj = TemplateSafeObject({"a": 1, "b": 2})
        items = list(obj.items())
        assert ("a", 1) in items
        assert ("b", 2) in items

    def test_items_non_dict(self):
        """Test items for non-dict value."""
        obj = TemplateSafeObject("string")
        assert list(obj.items()) == []


class TestUnwrapTemplateSafe:
    """Tests for unwrap_template_safe function."""

    def test_unwrap_simple(self):
        """Test unwrapping simple TemplateSafeObject."""
        obj = TemplateSafeObject("value")
        assert unwrap_template_safe(obj) == "value"

    def test_unwrap_dict(self):
        """Test unwrapping dict with TemplateSafeObject values."""
        data = {"key": TemplateSafeObject("value")}
        result = unwrap_template_safe(data)
        assert result == {"key": "value"}

    def test_unwrap_list(self):
        """Test unwrapping list with TemplateSafeObject values."""
        data = [TemplateSafeObject("a"), TemplateSafeObject("b")]
        result = unwrap_template_safe(data)
        assert result == ["a", "b"]

    def test_unwrap_tuple(self):
        """Test unwrapping tuple with TemplateSafeObject values."""
        data = (TemplateSafeObject("a"), TemplateSafeObject("b"))
        result = unwrap_template_safe(data)
        assert result == ("a", "b")

    def test_unwrap_nested(self):
        """Test unwrapping nested structures."""
        data = {"outer": {"inner": TemplateSafeObject("value")}}
        result = unwrap_template_safe(data)
        assert result == {"outer": {"inner": "value"}}

    def test_unwrap_plain_value(self):
        """Test unwrapping plain value."""
        assert unwrap_template_safe("plain") == "plain"
        assert unwrap_template_safe(42) == 42

