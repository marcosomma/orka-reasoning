# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Screen implementations for OrKa Textual TUI application.
"""

import logging
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from .textual_widgets import LogsWidget, MemoryTableWidget, StatsWidget
from .message_renderer import VintageMessageRenderer

logger = logging.getLogger(__name__)


class BaseOrKaScreen(Screen):
    """Base screen for OrKa application with common functionality."""

    def __init__(self, data_manager: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data_manager = data_manager

    def compose(self) -> ComposeResult:
        """Base compose method with header and footer."""
        yield Header()
        yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        """Override this method in subclasses."""
        yield Static("Base screen - override compose_content()")

    def on_mount(self) -> None:
        """Handle mounting of the screen."""
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh screen data - override in subclasses."""


class DashboardScreen(BaseOrKaScreen):
    """Dashboard screen showing overview of memory system."""

    def compose_content(self) -> ComposeResult:
        """Compose the dashboard layout."""
        with Container(classes="dashboard-grid"):
            # Top row: Stats and quick health
            with Container(classes="stats-container"):
                yield StatsWidget(self.data_manager, id="dashboard-stats")

            with Container(classes="health-container"):
                yield Static("[HEALTH] Quick Health", classes="container")
                yield Static("", id="quick-health")

            # Middle row: Recent memories table (spanning 2 columns)
            with Container(classes="memory-container"):
                yield Static("[LIST] Recent Memories", classes="container")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="all",
                    id="dashboard-memories",
                )

            # Bottom row: Recent logs
            with Container(classes="logs-container"):
                yield Static("[LIST] System Memory", classes="container")
                yield LogsWidget(self.data_manager, id="dashboard-logs")

    def refresh_data(self) -> None:
        """Refresh dashboard data."""
        try:
            # Update stats widget
            stats_widget = self.query_one("#dashboard-stats", StatsWidget)
            stats_widget.update_stats()

            # Update quick health using unified stats
            health_widget = self.query_one("#quick-health", Static)
            unified = self.data_manager.get_unified_stats()
            health = unified["health"]
            backend = unified["backend"]

            # Format health status with icons
            connection_status = f"{health['backend']['icon']} {health['backend']['message']}"
            health_content = f"""
{connection_status}
[STATS] Total: {unified["total_entries"]:,} entries
[FAST] Active: {backend["active_entries"]:,} entries  
[PERF] Backend: {backend["type"]}
"""
            health_widget.update(health_content)

            # Update memories table
            memories_widget = self.query_one("#dashboard-memories", MemoryTableWidget)
            memories_widget.update_data("all")

            # [TARGET] FIX: Update logs using correct method name
            logs_widget = self.query_one("#dashboard-logs", LogsWidget)
            logs_widget.update_data()  # Changed from update_logs() to update_data()

        except Exception as e:
            # Handle refresh errors gracefully
            logger.debug(f"TUI dashboard refresh error (non-fatal): {e}")


class ShortMemoryScreen(BaseOrKaScreen):
    """Screen for viewing short-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the short memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="short-memory-header"):
                yield Static("[FAST] Short-Term Memory", classes="container-compact")
                yield Static("", id="short-memory-info")

            # Middle section: Memory table
            with Container(id="short-memory-content"):
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="short",
                    id="short-memory-table",
                )

            # Bottom section: Content and Metadata viewer
            with Container(classes="content-panel", id="short-content-panel"):
                yield Static("[FILE] Content & Metadata", classes="container-compact")
                with Container(id="short-selected-content"):
                    yield Static(
                        "[dim]Select a row to view memory content and metadata[/dim]",
                        id="short-content-text",
                    )

    def on_memory_table_widget_memory_selected(
        self,
        message: MemoryTableWidget.MemorySelected,
    ) -> None:
        """Handle memory selection to show content and metadata in lower panel."""
        content_widget = None
        try:
            content_widget = self.query_one("#short-content-text", Static)
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI short-content-text widget not found (non-fatal): {e}")
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata using VintageMessageRenderer
            try:
                # Use the advanced message renderer for better formatting
                renderer = VintageMessageRenderer(theme="default")
                formatted_content = renderer.render_memory_content(
                    message.memory_data,
                    show_full_key=False
                )
                
                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh short memory data."""
        try:
            # [TARGET] USE UNIFIED: Get comprehensive stats from centralized calculation
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            # Update info section - condensed
            info_widget = self.query_one("#short-memory-info", Static)
            info_content = (
                f"[cyan]{stored_memories['short_term']:,}[/cyan] entries | Auto-refresh: 2s"
            )
            info_widget.update(info_content)

            # Update table
            table_widget = self.query_one("#short-memory-table", MemoryTableWidget)
            table_widget.update_data("short")

        except Exception as e:
            logger.debug(f"TUI short memory refresh error (non-fatal): {e}")


