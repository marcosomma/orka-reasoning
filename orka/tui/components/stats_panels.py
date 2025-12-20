# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Stats Panel Component Builders."""

try:
    from rich.box import ROUNDED
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class StatsPanelMixin:
    """Mixin providing statistics panel builders."""

    # Expected from host class
    stats: object
    memory_logger: object
    backend: str
    performance_history: list

    def create_compact_stats_panel(self):
        """Create a compact stats panel with comprehensive metrics."""
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
        core_metrics = [
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

    def create_stats_panel(self):
        """Create comprehensive memory statistics panel with trending."""
        if not self.stats.current:
            return Panel("Loading statistics...", title="📊 Memory Statistics")

        stats = self.stats.current

        # Create statistics table with trending information
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=18)
        table.add_column(style="white", width=12)
        table.add_column(style="green", width=8)
        table.add_column(style="yellow", width=6)

        # Core metrics with trends
        core_metrics = [
            ("Total Entries", stats.get("total_entries", 0), "entries"),
            ("Stored Memories", stats.get("stored_memories", 0), "memories"),
            ("Orchestration Logs", stats.get("orchestration_logs", 0), "logs"),
            ("Active Entries", stats.get("active_entries", 0), "active"),
            ("Expired Entries", stats.get("expired_entries", 0), "expired"),
        ]

        table.add_row("[bold]Core Metrics:[/bold]", "", "", "")

        for name, value, unit in core_metrics:
            # Get trend and rate information
            key = name.lower().replace(" ", "_")
            trend = self.stats.get_trend(key)
            rate = self.stats.get_rate(key)

            # Format rate display
            if abs(rate) > 0.01:
                if rate > 0:
                    rate_text = f"[green]+{rate:.1f}/s[/green]"
                else:
                    rate_text = f"[red]{rate:.1f}/s[/red]"
            else:
                rate_text = "[dim]stable[/dim]"

            # Trend icon with color
            if trend == "↗":
                trend_display = "[green]↗[/green]"
            elif trend == "↘":
                trend_display = "[red]↘[/red]"
            else:
                trend_display = "[dim]→[/dim]"

            table.add_row(
                f"  {name}",
                f"[bold]{value:,}[/bold]",
                unit,
                f"{trend_display} {rate_text}",
            )

        # Backend health indicators
        table.add_row("", "", "", "")  # Separator
        table.add_row("[bold]Backend Health:[/bold]", "", "", "")

        # Decay status
        decay_enabled = stats.get("decay_enabled", False)
        decay_status = "✅ Active" if decay_enabled else "❌ Inactive"
        table.add_row("  Memory Decay", decay_status, "", "")

        # Backend type with status
        backend_status = "✅ Online" if hasattr(self.memory_logger, "client") else "❌ Offline"
        table.add_row("  Backend", f"{self.backend.upper()}", backend_status, "")

        # Performance indicator
        if self.performance_history:
            latest_perf = self.performance_history[-1]
            avg_search_time = latest_perf.get("average_search_time", 0)
            if avg_search_time < 0.1:
                perf_status = "[green]⚡ Fast[/green]"
            elif avg_search_time < 0.5:
                perf_status = "[yellow]⚠ Moderate[/yellow]"
            else:
                perf_status = "[red]🐌 Slow[/red]"
            table.add_row("  Performance", perf_status, f"{avg_search_time:.3f}s", "")

        return Panel(table, title="📊 Memory Statistics & Health", box=ROUNDED)

