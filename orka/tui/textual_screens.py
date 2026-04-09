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

"""
Screen implementations for OrKa Textual TUI application.
"""

import logging
import platform
import sys
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from .textual_widgets import LogsWidget, MemoryTableWidget, SkillsTableWidget, StatsWidget
from .message_renderer import VintageMessageRenderer
from ..startup.banner import get_version

logger = logging.getLogger(__name__)

# Compact OrKa ASCII branding (4 lines, fits in a TUI header strip)
ORKA_LOGO = (
    "\n"
    "[bold cyan]   ██████╗          ██╗  ██╗  █████╗ [/bold cyan]\n"
    "[bold blue]  ██╔═══██╗ ██╗ ██╗ ██║ ██╔╝ ██╔══██╗[/bold blue]\n"
    "[bold purple]  ██║   ██║ ████╔═╝ █████╔╝  ███████║[/bold purple]\n"
    "[bold magenta]  ██║   ██║ ██║     ██╔═██╗  ██╔══██║[/bold magenta]\n"
    "[bold pink]  ╚██████╔╝ ██║     ██║  ██╗ ██║  ██║[/bold pink]\n"
    "[bold yellow]   ╚═════╝  ╚═╝     ╚═╝  ╚═╝ ╚═╝  ╚═╝[/bold yellow]"
)


def _build_logo_banner() -> str:
    """Build a branded logo banner with version."""
    version = get_version()
    return (
        f"{ORKA_LOGO}\n"
        f"[bold magenta]  Orchestrator[/bold magenta] [bold yellow]Kit[/bold yellow] [bold cyan]Agents[/bold cyan]  "
        f"[dim]·[/dim] [bold white]v{version}[/bold white]  "
        f"[dim]· Reasoning Framework[/dim]"
        f"\n"
    )


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
        # Branded logo header
        yield Static(_build_logo_banner(), id="dashboard-logo", classes="logo-banner")

        with Container(classes="dashboard-grid"):
            # Row 1 left: Memory stats
            with Container(classes="stats-container"):
                yield StatsWidget(self.data_manager, id="dashboard-stats")

            # Row 1 right: Brain skills overview
            with Container(classes="health-container"):
                yield Static("[AI] Brain Skills", classes="container-compact")
                yield Static("", id="dashboard-skills")

            # Row 2 left: Recent memories
            with Container(classes="memory-container"):
                yield Static("[LIST] Recent Memories", classes="container-compact")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="all",
                    id="dashboard-memories",
                )

            # Row 2 right: Recent logs
            with Container(classes="logs-container"):
                yield Static("[LIST] Recent Logs", classes="container-compact")
                yield LogsWidget(self.data_manager, id="dashboard-logs")

            # Row 3 left: Quick health
            with Container(classes="health-container"):
                yield Static("[HEALTH] System", classes="container-compact")
                yield Static("", id="quick-health")

            # Row 3 right: Environment
            with Container(classes="stats-container"):
                yield Static("[CONF] Environment", classes="container-compact")
                yield Static("", id="dashboard-env")

    def refresh_data(self) -> None:
        """Refresh dashboard data."""
        try:
            # Update stats widget
            stats_widget = self.query_one("#dashboard-stats", StatsWidget)
            stats_widget.update_stats()

            unified = self.data_manager.get_unified_stats()
            health = unified["health"]
            backend = unified["backend"]

            # ── Brain skills panel ──
            skills_widget = self.query_one("#dashboard-skills", Static)
            brain_skills = self.data_manager.get_brain_skills()
            skills_count = len(brain_skills)
            if skills_count > 0:
                avg_conf = sum(s.confidence for s in brain_skills) / skills_count
                total_uses = sum(s.usage_count for s in brain_skills)
                total_tx = sum(len(s.transfer_history) for s in brain_skills)
                avg_success = (
                    sum(s.success_rate for s in brain_skills) / skills_count
                )
                # Count by type
                type_counts: dict[str, int] = {}
                for sk in brain_skills:
                    st = getattr(sk, "skill_type", "procedural")
                    label = st.replace("_", " ").title()
                    type_counts[label] = type_counts.get(label, 0) + 1
                type_lines = "\n".join(
                    f"  [cyan]{cnt}[/cyan] {typ}" for typ, cnt in type_counts.items()
                )
                skills_content = (
                    f"[bold cyan]{skills_count}[/bold cyan] skills  "
                    f"[dim]│[/dim] avg conf [cyan]{avg_conf:.0%}[/cyan]  "
                    f"[dim]│[/dim] success [cyan]{avg_success:.0%}[/cyan]\n"
                    f"Uses: [cyan]{total_uses}[/cyan]  "
                    f"[dim]│[/dim] Transfers: [cyan]{total_tx}[/cyan]\n\n"
                    f"{type_lines}"
                )
            else:
                skills_content = (
                    "[dim]No skills yet[/dim]\n"
                    "[dim]Run brain workflows to start learning[/dim]"
                )
            skills_widget.update(skills_content)

            # ── Quick health panel ──
            health_widget = self.query_one("#quick-health", Static)
            overall = health["overall"]
            connection_status = f"{health['backend']['icon']} {health['backend']['message']}"
            perf = health["performance"]
            health_content = (
                f"{overall['icon']} Overall: {overall['message']}\n"
                f"{connection_status}\n"
                f"{perf['icon']} Perf: {perf['message']}\n"
                f"Active: [cyan]{backend['active_entries']:,}[/cyan]  "
                f"[dim]│[/dim] Expired: [cyan]{backend['expired_entries']:,}[/cyan]"
            )
            health_widget.update(health_content)

            # ── Environment panel ──
            env_widget = self.query_one("#dashboard-env", Static)
            os_name = platform.system()
            os_ver = platform.release()
            py_ver = (
                f"{sys.version_info.major}.{sys.version_info.minor}"
                f".{sys.version_info.micro}"
            )
            env_content = (
                f"OS: [cyan]{os_name} {os_ver}[/cyan]\n"
                f"Python: [cyan]{py_ver}[/cyan]\n"
                f"Backend: [cyan]{backend['type']}[/cyan]\n"
                f"Entries: [cyan]{unified['total_entries']:,}[/cyan]"
            )
            env_widget.update(env_content)

            # ── Tables ──
            memories_widget = self.query_one("#dashboard-memories", MemoryTableWidget)
            memories_widget.update_data("all")

            logs_widget = self.query_one("#dashboard-logs", LogsWidget)
            logs_widget.update_data()

        except Exception as e:
            logger.debug(f"TUI dashboard refresh error (non-fatal): {e}")


