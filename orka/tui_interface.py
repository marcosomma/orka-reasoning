"""
🎨 **OrKa Modern TUI Interface** - Beautiful Real-time Memory Monitoring
=====================================================================

Modern Terminal User Interface for OrKa memory system monitoring, inspired by
htop, btop, and other modern system monitoring tools. Provides real-time
visualizations, interactive controls, and comprehensive system insights.

**Features:**
- 📊 Real-time memory statistics with live charts
- 🎯 Interactive memory browser with filtering
- 🚀 Performance metrics and trending
- 🧠 Vector search monitoring for RedisStack
- 🎨 Beautiful color-coded interface
- ⌨️  Keyboard shortcuts for navigation
- 📈 Historical data visualization
- 🔄 Auto-refresh with customizable intervals

**Key Components:**
- **Dashboard View**: Overview of system health and memory usage
- **Memory Browser**: Interactive table of stored memories
- **Performance View**: Charts and metrics for system performance
- **Configuration View**: Real-time configuration monitoring
"""

import datetime
import json
import os
import signal
import sys
import time
from collections import deque
from typing import Any, Dict

try:
    from rich import print as rich_print
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED, SIMPLE
    from rich.columns import Columns
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.markup import escape
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.style import Style
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Try to import textual for advanced interactions
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widgets import Button, DataTable, Footer, Header, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from .memory_logger import create_memory_logger


class MemoryStats:
    """Container for memory statistics with historical tracking."""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self.current: Dict[str, Any] = {}

    def update(self, stats: Dict[str, Any]):
        """Update current stats and add to history."""
        self.current = stats.copy()
        self.current["timestamp"] = time.time()
        self.history.append(self.current.copy())

    def get_trend(self, key: str, window: int = 10) -> str:
        """Get trend direction for a metric."""
        if len(self.history) < 2:
            return "→"

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return "→"

        values = [item.get(key, 0) for item in recent if key in item]
        if len(values) < 2:
            return "→"

        if values[-1] > values[0]:
            return "↗"
        elif values[-1] < values[0]:
            return "↘"
        else:
            return "→"

    def get_rate(self, key: str, window: int = 5) -> float:
        """Get rate of change for a metric (per second)."""
        if len(self.history) < 2:
            return 0.0

        recent = list(self.history)[-window:]
        if len(recent) < 2:
            return 0.0

        # Calculate rate between first and last points
        first = recent[0]
        last = recent[-1]

        if key not in first or key not in last:
            return 0.0

        value_diff = last[key] - first[key]
        time_diff = last["timestamp"] - first["timestamp"]

        if time_diff <= 0:
            return 0.0

        return value_diff / time_diff


