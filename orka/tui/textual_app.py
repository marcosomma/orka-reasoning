"""
Modern Textual-native TUI application for OrKa memory monitoring.
Features native Textual layout system with proper navigation.
"""

from textual.app import App
from textual.binding import Binding

from .textual_screens import (
    DashboardScreen,
    HealthScreen,
    LongMemoryScreen,
    MemoryLogsScreen,
    ShortMemoryScreen,
)


class OrKaTextualApp(App):
    """Modern Textual-native OrKa monitoring application."""

    TITLE = "OrKa Memory Monitor"
    SUB_TITLE = "Real-time Memory System Monitoring"

    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard", show=True),
        Binding("2", "show_short_memory", "Short Memory", show=True),
        Binding("3", "show_long_memory", "Long Memory", show=True),
        Binding("4", "show_memory_logs", "Memory Logs", show=True),
        Binding("5", "show_health", "Health", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+p", "command_palette", "Palette", show=True),
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_fullscreen", "Fullscreen"),
    ]

    CSS_PATH = "textual_styles.tcss"

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.screens = {}

    def on_mount(self) -> None:
        """Initialize the application."""
        # Pre-create screens for faster switching
        self.screens = {
            "dashboard": DashboardScreen(self.data_manager),
            "short_memory": ShortMemoryScreen(self.data_manager),
            "long_memory": LongMemoryScreen(self.data_manager),
            "memory_logs": MemoryLogsScreen(self.data_manager),
            "health": HealthScreen(self.data_manager),
        }

        # Install screens
        for name, screen in self.screens.items():
            self.install_screen(screen, name=name)

        # Start with dashboard
        self.push_screen("dashboard")

        # Set up periodic refresh
        self.set_interval(2.0, self.refresh_current_screen)

    def refresh_current_screen(self) -> None:
        """Refresh the current screen's data."""
        try:
            self.data_manager.update_data()
            if hasattr(self.screen, "refresh_data"):
                self.screen.refresh_data()
        except Exception as e:
            self.notify(f"Error refreshing data: {e}", severity="error")

    def action_show_dashboard(self) -> None:
        """Switch to dashboard view."""
        self.push_screen("dashboard")

    def action_show_short_memory(self) -> None:
        """Switch to short memory view."""
        self.push_screen("short_memory")

    def action_show_long_memory(self) -> None:
        """Switch to long memory view."""
        self.push_screen("long_memory")

    def action_show_memory_logs(self) -> None:
        """Switch to memory logs view."""
        self.push_screen("memory_logs")

    def action_show_health(self) -> None:
        """Switch to health monitoring view."""
        self.push_screen("health")

    def action_refresh(self) -> None:
        """Force refresh current screen."""
        self.refresh_current_screen()
        self.notify("Data refreshed", timeout=1.0)

    def action_toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        # This is handled by Textual automatically

    def on_screen_resume(self, event) -> None:
        """Handle screen resume events."""
        # Refresh data when switching screens
        self.refresh_current_screen()
