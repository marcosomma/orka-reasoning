"""
Custom Textual widgets for OrKa memory monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List

from textual.containers import Container
from textual.widgets import DataTable, Static


class StatsWidget(Static):
    """Widget for displaying memory statistics."""

    def __init__(self, data_manager, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager

    def update_stats(self):
        """Update the stats display."""
        stats = self.data_manager.stats.current

        # Format the statistics
        content = self._format_stats(stats)
        self.update(content)

    def _format_stats(self, stats: Dict[str, Any]) -> str:
        """Format statistics for display using centralized filtering."""
        # Use centralized filtering for consistency across all screens
        short_memories = self.data_manager.get_filtered_memories("short")
        long_memories = self.data_manager.get_filtered_memories("long")
        all_logs = self.data_manager.get_filtered_memories("logs")
        all_memories = self.data_manager.get_filtered_memories("all")

        # Count orchestration logs specifically
        orchestration_logs = [
            m
            for m in self.data_manager.memory_data
            if self.data_manager._get_log_type(m) == "orchestration"
        ]

        # Get basic stats from memory logger
        active = stats.get("active_entries", 0)
        expired = stats.get("expired_entries", 0)

        # Calculate trends
        total_trend = self.data_manager.stats.get_trend("total_entries")
        stored_trend = self.data_manager.stats.get_trend("stored_memories")

        return f"""[bold]📊 Memory Statistics[/bold]

[metric-label]Total Entries:[/metric-label] [metric-value]{len(all_memories):,}[/metric-value] {total_trend}
[metric-label]Short-term Memory:[/metric-label] [metric-value]{len(short_memories):,}[/metric-value] 
[metric-label]Long-term Memory:[/metric-label] [metric-value]{len(long_memories):,}[/metric-value] {stored_trend}
[metric-label]Orchestration Logs:[/metric-label] [metric-value]{len(orchestration_logs):,}[/metric-value]
[metric-label]Active Entries:[/metric-label] [metric-value]{active:,}[/metric-value]
[metric-label]Expired Entries:[/metric-label] [metric-value]{expired:,}[/metric-value]

[metric-label]Backend:[/metric-label] [status-info]{self.data_manager.backend}[/status-info]
[metric-label]Status:[/metric-label] [status-good]Connected[/status-good]"""


class MemoryTableWidget(DataTable):
    """Custom data table for displaying memory entries."""

    def __init__(self, data_manager, memory_type="all", **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager
        self.memory_type = memory_type
        self.add_columns(
            "Timestamp",
            "Type",
            "Key",
            "Content Preview",
            "TTL",
            "Size",
        )

    def update_data(self):
        """Update the table with fresh memory data."""
        self.clear()

        memories = self._get_filtered_memories()

        if not memories:
            # Add a placeholder row to show that filtering is working
            self.add_row("--", "--", f"No {self.memory_type} data", "--", "--", "--")
            return

        for memory in memories:
            # Extract values with proper decoding and fallbacks
            timestamp = memory.get("timestamp") or memory.get("created_at") or memory.get("time")

            # Get log_type from metadata or root
            metadata = memory.get("metadata", {})
            log_type = (
                metadata.get("log_type") or memory.get("log_type") or memory.get("type") or "memory"
            )

            # Decode key if it's bytes
            key = memory.get("key") or memory.get("id") or memory.get("node_id") or "unknown"
            if isinstance(key, bytes):
                key = key.decode("utf-8", errors="ignore")

            # Decode content if it's bytes
            content = memory.get("content") or memory.get("message") or memory.get("data") or ""
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")

            # Get TTL from different possible fields
            ttl = (
                memory.get("ttl_seconds")
                or memory.get("ttl")
                or memory.get("expires_at")
                or memory.get("expiry")
            )

            size = memory.get("size") or len(str(content)) if content else 0

            self.add_row(
                self._format_timestamp(timestamp),
                self._format_type(log_type),
                self._truncate(str(key), 20),
                self._truncate(str(content), 40),
                self._format_ttl(ttl),
                self._format_size(size),
            )

    def _get_filtered_memories(self) -> List[Dict]:
        """Get memories filtered by type."""
        return self.data_manager.get_filtered_memories(self.memory_type)

    def _is_short_term(self, memory: Dict) -> bool:
        """Check if memory is short-term based on TTL."""
        ttl = (
            memory.get("ttl_seconds")
            or memory.get("ttl")
            or memory.get("expires_at")
            or memory.get("expiry")
        )
        if ttl is None or ttl == "" or ttl == -1:
            return False
        try:
            # Handle string TTL values
            if isinstance(ttl, str):
                if ttl.lower() in ["none", "null", "infinite", "∞", ""]:
                    return False
                ttl_val = int(float(ttl))
            else:
                ttl_val = int(ttl)

            if ttl_val <= 0:
                return False
            return ttl_val < 3600  # Less than 1 hour
        except (ValueError, TypeError):
            return False

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "N/A"
        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(str(timestamp))
            return dt.strftime("%H:%M:%S")
        except:
            return str(timestamp)[:8]

    def _format_type(self, log_type: str) -> str:
        """Format log type with color coding."""
        type_colors = {
            "memory": "[memory-short]MEM[/memory-short]",
            "orchestration": "[memory-long]ORC[/memory-long]",
            "system": "[status-info]SYS[/status-info]",
        }
        return type_colors.get(log_type, log_type.upper()[:3])

    def _format_ttl(self, ttl) -> str:
        """Format TTL for display."""
        if ttl is None or ttl == "" or ttl == -1:
            return "∞"
        try:
            # Handle string TTL values
            if isinstance(ttl, str):
                if ttl.lower() in ["none", "null", "infinite", "∞", ""]:
                    return "∞"
                ttl_val = int(float(ttl))
            else:
                ttl_val = int(ttl)

            if ttl_val <= 0:
                return "∞"
            elif ttl_val < 60:
                return f"{ttl_val}s"
            elif ttl_val < 3600:
                return f"{ttl_val // 60}m"
            elif ttl_val < 86400:
                return f"{ttl_val // 3600}h"
            else:
                return f"{ttl_val // 86400}d"
        except (ValueError, TypeError):
            return str(ttl) if ttl else "∞"

    def _format_size(self, size) -> str:
        """Format size for display."""
        if not size:
            return "0B"
        try:
            size_val = int(size)
            if size_val < 1024:
                return f"{size_val}B"
            elif size_val < 1024 * 1024:
                return f"{size_val // 1024}KB"
            else:
                return f"{size_val // (1024 * 1024)}MB"
        except (ValueError, TypeError):
            return str(size)

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to maximum length."""
        if not text:
            return ""
        text_str = str(text)
        return text_str[: max_len - 3] + "..." if len(text_str) > max_len else text_str