class ShortMemoryScreen(BaseOrKaScreen):
    """Screen for viewing short-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the short memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="short-memory-header"):
                yield Static("[FAST] Short-Term Memory", classes="container-compact")
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
                yield Static("[FILE] Content & Metadata", classes="container-compact")
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
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI short-content-text widget not found (non-fatal): {e}")
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata using VintageMessageRenderer
            try:
                # Use the advanced message renderer for better formatting
                renderer = VintageMessageRenderer(theme="default")
                formatted_content = renderer.render_memory_content(
                    message.memory_data,
                    show_full_key=False
                )
                
                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh short memory data."""
        try:
            # [TARGET] USE UNIFIED: Get comprehensive stats from centralized calculation
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

        except Exception as e:
            logger.debug(f"TUI short memory refresh error (non-fatal): {e}")


class LongMemoryScreen(BaseOrKaScreen):
    """Screen for viewing long-term memory entries."""

    def compose_content(self) -> ComposeResult:
        """Compose the long memory layout."""
        with Vertical():
            # Top section: Compact header
            with Container(classes="memory-container", id="long-memory-header"):
                yield Static("[AI] Long-Term Memory", classes="container-compact")
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
                yield Static("[FILE] Content & Metadata", classes="container-compact")
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
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI long-content-text widget not found (non-fatal): {e}")
            return

        if not content_widget:
            return

        if message.memory_data is None:
            # Deselected - show simple placeholder
            content_widget.update("[dim]Select a row to view memory content and metadata[/dim]")  # type: ignore [unreachable]
        else:
            # Selected - show content and metadata using VintageMessageRenderer
            try:
                # Use the advanced message renderer for better formatting
                renderer = VintageMessageRenderer(theme="default")
                formatted_content = renderer.render_memory_content(
                    message.memory_data,
                    show_full_key=False
                )
                
                content_widget.update(formatted_content)
            except Exception as e:
                content_widget.update(f"[red]Error loading content: {e!s}[/red]")

    def refresh_data(self) -> None:
        """Refresh long memory data."""
        try:
            # [TARGET] USE UNIFIED: Get comprehensive stats from centralized calculation
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

        except Exception as e:
            logger.debug(f"TUI long memory refresh error (non-fatal): {e}")


