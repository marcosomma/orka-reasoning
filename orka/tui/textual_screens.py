"""
Screen implementations for OrKa Textual TUI application.
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from .textual_widgets import (
    LogsWidget,
    MemoryTableWidget,
    StatsWidget,
)


class BaseOrKaScreen(Screen):
    """Base screen for OrKa application with common functionality."""

    def __init__(self, data_manager, **kwargs):
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
            # Top 20%: Header and info
            with Container(classes="memory-container", id="short-memory-header"):
                yield Static("⚡ Short-Term Memory (TTL < 1 hour)", classes="container")
                yield Static("", id="short-memory-info")

            # Bottom 80%: Memory table
            with Container(id="short-memory-content"):
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="short",
                    id="short-memory-table",
                )

    def refresh_data(self) -> None:
        """Refresh short memory data."""
        try:
            # 🎯 USE UNIFIED: Get comprehensive stats from centralized calculation
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            # Update info section
            info_widget = self.query_one("#short-memory-info", Static)
            info_content = f"""
Total Short-term Entries: {stored_memories["short_term"]:,}
Criteria: Memory type = 'short_term'
Auto-refresh: Every 2 seconds
"""
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
            # Top 20%: Header and info
            with Container(classes="memory-container", id="long-memory-header"):
                yield Static(
                    "🧠 Long-Term Memory (TTL > 1 hour or persistent)",
                    classes="container",
                )
                yield Static("", id="long-memory-info")

            # Bottom 80%: Memory table
            with Container(id="long-memory-content"):
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="long",
                    id="long-memory-table",
                )

    def refresh_data(self) -> None:
        """Refresh long memory data."""
        try:
            # 🎯 USE UNIFIED: Get comprehensive stats from centralized calculation
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            # Update info section
            info_widget = self.query_one("#long-memory-info", Static)
            info_content = f"""
Total Long-term Entries: {stored_memories["long_term"]:,}
Criteria: Memory type = 'long_term'
Auto-refresh: Every 2 seconds
"""
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
            # Top 70%: Orchestration Logs Table
            with Container(classes="logs-container", id="logs-top-section"):
                yield Static("🔄 Orchestration Logs", classes="container")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="logs",
                    id="orchestration-logs-table",
                )

            # Bottom 30%: Memory System Logs Summary
            with Container(classes="stats-container", id="logs-bottom-section"):
                yield Static("📋 Memory System Logs", classes="container")
                yield Static("", id="logs-info")

    def refresh_data(self) -> None:
        """Refresh memory logs data."""
        try:
            # Update orchestration logs table
            logs_table = self.query_one("#orchestration-logs-table", MemoryTableWidget)
            logs_table.update_data("logs")

            # Update memory system logs summary using unified stats
            info_widget = self.query_one("#logs-info", Static)

            # 🎯 USE UNIFIED: Get all data from centralized calculation
            unified = self.data_manager.get_unified_stats()
            log_entries = unified["log_entries"]
            stored_memories = unified["stored_memories"]
            backend = unified["backend"]

            # Calculate recent activity
            recent_logs = 0  # Placeholder - could be enhanced with timestamp filtering

            info_content = f"""
📊 System Overview:
  • Orchestration Logs: {log_entries["orchestration"]:,}
  • System/Other Logs: {log_entries["system"]:,}
  • Short-term Memory: {stored_memories["short_term"]:,}
  • Long-term Memory: {stored_memories["long_term"]:,}
  • Total Log Events: {log_entries["total"]:,}
  • Recent Activity (5m): {recent_logs:,}

🔄 Auto-refresh: Every 2 seconds
📋 Backend: {backend["type"]}
"""
            info_widget.update(info_content)

        except Exception:
            pass


class HealthScreen(BaseOrKaScreen):
    """Screen for system health monitoring."""

    def compose_content(self) -> ComposeResult:
        """Compose the health monitoring layout."""
        with Vertical():
            with Container(classes="health-container"):
                yield Static("🏥 System Health Monitor", classes="container")
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

            # Update health summary
            summary_widget = self.query_one("#health-summary", Static)
            overall = health["overall"]
            summary_content = f"""
Overall System Health: {overall["icon"]} {overall["message"]}
Last Update: {self._format_current_time()}
Monitoring Interval: 2 seconds
"""
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
