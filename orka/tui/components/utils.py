# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""TUI Utility Functions - Common helpers for UI components."""

import datetime
from typing import Any


def format_bytes_content(raw_content: Any, max_length: int = 35) -> str:
    """Format content that may be bytes to a string with optional truncation."""
    if isinstance(raw_content, bytes):
        raw_content = raw_content.decode("utf-8", errors="replace")
    content = str(raw_content)
    if len(content) > max_length:
        return content[:max_length - 3] + "..."
    return content


def parse_timestamp(raw_timestamp: Any) -> str:
    """Parse a timestamp (bytes, int, or str) to formatted time string."""
    try:
        if isinstance(raw_timestamp, bytes):
            timestamp = int(raw_timestamp.decode())
        else:
            timestamp = int(raw_timestamp) if raw_timestamp else 0

        if timestamp > 1000000000000:  # milliseconds
            dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        else:  # seconds
            dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return "??:??:??"


def format_ttl_display(ttl: str, has_rich: bool = True) -> str:
    """Format TTL with color coding for Rich display."""
    if ttl == "0s" or "Expired" in ttl:
        return f"[red]💀 {ttl}[/red]" if has_rich else f"💀 {ttl}"
    elif "Never" in ttl:
        return f"[green]♾️ {ttl}[/green]" if has_rich else f"♾️ {ttl}"
    elif any(unit in ttl for unit in ["s", "m", "h"]):
        if "h" in ttl:
            return f"[green]⏰ {ttl}[/green]" if has_rich else f"⏰ {ttl}"
        elif "m" in ttl:
            return f"[yellow]⏰ {ttl}[/yellow]" if has_rich else f"⏰ {ttl}"
        else:  # seconds
            return f"[red]⚠️ {ttl}[/red]" if has_rich else f"⚠️ {ttl}"
    return ttl


def decode_bytes_field(value: Any, max_length: int | None = None) -> str:
    """Decode a bytes field to string with optional length limit."""
    if isinstance(value, bytes):
        result = value.decode("utf-8", errors="replace")
    else:
        result = str(value) if value is not None else ""
    
    if max_length and len(result) > max_length:
        return result[:max_length]
    return result


def parse_importance_score(raw_importance: Any) -> float:
    """Parse importance score from bytes or numeric value."""
    if isinstance(raw_importance, bytes):
        try:
            return float(raw_importance.decode())
        except Exception:
            return 0.0
    return float(raw_importance) if raw_importance else 0.0


def get_memory_type_color(memory_type: str) -> str:
    """Get the color for a memory type."""
    if memory_type == "long_term":
        return "green"
    elif memory_type == "short_term":
        return "yellow"
    return "dim"