class MemoryLogsScreen(BaseOrKaScreen):
    """Screen for viewing memory system logs."""

    def compose_content(self) -> ComposeResult:
        """Compose the memory logs layout."""
        with Vertical():
            # Top 50%: Orchestration Logs Table
            with Container(classes="logs-container", id="logs-top-section"):
                yield Static("[SYNC] Orchestration Logs", classes="container-compact")
                yield MemoryTableWidget(
                    self.data_manager,
                    memory_type="logs",
                    id="orchestration-logs-table",
                )

            # Bottom 50%: Content inspector for selected logs
            with Container(classes="content-panel", id="logs-content-panel"):
                yield Static("[FILE] Entry Details", classes="container-compact")
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
        except Exception as e:
            # If we can't find the widget, log error and return
            logger.debug(f"TUI logs-content-text widget not found (non-fatal): {e}")
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

[bold green][FILE] CONTENT:[/bold green]
{content_text}

[bold yellow][LIST] METADATA:[/bold yellow]
{metadata_display}

[bold cyan][TAG]️ SYSTEM INFO:[/bold cyan]
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

        except Exception as e:
            logger.debug(f"TUI memory logs refresh error (non-fatal): {e}")


class HealthScreen(BaseOrKaScreen):
    """Screen for system health monitoring."""

    def compose_content(self) -> ComposeResult:
        """Compose the health monitoring layout as a 2×2 grid with summary bar."""
        with Vertical():
            # Branded logo header
            yield Static(_build_logo_banner(), id="health-logo", classes="logo-banner")

            # Top: 1-line summary bar
            yield Static("", id="health-summary")

            # 2×2 grid of health panels
            with Container(classes="health-grid"):
                with Container(classes="health-panel"):
                    yield Static("[CONN] Connection", classes="container-compact")
                    yield Static("", id="health-connection")

                with Container(classes="health-panel"):
                    yield Static("[FAST] Performance", classes="container-compact")
                    yield Static("", id="health-performance")

                with Container(classes="health-panel"):
                    yield Static("[AI] Memory & Brain", classes="container-compact")
                    yield Static("", id="health-memory")

                with Container(classes="health-panel"):
                    yield Static("[CONF] System", classes="container-compact")
                    yield Static("", id="health-system")

    def refresh_data(self) -> None:
        """Refresh health monitoring data."""
        try:
            unified = self.data_manager.get_unified_stats()
            health = unified["health"]
            backend = unified["backend"]
            stored_memories = unified["stored_memories"]
            log_entries = unified["log_entries"]

            overall = health["overall"]
            backend_health = health["backend"]
            memory_health = health["memory"]
            perf_health = health["performance"]
            total_entries = backend["active_entries"] + backend["expired_entries"]
            search_time = unified["performance"]["search_time"]
            stored_total = stored_memories["total"]
            logs_total = log_entries["orchestration"]
            usage_pct = (
                (backend["active_entries"] / total_entries * 100) if total_entries > 0 else 0
            )
            data_points = len(self.data_manager.stats.history)
            trend = unified["trends"]["total_entries"]

            # ── Summary bar ──
            summary = self.query_one("#health-summary", Static)
            summary.update(
                f"[bold]{overall['icon']} {overall['message']}[/bold]  "
                f"[dim]│[/dim] [cyan]{total_entries:,}[/cyan] total  "
                f"[dim]│[/dim] [green]{backend['active_entries']:,}[/green] active  "
                f"[dim]│[/dim] [red]{backend['expired_entries']:,}[/red] expired  "
                f"[dim]│[/dim] {self._format_current_time()}  "
                f"[dim]│ 2s refresh │ {backend['type']}[/dim]"
            )

            # ── Connection panel ──
            conn = self.query_one("#health-connection", Static)
            conn.update(
                f"{backend_health['icon']} {backend_health['message']}\n\n"
                f"[cyan]Backend:[/cyan]  {backend['type']}\n"
                f"[cyan]Protocol:[/cyan] Redis\n"
                f"[cyan]Decay:[/cyan]    "
                f"{'[green]Active[/green]' if backend.get('decay_enabled') else '[yellow]Inactive[/yellow]'}"
            )

            # ── Performance panel ──
            perf = self.query_one("#health-performance", Static)
            if search_time < 0.01:
                time_color = "green"
            elif search_time < 0.1:
                time_color = "yellow"
            else:
                time_color = "red"
            perf.update(
                f"{perf_health['icon']} {perf_health['message']}\n\n"
                f"[cyan]Response:[/cyan]   [{time_color}]{search_time:.3f}s[/{time_color}]\n"
                f"[cyan]Data pts:[/cyan]   {data_points:,}\n"
                f"[cyan]Trend:[/cyan]      {trend}\n"
                f"[cyan]Retention:[/cyan]  100 points"
            )

            # ── Memory & Brain panel ──
            mem = self.query_one("#health-memory", Static)
            brain_skills = self.data_manager.get_brain_skills()
            skills_count = len(brain_skills)
            if skills_count > 0:
                avg_conf = sum(s.confidence for s in brain_skills) / skills_count
                brain_line = (
                    f"[cyan]Skills:[/cyan]   [green]{skills_count}[/green] "
                    f"(avg conf {avg_conf:.0%})"
                )
            else:
                brain_line = "[cyan]Skills:[/cyan]   [dim]none yet[/dim]"
            mem.update(
                f"{memory_health['icon']} {memory_health['message']}\n\n"
                f"[cyan]Active:[/cyan]   [green]{backend['active_entries']:,}[/green]\n"
                f"[cyan]Expired:[/cyan]  [red]{backend['expired_entries']:,}[/red]\n"
                f"[cyan]Stored:[/cyan]   {stored_total:,}  "
                f"[dim]│[/dim] Logs: {logs_total:,}\n"
                f"[cyan]Usage:[/cyan]    {usage_pct:.0f}%\n"
                f"{brain_line}"
            )

            # ── System panel ──
            sys_widget = self.query_one("#health-system", Static)
            os_name = platform.system()
            os_ver = platform.release()
            py_ver = (
                f"{sys.version_info.major}.{sys.version_info.minor}"
                f".{sys.version_info.micro}"
            )
            sys_widget.update(
                f"[cyan]OS:[/cyan]       {os_name} {os_ver}\n"
                f"[cyan]Python:[/cyan]   {py_ver}\n"
                f"[cyan]Backend:[/cyan]  {backend['type']}\n"
                f"[cyan]Features:[/cyan] TTL, Search, Indexing\n"
                f"[cyan]Config:[/cyan]   Auto-detected"
            )

        except Exception as e:
            logger.warning(f"HealthScreen refresh_data error: {e}")

    def _format_current_time(self) -> str:
        """Format current time for display."""
        return datetime.now().strftime("%H:%M:%S")


