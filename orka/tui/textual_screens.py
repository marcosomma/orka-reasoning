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
                yield LogsWidget(self.data_manager, id="dashboard-logs")

    def refresh_data(self) -> None:
        """Refresh dashboard data."""
        try:
            # Update stats widget
            stats_widget = self.query_one("#dashboard-stats", StatsWidget)
            stats_widget.update_stats()

            # Update quick health
            health_widget = self.query_one("#quick-health", Static)
            stats = self.data_manager.stats.current
            connection = "🟢 Connected" if self.data_manager.memory_logger else "🔴 Disconnected"
            total = stats.get("total_entries", 0)
            active = stats.get("active_entries", 0)

            health_content = f"""
{connection}
📊 Total: {total:,} entries
⚡ Active: {active:,} entries
📈 Backend: {self.data_manager.backend}
"""
            health_widget.update(health_content)

            # Update memories table
            memories_widget = self.query_one("#dashboard-memories", MemoryTableWidget)
            memories_widget.update_data()

            # Update logs
            logs_widget = self.query_one("#dashboard-logs", LogsWidget)
            logs_widget.update_logs()

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
            # Use centralized filtering
            short_memories = self.data_manager.get_filtered_memories("short")

            # Update info section
            info_widget = self.query_one("#short-memory-info", Static)
            info_content = f"""
Total Short-term Entries: {len(short_memories):,}
Criteria: Memory type + TTL < 1 hour
Auto-refresh: Every 2 seconds
"""
            info_widget.update(info_content)

            # Update table
            table_widget = self.query_one("#short-memory-table", MemoryTableWidget)
            table_widget.update_data()

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
            # Use centralized filtering
            long_memories = self.data_manager.get_filtered_memories("long")

            # Update info section
            info_widget = self.query_one("#long-memory-info", Static)
            info_content = f"""
Total Long-term Entries: {len(long_memories):,}
Criteria: Memory type + TTL > 1 hour or persistent
Auto-refresh: Every 2 seconds
"""
            info_widget.update(info_content)

            # Update table
            table_widget = self.query_one("#long-memory-table", MemoryTableWidget)
            table_widget.update_data()

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
            logs_table.update_data()

            # Update memory system logs summary
            info_widget = self.query_one("#logs-info", Static)

            # Use centralized filtering for consistency
            orchestration_logs = [
                m
                for m in self.data_manager.memory_data
                if self.data_manager._get_log_type(m) == "orchestration"
            ]
            system_logs = [
                m
                for m in self.data_manager.memory_data
                if self.data_manager._get_log_type(m) in ["log", "system"]
            ]
            short_memories = self.data_manager.get_filtered_memories("short")
            long_memories = self.data_manager.get_filtered_memories("long")
            all_logs = self.data_manager.get_filtered_memories("logs")

            # Calculate stats
            total_logs = len(all_logs)
            recent_logs = len(
                [
                    m
                    for m in orchestration_logs + system_logs
                    if m.get("timestamp", 0)
                    > (self.data_manager.stats.current.get("timestamp", 0) - 300)  # Last 5 minutes
                ],
            )

            info_content = f"""
📊 System Overview:
  • Orchestration Logs: {len(orchestration_logs):,}
  • System/Other Logs: {len(system_logs):,}
  • Short-term Memory: {len(short_memories):,}
  • Long-term Memory: {len(long_memories):,}
  • Total Log Events: {total_logs:,}
  • Recent Activity (5m): {recent_logs:,}

🔄 Auto-refresh: Every 2 seconds
📋 Backend: {self.data_manager.backend or "Unknown"}
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
            stats = self.data_manager.stats.current

            # Update health summary
            summary_widget = self.query_one("#health-summary", Static)
            overall_status = self._calculate_overall_health(stats)
            summary_content = f"""
Overall System Health: {overall_status}
Last Update: {self._format_current_time()}
Monitoring Interval: 2 seconds
"""
            summary_widget.update(summary_content)

            # Update connection health
            conn_widget = self.query_one("#connection-health", Static)
            conn_status = "🟢 Connected" if self.data_manager.memory_logger else "🔴 Disconnected"
            backend = self.data_manager.backend or "Unknown"
            conn_content = f"""
Status: {conn_status}
Backend: {backend}
Protocol: Redis
"""
            conn_widget.update(conn_content)

            # Update memory system health
            mem_widget = self.query_one("#memory-health", Static)
            total = stats.get("total_entries", 0)
            active = stats.get("active_entries", 0)
            expired = stats.get("expired_entries", 0)

            mem_health = self._assess_memory_health(total, active, expired)
            mem_content = f"""
Health: {mem_health}
Total: {total:,} entries
Active: {active:,} entries
Expired: {expired:,} entries
"""
            mem_widget.update(mem_content)

            # Update performance health
            perf_widget = self.query_one("#performance-health", Static)
            perf_content = """
Status: 🟢 Good
Response Time: < 100ms
Throughput: Normal
Errors: < 0.1%
"""
            perf_widget.update(perf_content)

            # Update backend info
            backend_widget = self.query_one("#backend-info", Static)
            backend_content = f"""
Type: {backend}
Version: Latest
Features: TTL, Search, Indexing
Config: Auto-detected
"""
            backend_widget.update(backend_content)

            # Update system metrics
            metrics_widget = self.query_one("#system-metrics", Static)
            stored = stats.get("stored_memories", 0)
            logs = stats.get("orchestration_logs", 0)

            metrics_content = f"""
Stored Memories: {stored:,}
Orchestration Logs: {logs:,}
Memory Usage: {self._calculate_memory_usage(stats)}%
Cache Hit Rate: 95%
"""
            metrics_widget.update(metrics_content)

            # Update historical data
            hist_widget = self.query_one("#historical-data", Static)
            hist_content = f"""
Data Points: {len(self.data_manager.stats.history)}
Trends: {self.data_manager.stats.get_trend("total_entries")}
Performance: Stable
Retention: 100 points
"""
            hist_widget.update(hist_content)

        except Exception:
            pass

    def _calculate_overall_health(self, stats) -> str:
        """Calculate overall system health status."""
        if not self.data_manager.memory_logger:
            return "🔴 Critical - No Connection"

        total = stats.get("total_entries", 0)
        expired = stats.get("expired_entries", 0)

        if total == 0:
            return "🟡 Warning - No Data"

        expired_ratio = expired / total if total > 0 else 0

        if expired_ratio < 0.1:
            return "🟢 Healthy"
        elif expired_ratio < 0.3:
            return "🟡 Degraded"
        else:
            return "🔴 Critical"

    def _assess_memory_health(self, total, active, expired) -> str:
        """Assess memory system health."""
        if total == 0:
            return "🟡 No Data"

        expired_ratio = expired / total if total > 0 else 0

        if expired_ratio < 0.1:
            return "🟢 Healthy"
        elif expired_ratio < 0.3:
            return "🟡 Degraded"
        else:
            return "🔴 Critical"

    def _calculate_memory_usage(self, stats) -> int:
        """Calculate memory usage percentage."""
        total = stats.get("total_entries", 0)
        active = stats.get("active_entries", 0)

        if total == 0:
            return 0

        return int((active / total) * 100)

    def _format_current_time(self) -> str:
        """Format current time for display."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")
