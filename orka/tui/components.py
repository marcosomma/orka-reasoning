"""
UI component builders for TUI interface panels and displays.
"""

import datetime

try:
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED, SIMPLE
    from rich.layout import Layout
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ComponentBuilder:
    """Builds UI components for the TUI interface."""

    def __init__(self, data_manager):
        self.data_manager = data_manager

    @property
    def stats(self):
        return self.data_manager.stats

    @property
    def memory_data(self):
        return self.data_manager.memory_data

    @property
    def performance_history(self):
        return self.data_manager.performance_history

    @property
    def memory_logger(self):
        return self.data_manager.memory_logger

    @property
    def backend(self):
        return self.data_manager.backend

    @property
    def running(self):
        return getattr(self.data_manager, "running", True)

    def create_compact_header(self):
        """Create a compact header."""
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        status_color = "green" if self.running else "red"

        header_text = Text()
        header_text.append("🚀 OrKa Monitor ", style="bold blue")
        header_text.append(f"| {self.backend.upper()} ", style="cyan")
        header_text.append(f"| {current_time} ", style="dim")
        header_text.append("●", style=f"bold {status_color}")

        return Panel(Align.center(header_text), box=SIMPLE, style="blue")

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

    def create_compact_memories_panel(self):
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

    def create_compact_performance_panel(self):
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

    def create_compact_footer(self):
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

    def create_header(self):
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

    def create_footer(self):
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

    def create_recent_memories_panel(self):
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

    def create_simple_chart(self, data, width=25, height=3):
        """Create a simple ASCII chart for trending data."""
        if not data or len(data) < 2:
            return "[dim]No data[/dim]"

        # Normalize data to chart height
        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)

        if max_val == min_val:
            return "[dim]Stable[/dim]"

        chart_lines = []
        for row in range(height):
            line = ""
            for i, value in enumerate(data[-width:]):
                normalized = (value - min_val) / (max_val - min_val) * (height - 1)
                if normalized >= (height - 1 - row):
                    line += "█"
                else:
                    line += " "
            chart_lines.append(line)

        return "\n".join(chart_lines)

    # Placeholder methods for missing components referenced in the original code
    def create_memory_browser(self):
        """Create memory browser view (placeholder)."""
        return Panel("Memory browser not implemented yet", title="🧠 Memory Browser")

    def create_performance_view(self):
        """Create performance view (placeholder)."""
        return Panel("Performance view not implemented yet", title="⚡ Performance View")

    def create_performance_panel(self):
        """Create comprehensive performance metrics panel."""

        if not self.performance_history and not hasattr(
            self.memory_logger,
            "get_performance_metrics",
        ):
            return Panel("No performance data available", title="🚀 Performance")

        # Create layout for performance view
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Split main into performance sections
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        layout["left"].split_column(
            Layout(name="performance_metrics", size=15),
            Layout(name="quality_metrics"),
        )

        layout["right"].update(
            Panel(
                "[dim]Performance charts would go here[/dim]",
                title="📈 Performance Trends",
                box=ROUNDED,
            ),
        )

        layout["header"].update(
            Panel(
                "🚀 Performance Monitoring - Real-time Memory & System Metrics",
                box=HEAVY,
                style="bold green",
            ),
        )

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

            except Exception as e:
                table.add_row("Performance Error:", str(e)[:30], "")

        layout["performance_metrics"].update(
            Panel(table, title="⚡ Performance Metrics", box=ROUNDED),
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

        layout["footer"].update(self.create_footer())

        return layout

    def create_config_view(self):
        """Create comprehensive configuration view with backend testing."""
        import time

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

        layout["footer"].update(self.create_footer())

        return layout
