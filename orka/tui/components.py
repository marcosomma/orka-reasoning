"""Build UI components for TUI interface panels and displays."""

import datetime
from typing import Any, Dict, List

try:
    from rich.align import Align
    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ComponentBuilder:
    """Builds UI components for the TUI interface."""

    def __init__(self, data_manager: Any) -> None:
        """
        Initialize the component builder.

        Args:
            data_manager: Data manager instance for accessing memory data.
        """
        self.data_manager = data_manager

    @property
    def stats(self) -> Any:
        """Get memory statistics."""
        return self.data_manager.stats

    @property
    def memory_data(self) -> List[Dict[str, Any]]:
        """Get memory data."""
        return self.data_manager.memory_data

    @property
    def performance_history(self) -> List[Dict[str, Any]]:
        """Get performance history."""
        return self.data_manager.performance_history

    @property
    def memory_logger(self) -> Any:
        """Get memory logger instance."""
        return self.data_manager.memory_logger

    @property
    def backend(self) -> str:
        """Get backend type."""
        return self.data_manager.backend

    @property
    def running(self) -> bool:
        """Get running state."""
        return getattr(self.data_manager, "running", True)

    def create_compact_header(self) -> Panel:
        """
        Create a compact header.

        Returns:
            A Rich Panel containing the header.
        """
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        status_color = "green" if self.running else "red"

        header_text = Text()
        header_text.append("🚀 OrKa Monitor ", style="bold blue")
        header_text.append(f"| {self.backend.upper()} ", style="cyan")
        header_text.append(f"| {current_time} ", style="dim")
        header_text.append("●", style=f"bold {status_color}")

        return Panel(Align.center(header_text), box=SIMPLE, style="blue")

    def create_compact_stats_panel(self) -> Panel:
        """
        Create a compact stats panel with comprehensive metrics.

        Returns:
            A Rich Panel containing the stats.
        """
        if not self.stats.current:
            return Panel("Loading...", title="📊 Memory Statistics")

        stats = self.stats.current

        # Create a detailed table with all metrics
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=14)
        table.add_column(style="white", width=8, justify="right")
        table.add_column(style="green", width=6)
        table.add_column(style="yellow", width=4)

        # Core metrics with trends
        core_metrics: List[tuple[str, int, str]] = [
            ("Total Entries", stats.get("total_entries", 0), "entries"),
            ("Stored Memories", stats.get("stored_memories", 0), "mem"),
            ("Orchestration", stats.get("orchestration_logs", 0), "logs"),
            ("Active", stats.get("active_entries", 0), "act"),
            ("Expired", stats.get("expired_entries", 0), "exp"),
        ]

        for name, value, unit in core_metrics:
            # Get trend information
            key = name.lower().replace(" ", "_")
            trend = self.stats.get_trend(key)

            # Trend icon
            if trend == "↗":
                trend_display = "[green]↗[/green]"
            elif trend == "↘":
                trend_display = "[red]↘[/red]"
            else:
                trend_display = "[dim]→[/dim]"

            table.add_row(f"  {name}", f"[bold]{value:,}[/bold]", unit, trend_display)

        # Backend health with more details
        table.add_row("", "", "", "")  # Separator
        decay_enabled = stats.get("decay_enabled", False)
        backend_status = "✅" if hasattr(self.memory_logger, "client") else "❌"
        table.add_row("  Backend", f"{self.backend.upper()}", backend_status, "")
        table.add_row("  Decay", "✅" if decay_enabled else "❌", "auto", "")

        # Performance if available
        if self.performance_history:
            latest_perf = self.performance_history[-1]
            avg_time = latest_perf.get("average_search_time", 0)
            perf_icon = "⚡" if avg_time < 0.1 else "⚠" if avg_time < 0.5 else "🐌"
            table.add_row("  Search", f"{avg_time:.3f}s", "time", f"[cyan]{perf_icon}[/cyan]")

        return Panel(table, title="📊 Memory Statistics & Health", box=ROUNDED)

    def create_compact_memories_panel(self) -> Panel:
        """
        Create a compact memories panel with comprehensive details.

        Returns:
            A Rich Panel containing the memories table.
        """
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
        for memory in self.memory_data[:6]:
            # Handle bytes content
            raw_content = memory.get("content", "")
            if isinstance(raw_content, bytes):
                raw_content = raw_content.decode("utf-8", errors="replace")
            content = raw_content[:22] + ("..." if len(raw_content) > 22 else "")

            # Handle bytes for node_id
            raw_node_id = memory.get("node_id", "unknown")
            node_id = (
                raw_node_id.decode("utf-8", errors="replace")
                if isinstance(raw_node_id, bytes)
                else str(raw_node_id)
            )[
                :8
            ]  # Limit node_id length

            # Handle memory type
            raw_memory_type = memory.get("memory_type", "unknown")
            memory_type = (
                raw_memory_type.decode("utf-8", errors="replace")
                if isinstance(raw_memory_type, bytes)
                else str(raw_memory_type)
            )[
                :6
            ]  # Shorten type

            # Handle importance score
            raw_importance = memory.get("importance_score", 0)
            if isinstance(raw_importance, bytes):
                try:
                    importance = float(raw_importance.decode())
                except ValueError:
                    importance = 0.0
            else:
                importance = float(raw_importance) if raw_importance else 0.0

            # Handle timestamp
            try:
                raw_timestamp = memory.get("timestamp", 0)
                if isinstance(raw_timestamp, bytes):
                    timestamp = int(raw_timestamp.decode())
                else:
                    timestamp = int(raw_timestamp) if raw_timestamp else 0

                if timestamp > 1000000000000:  # milliseconds
                    dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                else:  # seconds
                    dt = datetime.datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                time_str = "??:??"

            # Handle TTL
            raw_ttl = memory.get("ttl_formatted", "?")
            ttl = (
                raw_ttl.decode("utf-8", errors="replace")
                if isinstance(raw_ttl, bytes)
                else str(raw_ttl)
            )[
                :8
            ]  # Limit TTL length

            # Color code TTL
            if "h" in ttl and int(ttl.split("h")[0]) > 1:
                ttl_display = f"[green]{ttl}[/green]"
            elif "m" in ttl or ("h" in ttl and int(ttl.split("h")[0]) <= 1):
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
