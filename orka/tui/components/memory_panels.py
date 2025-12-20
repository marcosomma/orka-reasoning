# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Memory Panel Component Builders."""

import datetime

try:
    from rich.box import ROUNDED
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .utils import (
    decode_bytes_field,
    format_bytes_content,
    format_ttl_display,
    get_memory_type_color,
    parse_importance_score,
    parse_timestamp,
)


class MemoryPanelMixin:
    """Mixin providing memory panel builders."""

    # Expected from host class
    memory_data: list

    def create_compact_memories_panel(self):
        """Create a compact memories panel with comprehensive details."""
        if not self.memory_data:
            return Panel("No memories", title="🧠 Recent Memories")

        table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
        table.add_column("Time", style="dim", width=5)
        table.add_column("Node", style="cyan", width=10)
        table.add_column("Type", style="green", width=8)
        table.add_column("Content", style="white", width=25)
        table.add_column("Score", style="yellow", width=4)
        table.add_column("TTL", style="red", width=8)

        # Show 6 memories with full details
        for mem in self.memory_data[:6]:
            content = format_bytes_content(mem.get("content", ""), max_length=22)
            node_id = decode_bytes_field(mem.get("node_id", "unknown"), max_length=8)
            memory_type = decode_bytes_field(mem.get("memory_type", "unknown"), max_length=6)
            importance = parse_importance_score(mem.get("importance_score", 0))
            
            # Parse timestamp - short format
            try:
                raw_timestamp = mem.get("timestamp", 0)
                if isinstance(raw_timestamp, bytes):
                    timestamp = int(raw_timestamp.decode())
                else:
                    timestamp = int(raw_timestamp) if raw_timestamp else 0

                if timestamp > 1000000000000:
                    dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                else:
                    dt = datetime.datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M")
            except Exception:
                time_str = "??:??"

            # Handle TTL
            ttl = decode_bytes_field(mem.get("ttl_formatted", "?"), max_length=8)

            # Color code TTL
            if "h" in ttl:
                try:
                    hours = int(ttl.split("h")[0])
                    if hours > 1:
                        ttl_display = f"[green]{ttl}[/green]"
                    else:
                        ttl_display = f"[yellow]{ttl}[/yellow]"
                except Exception:
                    ttl_display = f"[yellow]{ttl}[/yellow]"
            elif "m" in ttl:
                ttl_display = f"[yellow]{ttl}[/yellow]"
            elif ttl == "Never":
                ttl_display = "[blue]∞[/blue]"
            else:
                ttl_display = f"[red]{ttl}[/red]"

            table.add_row(
                time_str,
                node_id,
                memory_type,
                content,
                f"{importance:.1f}",
                ttl_display,
            )

        return Panel(
            table,
            title=f"🧠 Recent Memories ({len(self.memory_data)} total)",
            box=ROUNDED,
        )

    def create_recent_memories_panel(self):
        """Create recent memories panel with full details."""
        if not self.memory_data:
            return Panel("No memories found", title="🧠 Recent Memories")

        table = Table(show_header=True, header_style="bold magenta", box=ROUNDED)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Node", style="cyan", width=15)
        table.add_column("Type", style="green", width=12)
        table.add_column("Content", style="white", width=40)
        table.add_column("Score", style="yellow", width=6)
        table.add_column("TTL", style="red", width=12)

        for mem in self.memory_data[:8]:  # Show top 8 for better detail
            content = format_bytes_content(mem.get("content", ""), max_length=35)
            node_id = decode_bytes_field(mem.get("node_id", "unknown"))
            memory_type = decode_bytes_field(mem.get("memory_type", "unknown"))
            importance = parse_importance_score(mem.get("importance_score", 0))
            time_str = parse_timestamp(mem.get("timestamp", 0))

            # Handle TTL with full information
            ttl = decode_bytes_field(mem.get("ttl_formatted", "N/A"))
            ttl_style = format_ttl_display(ttl, has_rich=True)

            # Memory type color coding
            type_color = get_memory_type_color(memory_type)

            table.add_row(
                time_str,
                node_id[:15],
                f"[{type_color}]{memory_type[:12]}[/{type_color}]",
                escape(content),
                f"{importance:.2f}",
                ttl_style,
            )

        return Panel(table, title="🧠 Recent Stored Memories", box=ROUNDED)

    def create_memory_browser(self):
        """Create memory browser view (placeholder)."""
        return Panel("Memory browser not implemented yet", title="🧠 Memory Browser")