class LongMemoryScreen(BaseOrKaScreen):
    """Screen for viewing long-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the long memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="long-memory-header"):
                yield Static("[AI] Long-Term Memory", classes="container-compact")
                yield Static("", id="long-memory-info")

            # Middle section: Memory table
            with Container(id="long-memory-content"):
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="long",
                    id="long-memory-table",
                )

            # Bottom section: Content and Metadata viewer
            with Container(classes="content-panel", id="long-content-panel"):
                yield Static("[FILE] Content & Metadata", classes="container-compact")
                with Container(id="long-selected-content"):
                    yield Static(
                        "[dim]Select a row to view memory content and metadata[/dim]",
                        id="long-content-text",
                    )

    def on_memory_table_widget_memory_selected(
        self,
        message: MemoryTableWidget.MemorySelected,
    ) -> None:
        """Handle memory selection to show content and metadata in lower panel."""
        content_widget = None
        try:
            content_widget = self.query_one("#long-content-text", Static)
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI long-content-text widget not found (non-fatal): {e}")
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata using VintageMessageRenderer
            try:
                # Use the advanced message renderer for better formatting
                renderer = VintageMessageRenderer(theme="default")
                formatted_content = renderer.render_memory_content(
                    message.memory_data,
                    show_full_key=False
                )
                
                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh long memory data."""
        try:
            # [TARGET] USE UNIFIED: Get comprehensive stats from centralized calculation
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            # Update info section - condensed
            info_widget = self.query_one("#long-memory-info", Static)
            info_content = (
                f"[cyan]{stored_memories['long_term']:,}[/cyan] entries | Auto-refresh: 2s"
            )
            info_widget.update(info_content)

            # Update table
            table_widget = self.query_one("#long-memory-table", MemoryTableWidget)
            table_widget.update_data("long")

        except Exception as e:
            logger.debug(f"TUI long memory refresh error (non-fatal): {e}")


class MemoryLogsScreen(BaseOrKaScreen):
    """Screen for viewing memory system logs."""

    def compose_content(self) -> ComposeResult:
        """Compose the memory logs layout."""
        with Vertical():
            # Top 50%: Orchestration Logs Table
            with Container(classes="logs-container", id="logs-top-section"):
                yield Static("[SYNC] Orchestration Logs", classes="container-compact")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="logs",
                    id="orchestration-logs-table",
                )

            # Bottom 50%: Content inspector for selected logs
            with Container(classes="content-panel", id="logs-content-panel"):
                yield Static("[FILE] Entry Details", classes="container-compact")
                with Container(id="logs-selected-content"):
                    yield Static(
                        "[dim]Select a row to view entry details and metadata[/dim]",
                        id="logs-content-text",
                    )

    def on_memory_table_widget_memory_selected(
        self,
        message: MemoryTableWidget.MemorySelected,
    ) -> None:
        """Handle memory selection to show content and metadata in lower panel."""
        content_widget = None
        try:
            content_widget = self.query_one("#logs-content-text", Static)
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI logs-content-text widget not found (non-fatal): {e}")
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view entry details and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata
            try:
                content = self.data_manager._get_content(message.memory_data)
                metadata_display = self.data_manager._format_metadata_for_display(
                    message.memory_data,
                )
                memory_key = self.data_manager._get_key(message.memory_data)
                log_type = self.data_manager._get_log_type(message.memory_data)
                importance_score = self.data_manager._get_importance_score(message.memory_data)
                node_id = self.data_manager._get_node_id(message.memory_data)

                # Format content
                if content is None or str(content).strip() == "":
                    content_text = "[dim]No content[/dim]"
                else:
                    content_str = str(content)
                    # Don't truncate content - let users scroll to see everything
                    content_text = content_str

                # Build comprehensive display
                key_short = memory_key[-20:] if len(memory_key) > 20 else memory_key

                formatted_content = f"""[bold blue]Entry: ...{key_short}[/bold blue]

[bold green][FILE] CONTENT:[/bold green]
{content_text}

[bold yellow][LIST] METADATA:[/bold yellow]
{metadata_display}

[bold cyan][TAG]️ SYSTEM INFO:[/bold cyan]
[cyan]Log Type:[/cyan] {log_type}
[cyan]Node ID:[/cyan] {node_id}
[cyan]Importance:[/cyan] {importance_score}"""

                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh memory logs data."""
        try:
            # Update orchestration logs table
            logs_table = self.query_one("#orchestration-logs-table", MemoryTableWidget)
            logs_table.update_data("logs")

        except Exception as e:
            logger.debug(f"TUI memory logs refresh error (non-fatal): {e}")


class HealthScreen(BaseOrKaScreen):
    """Screen for system health monitoring."""

    def compose_content(self) -> ComposeResult:
        """Compose the health monitoring layout - single unified box with styled sections."""
        with Container(classes="health-main-container"):
            # Header with overall status
            yield Static("[HEALTH] System Health Monitor", classes="container")
            yield Static("", id="health-summary")
            
            # All sections in one container
            yield Static("", id="health-details")

    def refresh_data(self) -> None:
        """Refresh health monitoring data."""
        try:
            # Get all health data from centralized calculation
            unified = self.data_manager.get_unified_stats()
            health = unified["health"]
            backend = unified["backend"]
            stored_memories = unified["stored_memories"]
            log_entries = unified["log_entries"]

            # Calculate metrics
            overall = health["overall"]
            backend_health = health["backend"]
            memory_health = health["memory"]
            perf_health = health["performance"]
            total_entries = backend["active_entries"] + backend["expired_entries"]
            search_time = unified["performance"]["search_time"]
            stored_total = stored_memories["total"]
            logs_total = log_entries["orchestration"]
            usage_pct = (backend["active_entries"] / total_entries * 100) if total_entries > 0 else 0
            data_points = len(self.data_manager.stats.history)
            trend = unified["trends"]["total_entries"]

            # Update summary
            summary_widget = self.query_one("#health-summary", Static)
            summary_content = f"""[bold]Overall:[/bold] {overall["icon"]} {overall["message"]} [dim]│[/dim] [cyan]Total:[/cyan] {total_entries:,} [dim]│[/dim] [green]Active:[/green] {backend["active_entries"]:,} [dim]│[/dim] [red]Expired:[/red] {backend["expired_entries"]:,}
