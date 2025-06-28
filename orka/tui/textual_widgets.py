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
        """Format statistics for display using unified stats system."""
        # 🎯 USE UNIFIED: Get all stats from centralized calculation
        unified = self.data_manager.get_unified_stats()

        # Extract key metrics from unified stats
        total_entries = unified["total_entries"]
        stored_memories = unified["stored_memories"]
        log_entries = unified["log_entries"]
        backend = unified["backend"]
        health = unified["health"]
        trends = unified["trends"]

        return f"""[bold]📊 Memory Statistics[/bold]

[metric-label]Total Entries:[/metric-label] [metric-value]{total_entries:,}[/metric-value] {trends["total_entries"]}
[metric-label]Short-term Memory:[/metric-label] [metric-value]{stored_memories["short_term"]:,}[/metric-value] 
[metric-label]Long-term Memory:[/metric-label] [metric-value]{stored_memories["long_term"]:,}[/metric-value] {trends["stored_memories"]}
[metric-label]Orchestration Logs:[/metric-label] [metric-value]{log_entries["orchestration"]:,}[/metric-value]
[metric-label]Active Entries:[/metric-label] [metric-value]{backend["active_entries"]:,}[/metric-value]
[metric-label]Expired Entries:[/metric-label] [metric-value]{backend["expired_entries"]:,}[/metric-value]

[metric-label]Backend:[/metric-label] [status-info]{backend["type"]}[/status-info]
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

    def update_data(self, memory_type="all"):
        """Update the table with filtered data."""
        self.clear()

        # Get filtered memories
        memories = self.data_manager.get_filtered_memories(memory_type)

        # 🎯 FIX: Show helpful message when no memories of a specific type exist
        if not memories and memory_type in ["short", "long"]:
            # 🎯 USE UNIFIED: Get distribution from unified stats
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            if stored_memories["total"] == 0:
                # No stored memories at all
                self.add_row(
                    "[dim]No stored memories found[/dim]",
                    "[dim]Create memories using memory-writer nodes[/dim]",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                )
            else:
                # Stored memories exist but not of the requested type
                short_count = stored_memories["short_term"]
                long_count = stored_memories["long_term"]

                if memory_type == "short" and short_count == 0:
                    self.add_row(
                        "[dim]No short-term memories found[/dim]",
                        f"[dim]Found {long_count} long-term memories instead[/dim]",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                    )
                elif memory_type == "long" and long_count == 0:
                    self.add_row(
                        "[dim]No long-term memories found[/dim]",
                        f"[dim]Found {short_count} short-term memories instead[/dim]",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                    )
            return

        # Populate table with memory data using unified extraction methods
        for memory in memories[:20]:  # Limit to 20 entries for performance
            # 🎯 USE UNIFIED: Use centralized, safe data extraction
            content = self.data_manager._get_content(memory)
            node_id = self.data_manager._get_node_id(memory)
            importance_score = self.data_manager._get_importance_score(memory)
            ttl_formatted = self.data_manager._get_ttl_formatted(memory)
            timestamp = self.data_manager._get_timestamp(memory)

            # Format content
            content_display = content[:40] + "..." if len(content) > 40 else content

            # Format timestamp
            try:
                if timestamp > 1000000000000:  # milliseconds
                    dt = datetime.fromtimestamp(timestamp / 1000)
                else:  # seconds
                    dt = datetime.fromtimestamp(timestamp)
                time_display = dt.strftime("%H:%M:%S")
            except:
                time_display = "Unknown"

            # Format TTL with color coding
            if ttl_formatted == "Never" or ttl_formatted == "∞":
                ttl_display = "[blue]∞[/blue]"
            elif "h" in ttl_formatted:
                ttl_display = f"[green]{ttl_formatted}[/green]"
            elif "m" in ttl_formatted:
                ttl_display = f"[yellow]{ttl_formatted}[/yellow]"
            else:
                ttl_display = f"[red]{ttl_formatted}[/red]"

            self.add_row(
                time_display,
                node_id[:15],  # Limit node_id length
                content_display,
                f"{importance_score:.2f}",
                ttl_display,
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
        """Update health display with unified health calculations."""
        # 🎯 USE UNIFIED: Get all health data from centralized calculation
        unified = self.data_manager.get_unified_stats()
        health = unified["health"]
        backend = unified["backend"]
        performance = unified["performance"]

        # Overall system health
        overall = health["overall"]
        overall_text = f"{overall['icon']} {overall['message']}"

        # Memory system health
        memory = health["memory"]
        memory_text = f"{memory['icon']} {memory['message']}"

        # Backend health
        backend_health = health["backend"]
        backend_text = f"{backend_health['icon']} {backend_health['message']}"

        # Performance health
        perf_health = health["performance"]
        perf_text = f"{perf_health['icon']} {perf_health['message']}"

        # Usage statistics
        total = backend["active_entries"] + backend["expired_entries"]
        usage_pct = (backend["active_entries"] / total * 100) if total > 0 else 0

        # Format content with unified data
        health_content = f"""
[bold]🏥 System Health Monitor[/bold]

[metric-label]Overall Status:[/metric-label] {overall_text}
[metric-label]Memory Health:[/metric-label] {memory_text}
[metric-label]Backend Status:[/metric-label] {backend_text}
[metric-label]Performance:[/metric-label] {perf_text}