class BrainSkillsScreen(BaseOrKaScreen):
    """Screen for viewing brain-learned skills."""

    def compose_content(self) -> ComposeResult:
        """Compose the brain skills layout."""
        with Vertical():
            # Compact 1-line header with title + stats
            yield Static("[AI] Brain — Learned Skills", id="brain-skills-info")

            # Skills table (gets most of the space)
            with Container(id="brain-skills-content"):
                yield SkillsTableWidget(
                    self.data_manager,
                    id="brain-skills-table",
                )

            # Bottom section: Scrollable skill detail viewer
            with VerticalScroll(classes="content-panel", id="brain-skills-detail-panel"):
                yield Static("[FILE] Skill Details", classes="container-compact")
                yield Static(
                    "[dim]Select a skill to view its procedure, conditions, and transfer history[/dim]",
                    id="brain-skill-text",
                )

    def on_skills_table_widget_skill_selected(
        self,
        message: SkillsTableWidget.SkillSelected,
    ) -> None:
        """Handle skill selection to show details in lower panel."""
        try:
            content_widget = self.query_one("#brain-skill-text", Static)
        except Exception as e:
            logger.debug(f"TUI brain-skill-text widget not found (non-fatal): {e}")
            return

        if not message.skill_data:
            content_widget.update(
                "[dim]Select a skill to view its procedure, conditions, and transfer history[/dim]"
            )
            return

        try:
            s = message.skill_data
            name = s.get("name", "unnamed")
            description = s.get("description", "")
            skill_type = s.get("skill_type", "procedural")
            confidence = s.get("confidence", 0.0)
            usage_count = s.get("usage_count", 0)
            success_rate = s.get("success_rate", 0.0)
            tags = ", ".join(s.get("tags", [])) or "none"
            created = s.get("created_at", "unknown")[:19]
            updated = s.get("updated_at", "unknown")[:19]
            domain_keywords = s.get("domain_keywords", [])
            search_tokens = s.get("search_tokens", [])
            anti_signals = s.get("anti_signals", [])
            recipe = s.get("recipe", {})
            task_description = s.get("task_description", "")
            output_description = s.get("output_description", "")

            # Format skill type with colour
            type_labels = {
                "execution_recipe": "[green]Execution Recipe[/green]",
                "anti_pattern": "[red]Anti-Pattern[/red]",
                "graph_path": "[cyan]Graph Path[/cyan]",
                "procedural": "[blue]Procedural[/blue]",
                "prompt_template": "[yellow]Prompt Template[/yellow]",
                "parameter_config": "[magenta]Parameter Config[/magenta]",
                "domain_heuristic": "[white]Domain Heuristic[/white]",
            }
            type_display = type_labels.get(skill_type, skill_type)

            # Format procedure steps
            procedure = s.get("procedure", [])
            if procedure:
                steps_lines = []
                for step in procedure:
                    order = step.get("order", 0)
                    action = step.get("action", "")
                    desc = step.get("description", "")
                    optional = " [dim](optional)[/dim]" if step.get("is_optional") else ""
                    step_text = f"  {order}. [cyan]{action}[/cyan]{optional}"
                    if desc:
                        step_text += f"\n     [dim]{desc}[/dim]"
                    steps_lines.append(step_text)
                procedure_text = "\n".join(steps_lines)
            else:
                procedure_text = "  [dim]No procedure recorded[/dim]"

            # Format preconditions
            preconditions = s.get("preconditions", [])
            if preconditions:
                pre_lines = []
                for c in preconditions:
                    req = "[red]*[/red]" if c.get("required") else " "
                    pre_lines.append(f"  {req} {c.get('predicate', '')}")
                pre_text = "\n".join(pre_lines)
            else:
                pre_text = "  [dim]None[/dim]"

            # Format transfer history
            transfers = s.get("transfer_history", [])
            if transfers:
                tx_lines = []
                for t in transfers[-5:]:  # Show last 5
                    status = "[green]OK[/green]" if t.get("success") else "[red]FAIL[/red]"
                    ts = t.get("timestamp", "")[:10]
                    conf = t.get("confidence", 0.0)
                    tx_lines.append(f"  {status} conf={conf:.0%} [dim]{ts}[/dim]")
                tx_text = "\n".join(tx_lines)
            else:
                tx_text = "  [dim]No transfers yet[/dim]"

            # Format recipe (for execution_recipe type)
            recipe_text = ""
            if recipe:
                agents_raw = recipe.get("agents", [])
                strategy = recipe.get("strategy", recipe.get("pattern", ""))
                recipe_parts = []
                if strategy:
                    recipe_parts.append(f"  Strategy: [cyan]{strategy}[/cyan]")
                if agents_raw:
                    agent_names = [
                        a.get("id", str(a)) if isinstance(a, dict) else str(a)
                        for a in agents_raw
                    ]
                    recipe_parts.append(f"  Agents: [cyan]{', '.join(agent_names)}[/cyan]")
                recipe_text = "\n".join(recipe_parts) if recipe_parts else "  [dim]Empty[/dim]"
            else:
                recipe_text = "  [dim]N/A[/dim]"

            # Format domain keywords and search tokens
            kw_text = ", ".join(domain_keywords) if domain_keywords else "[dim]none[/dim]"
            tokens_text = ", ".join(search_tokens[:10]) if search_tokens else "[dim]none[/dim]"
            anti_text = ", ".join(anti_signals) if anti_signals else "[dim]none[/dim]"

            # Build sections — only show relevant sections per type
            sections = [
                f"[bold blue]{name}[/bold blue]  {type_display}",
                f"{description}" if description else "",
                "",
                "[bold green][LIST] PROCEDURE:[/bold green]",
                procedure_text,
                "",
                "[bold yellow][CONF] PRECONDITIONS:[/bold yellow]",
                pre_text,
            ]

            # Recipe section — only for execution_recipe type
            if skill_type == "execution_recipe":
                sections += [
                    "",
                    "[bold green][SYNC] RECIPE:[/bold green]",
                    recipe_text,
                ]

            # Anti-signals — only for anti_pattern type
            if skill_type == "anti_pattern" and anti_signals:
                sections += [
                    "",
                    "[bold red][WARN] ANTI-SIGNALS:[/bold red]",
                    f"  {anti_text}",
                ]

            sections += [
                "",
                f"[bold magenta][SYNC] TRANSFER HISTORY ({len(transfers)} total):[/bold magenta]",
                tx_text,
                "",
                "[bold cyan][TAG] INFO:[/bold cyan]",
                f"[cyan]Type:[/cyan] {type_display}",
                f"[cyan]Confidence:[/cyan] {confidence:.0%}",
                f"[cyan]Uses:[/cyan] {usage_count}",
                f"[cyan]Success Rate:[/cyan] {success_rate:.0%}",
                f"[cyan]Tags:[/cyan] {tags}",
                f"[cyan]Domain:[/cyan] {kw_text}",
                f"[cyan]Tokens:[/cyan] {tokens_text}",
                f"[cyan]Created:[/cyan] {created}",
                f"[cyan]Updated:[/cyan] {updated}",
                f"[cyan]TTL:[/cyan] {self._format_ttl_detail(s)}",
            ]

            # Task/output descriptions if present
            if task_description:
                sections.append(f"[cyan]Task:[/cyan] {task_description}")
            if output_description:
                sections.append(f"[cyan]Output:[/cyan] {output_description}")

            formatted = "\n".join(sections)

            content_widget.update(formatted)
        except Exception as e:
            content_widget.update(f"[red]Error loading skill details: {e!s}[/red]")

    @staticmethod
    def _format_ttl_detail(skill_data: dict) -> str:
        """Format TTL for the detail panel."""
        from datetime import UTC, datetime

        expires_at = skill_data.get("expires_at", "")
        if not expires_at:
            return "∞ Never expires"
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            remaining = expires_dt - datetime.now(UTC)
            total_seconds = remaining.total_seconds()
            if total_seconds <= 0:
                return "EXPIRED"
            hours = total_seconds / 3600
            if hours < 1:
                return f"{int(total_seconds / 60)}m remaining (expires {expires_at[:19]})"
            elif hours < 24:
                return f"{int(hours)}h remaining (expires {expires_at[:19]})"
            else:
                days = int(hours / 24)
                return f"{days}d {int(hours % 24)}h remaining (expires {expires_at[:19]})"
        except (ValueError, TypeError):
            return "Unknown"

    @staticmethod
    def _is_expiring_soon(skill: Any) -> bool:
        """Check if a skill expires within 24 hours."""
        from datetime import UTC, datetime

        try:
            expires_dt = datetime.fromisoformat(skill.expires_at)
            remaining_hours = (expires_dt - datetime.now(UTC)).total_seconds() / 3600
            return 0 < remaining_hours < 24
        except (ValueError, TypeError, AttributeError):
            return False

    def refresh_data(self) -> None:
        """Refresh brain skills data."""
        try:
            skills = self.data_manager.get_brain_skills()

            # Update info section — single compact line
            info_widget = self.query_one("#brain-skills-info", Static)
            count = len(skills)
            if count > 0:
                avg_conf = sum(s.confidence for s in skills) / count
                total_tx = sum(len(s.transfer_history) for s in skills)
                expiring_soon = sum(
                    1 for s in skills
                    if s.expires_at and not s.is_expired and self._is_expiring_soon(s)
                )
                expiring_part = (
                    f" [dim]│[/dim] [yellow]{expiring_soon} expiring soon[/yellow]"
                    if expiring_soon else ""
                )
                info_content = (
                    f"[bold][AI] Brain — Learned Skills[/bold] [dim]│[/dim] "
                    f"[cyan]{count}[/cyan] skills [dim]│[/dim] "
                    f"Avg conf: [cyan]{avg_conf:.0%}[/cyan] [dim]│[/dim] "
                    f"Transfers: [cyan]{total_tx}[/cyan]"
                    f"{expiring_part}"
                )
            else:
                info_content = (
                    "[bold][AI] Brain — Learned Skills[/bold] [dim]│[/dim] "
                    "[dim]No skills yet — run brain workflows to learn[/dim]"
                )
            info_widget.update(info_content)

            # Update table
            table_widget = self.query_one("#brain-skills-table", SkillsTableWidget)
            table_widget.update_skills()
        except Exception as e:
            logger.debug(f"TUI brain skills refresh error (non-fatal): {e}")