[dim]Last Update: {self._format_current_time()} │ Auto-refresh: 2s │ Backend: {backend["type"]}[/dim]"""
            summary_widget.update(summary_content)

            # Build unified details content with visual headers
            details_content = f"""
[bold yellow][CONN] CONNECTION[/bold yellow]
   Status: {backend_health["icon"]} {backend_health["message"]}
   Backend: {backend["type"]}
   Protocol: Redis

[bold magenta][AI] MEMORY SYSTEM[/bold magenta]
   Health: {memory_health["icon"]} {memory_health["message"]}
   Total: {total_entries:,} entries
   Active: {backend["active_entries"]:,} entries
   Expired: {backend["expired_entries"]:,} entries

[bold green][FAST] PERFORMANCE[/bold green]
   Status: {perf_health["icon"]} {perf_health["message"]}
   Response Time: {search_time:.3f}s
   Throughput: Normal
   Errors: < 0.1%

[bold blue][CONF] BACKEND INFO[/bold blue]
   Type: {backend["type"]}
   Version: Latest
   Features: TTL, Search, Indexing
   Config: Auto-detected

[bold white][STATS] SYSTEM METRICS[/bold white]
   Stored Memories: {stored_total:,}
   Orchestration Logs: {logs_total:,}
   Memory Usage: {usage_pct:.1f}%
   Cache Hit Rate: 95%

[bold cyan][PERF] HISTORICAL[/bold cyan]
   Data Points: {data_points:,}
   Trends: {trend}
   Performance: Stable
   Retention: 100 points"""

            # Update the details widget
            details_widget = self.query_one("#health-details", Static)
            details_widget.update(details_content)

        except Exception as e:
            # Log error to help diagnose issues
            import logging
            logging.getLogger(__name__).warning(f"HealthScreen refresh_data error: {e}")

    def _format_current_time(self) -> str:
        """Format current time for display."""
        return datetime.now().strftime("%H:%M:%S")


class HelpScreen(Screen):
    """Help screen with vintage-style keybinding reference."""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the help screen with ASCII art help panel."""
        help_text = """
╔═════════════════════════════════════════════════════════╗
║              ORKA MEMORY MONITOR - HELP                 ║
║                   QUICK REFERENCE                       ║
╠═════════════════════════════════════════════════════════╣
║                                                         ║
║  [bold cyan]NAVIGATION:[/bold cyan]                                          ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ 1-5        Switch views                         │   ║
║  │ j/k        Navigate up/down (vim-style)         │   ║
║  │ g/G        Jump to top/bottom                   │   ║
║  │ tab        Focus next widget                    │   ║
║  │ enter      Select/expand item                   │   ║
║  │ esc        Go back/close                        │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]VIEWS:[/bold cyan]                                               ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ 1          Dashboard (overview)                 │   ║
║  │ 2          Short-term memory                    │   ║
║  │ 3          Long-term memory                     │   ║
║  │ 4          Memory logs                          │   ║
║  │ 5          Health & diagnostics                 │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]ACTIONS:[/bold cyan]                                             ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ r          Refresh data                         │   ║
║  │ ctrl+p     Command palette (change theme, etc.) │   ║
║  │ e          Export visible data to JSON          │   ║
║  │ f          Toggle fullscreen                    │   ║
║  │ ?          Show this help                       │   ║
║  │ q          Quit application                     │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]TIPS:[/bold cyan]                                                ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ • Use vim keys (j/k) for faster navigation      │   ║
║  │ • Press Ctrl+P to open command palette          │   ║
║  │ • Type 'theme' in palette to change themes      │   ║
║  │ • Available: default, orka-vintage, orka-dark   │   ║
║  │ • Select rows to view full content              │   ║
║  │ • Export saves current view to JSON file        │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
╚═════════════════════════════════════════════════════════╝

[dim]Press ESC or Q to close this help screen...[/dim]
        """
        
        yield Header()
        yield Container(
            Static(help_text, classes="help-screen"),
            classes="help-container"
        )
        yield Footer()
    
    def action_dismiss(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
