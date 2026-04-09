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
        """Test item access on non-dict/non-list."""
        obj = TemplateSafeObject("string")
        with pytest.raises(TypeError):
            _ = obj["key"]

    def test_getitem_list(self):
        """Test item access for list values."""
        obj = TemplateSafeObject(["a", "b", "c"])
        assert obj[0] == "a"
        assert obj[1] == "b"
        assert obj[-1] == "c"

    def test_getitem_list_nested_dict(self):
        """Test item access for list with nested dict elements."""
        obj = TemplateSafeObject([{"action": "step1"}, {"action": "step2"}])
        result = obj[0]
        assert isinstance(result, TemplateSafeObject)
        assert str(result.action) == "step1"

    def test_iter_list(self):
        """Test iteration over list values."""
        obj = TemplateSafeObject(["a", "b", "c"])
        assert list(obj) == ["a", "b", "c"]

    def test_iter_list_nested_dicts(self):
        """Test iteration over list with dict elements wraps each in TemplateSafeObject."""
        steps = [{"action": "do_thing", "result": "ok"}, {"action": "check", "result": "pass"}]
        obj = TemplateSafeObject(steps)
        items = list(obj)
        assert len(items) == 2
        assert all(isinstance(i, TemplateSafeObject) for i in items)
        assert str(items[0].action) == "do_thing"
        assert str(items[1].result) == "pass"

    def test_iter_dict_keys(self):
        """Test iteration over dict returns keys."""
        obj = TemplateSafeObject({"a": 1, "b": 2})
        assert set(obj) == {"a", "b"}

    def test_iter_non_iterable(self):
        """Test iteration over non-iterable raises TypeError."""
        obj = TemplateSafeObject(42)
        with pytest.raises(TypeError):
            list(obj)

    def test_len_list(self):
        """Test len for list values."""
        obj = TemplateSafeObject([1, 2, 3])
        assert len(obj) == 3

    def test_len_dict(self):
        """Test len for dict values."""
        obj = TemplateSafeObject({"a": 1, "b": 2})
        assert len(obj) == 2

    def test_len_string(self):
        """Test len for string values."""
        obj = TemplateSafeObject("hello")
        assert len(obj) == 5

    def test_len_non_sized(self):
        """Test len for non-sized raises TypeError."""
        obj = TemplateSafeObject(42)
        with pytest.raises(TypeError):
            len(obj)

    def test_bool_none(self):
        """Test bool for None value."""
        obj = TemplateSafeObject(None)
        assert bool(obj) is False

    def test_bool_empty_dict(self):
        """Test bool for empty dict."""
        obj = TemplateSafeObject({})
        assert bool(obj) is False

    def test_bool_nonempty_dict(self):
        """Test bool for non-empty dict."""
        obj = TemplateSafeObject({"key": "value"})
        assert bool(obj) is True

    def test_bool_empty_list(self):
        """Test bool for empty list."""
        obj = TemplateSafeObject([])
        assert bool(obj) is False

    def test_bool_nonempty_list(self):
        """Test bool for non-empty list."""
        obj = TemplateSafeObject([1, 2])
        assert bool(obj) is True

    def test_bool_zero(self):
        """Test bool for zero."""
        obj = TemplateSafeObject(0)
        assert bool(obj) is False

    def test_bool_nonzero(self):
        """Test bool for non-zero."""
        obj = TemplateSafeObject(42)
        assert bool(obj) is True

    def test_contains_dict(self):
        """Test 'in' operator for dict keys."""
        obj = TemplateSafeObject({"a": 1, "b": 2})
        assert "a" in obj
        assert "c" not in obj

    def test_contains_list(self):
        """Test 'in' operator for list values."""
        obj = TemplateSafeObject([1, 2, 3])
        assert 2 in obj
        assert 4 not in obj

    def test_contains_string(self):
        """Test 'in' operator for string."""
        obj = TemplateSafeObject("hello world")
        assert "hello" in obj
        assert "xyz" not in obj

    def test_contains_non_container(self):
        """Test 'in' operator for non-container."""
        obj = TemplateSafeObject(42)
        assert "x" not in obj

    def test_jinja2_for_loop_pattern(self):
        """Test the exact pattern that failed: iterating nested list via TemplateSafeObject.

        This simulates: {% for step in input.execution_trace.steps %}
        """
        input_data = {
            "domain": "compliance",
            "execution_trace": {
                "steps": [
                    {"action": "analyze", "result": "gaps found"},
                    {"action": "recommend", "result": "plan created"},
                ],
                "strategy": "sequential",
            },
        }
        obj = TemplateSafeObject(input_data)

        # Simulate: input.execution_trace
        trace = obj.execution_trace
        assert isinstance(trace, TemplateSafeObject)

        # Simulate: input.execution_trace.steps
        steps = trace.steps
        assert isinstance(steps, TemplateSafeObject)

        # Simulate: {% for step in input.execution_trace.steps %}
        collected = []
        for step in steps:
            assert isinstance(step, TemplateSafeObject)
            collected.append({"action": str(step.action), "result": str(step.result)})
        assert len(collected) == 2
        assert collected[0]["action"] == "analyze"
        assert collected[1]["result"] == "plan created"

        # Simulate: input.execution_trace.strategy
        assert str(trace.strategy) == "sequential"

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