class HelpScreen(Screen):
    """Help screen with vintage-style keybinding reference."""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the help screen with ASCII art help panel."""
        help_text = """
╔═════════════════════════════════════════════════════════╗
║              ORKA MEMORY MONITOR - HELP                 ║
║                   QUICK REFERENCE                       ║
╠═════════════════════════════════════════════════════════╣
║                                                         ║
║  [bold cyan]NAVIGATION:[/bold cyan]                                          ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ 1-5,0      Switch views                         │   ║
║  │ j/k        Navigate up/down (vim-style)         │   ║
║  │ g/G        Jump to top/bottom                   │   ║
║  │ tab        Focus next widget                    │   ║
║  │ enter      Select/expand item                   │   ║
║  │ esc        Go back/close                        │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]VIEWS:[/bold cyan]                                               ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ 1          Dashboard (overview)                 │   ║
║  │ 2          Short-term memory                    │   ║
║  │ 3          Long-term memory                     │   ║
║  │ 4          Memory logs                          │   ║
║  │ 5          Brain skills (learned)               │   ║
║  │ 0          Health & diagnostics                 │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]ACTIONS:[/bold cyan]                                             ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ r          Refresh data                         │   ║
║  │ ctrl+p     Command palette (change theme, etc.) │   ║
║  │ e          Export visible data to JSON          │   ║
║  │ f          Toggle fullscreen                    │   ║
║  │ ?          Show this help                       │   ║
║  │ q          Quit application                     │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
║  [bold cyan]TIPS:[/bold cyan]                                                ║
║  ┌─────────────────────────────────────────────────┐   ║
║  │ • Use vim keys (j/k) for faster navigation      │   ║
║  │ • Press Ctrl+P to open command palette          │   ║
║  │ • Type 'theme' in palette to change themes      │   ║
║  │ • Available: default, orka-vintage, orka-dark   │   ║
║  │ • Select rows to view full content              │   ║
║  │ • Export saves current view to JSON file        │   ║
║  └─────────────────────────────────────────────────┘   ║
║                                                         ║
╚═════════════════════════════════════════════════════════╝

[dim]Press ESC or Q to close this help screen...[/dim]
        """
        
        yield Header()
        yield Container(
            Static(help_text, classes="help-screen"),
            classes="help-container"
        )
        yield Footer()
    
    def action_dismiss(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