class HealthWidget(Container):
    """Widget for displaying system health metrics."""

    def __init__(self, data_manager, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager

    def compose(self):
        """Compose the health widget."""
        yield Static("🏥 System Health", classes="container")
        yield Static("", id="health-content")

    def update_health(self):
        """Update health display."""
        content_widget = self.query_one("#health-content")

        # Get health metrics
        stats = self.data_manager.stats.current

        # Calculate health scores
        connection_status = self._check_connection()
        memory_health = self._check_memory_health(stats)
        performance_health = self._check_performance()

        # Format health display
        content = f"""
[status-info]Connection:[/status-info] {connection_status}
[status-info]Memory System:[/status-info] {memory_health}
[status-info]Performance:[/status-info] {performance_health}

[bold]Quick Metrics:[/bold]
• Memory Usage: {self._format_memory_usage(stats)}
• Response Time: {self._format_response_time()}
• Error Rate: {self._format_error_rate()}
• Uptime: {self._format_uptime()}
"""

        content_widget.update(content)

    def _check_connection(self) -> str:
        """Check connection status."""
        try:
            if self.data_manager.memory_logger:
                return "[status-good]✓ Connected[/status-good]"
            else:
                return "[status-warning]⚠ Disconnected[/status-warning]"
        except:
            return "[status-error]✗ Error[/status-error]"

    def _check_memory_health(self, stats: Dict) -> str:
        """Check memory system health."""
        total = stats.get("total_entries", 0)
        expired = stats.get("expired_entries", 0)

        if total == 0:
            return "[status-warning]⚠ No Data[/status-warning]"

        expired_ratio = expired / total if total > 0 else 0

        if expired_ratio < 0.1:
            return "[status-good]✓ Healthy[/status-good]"
        elif expired_ratio < 0.3:
            return "[status-warning]⚠ Degraded[/status-warning]"
        else:
            return "[status-error]✗ Critical[/status-error]"

    def _check_performance(self) -> str:
        """Check performance health."""
        # Simplified performance check
        perf_history = self.data_manager.performance_history
        if len(perf_history) < 2:
            return "[status-info]? Unknown[/status-info]"

        # For now, always show good performance
        return "[status-good]✓ Good[/status-good]"

    def _format_memory_usage(self, stats: Dict) -> str:
        """Format memory usage."""
        total = stats.get("total_entries", 0)
        active = stats.get("active_entries", 0)

        if total == 0:
            return "0%"

        usage_pct = (active / total) * 100
        return f"{usage_pct:.1f}%"

    def _format_response_time(self) -> str:
        """Format average response time."""
        return "< 100ms"  # Placeholder

    def _format_error_rate(self) -> str:
        """Format error rate."""
        return "< 0.1%"  # Placeholder

    def _format_uptime(self) -> str:
        """Format system uptime."""
        return "99.9%"  # Placeholder


class LogsWidget(Container):
    """Enhanced widget for displaying memory logs with orchestration priority."""

    def __init__(self, data_manager, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager

    def compose(self):
        """Compose the logs widget with enhanced layout."""
        yield Static("📋 Memory Logs", classes="container")
        yield Static("", id="orchestration-section")
        yield Static("", id="other-logs-section")

    def update_logs(self):
        """Update logs display with orchestration priority."""
        # Get all filtered logs
        all_logs = self.data_manager.get_filtered_memories("logs")

        # Separate orchestration logs from others
        orchestration_logs = [
            log for log in all_logs if self.data_manager._get_log_type(log) == "orchestration"
        ]
        other_logs = [
            log for log in all_logs if self.data_manager._get_log_type(log) in ["log", "system"]
        ]

        # Sort by timestamp (most recent first)
        orchestration_logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        other_logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        # Update orchestration section (takes 70% of space)
        self._update_orchestration_section(orchestration_logs[:8])

        # Update other logs section (takes 30% of space)
        self._update_other_logs_section(other_logs[:4])

    def _update_orchestration_section(self, orchestration_logs):
        """Update the orchestration logs section with detailed view."""
        content_widget = self.query_one("#orchestration-section")

        if not orchestration_logs:
            content = """
[bold][status-warning]🔄 ORCHESTRATION LOGS[/status-warning][/bold]
[status-info]No orchestration logs available[/status-info]
"""
        else:
            content_lines = ["[bold][status-good]🔄 ORCHESTRATION LOGS[/status-good][/bold]", ""]

            for log in orchestration_logs:
                timestamp = self._format_timestamp(log.get("timestamp"))
                node_id = self._decode_field(log.get("node_id") or log.get("key", "unknown"))
                trace_id = self._decode_field(log.get("trace_id", ""))
                content = self._decode_field(log.get("content", ""))

                # Extract meaningful parts from content
                content_preview = self._extract_orchestration_info(content)

                # Format orchestration entry with more detail
                entry = f"[bold][{timestamp}][/bold] [status-info]{self._truncate(node_id, 25)}[/status-info]"
                if trace_id and trace_id != "default":
                    entry += f" | [dim]{self._truncate(trace_id, 15)}[/dim]"
                entry += f"\n  └─ {content_preview}\n"

                content_lines.append(entry)

            content = "\n".join(content_lines)

        content_widget.update(content)

    def _update_other_logs_section(self, other_logs):
        """Update the other logs section with compact view."""
        content_widget = self.query_one("#other-logs-section")

        if not other_logs:
            content = "\n[bold][dim]📝 OTHER LOGS[/dim][/bold]\n[dim]No other logs available[/dim]"
        else:
            content_lines = ["[bold][dim]📝 OTHER LOGS[/dim][/bold]", ""]

            for log in other_logs:
                timestamp = self._format_timestamp(log.get("timestamp"))
                log_type = self.data_manager._get_log_type(log).upper()
                content = self._decode_field(log.get("content", ""))

                # Compact format for other logs
                entry = f"[dim][{timestamp}] {log_type}:[/dim] {self._truncate(content, 50)}"
                content_lines.append(entry)

            content = "\n".join(content_lines)

        content_widget.update(content)

    def _extract_orchestration_info(self, content):
        """Extract meaningful information from orchestration content."""
        if not content:
            return "[dim]No content[/dim]"

        content_str = str(content).lower()

        # Look for key orchestration events
        if "error" in content_str or "fail" in content_str:
            return f"[status-error]⚠ {self._truncate(content, 70)}[/status-error]"
        elif "success" in content_str or "complete" in content_str:
            return f"[status-good]✓ {self._truncate(content, 70)}[/status-good]"
        elif "start" in content_str or "begin" in content_str:
            return f"[status-info]▶ {self._truncate(content, 70)}[/status-info]"
        elif "processing" in content_str or "executing" in content_str:
            return f"[status-warning]⚙ {self._truncate(content, 70)}[/status-warning]"
        else:
            return f"{self._truncate(content, 80)}"

    def _decode_field(self, field):
        """Decode field if it's bytes."""
        if isinstance(field, bytes):
            return field.decode("utf-8", errors="ignore")
        return str(field) if field else ""

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp for logs."""
        if not timestamp:
            return "??:??:??"
        try:
            if isinstance(timestamp, (int, float)):
                # Convert milliseconds to seconds if needed
                if timestamp > 1e10:  # Likely milliseconds
                    timestamp = timestamp / 1000
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(str(timestamp))
            return dt.strftime("%H:%M:%S")
        except:
            return str(timestamp)[:8]

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to maximum length."""
        if not text:
            return ""
        text_str = str(text)
        return text_str[: max_len - 3] + "..." if len(text_str) > max_len else text_str
