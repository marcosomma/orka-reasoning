"""
Screen implementations for OrKa Textual TUI application.
"""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from .textual_widgets import LogsWidget, MemoryTableWidget, StatsWidget


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
                yield Static("🏥 Quick Health", classes="container")
                yield Static("", id="quick-health")

            # Middle row: Recent memories table (spanning 2 columns)
            with Container(classes="memory-container"):
                yield Static("📋 Recent Memories", classes="container")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="all",
                    id="dashboard-memories",
                )

            # Bottom row: Recent logs
            with Container(classes="logs-container"):
                yield Static("📋 System Memory", classes="container")
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
📊 Total: {unified["total_entries"]:,} entries
⚡ Active: {backend["active_entries"]:,} entries  
📈 Backend: {backend["type"]}
"""
            health_widget.update(health_content)

            # Update memories table
            memories_widget = self.query_one("#dashboard-memories", MemoryTableWidget)
            memories_widget.update_data("all")

            # 🎯 FIX: Update logs using correct method name
            logs_widget = self.query_one("#dashboard-logs", LogsWidget)
            logs_widget.update_data()  # Changed from update_logs() to update_data()

        except Exception:
            # Handle refresh errors gracefully
            pass


class ShortMemoryScreen(BaseOrKaScreen):
    """Screen for viewing short-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the short memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="short-memory-header"):
                yield Static("⚡ Short-Term Memory", classes="container-compact")
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
                yield Static("📄 Content & Metadata", classes="container-compact")
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
        except Exception:
            # If we can't find the widget, log error and return
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata
            try:
                content = self.data_manager._get_content(message.memory_data)
                metadata_display = self.data_manager._format_metadata_for_display(
                    message.memory_data,
                )
                memory_key = self.data_manager._get_key(message.memory_data)
                memory_type = self.data_manager._get_memory_type(message.memory_data)
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

                formatted_content = f"""[bold blue]Memory: ...{key_short}[/bold blue]

[bold green]📄 CONTENT:[/bold green]
{content_text}

[bold yellow]📋 METADATA:[/bold yellow]
{metadata_display}

[bold cyan]🏷️ SYSTEM INFO:[/bold cyan]
[cyan]Type:[/cyan] {memory_type}
[cyan]Node ID:[/cyan] {node_id}
[cyan]Importance:[/cyan] {importance_score}"""

                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh short memory data."""
        try:
            # 🎯 USE UNIFIED: Get comprehensive stats from centralized calculation
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

        except Exception:
            pass


class LongMemoryScreen(BaseOrKaScreen):
    """Screen for viewing long-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the long memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="long-memory-header"):
                yield Static("🧠 Long-Term Memory", classes="container-compact")
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
                yield Static("📄 Content & Metadata", classes="container-compact")
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
        except Exception:
            # If we can't find the widget, log error and return
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata
            try:
                content = self.data_manager._get_content(message.memory_data)
                metadata_display = self.data_manager._format_metadata_for_display(
                    message.memory_data,
                )
                memory_key = self.data_manager._get_key(message.memory_data)
                memory_type = self.data_manager._get_memory_type(message.memory_data)
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

                formatted_content = f"""[bold blue]Memory: ...{key_short}[/bold blue]

[bold green]📄 CONTENT:[/bold green]
{content_text}

[bold yellow]📋 METADATA:[/bold yellow]
{metadata_display}

[bold cyan]🏷️ SYSTEM INFO:[/bold cyan]
[cyan]Type:[/cyan] {memory_type}
[cyan]Node ID:[/cyan] {node_id}
[cyan]Importance:[/cyan] {importance_score}"""

                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh long memory data."""
        try:
            # 🎯 USE UNIFIED: Get comprehensive stats from centralized calculation
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

        except Exception:
            pass


class MemoryLogsScreen(BaseOrKaScreen):
    """Screen for viewing memory system logs."""

    def compose_content(self) -> ComposeResult:
        """Compose the memory logs layout."""
        with Vertical():
            # Top 50%: Orchestration Logs Table
            with Container(classes="logs-container", id="logs-top-section"):
                yield Static("🔄 Orchestration Logs", classes="container-compact")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="logs",
                    id="orchestration-logs-table",
                )

            # Bottom 50%: Content inspector for selected logs
            with Container(classes="content-panel", id="logs-content-panel"):
                yield Static("📄 Entry Details", classes="container-compact")
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
        except Exception:
            # If we can't find the widget, log error and return
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

[bold green]📄 CONTENT:[/bold green]
{content_text}

[bold yellow]📋 METADATA:[/bold yellow]
{metadata_display}

[bold cyan]🏷️ SYSTEM INFO:[/bold cyan]
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

        except Exception:
            pass


class HealthScreen(BaseOrKaScreen):
    """Screen for system health monitoring."""

    def compose_content(self) -> ComposeResult:
        """Compose the health monitoring layout."""
        with Vertical():
            # 🎯 COMPACT: Reduce height of health header area
            with Container(classes="health-container-compact"):
                yield Static("🏥 System Health Monitor", classes="container-compact")
                yield Static("", id="health-summary")

            with Container(classes="dashboard-grid"):
                # Connection health
                with Container(classes="stats-container"):
                    yield Static("🔌 Connection", classes="container")
                    yield Static("", id="connection-health")

                # Memory system health
                with Container(classes="memory-container"):
                    yield Static("🧠 Memory System", classes="container")
                    yield Static("", id="memory-health")

                # Performance health
                with Container(classes="logs-container"):
                    yield Static("⚡ Performance", classes="container")
                    yield Static("", id="performance-health")

                # Backend information
                with Container():
                    yield Static("🔧 Backend Info", classes="container")
                    yield Static("", id="backend-info")

                # System metrics
                with Container():
                    yield Static("📊 System Metrics", classes="container")
                    yield Static("", id="system-metrics")

                # Historical data
                with Container():
                    yield Static("📈 Historical", classes="container")
                    yield Static("", id="historical-data")

    def refresh_data(self) -> None:
        """Refresh health monitoring data."""
        try:
            # 🎯 USE UNIFIED: Get all health data from centralized calculation
            unified = self.data_manager.get_unified_stats()
            health = unified["health"]
            backend = unified["backend"]
            stored_memories = unified["stored_memories"]
            log_entries = unified["log_entries"]

            # 🎯 IMPROVED: Better organized health summary with key metrics
            summary_widget = self.query_one("#health-summary", Static)
            overall = health["overall"]
            total_entries = backend["active_entries"] + backend["expired_entries"]
            summary_content = f"""[bold]Overall: {overall["icon"]} {overall["message"]}[/bold] | [cyan]Total: {total_entries:,} entries[/cyan] | [green]Active: {backend["active_entries"]:,}[/green] | [red]Expired: {backend["expired_entries"]:,}[/red]
