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

"""Performance Panel Component Builders."""

try:
    from rich.box import HEAVY, ROUNDED
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class PerformancePanelMixin:
    """Mixin providing performance panel builders."""

    # Expected from host class
    memory_logger: object
    backend: str
    performance_history: list

    def create_compact_performance_panel(self):
        """Create a compact performance panel with comprehensive metrics."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=11)
        table.add_column(style="white", width=8, justify="right")
        table.add_column(style="green", width=6)
        table.add_column(style="yellow", width=4)

        if not self.performance_history:
            table.add_row("  Status", "Collecting", "data", "⏳")
            return Panel(table, title="[FAST] Performance & System", box=ROUNDED)

        latest_perf = self.performance_history[-1]

        # Performance metrics with status indicators
        avg_search_time = latest_perf.get("average_search_time", 0)
        if avg_search_time < 0.1:
            perf_status = "[FAST]"
        elif avg_search_time < 0.5:
            perf_status = "[WARN]"
        else:
            perf_status = "[SLOW]"

        table.add_row(
            "  Search Speed",
            f"{avg_search_time:.3f}s",
            "time",
            f"[cyan]{perf_status}[/cyan]",
        )

        # Vector search metrics for RedisStack
        if self.backend == "redisstack":
            self._add_redisstack_metrics(table)
        else:
            # Basic Redis metrics
            table.add_row("  Backend", self.backend.upper(), "type", "[DB]️")
            table.add_row(
                "  Status",
                "Connected",
                "conn",
                "[OK]" if hasattr(self.memory_logger, "client") else "[FAIL]",
            )

        # Memory operations if available
        if hasattr(self.memory_logger, "get_performance_metrics"):
            try:
                perf = self.memory_logger.get_performance_metrics()
                writes = perf.get("memory_writes", 0)
                reads = perf.get("memory_reads", 0)
                table.add_row("  Writes/min", f"{writes}", "ops", "[EDIT]️")
                table.add_row("  Reads/min", f"{reads}", "ops", "[VIEW]️")
            except Exception:
                pass

        return Panel(table, title="[FAST] Performance & System Health", box=ROUNDED)

    def _add_redisstack_metrics(self, table):
        """Add RedisStack-specific metrics to the table."""
        try:
            if hasattr(self.memory_logger, "client"):
                # HNSW Index status
                index_info = self.memory_logger.client.ft("enhanced_memory_idx").info()
                docs = index_info.get("num_docs", 0)
                indexing = index_info.get("indexing", False)

                table.add_row("  Vector Docs", f"{docs:,}", "docs", "[STATS]")
                table.add_row(
                    "  HNSW Index",
                    "Active" if indexing else "Idle",
                    "status",
                    "[OK]" if indexing else "⏸",
                )

                # Redis system info
                redis_info = self.memory_logger.client.info()
                memory_used = redis_info.get("used_memory_human", "N/A")
                clients = redis_info.get("connected_clients", 0)
                ops_per_sec = redis_info.get("instantaneous_ops_per_sec", 0)

                table.add_row("  Memory Used", memory_used, "mem", "[SAVE]")
                table.add_row("  Clients", f"{clients}", "conn", "[LINK]")
                table.add_row(
                    "  Ops/sec",
                    f"{ops_per_sec}",
                    "rate",
                    "[FAST]" if ops_per_sec > 10 else "[PERF]",
                )

                # Module detection
                try:
                    modules = self.memory_logger.client.execute_command("MODULE", "LIST")
                    module_count = len(modules) if modules else 0
                    table.add_row("  Modules", f"{module_count}", "ext", "[CONN]")
                except Exception:
                    table.add_row("  Modules", "Unknown", "ext", "[?]")

        except Exception as e:
            table.add_row("  Vector", "Error", "state", "[FAIL]")
            table.add_row("  Redis", str(e)[:6], "err", "[CRASH]")

    def create_performance_view(self):
        """Create performance view (placeholder)."""
        return Panel("Performance view not implemented yet", title="[FAST] Performance View")

    def create_performance_panel(self):
        """Create comprehensive performance metrics panel."""
        if not self.performance_history and not hasattr(
            self.memory_logger,
            "get_performance_metrics",
        ):
            return Panel("No performance data available", title="[START] Performance")

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
                title="[PERF] Performance Trends",
                box=ROUNDED,
            ),
        )

        layout["header"].update(
            Panel(
                "[START] Performance Monitoring - Real-time Memory & System Metrics",
                box=HEAVY,
                style="bold green",
            ),
        )

        # Create performance table
        perf_table = self._create_performance_metrics_table()
        layout["performance_metrics"].update(
            Panel(perf_table, title="[FAST] Performance Metrics", box=ROUNDED),
        )

        # Quality metrics
        quality_table = self._create_quality_metrics_table()
        layout["quality_metrics"].update(
            Panel(quality_table, title="⭐ Memory Quality", box=ROUNDED),
        )

        layout["footer"].update(self.create_footer())

        return layout

    def _create_performance_metrics_table(self):
        """Create the performance metrics table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white", width=15)
        table.add_column(style="green", width=10)

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

                table.add_row("", "", "")
                table.add_row("[bold]Memory Operations:[/bold]", "", "")
                table.add_row("  Memory Writes", f"{latest.get('memory_writes', 0):,}", "/min")
                table.add_row("  Memory Reads", f"{latest.get('memory_reads', 0):,}", "/min")
                table.add_row("  Total Memories", f"{latest.get('memory_count', 0):,}", "stored")

                # Index health
                index_status = latest.get("index_status", {})
                if index_status and index_status.get("status") != "unavailable":
                    table.add_row("", "", "")
                    table.add_row("[bold]HNSW Index Health:[/bold]", "", "")
                    table.add_row(
                        "  Index Status",
                        "[OK] Active" if index_status.get("indexing", False) else "⏸️ Idle",
                        "",
                    )
                    table.add_row("  Documents", f"{index_status.get('num_docs', 0):,}", "docs")
                    table.add_row(
                        "  Index Progress",
                        f"{index_status.get('percent_indexed', 100):.1f}",
                        "%",
                    )

            except Exception as e:
                table.add_row("Performance Error:", str(e)[:30], "")

        return table

    def _create_quality_metrics_table(self):
        """Create the quality metrics table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=18)
        table.add_column(style="white", width=12)
        table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "get_performance_metrics"):
            try:
                perf = self.memory_logger.get_performance_metrics()
                quality_metrics = perf.get("memory_quality", {})

                if quality_metrics:
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
                    table.add_row(
                        "  Avg Content Size",
                        f"{quality_metrics.get('avg_content_length', 0):.0f}",
                        "chars",
                    )

                    table.add_row("", "", "")
                    table.add_row("[bold]Quality Distribution:[/bold]", "", "")

                    score_ranges = quality_metrics.get("score_distribution", {})
                    for range_name, count in score_ranges.items():
                        table.add_row(f"  {range_name}", f"{count:,}", "memories")
                else:
                    table.add_row("No quality metrics", "available", "")

            except Exception as e:
                table.add_row("Quality Error:", str(e)[:15], "")

        return table

    def create_simple_chart(self, data, width=25, height=3):
        """Create a simple ASCII chart for trending data."""
        if not data or len(data) < 2:
            return "[dim]No data[/dim]"

        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)

        if max_val == min_val:
            return "[dim]Stable[/dim]"

        chart_lines = []
        for row in range(height):
            line = ""
            for value in data[-width:]:
                normalized = (value - min_val) / (max_val - min_val) * (height - 1)
                if normalized >= (height - 1 - row):
                    line += "█"
                else:
                    line += " "
            chart_lines.append(line)

        return "\n".join(chart_lines)

