# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).

"""Unit tests for metric normalization utilities."""

import pytest
from orka.utils.metric_normalization import (
    normalize_confidence,
    normalize_cost,
    normalize_tokens,
    normalize_latency,
    normalize_metrics,
    normalize_payload,
)


class TestNormalizeConfidence:
    """Tests for normalize_confidence function."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (0.5, 0.5),
            ("0.5", 0.5),
            ("0.0", 0.0),
            ("1.0", 1.0),
            (1, 1.0),
            (0, 0.0),
            (None, 0.0),
            ("invalid", 0.0),
            (1.5, 1.0),  # Clamped to max
            (-0.5, 0.0),  # Clamped to min
            (2.0, 1.0),  # Clamped to max
            ("0.85", 0.85),
        ],
    )
    def test_normalize_confidence(self, input_val, expected):
        """Verify confidence normalization for various input types."""
        assert normalize_confidence(input_val) == expected

    def test_normalize_confidence_with_custom_default(self):
        """Test custom default value."""
        assert normalize_confidence(None, default=0.5) == 0.5
        assert normalize_confidence("invalid", default=0.3) == 0.3


class TestNormalizeCost:
    """Tests for normalize_cost function."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (0.001, 0.001),
            ("0.001", 0.001),
            (0.0, 0.0),
            (None, None),
            ("invalid", None),
            (-1, None),  # Negative costs are invalid
            (-0.5, None),
            (0.12345, 0.12345),
        ],
    )
    def test_normalize_cost(self, input_val, expected):
        """Verify cost normalization for various input types."""
        assert normalize_cost(input_val) == expected

    def test_normalize_cost_with_custom_default(self):
        """Test custom default value for cost."""
        assert normalize_cost(None, default=0.0) == 0.0
        assert normalize_cost("invalid", default=0.0) == 0.0


class TestNormalizeTokens:
    """Tests for normalize_tokens function."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (100, 100),
            ("150", 150),
            (0, 0),
            (None, 0),
            ("invalid", 0),
            (-50, 0),  # Negative tokens clamped to 0
            (3.5, 3),  # Float truncated to int
            ("200", 200),
        ],
    )
    def test_normalize_tokens(self, input_val, expected):
        """Verify token normalization for various input types."""
        assert normalize_tokens(input_val) == expected

    def test_normalize_tokens_with_custom_default(self):
        """Test custom default value for tokens."""
        assert normalize_tokens(None, default=10) == 10


class TestNormalizeLatency:
    """Tests for normalize_latency function."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            (234.5, 234.5),
            ("123.4", 123.4),
            (0.0, 0.0),
            (None, 0.0),
            ("invalid", 0.0),
            (-50.0, 0.0),  # Negative latency clamped to 0
            (1000, 1000.0),
        ],
    )
    def test_normalize_latency(self, input_val, expected):
        """Verify latency normalization for various input types."""
        assert normalize_latency(input_val) == expected


class TestNormalizeMetrics:
    """Tests for normalize_metrics function."""

    def test_full_normalization(self):
        """Test normalizing a complete metrics dict."""
        raw = {
            "confidence": "0.85",
            "cost_usd": "0.001",
            "tokens": "150",
            "prompt_tokens": "100",
            "completion_tokens": "50",
            "latency_ms": "234.5",
            "model": "gpt-4",  # Should pass through unchanged
        }
        result = normalize_metrics(raw)

        assert result["confidence"] == 0.85
        assert result["cost_usd"] == 0.001
        assert result["tokens"] == 150
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["latency_ms"] == 234.5
        assert result["model"] == "gpt-4"

    def test_partial_normalization(self):
        """Test normalizing metrics with only some fields."""
        raw = {"tokens": "100", "model": "local"}
        result = normalize_metrics(raw)

        assert result["tokens"] == 100
        assert result["model"] == "local"

    def test_empty_dict(self):
        """Test normalizing empty dict."""
        assert normalize_metrics({}) == {}

    def test_non_dict_input(self):
        """Test normalizing non-dict input."""
        assert normalize_metrics(None) == {}
        assert normalize_metrics("not a dict") == {}
        assert normalize_metrics([1, 2, 3]) == {}

    def test_preserves_unknown_fields(self):
        """Test that unknown fields are preserved."""
        raw = {"confidence": "0.5", "custom_field": "value"}
        result = normalize_metrics(raw)
        assert result["custom_field"] == "value"


class TestNormalizePayload:
    """Tests for normalize_payload function."""

    def test_payload_with_nested_metrics(self):
        """Test normalizing payload with nested _metrics."""
        payload = {
            "agent_id": "test",
            "confidence": "0.9",
            "_metrics": {
                "tokens": "100",
                "cost_usd": None,
            },
        }
        result = normalize_payload(payload)

        assert result["confidence"] == 0.9
        assert result["_metrics"]["tokens"] == 100
        assert result["_metrics"]["cost_usd"] is None
        assert result["agent_id"] == "test"

    def test_payload_without_metrics(self):
        """Test normalizing payload without _metrics."""
        payload = {"agent_id": "test", "result": "success"}
        result = normalize_payload(payload)

        assert result == payload

    def test_payload_with_confidence_only(self):
        """Test normalizing payload with only confidence."""
        payload = {"agent_id": "test", "confidence": "0.75"}
        result = normalize_payload(payload)

        assert result["confidence"] == 0.75

    def test_non_dict_payload(self):
        """Test that non-dict payloads pass through."""
        assert normalize_payload("string") == "string"
        assert normalize_payload(123) == 123
        assert normalize_payload(None) is None

    def test_string_confidence_zero(self):
        """Test that string '0.0' becomes float 0.0."""
        payload = {"confidence": "0.0"}
        result = normalize_payload(payload)
        assert result["confidence"] == 0.0
        assert isinstance(result["confidence"], float)