[metric-label]Memory Usage:[/metric-label] [metric-value]{usage_pct:.1f}%[/metric-value]
[metric-label]Response Time:[/metric-label] [metric-value]{performance["search_time"]:.3f}s[/metric-value]
[metric-label]Backend Type:[/metric-label] [status-info]{backend["type"]}[/status-info]
[metric-label]Decay Status:[/metric-label] {"✅ Active" if backend["decay_enabled"] else "❌ Inactive"}
"""

        self.update(health_content)


class LogsWidget(DataTable):
    """Enhanced widget for displaying memory logs with orchestration priority."""

    def __init__(self, data_manager, **kwargs):
        super().__init__(**kwargs)
        self.data_manager = data_manager
        self.add_columns("Time", "Node", "Type", "Content", "Details")

    def update_data(self):
        """Update logs with unified filtering - show overview of recent orchestration and system logs."""
        self.clear()

        # 🎯 USE UNIFIED: Get all log data from centralized calculation
        unified = self.data_manager.get_unified_stats()
        log_entries = unified["log_entries"]

        # Get actual log memories using existing filtering
        all_logs = self.data_manager.get_filtered_memories("logs")

        # Separate orchestration logs from others using unified data
        orchestration_logs = [
            log for log in all_logs if self.data_manager._get_log_type(log) == "log"
        ]
        system_logs = [
            log for log in all_logs if self.data_manager._get_log_type(log) in ["system"]
        ]

        # Sort logs by timestamp (most recent first)
        orchestration_logs.sort(key=lambda x: self.data_manager._get_timestamp(x), reverse=True)
        system_logs.sort(key=lambda x: self.data_manager._get_timestamp(x), reverse=True)

        # Add summary header
        summary_details = (
            f"Orchestration: {log_entries['orchestration']} | System: {log_entries['system']}"
        )
        self.add_row(
            "[bold]--:--:--[/bold]",
            "[bold]SUMMARY[/bold]",
            "[bold]OVERVIEW[/bold]",
            f"[bold]📊 Total Logs: {log_entries['total']}[/bold]",
            f"[bold]{summary_details}[/bold]",
        )

        # Add separator
        self.add_row("", "", "", "", "")

        # Add recent orchestration logs (most important)
        if orchestration_logs:
            self.add_row(
                "[cyan]--:--:--[/cyan]",
                "[cyan]ORCHESTRATION[/cyan]",
                "[cyan]HEADER[/cyan]",
                "[cyan]📋 Recent Orchestration Activity[/cyan]",
                "[cyan]Last 8 entries[/cyan]",
            )

            for log in orchestration_logs[:8]:  # Show 8 most recent
                content = self.data_manager._get_content(log)
                node_id = self.data_manager._get_node_id(log)
                timestamp = self.data_manager._get_timestamp(log)

                # Format timestamp
                try:
                    if timestamp > 1000000000000:  # milliseconds
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    else:  # seconds
                        dt = datetime.fromtimestamp(timestamp)
                    time_display = dt.strftime("%H:%M:%S")
                except:
                    time_display = "Unknown"

                # Format content for overview (shorter)
                content_overview = content[:35] + "..." if len(content) > 35 else content

                # Extract key details (node activity, trace info, etc.)
                details = self._extract_log_details(log)

                self.add_row(
                    time_display,
                    node_id[:12],  # Limit node_id length
                    "[cyan]orchestration[/cyan]",
                    content_overview,
                    details[:20] + "..." if len(details) > 20 else details,
                )

        # Add recent system logs if any
        if system_logs:
            # Add separator
            self.add_row("", "", "", "", "")

            self.add_row(
                "[yellow]--:--:--[/yellow]",
                "[yellow]SYSTEM[/yellow]",
                "[yellow]HEADER[/yellow]",
                "[yellow]🔧 Recent System Activity[/yellow]",
                "[yellow]Last 3 entries[/yellow]",
            )

            for log in system_logs[:3]:  # Show 3 most recent system logs
                content = self.data_manager._get_content(log)
                node_id = self.data_manager._get_node_id(log)
                timestamp = self.data_manager._get_timestamp(log)

                # Format timestamp
                try:
                    if timestamp > 1000000000000:  # milliseconds
                        dt = datetime.fromtimestamp(timestamp / 1000)
                    else:  # seconds
                        dt = datetime.fromtimestamp(timestamp)
                    time_display = dt.strftime("%H:%M:%S")
                except:
                    time_display = "Unknown"

                content_overview = content[:35] + "..." if len(content) > 35 else content
                details = self._extract_log_details(log)

                self.add_row(
                    time_display,
                    node_id[:12],
                    "[yellow]system[/yellow]",
                    content_overview,
                    details[:20] + "..." if len(details) > 20 else details,
                )

        # If no logs found
        if not orchestration_logs and not system_logs:
            self.add_row(
                "[dim]--:--:--[/dim]",
                "[dim]NO DATA[/dim]",
                "[dim]EMPTY[/dim]",
                "[dim]No recent logs found[/dim]",
                "[dim]Run workflows to generate logs[/dim]",
            )

    def _extract_log_details(self, log):
        """Extract key details from log entry for overview."""
        # Try to get trace_id, importance, or other key details
        trace_id = self.data_manager._get_safe_field(log, "trace_id", "trace", default="")
        importance = self.data_manager._get_importance_score(log)

        # Build details string
        details_parts = []

        if trace_id and trace_id != "unknown":
            details_parts.append(f"trace:{trace_id[:8]}")

        if importance > 0:
            details_parts.append(f"imp:{importance:.1f}")

        # Check for special fields in metadata
        metadata = log.get("metadata", {})
        if isinstance(metadata, dict):
            category = self.data_manager._safe_decode(metadata.get("category", ""))
            if category and category != "unknown":
                details_parts.append(f"cat:{category[:5]}")

        return " | ".join(details_parts) if details_parts else "standard"
