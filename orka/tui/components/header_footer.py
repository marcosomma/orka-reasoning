# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Header and Footer Component Builders."""

import datetime

try:
    from rich.align import Align
    from rich.box import HEAVY, SIMPLE
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class HeaderFooterMixin:
    """Mixin providing header and footer component builders."""

    # Expected from host class
    running: bool
    backend: str

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

