# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Template Safe Object
====================

Wrapper that makes template attribute access and common string ops safe.
"""

from typing import Any


class TemplateSafeObject:
    """
    Wrapper that makes template attribute access and common string ops safe.

    It wraps arbitrary values (dict, list, string, number) and exposes
    attribute access (dot notation) by delegating to dict keys when
    possible or falling back to sensible defaults.
    """

    def __init__(self, value: Any):
        self._value = value

    def __getattr__(self, name: str) -> Any:
        # Support common pattern: previous_outputs.agent.result
        val = self._value
        if isinstance(val, dict):
            if name in val:
                return TemplateSafeObject(val[name])
            # allow nested 'result' lookup in nested result dicts
            if "result" in val and isinstance(val["result"], dict) and name in val["result"]:
                return TemplateSafeObject(val["result"][name])
        # fallback: raise AttributeError so Jinja treats as missing
        raise AttributeError(name)

    def __str__(self) -> str:
        val = self._value
        if isinstance(val, (dict, list)):
            return str(val)
        return str(val)

    def __repr__(self) -> str:
        return f"TemplateSafeObject({repr(self._value)})"

    def get(self, key, default=None):
        if isinstance(self._value, dict):
            return self._value.get(key, default)
        return default

    def raw(self):
        """Return the underlying raw value wrapped by this object."""
        return self._value

    def __getitem__(self, key):
        if isinstance(self._value, dict):
            val = self._value[key]
            if isinstance(val, (dict, list)):
                return TemplateSafeObject(val)
            return val
        raise TypeError("TemplateSafeObject is not subscriptable for non-dict values")

    def startswith(self, prefix):
        """Safe startswith: only works for string-like values."""
        if isinstance(self._value, str):
            return self._value.startswith(prefix)
        return False

    def items(self):
        if isinstance(self._value, dict):
            return self._value.items()
        return []


def unwrap_template_safe(value: Any) -> Any:
    """
    Recursively unwrap TemplateSafeObject (or any object exposing .raw()) into plain
    Python types for safe JSON serialization inside templates (e.g. via `|tojson`).
    """
    if hasattr(value, "raw") and callable(getattr(value, "raw")):
        try:
            value = value.raw()
        except Exception:
            return str(value)

    if isinstance(value, dict):
        return {k: unwrap_template_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap_template_safe(v) for v in value]
    if isinstance(value, tuple):
        return tuple(unwrap_template_safe(v) for v in value)

    return value