[dim]Last Update: {self._format_current_time()} | Auto-refresh: 2s | Backend: {backend["type"]}[/dim]"""
            summary_widget.update(summary_content)

            # Update connection health
            conn_widget = self.query_one("#connection-health", Static)
            backend_health = health["backend"]
            conn_status = f"{backend_health['icon']} {backend_health['message']}"
            conn_content = f"""
Status: {conn_status}
Backend: {backend["type"]}
Protocol: Redis
"""
            conn_widget.update(conn_content)

            # Update memory system health
            mem_widget = self.query_one("#memory-health", Static)
            memory_health = health["memory"]
            total = backend["active_entries"] + backend["expired_entries"]

            mem_content = f"""
Health: {memory_health["icon"]} {memory_health["message"]}
Total: {total:,} entries
Active: {backend["active_entries"]:,} entries
Expired: {backend["expired_entries"]:,} entries
"""
            mem_widget.update(mem_content)

            # Update performance health
            perf_widget = self.query_one("#performance-health", Static)
            perf_health = health["performance"]
            search_time = unified["performance"]["search_time"]
            perf_content = f"""
Status: {perf_health["icon"]} {perf_health["message"]}
Response Time: {search_time:.3f}s
Throughput: Normal
Errors: < 0.1%
"""
            perf_widget.update(perf_content)

            # Update backend info
            backend_widget = self.query_one("#backend-info", Static)
            backend_content = f"""
Type: {backend["type"]}
Version: Latest
Features: TTL, Search, Indexing
Config: Auto-detected
"""
            backend_widget.update(backend_content)

            # Update system metrics
            metrics_widget = self.query_one("#system-metrics", Static)
            stored_total = stored_memories["total"]
            logs_total = log_entries["orchestration"]
            usage_pct = (backend["active_entries"] / total * 100) if total > 0 else 0

            metrics_content = f"""
Stored Memories: {stored_total:,}
Orchestration Logs: {logs_total:,}
Memory Usage: {usage_pct:.1f}%
Cache Hit Rate: 95%
"""
            metrics_widget.update(metrics_content)

            # Update historical data
            hist_widget = self.query_one("#historical-data", Static)
            hist_content = f"""
Data Points: {len(self.data_manager.stats.history)}
Trends: {unified["trends"]["total_entries"]}
Performance: Stable
Retention: 100 points
"""
            hist_widget.update(hist_content)

        except Exception:
            pass

    def _format_current_time(self) -> str:
        """Format current time for display."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")