class ModernTUIInterface:
    """Modern TUI interface for OrKa memory monitoring."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.memory_logger = None
        self.backend = None
        self.running = False
        self.refresh_interval = 2.0
        self.stats = MemoryStats()
        self.current_view = "dashboard"  # dashboard, memories, performance, config
        self.memory_data = []
        self.selected_row = 0
        self.filter_text = ""

        # Performance tracking
        self.performance_history = deque(maxlen=60)  # 1 minute at 1s intervals

    def run(self, args):
        """Main entry point for the TUI interface."""
        if not RICH_AVAILABLE:
            print("❌ Modern TUI requires 'rich' library. Install with: pip install rich")
            print("Falling back to basic interface...")
            return self._run_basic_fallback(args)

        try:
            # Initialize memory logger
            self._init_memory_logger(args)

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)

            # Start monitoring
            self.running = True
            self.refresh_interval = getattr(args, "interval", 2.0)

            # Try rich interface first for better stability, fallback to textual
            if getattr(args, "use_textual", False) and TEXTUAL_AVAILABLE:
                return self._run_textual_interface(args)
            else:
                return self._run_rich_interface(args)

        except Exception as e:
            if self.console:
                self.console.print(f"[red]❌ Error in TUI interface: {e}[/red]")
            else:
                print(f"❌ Error in TUI interface: {e}")
            import traceback

            traceback.print_exc()
            return 1

    def _init_memory_logger(self, args):
        """Initialize the memory logger."""
        self.backend = getattr(args, "backend", None) or os.getenv(
            "ORKA_MEMORY_BACKEND",
            "redisstack",
        )

        # Provide proper Redis URL based on backend
        if self.backend == "redisstack":
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.memory_logger = create_memory_logger(backend=self.backend, redis_url=redis_url)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        self.running = False

    def _run_rich_interface(self, args):
        """Run the rich-based interface with live updates."""
        try:
            with Live(
                self._create_dashboard(),
                console=self.console,
                refresh_per_second=0.5,  # Slower refresh to prevent jumping
                screen=True,
                vertical_overflow="crop",  # Prevent overflow
            ) as live:
                while self.running:
                    try:
                        # Update data
                        self._update_data()

                        # Update display based on current view
                        if self.current_view == "dashboard":
                            live.update(self._create_dashboard())
                        elif self.current_view == "memories":
                            live.update(self._create_memory_browser())
                        elif self.current_view == "performance":
                            live.update(self._create_performance_view())
                        elif self.current_view == "config":
                            live.update(self._create_config_view())

                        time.sleep(max(self.refresh_interval, 2.0))  # Minimum 2 second intervals

                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        live.update(Panel(f"[red]Error: {e}[/red]", title="Error"))
                        time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            pass

        self.console.print("\n[green]👋 OrKa TUI monitoring stopped[/green]")
        return 0

    def _run_textual_interface(self, args):
        """Run the textual-based interface (more interactive)."""
        app = OrKaMonitorApp(self)
        app.run()
        return 0

    def _update_data(self):
        """Update all monitoring data."""
        try:
            # Get memory statistics
            stats = self.memory_logger.get_memory_stats()
            self.stats.update(stats)

            # Get recent memories
            if hasattr(self.memory_logger, "get_recent_stored_memories"):
                self.memory_data = self.memory_logger.get_recent_stored_memories(20)
            elif hasattr(self.memory_logger, "search_memories"):
                self.memory_data = self.memory_logger.search_memories(
                    query=" ",
                    num_results=20,
                    log_type="memory",
                )
            else:
                self.memory_data = []

            # Get performance metrics if available
            if hasattr(self.memory_logger, "get_performance_metrics"):
                perf_metrics = self.memory_logger.get_performance_metrics()
                perf_metrics["timestamp"] = time.time()
                self.performance_history.append(perf_metrics)

        except Exception:
            # Log error but continue
            pass

    def _create_dashboard(self):
        """Create a compact dashboard that fits in standard terminal windows."""
        layout = Layout()

        # Split into header, main content, and footer (more compact)
        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="main"),
            Layout(name="footer", size=2),
        )

        # Split main content into two columns only for better fit
        layout["main"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2),
        )

        # Split left column: stats and memories only
        layout["left"].split_column(
            Layout(name="stats", size=10),
            Layout(name="memories"),
        )

        # Right column: performance only (compact)
        layout["right"].update(self._create_compact_performance_panel())

        # Create compact panels
        layout["header"].update(self._create_compact_header())
        layout["stats"].update(self._create_compact_stats_panel())
        layout["memories"].update(self._create_compact_memories_panel())
        layout["footer"].update(self._create_compact_footer())

        return layout

    def _create_compact_header(self):
        """Create a compact header."""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        status_color = "green" if self.running else "red"

        header_text = Text()
        header_text.append("🚀 OrKa Monitor ", style="bold blue")
        header_text.append(f"| {self.backend.upper()} ", style="cyan")
        header_text.append(f"| {current_time} ", style="dim")
        header_text.append("●", style=f"bold {status_color}")

        return Panel(Align.center(header_text), box=SIMPLE, style="blue")

    def _create_compact_stats_panel(self):
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
            rate = self.stats.get_rate(key)

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

    def _create_compact_memories_panel(self):
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
        for i, mem in enumerate(self.memory_data[:6]):
            # Handle bytes content
            raw_content = mem.get("content", "")
            if isinstance(raw_content, bytes):
                raw_content = raw_content.decode("utf-8", errors="replace")
            content = raw_content[:22] + ("..." if len(raw_content) > 22 else "")

            # Handle bytes for node_id
            raw_node_id = mem.get("node_id", "unknown")
            node_id = (
                raw_node_id.decode("utf-8", errors="replace")
                if isinstance(raw_node_id, bytes)
                else str(raw_node_id)
            )[:8]  # Limit node_id length

            # Handle memory type
            raw_memory_type = mem.get("memory_type", "unknown")
            memory_type = (
                raw_memory_type.decode("utf-8", errors="replace")
                if isinstance(raw_memory_type, bytes)
                else str(raw_memory_type)
            )[:6]  # Shorten type

            # Handle importance score
            raw_importance = mem.get("importance_score", 0)
            if isinstance(raw_importance, bytes):
                try:
                    importance = float(raw_importance.decode())
                except:
                    importance = 0.0
            else:
                importance = float(raw_importance) if raw_importance else 0.0

            # Handle timestamp
            try:
                raw_timestamp = mem.get("timestamp", 0)
                if isinstance(raw_timestamp, bytes):
                    timestamp = int(raw_timestamp.decode())
                else:
                    timestamp = int(raw_timestamp) if raw_timestamp else 0

                if timestamp > 1000000000000:  # milliseconds
                    dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                else:  # seconds
                    dt = datetime.datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "??:??"

            # Handle TTL
            raw_ttl = mem.get("ttl_formatted", "?")
            ttl = (
                raw_ttl.decode("utf-8", errors="replace")
                if isinstance(raw_ttl, bytes)
                else str(raw_ttl)
            )[:8]  # Limit TTL length

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

    def _create_compact_performance_panel(self):
        """Create a compact performance panel with comprehensive metrics."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=11)
        table.add_column(style="white", width=8, justify="right")
        table.add_column(style="green", width=6)
        table.add_column(style="yellow", width=4)

        if not self.performance_history:
            table.add_row("  Status", "Collecting", "data", "⏳")
            return Panel(table, title="⚡ Performance & System", box=ROUNDED)

        latest_perf = self.performance_history[-1]

        # Performance metrics with status indicators
        avg_search_time = latest_perf.get("average_search_time", 0)
        if avg_search_time < 0.1:
            perf_status = "⚡"
        elif avg_search_time < 0.5:
            perf_status = "⚠"
        else:
            perf_status = "🐌"

        table.add_row(
            "  Search Speed",
            f"{avg_search_time:.3f}s",
            "time",
            f"[cyan]{perf_status}[/cyan]",
        )

        # Vector search metrics for RedisStack
        if self.backend == "redisstack":
            try:
                if hasattr(self.memory_logger, "client"):
                    # HNSW Index status
                    index_info = self.memory_logger.client.ft("enhanced_memory_idx").info()
                    docs = index_info.get("num_docs", 0)
                    indexing = index_info.get("indexing", False)

                    table.add_row("  Vector Docs", f"{docs:,}", "docs", "📊")
                    table.add_row(
                        "  HNSW Index",
                        "Active" if indexing else "Idle",
                        "status",
                        "✅" if indexing else "⏸",
                    )

                    # Redis system info
                    redis_info = self.memory_logger.client.info()
                    memory_used = redis_info.get("used_memory_human", "N/A")
                    clients = redis_info.get("connected_clients", 0)
                    ops_per_sec = redis_info.get("instantaneous_ops_per_sec", 0)

                    table.add_row("  Memory Used", memory_used, "mem", "💾")
                    table.add_row("  Clients", f"{clients}", "conn", "🔗")
                    table.add_row(
                        "  Ops/sec",
                        f"{ops_per_sec}",
                        "rate",
                        "⚡" if ops_per_sec > 10 else "📈",
                    )

                    # Module detection
                    try:
                        modules = self.memory_logger.client.execute_command("MODULE", "LIST")
                        module_count = len(modules) if modules else 0
                        table.add_row("  Modules", f"{module_count}", "ext", "🔌")
                    except:
                        table.add_row("  Modules", "Unknown", "ext", "❓")

            except Exception as e:
                table.add_row("  Vector", "Error", "state", "❌")
                table.add_row("  Redis", str(e)[:6], "err", "💥")
        else:
            # Basic Redis metrics
            table.add_row("  Backend", self.backend.upper(), "type", "🗄️")
            table.add_row(
                "  Status",
                "Connected",
                "conn",
                "✅" if hasattr(self.memory_logger, "client") else "❌",
            )

        # Memory operations if available
        if hasattr(self.memory_logger, "get_performance_metrics"):
            try:
                perf = self.memory_logger.get_performance_metrics()
                writes = perf.get("memory_writes", 0)
                reads = perf.get("memory_reads", 0)
                table.add_row("  Writes/min", f"{writes}", "ops", "✏️")
                table.add_row("  Reads/min", f"{reads}", "ops", "👁️")
            except:
                pass

        return Panel(table, title="⚡ Performance & System Health", box=ROUNDED)

    def _create_compact_footer(self):
        """Create a compact footer with essential controls."""
        controls = [
            "[white]1[/white] Dashboard",
            "[white]2[/white] Memories",
            "[white]3[/white] Performance",
            "[white]R[/white] Refresh",
            "[white]Ctrl+C[/white] Exit",
        ]

        footer_text = " | ".join(controls)
        return Panel(Align.center(footer_text), box=SIMPLE, style="dim")

    def _create_header(self):
        """Create header with title and status."""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status_color = "green" if self.running else "red"
        backend_info = f"Backend: [bold]{self.backend}[/bold]"

        header_text = Text()
        header_text.append("🚀 OrKa Memory Monitor ", style="bold blue")
        header_text.append(f"| {backend_info} ", style="dim")
        header_text.append(f"| {current_time} ", style="dim")
        header_text.append("● LIVE", style=f"bold {status_color}")

        return Panel(
            Align.center(header_text),
            box=HEAVY,
            style="blue",
        )

    def _create_stats_panel(self):
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
            rate_text = ""
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

    def _create_footer(self):
        """Create comprehensive footer with all available controls."""
        controls = [
            "[bold cyan]Navigation:[/bold cyan]",
            "[white]1[/white] Dashboard",
            "[white]2[/white] Memory Browser",
            "[white]3[/white] Performance",
            "[white]4[/white] Configuration",
            "[white]5[/white] Namespaces",
            "[bold cyan]Actions:[/bold cyan]",
            "[white]R[/white] Refresh",
            "[white]C[/white] Clear",
            "[white]S[/white] Stats",
            "[white]Ctrl+C[/white] Exit",
        ]

        # Add backend-specific controls
        if self.backend == "redisstack":
            controls.extend(
                [
                    "[bold cyan]RedisStack:[/bold cyan]",
                    "[white]V[/white] Vector Search",
                    "[white]I[/white] Index Health",
                ],
            )

        footer_text = " | ".join(controls)
        return Panel(
            Align.center(footer_text),
            box=SIMPLE,
            style="dim blue",
        )

    def _create_recent_memories_panel(self):
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

        for i, mem in enumerate(self.memory_data[:8]):  # Show top 8 for better detail
            # Handle bytes content with better decoding
            raw_content = mem.get("content", "")
            if isinstance(raw_content, bytes):
                raw_content = raw_content.decode("utf-8", errors="replace")
            content = raw_content[:35] + ("..." if len(raw_content) > 35 else "")

            # Handle bytes for node_id
            raw_node_id = mem.get("node_id", "unknown")
            node_id = (
                raw_node_id.decode("utf-8", errors="replace")
                if isinstance(raw_node_id, bytes)
                else str(raw_node_id)
            )

            # Handle memory type
            raw_memory_type = mem.get("memory_type", "unknown")
            memory_type = (
                raw_memory_type.decode("utf-8", errors="replace")
                if isinstance(raw_memory_type, bytes)
                else str(raw_memory_type)
            )

            # Handle importance score
            raw_importance = mem.get("importance_score", 0)
            if isinstance(raw_importance, bytes):
                try:
                    importance = float(raw_importance.decode())
                except:
                    importance = 0.0
            else:
                importance = float(raw_importance) if raw_importance else 0.0

            # Handle timestamp with better formatting
            try:
                raw_timestamp = mem.get("timestamp", 0)
                if isinstance(raw_timestamp, bytes):
                    timestamp = int(raw_timestamp.decode())
                else:
                    timestamp = int(raw_timestamp) if raw_timestamp else 0

                if timestamp > 1000000000000:  # milliseconds
                    dt = datetime.datetime.fromtimestamp(timestamp / 1000)
                else:  # seconds
                    dt = datetime.datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = "??:??:??"

            # Handle TTL with full information
            raw_ttl = mem.get("ttl_formatted", "N/A")
            ttl = (
                raw_ttl.decode("utf-8", errors="replace")
                if isinstance(raw_ttl, bytes)
                else str(raw_ttl)
            )

            raw_expires = mem.get("expires_at_formatted", "")
            expires_at = (
                raw_expires.decode("utf-8", errors="replace")
                if isinstance(raw_expires, bytes)
                else str(raw_expires)
            )

            has_expiry = mem.get("has_expiry", False)

            # Enhanced TTL display with color coding
            if ttl == "0s" or "Expired" in ttl:
                ttl_style = f"[red]💀 {ttl}[/red]"
            elif "Never" in ttl:
                ttl_style = f"[green]♾️ {ttl}[/green]"
            elif any(unit in ttl for unit in ["s", "m", "h"]):
                if "h" in ttl:
                    ttl_style = f"[green]⏰ {ttl}[/green]"
                elif "m" in ttl:
                    ttl_style = f"[yellow]⏰ {ttl}[/yellow]"
                else:  # seconds
                    ttl_style = f"[red]⚠️ {ttl}[/red]"
            else:
                ttl_style = ttl

            # Memory type color coding
            type_color = (
                "green"
                if memory_type == "long_term"
                else "yellow"
                if memory_type == "short_term"
                else "dim"
            )

            table.add_row(
                time_str,
                node_id[:15],
                f"[{type_color}]{memory_type[:12]}[/{type_color}]",
                escape(content),
                f"{importance:.2f}",
                ttl_style,
            )

        return Panel(table, title="🧠 Recent Stored Memories", box=ROUNDED)

    def _create_performance_panel(self):
        """Create comprehensive performance metrics panel."""
        if not self.performance_history and not hasattr(
            self.memory_logger,
            "get_performance_metrics",
        ):
            return Panel("No performance data available", title="🚀 Performance")

        # Create performance table with comprehensive metrics
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white", width=15)
        table.add_column(style="green", width=10)

        # Get latest performance metrics
        if hasattr(self.memory_logger, "get_performance_metrics"):
            try:
                latest = self.memory_logger.get_performance_metrics()

                # Core performance metrics
                table.add_row("[bold]Search Performance:[/bold]", "", "")
                table.add_row("  HNSW Searches", f"{latest.get('hybrid_searches', 0):,}", "ops")
                table.add_row("  Vector Searches", f"{latest.get('vector_searches', 0):,}", "ops")
                table.add_row(
                    "  Avg Search Time",
                    f"{latest.get('average_search_time', 0):.3f}",
                    "sec",
                )
                table.add_row(
                    "  Cache Hit Rate",
                    f"{(latest.get('cache_hits', 0) / max(1, latest.get('total_searches', 1)) * 100):.1f}",
                    "%",
                )

                table.add_row("", "", "")  # Separator
                table.add_row("[bold]Memory Operations:[/bold]", "", "")
                table.add_row("  Memory Writes", f"{latest.get('memory_writes', 0):,}", "/min")
                table.add_row("  Memory Reads", f"{latest.get('memory_reads', 0):,}", "/min")
                table.add_row("  Total Memories", f"{latest.get('memory_count', 0):,}", "stored")

                # Index health (RedisStack specific)
                index_status = latest.get("index_status", {})
                if index_status and index_status.get("status") != "unavailable":
                    table.add_row("", "", "")  # Separator
                    table.add_row("[bold]HNSW Index Health:[/bold]", "", "")
                    table.add_row(
                        "  Index Status",
                        "✅ Active" if index_status.get("indexing", False) else "⏸️ Idle",
                        "",
                    )
                    table.add_row("  Documents", f"{index_status.get('num_docs', 0):,}", "docs")
                    table.add_row(
                        "  Index Progress",
                        f"{index_status.get('percent_indexed', 100):.1f}",
                        "%",
                    )

                    if index_status.get("index_options"):
                        opts = index_status["index_options"]
                        table.add_row("  HNSW M", str(opts.get("M", 16)), "")
                        table.add_row(
                            "  EF Construction",
                            str(opts.get("ef_construction", 200)),
                            "",
                        )

                # Memory quality metrics
                quality_metrics = latest.get("memory_quality", {})
                if quality_metrics:
                    table.add_row("", "", "")  # Separator
                    table.add_row("[bold]Memory Quality:[/bold]", "", "")
                    table.add_row(
                        "  Avg Importance",
                        f"{quality_metrics.get('avg_importance_score', 0):.2f}",
                        "/5.0",
                    )
                    table.add_row(
                        "  Long-term %",
                        f"{quality_metrics.get('long_term_percentage', 0):.1f}",
                        "%",
                    )
                    table.add_row(
                        "  High Quality %",
                        f"{quality_metrics.get('high_quality_percentage', 0):.1f}",
                        "%",
                    )

            except Exception as e:
                table.add_row("Performance Error:", str(e)[:30], "")

        # Add simple trend chart if we have history
        if self.performance_history:
            search_times = [
                p.get("average_search_time", 0) for p in list(self.performance_history)[-20:]
            ]
            if search_times and max(search_times) > 0:
                table.add_row("", "", "")  # Separator
                table.add_row("Search Time Trend:", "", "")
                chart = self._create_simple_chart(search_times, width=25, height=3)
                table.add_row("", chart, "")
                charts_content.append("")

            # Memory operations trend
            memory_writes = [
                p.get("memory_writes", 0) for p in list(self.performance_history)[-20:]
            ]
            if memory_writes and max(memory_writes) > 0:
                charts_content.append("[bold]Memory Writes Trend (20 samples):[/bold]")
                chart = self._create_simple_chart(memory_writes, width=35, height=3)
                table.add_row("", chart, "")
                charts_content.append("")

            # Cache hit rate trend
            cache_rates = []
            for p in list(self.performance_history)[-20:]:
                hits = p.get("cache_hits", 0)
                total = p.get("total_searches", 1)
                rate = (hits / total * 100) if total > 0 else 0
                cache_rates.append(rate)

            if cache_rates and max(cache_rates) > 0:
                charts_content.append("[bold]Cache Hit Rate Trend (%):[/bold]")
                chart = self._create_simple_chart(cache_rates, width=35, height=3)
                table.add_row("", chart, "")
                charts_content.append("")
        else:
            charts_content.append("[yellow]No performance history available yet...[/yellow]")
            charts_content.append("Charts will appear after collecting data.")

        layout["charts"].update(
            Panel(
                "\n".join(charts_content),
                title="📈 Performance Trends",
                box=ROUNDED,
            ),
        )

        # Quality metrics
        quality_table = Table(show_header=False, box=None, padding=(0, 1))
        quality_table.add_column(style="cyan", width=18)
        quality_table.add_column(style="white", width=12)
        quality_table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "get_performance_metrics"):
            try:
                perf = self.memory_logger.get_performance_metrics()
                quality_metrics = perf.get("memory_quality", {})

                if quality_metrics:
                    quality_table.add_row("[bold]Memory Quality:[/bold]", "", "")
                    quality_table.add_row(
                        "  Avg Importance",
                        f"{quality_metrics.get('avg_importance_score', 0):.2f}",
                        "/5.0",
                    )
                    quality_table.add_row(
                        "  Long-term %",
                        f"{quality_metrics.get('long_term_percentage', 0):.1f}",
                        "%",
                    )
                    quality_table.add_row(
                        "  High Quality %",
                        f"{quality_metrics.get('high_quality_percentage', 0):.1f}",
                        "%",
                    )
                    quality_table.add_row(
                        "  Avg Content Size",
                        f"{quality_metrics.get('avg_content_length', 0):.0f}",
                        "chars",
                    )

                    quality_table.add_row("", "", "")  # Separator
                    quality_table.add_row("[bold]Quality Distribution:[/bold]", "", "")

                    # Quality score distribution
                    score_ranges = quality_metrics.get("score_distribution", {})
                    for range_name, count in score_ranges.items():
                        quality_table.add_row(f"  {range_name}", f"{count:,}", "memories")

                else:
                    quality_table.add_row("No quality metrics", "available", "")

            except Exception as e:
                quality_table.add_row("Quality Error:", str(e)[:15], "")

        layout["quality_metrics"].update(
            Panel(quality_table, title="⭐ Memory Quality", box=ROUNDED),
        )

        layout["footer"].update(self._create_footer())

        return layout

    def _create_config_view(self):
        """Create comprehensive configuration view with backend testing."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Split main for configuration sections
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        layout["left"].split_column(
            Layout(name="backend_config", size=15),
            Layout(name="decay_config", size=12),
            Layout(name="connection_test"),
        )

        layout["right"].split_column(
            Layout(name="system_info", size=18),
            Layout(name="module_info"),
        )

        layout["header"].update(
            Panel(
                "🔧 Configuration & System Health - Backend Testing & Diagnostics",
                box=HEAVY,
                style="bold magenta",
            ),
        )

        # Backend configuration testing
        backend_table = Table(show_header=False, box=None, padding=(0, 1))
        backend_table.add_column(style="cyan", width=20)
        backend_table.add_column(style="white", width=15)
        backend_table.add_column(style="green", width=8)

        backend_table.add_row("[bold]Backend Configuration:[/bold]", "", "")
        backend_table.add_row("  Type", self.backend.upper(), "")

        # Test backend connectivity
        if hasattr(self.memory_logger, "client"):
            try:
                self.memory_logger.client.ping()
                backend_table.add_row("  Connection", "✅ Active", "")

                # Get Redis info
                redis_info = self.memory_logger.client.info()
                backend_table.add_row(
                    "  Redis Version",
                    redis_info.get("redis_version", "Unknown"),
                    "",
                )
                backend_table.add_row("  Mode", redis_info.get("redis_mode", "standalone"), "")

                # Test memory operations
                try:
                    test_key = "orka:tui:health_check"
                    self.memory_logger.client.set(test_key, "test", ex=5)
                    test_result = self.memory_logger.client.get(test_key)
                    if test_result:
                        backend_table.add_row("  Read/Write", "✅ Working", "")
                        self.memory_logger.client.delete(test_key)
                    else:
                        backend_table.add_row("  Read/Write", "❌ Failed", "")
                except Exception:
                    backend_table.add_row("  Read/Write", "❌ Error", "")

            except Exception as e:
                backend_table.add_row("  Connection", "❌ Failed", "")
                backend_table.add_row("  Error", str(e)[:15], "")
        else:
            backend_table.add_row("  Connection", "❌ No Client", "")

        # Backend-specific tests
        if self.backend == "redisstack":
            backend_table.add_row("", "", "")  # Separator
            backend_table.add_row("[bold]RedisStack Tests:[/bold]", "", "")

            # Test vector search capabilities
            try:
                if hasattr(self.memory_logger, "client"):
                    # Check for search module
                    modules = self.memory_logger.client.execute_command("MODULE", "LIST")
                    has_search = any("search" in str(module).lower() for module in modules)

                    if has_search:
                        backend_table.add_row("  Search Module", "✅ Loaded", "")

                        # Test index existence
                        try:
                            index_info = self.memory_logger.client.ft("enhanced_memory_idx").info()
                            backend_table.add_row("  HNSW Index", "✅ Available", "")
                            backend_table.add_row(
                                "  Documents",
                                f"{index_info.get('num_docs', 0):,}",
                                "docs",
                            )
                        except Exception:
                            backend_table.add_row("  HNSW Index", "❌ Missing", "")
                    else:
                        backend_table.add_row("  Search Module", "❌ Missing", "")

            except Exception as e:
                backend_table.add_row("  Module Check", f"❌ {str(e)[:10]}", "")

        layout["backend_config"].update(
            Panel(backend_table, title="🔌 Backend Health", box=ROUNDED),
        )

        # Decay configuration
        decay_table = Table(show_header=False, box=None, padding=(0, 1))
        decay_table.add_column(style="cyan", width=18)
        decay_table.add_column(style="white", width=15)
        decay_table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "decay_config"):
            config = self.memory_logger.decay_config

            decay_table.add_row("[bold]Memory Decay:[/bold]", "", "")

            if config and config.get("enabled", False):
                decay_table.add_row("  Status", "✅ Enabled", "")
                decay_table.add_row(
                    "  Short-term TTL",
                    f"{config.get('default_short_term_hours', 1)}",
                    "hours",
                )
                decay_table.add_row(
                    "  Long-term TTL",
                    f"{config.get('default_long_term_hours', 24)}",
                    "hours",
                )
                decay_table.add_row(
                    "  Check Interval",
                    f"{config.get('check_interval_minutes', 30)}",
                    "min",
                )

                # Test decay functionality
                try:
                    test_result = self.memory_logger.cleanup_expired_memories(dry_run=True)
                    decay_table.add_row("  Cleanup Test", "✅ Working", "")
                    decay_table.add_row(
                        "  Last Check",
                        test_result.get("duration_seconds", 0),
                        "sec",
                    )
                except Exception:
                    decay_table.add_row("  Cleanup Test", "❌ Error", "")

            else:
                decay_table.add_row("  Status", "❌ Disabled", "")
                decay_table.add_row("  Reason", "Not configured", "")
        else:
            decay_table.add_row("  Status", "❌ Unavailable", "")

        layout["decay_config"].update(Panel(decay_table, title="⏰ Memory Decay", box=ROUNDED))

        # Connection testing
        conn_table = Table(show_header=False, box=None, padding=(0, 1))
        conn_table.add_column(style="cyan", width=20)
        conn_table.add_column(style="white", width=12)
        conn_table.add_column(style="green", width=8)

        conn_table.add_row("[bold]Connection Testing:[/bold]", "", "")

        # Test different operations
        if hasattr(self.memory_logger, "client"):
            try:
                # Latency test
                start_time = time.time()
                self.memory_logger.client.ping()
                latency = (time.time() - start_time) * 1000

                if latency < 5:
                    latency_status = "[green]⚡ Excellent[/green]"
                elif latency < 20:
                    latency_status = "[yellow]⚠ Good[/yellow]"
                else:
                    latency_status = "[red]🐌 Slow[/red]"

                conn_table.add_row("  Ping Latency", f"{latency:.1f}ms", latency_status)

                # Memory stats test
                start_time = time.time()
                stats = self.memory_logger.get_memory_stats()
                stats_time = (time.time() - start_time) * 1000
                conn_table.add_row("  Stats Query", f"{stats_time:.1f}ms", "✅")

                # Search test (if available)
                if hasattr(self.memory_logger, "search_memories"):
                    start_time = time.time()
                    search_results = self.memory_logger.search_memories(" ", num_results=1)
                    search_time = (time.time() - start_time) * 1000
                    conn_table.add_row("  Search Test", f"{search_time:.1f}ms", "✅")

            except Exception as e:
                conn_table.add_row("  Test Failed", str(e)[:15], "❌")

        layout["connection_test"].update(
            Panel(conn_table, title="🔍 Connection Tests", box=ROUNDED),
        )

        # System information (comprehensive)
        system_table = Table(show_header=False, box=None, padding=(0, 1))
        system_table.add_column(style="cyan", width=18)
        system_table.add_column(style="white", width=15)
        system_table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "client"):
            try:
                redis_info = self.memory_logger.client.info()

                system_table.add_row("[bold]Redis System:[/bold]", "", "")
                system_table.add_row("  Version", redis_info.get("redis_version", "Unknown"), "")
                system_table.add_row(
                    "  Architecture",
                    redis_info.get("arch_bits", "Unknown"),
                    "bit",
                )
                system_table.add_row("  OS", redis_info.get("os", "Unknown"), "")

                system_table.add_row("", "", "")  # Separator
                system_table.add_row("[bold]Memory Usage:[/bold]", "", "")
                system_table.add_row(
                    "  Used Memory",
                    redis_info.get("used_memory_human", "N/A"),
                    "",
                )
                system_table.add_row(
                    "  Peak Memory",
                    redis_info.get("used_memory_peak_human", "N/A"),
                    "",
                )
                system_table.add_row(
                    "  Memory Ratio",
                    f"{redis_info.get('used_memory_peak_perc', '0')}%",
                    "",
                )

            except Exception as e:
                system_table.add_row("System Error:", str(e)[:15], "")

        layout["system_info"].update(Panel(system_table, title="🖥️ System Information", box=ROUNDED))

        # Module information
        module_table = Table(show_header=True, header_style="bold cyan", box=ROUNDED)
        module_table.add_column("Module", style="cyan", width=15)
        module_table.add_column("Version", style="white", width=12)
        module_table.add_column("Status", style="green", width=10)

        if hasattr(self.memory_logger, "client"):
            try:
                modules = self.memory_logger.client.execute_command("MODULE", "LIST")

                if modules:
                    for module in modules:
                        if isinstance(module, list) and len(module) >= 4:
                            name = (
                                module[1].decode()
                                if isinstance(module[1], bytes)
                                else str(module[1])
                            )
                            version = (
                                module[3].decode()
                                if isinstance(module[3], bytes)
                                else str(module[3])
                            )

                            # Status based on module name
                            if "search" in name.lower():
                                status = "✅ Vector Ready"
                            elif "json" in name.lower():
                                status = "✅ JSON Ready"
                            elif "timeseries" in name.lower():
                                status = "✅ TS Ready"
                            else:
                                status = "✅ Loaded"

                            module_table.add_row(name, version, status)
                else:
                    module_table.add_row("No modules", "N/A", "❌ Plain Redis")

            except Exception as e:
                module_table.add_row("Error", str(e)[:10], "❌ Failed")

        layout["module_info"].update(Panel(module_table, title="🔌 Redis Modules", box=ROUNDED))

        layout["footer"].update(self._create_footer())

        return layout

    def _run_basic_fallback(self, args):
        """Basic fallback interface when Rich is not available."""
        try:
            backend = getattr(args, "backend", None) or os.getenv(
                "ORKA_MEMORY_BACKEND",
                "redisstack",
            )

            # Provide proper Redis URL based on backend
            if backend == "redisstack":
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6380/0")
            else:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

            memory = create_memory_logger(backend=backend, redis_url=redis_url)

            if getattr(args, "json", False):
                return self._basic_json_watch(memory, backend, args)
            else:
                return self._basic_display_watch(memory, backend, args)

        except Exception as e:
            print(f"❌ Error in basic fallback: {e}", file=sys.stderr)
            return 1

    def _basic_json_watch(self, memory, backend: str, args):
        """Basic JSON mode memory watch."""
        try:
            while True:
                try:
                    stats = memory.get_memory_stats()

                    output = {
                        "timestamp": stats.get("timestamp"),
                        "backend": backend,
                        "stats": stats,
                    }

                    print(json.dumps(output, indent=2, default=str))
                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(json.dumps({"error": str(e), "backend": backend}), file=sys.stderr)
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0

    def _basic_display_watch(self, memory, backend: str, args):
        """Basic display mode memory watch."""
        try:
            while True:
                try:
                    # Clear screen unless disabled
                    if not getattr(args, "no_clear", False):
                        os.system("cls" if os.name == "nt" else "clear")

                    print("=== OrKa Memory Watch ===")
                    print(f"Backend: {backend} | Interval: {getattr(args, 'interval', 5)}s")
                    print("-" * 60)

                    # Get comprehensive stats
                    stats = memory.get_memory_stats()

                    # Display basic metrics
                    print("📊 Memory Statistics:")
                    print(f"   Total Entries: {stats.get('total_entries', 0)}")
                    print(f"   Stored Memories: {stats.get('stored_memories', 0)}")
                    print(f"   Orchestration Logs: {stats.get('orchestration_logs', 0)}")

                    time.sleep(getattr(args, "interval", 5))

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error in memory watch: {e}", file=sys.stderr)
                    time.sleep(getattr(args, "interval", 5))

        except KeyboardInterrupt:
            pass

        return 0


# Textual App for more advanced interactions
if TEXTUAL_AVAILABLE:

    class OrKaMonitorApp(App):
        """Textual-based interactive monitoring app."""

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("1", "show_dashboard", "Dashboard"),
            Binding("2", "show_memories", "Memories"),
            Binding("3", "show_performance", "Performance"),
            Binding("4", "show_config", "Config"),
            Binding("r", "refresh", "Refresh"),
        ]

        CSS = """
        Screen {
            background: $surface;
        }
        
        .box {
            border: solid $primary;
            background: $surface;
        }
        
        .header {
            dock: top;
            height: 3;
            background: $primary;
            color: $text;
        }
        
        .footer {
            dock: bottom;
            height: 3;
            background: $primary-darken-3;
            color: $text;
        }
        """

        def __init__(self, tui_interface):
            super().__init__()
            self.tui = tui_interface

        def compose(self) -> ComposeResult:
            """Create the UI components."""
            yield Header()

            with Container(classes="box"):
                yield Static("OrKa Memory Monitor - Loading...", id="main-content")

            yield Footer()

        def on_mount(self) -> None:
            """Set up the app when mounted."""
            self.set_interval(self.tui.refresh_interval, self.update_display)

        def update_display(self) -> None:
            """Update the display with fresh data."""
            try:
                self.tui._update_data()
                content = self.query_one("#main-content", Static)

                # Simple text-based display for now
                stats = self.tui.stats.current
                display_text = f"""
OrKa Memory Statistics:
Total Entries: {stats.get("total_entries", 0)}
Stored Memories: {stats.get("stored_memories", 0)}
Orchestration Logs: {stats.get("orchestration_logs", 0)}
Active Entries: {stats.get("active_entries", 0)}
Expired Entries: {stats.get("expired_entries", 0)}

Backend: {self.tui.backend}
Status: Connected
                """

                content.update(display_text)

            except Exception as e:
                content = self.query_one("#main-content", Static)
                content.update(f"Error updating display: {e}")

        def action_show_dashboard(self) -> None:
            """Show dashboard view."""
            self.tui.current_view = "dashboard"

        def action_show_memories(self) -> None:
            """Show memories view."""
            self.tui.current_view = "memories"

        def action_show_performance(self) -> None:
            """Show performance view."""
            self.tui.current_view = "performance"

        def action_show_config(self) -> None:
            """Show config view."""
            self.tui.current_view = "config"

        def action_refresh(self) -> None:
            """Force refresh data."""
            self.update_display()
