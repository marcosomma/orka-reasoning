"""
Custom Textual widgets for OrKa memory monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from textual.containers import Container
from textual.message import Message
from textual.widgets import DataTable, Static


def _ensure_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Helper function to ensure we always have a dict."""
    return data if data is not None else {}


class StatsWidget(Static):
    """Widget for displaying memory statistics."""

    def __init__(self, data_manager: Any, **kwargs: Any) -> None:
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
    """Custom data table for displaying memory entries with checkbox selection."""

    class MemorySelected(Message):
        """Message sent when a memory row is selected."""

        def __init__(self, memory_data: Optional[Dict[str, Any]], row_index: int) -> None:
            super().__init__()  # Initialize Message first
            # Initialize with empty dict if None
            self.memory_data: Dict[str, Any] = memory_data if memory_data is not None else {}
            self.row_index = row_index

    def __init__(self, data_manager: Any, memory_type: str = "all", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data_manager = data_manager
        self.memory_type = memory_type
        self.current_memories: List[Dict[str, Any]] = []  # Store current memory data
        self.selected_memory_key: Optional[str] = None  # Track selected memory key across refreshes

        # Enable row selection
        self.cursor_type = "row"
        self.zebra_stripes = True

        # 🎯 IMPROVED: Add checkbox column + reorganized columns
        self.add_columns(
            "☐",  # Checkbox for selection
            "Time",  # When was it created
            "TTL",  # How long until expiry
            "Memory Key",  # Full access to memory key
            "Type",  # Memory type (short/long term)
            "Content",  # Content preview
            "Score",  # Importance score
        )

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection to toggle checkbox - alternative approach."""
        try:
            row_index = event.coordinate.row

            if 0 <= row_index < len(self.current_memories):
                selected_memory = self.current_memories[row_index]
                memory_key = self.data_manager._get_key(selected_memory)

                # Toggle selection
                if self.selected_memory_key == memory_key:
                    self.selected_memory_key = None
                    selected_memory_data: Optional[Dict[str, Any]] = None
                else:
                    self.selected_memory_key = memory_key
                    selected_memory_data = selected_memory

                # Refresh table to update checkboxes
                self.update_data(self.memory_type)

                # Send message to parent screen
                self.post_message(self.MemorySelected(selected_memory_data, row_index))

        except Exception as e:
            if hasattr(self, "app"):
                self.app.notify(f"Selection error: {e!s}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to toggle checkbox."""
        try:
            # Try to use the cursor_row directly
            row_index = self.cursor_row

            if row_index is not None and 0 <= row_index < len(self.current_memories):
                selected_memory = self.current_memories[row_index]
                memory_key = self.data_manager._get_key(selected_memory)

                # Toggle selection
                if self.selected_memory_key == memory_key:
                    self.selected_memory_key = None
                    selected_memory_data: Optional[Dict[str, Any]] = None
                    row_index = -1
                else:
                    self.selected_memory_key = memory_key
                    selected_memory_data = selected_memory

                # Refresh table to update checkboxes
                self.update_data(self.memory_type)

                # Send message to parent screen
                self.post_message(self.MemorySelected(selected_memory_data, row_index))

        except Exception as e:
            if hasattr(self, "app"):
                self.app.notify(f"Selection error: {e!s}", severity="error")

    def update_data(self, memory_type: str = "all") -> None:
        self.clear()

        # Get filtered memories
        memories = self.data_manager.get_filtered_memories(memory_type)
        self.current_memories = cast(
            List[Dict[str, Any]], memories[:25]
        )  # Store the memories we're actually displaying

        # Handle empty states
        if not memories and memory_type in ["short", "long"]:
            unified = self.data_manager.get_unified_stats()
            stored_memories = unified["stored_memories"]

            if stored_memories["total"] == 0:
                self.add_row(
                    "☐",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                    "[dim]No stored memories found[/dim]",
                    "[dim]--[/dim]",
                    "[dim]Create memories using memory-writer nodes[/dim]",
                    "[dim]--[/dim]",
                )
            else:
                short_count = stored_memories["short_term"]
                long_count = stored_memories["long_term"]

                if memory_type == "short" and short_count == 0:
                    self.add_row(
                        "☐",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                        "[dim]No short-term memories[/dim]",
                        "[dim]--[/dim]",
                        f"[dim]Found {long_count} long-term instead[/dim]",
                        "[dim]--[/dim]",
                    )
                elif memory_type == "long" and long_count == 0:
                    self.add_row(
                        "☐",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                        "[dim]No long-term memories[/dim]",
                        "[dim]--[/dim]",
                        f"[dim]Found {short_count} short-term instead[/dim]",
                        "[dim]--[/dim]",
                    )

            self.current_memories = []
            return

        # Populate table with memory data
        selected_row_found = False
        for i, memory in enumerate(self.current_memories):
            # Extract memory details
            content = self.data_manager._get_content(memory)
            node_id = self.data_manager._get_node_id(memory)
            importance_score = self.data_manager._get_importance_score(memory)
            ttl_formatted = self.data_manager._get_ttl_formatted(memory)
            timestamp = self.data_manager._get_timestamp(memory)
            memory_key = self.data_manager._get_key(memory)
            memory_type_actual = self.data_manager._get_memory_type(memory)

            # Format columns
            time_display = self._format_enhanced_timestamp(timestamp)
            ttl_display = self._format_enhanced_ttl(ttl_formatted)
            key_display = self._format_memory_key(memory_key)
            type_display = self._format_memory_type(memory_type_actual, node_id)
            content_display = self._format_content_preview(content)

            # Checkbox - check if this memory is selected
            if self.selected_memory_key == memory_key:
                checkbox = "✓"  # Simple checkmark without markup
                selected_row_found = True
            else:
                checkbox = "☐"

            self.add_row(
                checkbox,
                time_display,
                ttl_display,
                key_display,
                type_display,
                content_display,
                f"[cyan]{importance_score:.1f}[/cyan]",
            )

        # If selected memory was not found (expired), clear selection
        if not selected_row_found:
            self.selected_memory_key = None

    def _format_enhanced_timestamp(self, timestamp: Any) -> str:
        """Enhanced timestamp formatting with relative time info."""
        try:
            if timestamp > 1000000000000:  # milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000)
            else:  # seconds
                dt = datetime.fromtimestamp(timestamp)

            # Current time for relative calculations
            now = datetime.now()
            diff = now - dt

            # Format based on age
            if diff.total_seconds() < 60:  # Less than 1 minute
                return f"[green]{dt.strftime('%H:%M:%S')}[/green]"
            elif diff.total_seconds() < 3600:  # Less than 1 hour
                mins = int(diff.total_seconds() / 60)
                return f"[yellow]{dt.strftime('%H:%M')}[/yellow] [dim](-{mins}m)[/dim]"
            elif diff.total_seconds() < 86400:  # Less than 1 day
                hours = int(diff.total_seconds() / 3600)
                return f"[orange]{dt.strftime('%H:%M')}[/orange] [dim](-{hours}h)[/dim]"
            else:  # More than 1 day
                days = int(diff.total_seconds() / 86400)
                return f"[red]{dt.strftime('%m/%d')}[/red] [dim](-{days}d)[/dim]"
        except Exception:
            return "[dim]Unknown[/dim]"

    def _format_enhanced_ttl(self, ttl_formatted: Any) -> str:
        """Enhanced TTL formatting with urgency indicators."""
        if ttl_formatted == "Never" or ttl_formatted == "∞" or not ttl_formatted:
            return "[blue]♾️ Never[/blue]"

        # Parse TTL for urgency classification
        ttl_str = str(ttl_formatted).lower()

        if "s" in ttl_str and "m" not in ttl_str and "h" not in ttl_str:
            # Seconds only - critical urgency
            return f"[red]🚨 {ttl_formatted}[/red]"
        elif "m" in ttl_str and "h" not in ttl_str:
            # Minutes only - high urgency
            return f"[yellow]⚠️ {ttl_formatted}[/yellow]"
        elif "h" in ttl_str:
            # Hours - medium urgency
            if ttl_str.startswith("1h") or ttl_str.startswith("2h"):
                return f"[orange]⏰ {ttl_formatted}[/orange]"
            else:
                return f"[green]🕐 {ttl_formatted}[/green]"
        else:
            return f"[cyan]{ttl_formatted}[/cyan]"

    def _format_memory_key(self, memory_key: Any) -> str:
        """Format memory key with intelligent truncation."""
        if not memory_key:
            return "[dim]<no-key>[/dim]"

        key_str = str(memory_key)

        # Show meaningful parts of the key
        if len(key_str) <= 25:
            return f"[bright_blue]{key_str}[/bright_blue]"
        else:
            # Smart truncation: show start and end
            start = key_str[:12]
            end = key_str[-10:]
            return (
                f"[bright_blue]{start}[/bright_blue][dim]...[/dim][bright_blue]{end}[/bright_blue]"
            )

    def _format_memory_type(self, memory_type: Any, node_id: Any) -> str:
        """Format memory type with icons and node info."""
        # Decode if bytes
        if isinstance(memory_type, bytes):
            memory_type = memory_type.decode("utf-8", errors="ignore")
        if isinstance(node_id, bytes):
            node_id = node_id.decode("utf-8", errors="ignore")

        # Format based on type
        if memory_type == "short_term":
            icon = "⚡"
            color = "yellow"
        elif memory_type == "long_term":
            icon = "🧠"
            color = "green"
        else:
            icon = "📝"
            color = "white"
            memory_type = memory_type or "unknown"

        # Include node info for context
        node_short = str(node_id)[:8] if node_id else "?"
        return f"[{color}]{icon} {memory_type}[/{color}] [dim]({node_short})[/dim]"

    def _format_content_preview(self, content: Any) -> str:
        """Smart content preview with better truncation."""
        if not content:
            return "[dim]<empty>[/dim]"

        # Decode if bytes
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        content_str = str(content).strip()

        # Remove common JSON/structured prefixes for cleaner display
        if content_str.startswith('{"') and content_str.endswith('"}'):
            # Try to extract meaningful text from JSON
            try:


                data = json.loads(content_str)
                if isinstance(data, dict):
                    # Look for meaningful fields
                    for key in ["content", "text", "message", "description", "prompt"]:
                        if data.get(key):
                            content_str = str(data[key])
                            break
            except Exception:
                pass

        # Intelligent truncation
        if len(content_str) <= 35:
            return f"[white]{content_str}[/white]"
        else:
            # Find a good break point (space, comma, period)
            truncated = content_str[:32]
            for i in range(len(truncated) - 1, max(20, len(truncated) - 10), -1):
                if truncated[i] in [" ", ",", ".", ";"]:
                    truncated = truncated[:i]
                    break
            return f"[white]{truncated}[/white][dim]...[/dim]"

    def _get_filtered_memories(self) -> List[Dict[str, Any]]:
        """Get memories filtered by type."""
        memories = self.data_manager.get_filtered_memories(self.memory_type)
        return cast(List[Dict[str, Any]], memories)

    def _is_short_term(self, memory: Dict[str, Any]) -> bool:
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

    def _format_timestamp(self, timestamp: Any) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return "N/A"
        try:
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = datetime.fromisoformat(str(timestamp))
            return dt.strftime("%H:%M:%S")
        except Exception:
            return str(timestamp)[:8]

    def _format_type(self, log_type: str) -> str:
        """Format log type with color coding."""
        type_colors = {
            "memory": "[memory-short]MEM[/memory-short]",
            "orchestration": "[memory-long]ORC[/memory-long]",
            "system": "[status-info]SYS[/status-info]",
        }
        return type_colors.get(log_type, log_type.upper()[:3])

    def _format_ttl(self, ttl: Any) -> str:
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

    def _format_size(self, size: Any) -> str:
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

    def __init__(self, data_manager: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data_manager = data_manager
        self._health_content = Static("", id="health-content")

    def compose(self) -> Any:
        """Compose the health widget."""
        yield Static("🏥 System Health", classes="container")
        yield self._health_content

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

        self._health_content.update(health_content)


class LogsWidget(DataTable):
    """Enhanced widget for displaying memory logs with orchestration priority."""

    def __init__(self, data_manager: Any, **kwargs: Any) -> None:
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
                except Exception:
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
                except Exception:
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

    def _extract_log_details(self, log: Dict[str, Any]) -> str:
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


class BreadcrumbWidget(Static):
    """Widget for displaying navigation breadcrumb path."""
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.path: List[str] = ["ORKA"]
    
    def update_path(self, path: List[str]) -> None:
        """
        Update the breadcrumb path.
        
        Args:
            path: List of path segments (e.g., ["ORKA", "Memory", "Short-term"])
        """
        self.path = ["ORKA"] + path
        self.refresh()
    
    def render(self) -> str:
        """Render the breadcrumb path."""
        if not self.path:
            return "[dim][ORKA][/dim]"
        
        # Format breadcrumb with separators
        formatted_segments = []
        for i, segment in enumerate(self.path):
            if i == 0:
                # First segment (ORKA) - bold and centered
                formatted_segments.append(f"[bold cyan][{segment.center(8)}][/bold cyan]")
            else:
                # Other segments - normal
                formatted_segments.append(f"[cyan]{segment}[/cyan]")
        
        return " [dim]>[/dim] ".join(formatted_segments)
