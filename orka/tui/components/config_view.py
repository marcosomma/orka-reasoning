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

"""Configuration View Component Builder."""

import time

try:
    from rich.box import HEAVY, ROUNDED
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ConfigViewMixin:
    """Mixin providing configuration view builder."""

    # Expected from host class
    memory_logger: object
    backend: str

    def create_config_view(self):
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
                "[CONF] Configuration & System Health - Backend Testing & Diagnostics",
                box=HEAVY,
                style="bold magenta",
            ),
        )

        # Backend configuration testing
        layout["backend_config"].update(
            Panel(self._create_backend_config_table(), title="[CONN] Backend Health", box=ROUNDED),
        )

        # Decay configuration
        layout["decay_config"].update(
            Panel(self._create_decay_config_table(), title="⏰ Memory Decay", box=ROUNDED),
        )

        # Connection testing
        layout["connection_test"].update(
            Panel(self._create_connection_test_table(), title="[...] Connection Tests", box=ROUNDED),
        )

        # System information
        layout["system_info"].update(
            Panel(self._create_system_info_table(), title="[HOST]️ System Information", box=ROUNDED),
        )

        # Module information
        layout["module_info"].update(
            Panel(self._create_module_info_table(), title="[CONN] Redis Modules", box=ROUNDED),
        )

        layout["footer"].update(self.create_footer())

        return layout

    def _create_backend_config_table(self):
        """Create backend configuration table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white", width=15)
        table.add_column(style="green", width=8)

        table.add_row("[bold]Backend Configuration:[/bold]", "", "")
        table.add_row("  Type", self.backend.upper(), "")

        # Test backend connectivity
        if hasattr(self.memory_logger, "client"):
            try:
                self.memory_logger.client.ping()
                table.add_row("  Connection", "[OK] Active", "")

                # Get Redis info
                redis_info = self.memory_logger.client.info()
                table.add_row(
                    "  Redis Version",
                    redis_info.get("redis_version", "Unknown"),
                    "",
                )
                table.add_row("  Mode", redis_info.get("redis_mode", "standalone"), "")

                # Test memory operations
                try:
                    test_key = "orka:tui:health_check"
                    self.memory_logger.client.set(test_key, "test", ex=5)
                    test_result = self.memory_logger.client.get(test_key)
                    if test_result:
                        table.add_row("  Read/Write", "[OK] Working", "")
                        self.memory_logger.client.delete(test_key)
                    else:
                        table.add_row("  Read/Write", "[FAIL] Failed", "")
                except Exception:
                    table.add_row("  Read/Write", "[FAIL] Error", "")

            except Exception as e:
                table.add_row("  Connection", "[FAIL] Failed", "")
                table.add_row("  Error", str(e)[:15], "")
        else:
            table.add_row("  Connection", "[FAIL] No Client", "")

        # Backend-specific tests
        if self.backend == "redisstack":
            self._add_redisstack_backend_tests(table)

        return table

    def _add_redisstack_backend_tests(self, table):
        """Add RedisStack-specific backend tests."""
        table.add_row("", "", "")
        table.add_row("[bold]RedisStack Tests:[/bold]", "", "")

        try:
            if hasattr(self.memory_logger, "client"):
                modules = self.memory_logger.client.execute_command("MODULE", "LIST")
                has_search = any("search" in str(module).lower() for module in modules)

                if has_search:
                    table.add_row("  Search Module", "[OK] Loaded", "")

                    try:
                        index_info = self.memory_logger.client.ft("enhanced_memory_idx").info()
                        table.add_row("  HNSW Index", "[OK] Available", "")
                        table.add_row(
                            "  Documents",
                            f"{index_info.get('num_docs', 0):,}",
                            "docs",
                        )
                    except Exception:
                        table.add_row("  HNSW Index", "[FAIL] Missing", "")
                else:
                    table.add_row("  Search Module", "[FAIL] Missing", "")

        except Exception as e:
            table.add_row("  Module Check", f"[FAIL] {str(e)[:10]}", "")

    def _create_decay_config_table(self):
        """Create decay configuration table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=18)
        table.add_column(style="white", width=15)
        table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "decay_config"):
            config = self.memory_logger.decay_config

            table.add_row("[bold]Memory Decay:[/bold]", "", "")

            if config and config.get("enabled", False):
                table.add_row("  Status", "[OK] Enabled", "")
                table.add_row(
                    "  Short-term TTL",
                    f"{config.get('default_short_term_hours', 1)}",
                    "hours",
                )
                table.add_row(
                    "  Long-term TTL",
                    f"{config.get('default_long_term_hours', 24)}",
                    "hours",
                )
                table.add_row(
                    "  Check Interval",
                    f"{config.get('check_interval_minutes', 30)}",
                    "min",
                )

                try:
                    test_result = self.memory_logger.cleanup_expired_memories(dry_run=True)
                    table.add_row("  Cleanup Test", "[OK] Working", "")
                    table.add_row(
                        "  Last Check",
                        str(test_result.get("duration_seconds", 0)),
                        "sec",
                    )
                except Exception:
                    table.add_row("  Cleanup Test", "[FAIL] Error", "")

            else:
                table.add_row("  Status", "[FAIL] Disabled", "")
                table.add_row("  Reason", "Not configured", "")
        else:
            table.add_row("  Status", "[FAIL] Unavailable", "")

        return table

    def _create_connection_test_table(self):
        """Create connection testing table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white", width=12)
        table.add_column(style="green", width=8)

        table.add_row("[bold]Connection Testing:[/bold]", "", "")

        if hasattr(self.memory_logger, "client"):
            try:
                # Latency test
                start_time = time.time()
                self.memory_logger.client.ping()
                latency = (time.time() - start_time) * 1000

                if latency < 5:
                    latency_status = "[green][FAST] Excellent[/green]"
                elif latency < 20:
                    latency_status = "[yellow][WARN] Good[/yellow]"
                else:
                    latency_status = "[red][SLOW] Slow[/red]"

                table.add_row("  Ping Latency", f"{latency:.1f}ms", latency_status)

                # Memory stats test
                start_time = time.time()
                self.memory_logger.get_memory_stats()
                stats_time = (time.time() - start_time) * 1000
                table.add_row("  Stats Query", f"{stats_time:.1f}ms", "[OK]")

                # Search test
                if hasattr(self.memory_logger, "search_memories"):
                    start_time = time.time()
                    self.memory_logger.search_memories(" ", num_results=1)
                    search_time = (time.time() - start_time) * 1000
                    table.add_row("  Search Test", f"{search_time:.1f}ms", "[OK]")

            except Exception as e:
                table.add_row("  Test Failed", str(e)[:15], "[FAIL]")

        return table

    def _create_system_info_table(self):
        """Create system information table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="cyan", width=18)
        table.add_column(style="white", width=15)
        table.add_column(style="green", width=8)

        if hasattr(self.memory_logger, "client"):
            try:
                redis_info = self.memory_logger.client.info()

                table.add_row("[bold]Redis System:[/bold]", "", "")
                table.add_row("  Version", redis_info.get("redis_version", "Unknown"), "")
                table.add_row(
                    "  Architecture",
                    str(redis_info.get("arch_bits", "Unknown")),
                    "bit",
                )
                table.add_row("  OS", redis_info.get("os", "Unknown"), "")

                table.add_row("", "", "")
                table.add_row("[bold]Memory Usage:[/bold]", "", "")
                table.add_row(
                    "  Used Memory",
                    redis_info.get("used_memory_human", "N/A"),
                    "",
                )
                table.add_row(
                    "  Peak Memory",
                    redis_info.get("used_memory_peak_human", "N/A"),
                    "",
                )
                table.add_row(
                    "  Memory Ratio",
                    f"{redis_info.get('used_memory_peak_perc', '0')}%",
                    "",
                )

            except Exception as e:
                table.add_row("System Error:", str(e)[:15], "")

        return table

    def _create_module_info_table(self):
        """Create module information table."""
        table = Table(show_header=True, header_style="bold cyan", box=ROUNDED)
        table.add_column("Module", style="cyan", width=15)
        table.add_column("Version", style="white", width=12)
        table.add_column("Status", style="green", width=10)

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

                            if "search" in name.lower():
                                status = "[OK] Vector Ready"
                            elif "json" in name.lower():
                                status = "[OK] JSON Ready"
                            elif "timeseries" in name.lower():
                                status = "[OK] TS Ready"
                            else:
                                status = "[OK] Loaded"

                            table.add_row(name, version, status)
                else:
                    table.add_row("No modules", "N/A", "[FAIL] Plain Redis")

            except Exception as e:
                table.add_row("Error", str(e)[:10], "[FAIL] Failed")

        return table

