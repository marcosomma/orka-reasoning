# OrKa: Orchestrator Kit Agents
# Tests for TUI utility functions

import pytest

from orka.tui.components.utils import (
    decode_bytes_field,
    format_bytes_content,
    format_ttl_display,
    get_memory_type_color,
    parse_importance_score,
    parse_timestamp,
)


class TestFormatBytesContent:
    """Tests for format_bytes_content function."""

    def test_string_content(self):
        result = format_bytes_content("hello world")
        assert result == "hello world"

    def test_bytes_content(self):
        result = format_bytes_content(b"hello world")
        assert result == "hello world"

    def test_truncation(self):
        long_content = "a" * 100
        result = format_bytes_content(long_content, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_no_truncation_needed(self):
        result = format_bytes_content("short", max_length=20)
        assert result == "short"


class TestParseTimestamp:
    """Tests for parse_timestamp function."""

    def test_milliseconds_timestamp(self):
        # 2025-01-01 00:00:00 UTC in milliseconds
        result = parse_timestamp(1735689600000)
        assert ":" in result  # Has time format

    def test_seconds_timestamp(self):
        result = parse_timestamp(1735689600)
        assert ":" in result

    def test_bytes_timestamp(self):
        result = parse_timestamp(b"1735689600")
        assert ":" in result

    def test_invalid_timestamp(self):
        result = parse_timestamp("invalid")
        assert result == "??:??:??"

    def test_zero_timestamp(self):
        result = parse_timestamp(0)
        assert ":" in result


class TestFormatTtlDisplay:
    """Tests for format_ttl_display function."""

    def test_expired(self):
        result = format_ttl_display("0s")
        assert "💀" in result
        assert "[red]" in result

    def test_never_expires(self):
        result = format_ttl_display("Never")
        assert "♾️" in result
        assert "[green]" in result

    def test_hours(self):
        result = format_ttl_display("5h")
        assert "⏰" in result
        assert "[green]" in result

    def test_minutes(self):
        result = format_ttl_display("30m")
        assert "⏰" in result
        assert "[yellow]" in result

    def test_seconds(self):
        result = format_ttl_display("45s")
        assert "⚠️" in result
        assert "[red]" in result

    def test_no_rich(self):
        result = format_ttl_display("5h", has_rich=False)
        assert "⏰" in result
        assert "[" not in result


class TestDecodeBytesField:
    """Tests for decode_bytes_field function."""

    def test_bytes_input(self):
        result = decode_bytes_field(b"hello")
        assert result == "hello"

    def test_string_input(self):
        result = decode_bytes_field("hello")
        assert result == "hello"

    def test_none_input(self):
        result = decode_bytes_field(None)
        assert result == ""

    def test_max_length(self):
        result = decode_bytes_field("hello world", max_length=5)
        assert result == "hello"


class TestParseImportanceScore:
    """Tests for parse_importance_score function."""

    def test_float_value(self):
        result = parse_importance_score(3.5)
        assert result == 3.5

    def test_bytes_value(self):
        result = parse_importance_score(b"3.5")
        assert result == 3.5

    def test_none_value(self):
        result = parse_importance_score(None)
        assert result == 0.0

    def test_invalid_bytes(self):
        result = parse_importance_score(b"invalid")
        assert result == 0.0


class TestGetMemoryTypeColor:
    """Tests for get_memory_type_color function."""

    def test_long_term(self):
        assert get_memory_type_color("long_term") == "green"

    def test_short_term(self):
        assert get_memory_type_color("short_term") == "yellow"

    def test_unknown(self):
        assert get_memory_type_color("unknown") == "dim"

