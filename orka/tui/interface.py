"""
Core TUI interface coordination and lifecycle management.
"""

import logging
import os
import signal
import time
import traceback
from typing import Any

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from textual.app import App

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from .component_builder import ComponentBuilder
from .data_manager import DataManager
from .fallback import FallbackInterface


class ModernTUIInterface:
    """Modern TUI interface for OrKa memory monitoring."""

    def __init__(self) -> None:
        self.console = Console() if RICH_AVAILABLE else None
        self.running = False
        self.refresh_interval = 2.0
        self.current_view = "dashboard"  # dashboard, memories, performance, config
        self.selected_row = 0
        self.filter_text = ""

        # Initialize components
        self.data_manager = DataManager()
        self.components = ComponentBuilder(self.data_manager)
        # LayoutManager is a deprecated Rich-only fallback. Instantiate lazily only
        # if we actually run the Rich fallback path, to avoid emitting deprecation
        # warnings for the default Textual path.
        self.layouts = None
        self.fallback = FallbackInterface()

        # Share running state with data manager
        # self.data_manager.running = True

    def run(self, args: Any) -> int:
        """Main entry point for the TUI interface."""
        if not RICH_AVAILABLE:
            logger.error("Modern TUI requires 'rich' library. Install with: pip install rich")
            logger.info("Falling back to basic interface...")
            return self.fallback.run_basic_fallback(args)

        try:
            # Initialize memory logger
            self.data_manager.init_memory_logger(args)

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)

            # Start monitoring
            self.running = True
            # self.data_manager.running = True
            self.refresh_interval = getattr(args, "interval", 2.0)

            # Default to Textual interface (new primary interface)
            use_rich_fallback = (
                getattr(args, "use_rich", False)
                or getattr(args, "fallback", False)
                or os.getenv("ORKA_TUI_MODE", "").lower() == "rich"
            )

            if not TEXTUAL_AVAILABLE:
                if self.console:
                    self.console.print(
                        "[yellow]⚠️  Textual not available. Using Rich fallback interface.[/yellow]",
                    )
                    self.console.print("[blue]💡 Install with: pip install textual[/blue]")
                return self._run_rich_interface(args)
            elif use_rich_fallback:
                if self.console:
                    self.console.print("[blue]ℹ️  Using Rich fallback interface.[/blue]")
                return self._run_rich_interface(args)
            else:
                # Default to new Textual interface
                return self._run_textual_interface(args)

        except Exception as e:
            if self.console:
                self.console.print(f"[red]❌ Error in TUI interface: {e}[/red]")
            else:
                logger.error(f"Error in TUI interface: {e}")


            traceback.print_exc()
            return 1

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle interrupt signals gracefully."""
        self.running = False
        # self.data_manager.running = False

    def _run_rich_interface(self, args: Any) -> int:
        """Run the rich-based interface with live updates."""
        try:
            if self.layouts is None:
                from .layouts import LayoutManager

                self.layouts = LayoutManager(self.components)

            with Live(
                self.layouts.get_view(self.current_view),
                console=self.console,
                refresh_per_second=0.5,  # Slower refresh to prevent jumping
                screen=True,
                vertical_overflow="crop",  # Prevent overflow
            ) as live:
                while self.running:
                    try:
                        # Update data
                        self.data_manager.update_data()

                        # Update display based on current view
                        live.update(self.layouts.get_view(self.current_view))

                        time.sleep(max(self.refresh_interval, 2.0))  # Minimum 2 second intervals

                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        live.update(Panel(f"[red]Error: {e}[/red]", title="Error"))
                        time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            pass

        if self.console:
            self.console.print("\n[green]👋 OrKa TUI monitoring stopped[/green]")
        return 0

    def _run_textual_interface(self, args: Any) -> int:
        """Run the textual-based interface (more interactive)."""
        try:
            # Import the new Textual app
            from .textual_app import OrKaTextualApp

            app = OrKaTextualApp(self.data_manager)
            app.run()
            return 0
        except ImportError as e:
            if self.console:
                self.console.print(f"[red]Failed to load Textual interface: {e}[/red]")
                self.console.print("[yellow]Falling back to Rich interface...[/yellow]")
            # Fallback to rich interface
            return self._run_rich_interface(args)
