"""Coordinate and manage the core TUI interface lifecycle."""

import os
import signal
import time
from argparse import Namespace
from types import FrameType
from typing import Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from textual.app import App as TextualApp  # noqa: F401

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

from .components import ComponentBuilder
from .data_manager import DataManager
from .fallback import FallbackInterface
from .layouts import LayoutManager


class ModernTUIInterface:
    """Modern TUI interface for OrKa memory monitoring."""

    def __init__(self) -> None:
        """Initialize the TUI interface."""
        self.console: Optional[Console] = Console() if RICH_AVAILABLE else None
        self.running: bool = False
        self.refresh_interval: float = 2.0
        self.current_view: str = "dashboard"  # dashboard, memories, performance, config
        self.selected_row: int = 0
        self.filter_text: str = ""

        # Initialize components
        self.data_manager = DataManager()
        self.components = ComponentBuilder(self.data_manager)
        self.layouts = LayoutManager(self.components)
        self.fallback = FallbackInterface()

        # Share running state with data manager
        if hasattr(self.data_manager, "running"):
            self.data_manager.running = True  # type: ignore

    def run(self, args: Namespace) -> int:
        """
        Run the TUI interface.

        Args:
            args: Command-line arguments namespace.

        Returns:
            0 for success, 1 for failure.
        """
        if not RICH_AVAILABLE:
            print("❌ Modern TUI requires 'rich' library. Install with: pip install rich")
            print("Falling back to basic interface...")
            return self.fallback.run_basic_fallback(args)

        try:
            # Initialize memory logger
            self.data_manager.init_memory_logger(args)

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)

            # Start monitoring
            self.running = True
            if hasattr(self.data_manager, "running"):
                self.data_manager.running = True  # type: ignore
            self.refresh_interval = getattr(args, "interval", 2.0)

            # Default to Textual interface (new primary interface)
            use_rich_fallback: bool = (
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
                print(f"❌ Error in TUI interface: {e}")
            import traceback

            traceback.print_exc()
            return 1

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """
        Handle interrupt signals gracefully.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        self.running = False
        if hasattr(self.data_manager, "running"):
            self.data_manager.running = True  # type: ignore

    def _run_rich_interface(self, args: Namespace) -> int:
        """
        Run the rich-based interface with live updates.

        Args:
            args: Command-line arguments namespace.

        Returns:
            0 for success, 1 for failure.
        """
        try:
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

    def _run_textual_interface(self, args: Namespace) -> int:
        """
        Run the textual-based interface (more interactive).

        Args:
            args: Command-line arguments namespace.

        Returns:
            0 for success, 1 for failure.
        """
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
