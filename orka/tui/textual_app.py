"""
Modern Textual-native TUI application for OrKa memory monitoring.
Features native Textual layout system with proper navigation.
"""

import json
from pathlib import Path
from datetime import datetime
from textual.app import App
from textual.binding import Binding

from .textual_screens import (
    DashboardScreen,
    HealthScreen,
    LongMemoryScreen,
    MemoryLogsScreen,
    ShortMemoryScreen,
    HelpScreen,
)

# Import custom themes
from .theme_vintage import VINTAGE
from .theme_dark import DARK


class OrKaTextualApp(App):
    """Modern Textual-native OrKa monitoring application."""

    TITLE = "OrKa Memory Monitor"
    SUB_TITLE = "Near real-time Memory System Monitoring (deployment-dependent)"

    BINDINGS = [
        Binding("1", "show_dashboard", "Dashboard", show=True),
        Binding("2", "show_short_memory", "Short Memory", show=True),
        Binding("3", "show_long_memory", "Long Memory", show=True),
        Binding("4", "show_memory_logs", "Memory Logs", show=True),
        Binding("5", "show_health", "Health", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("e", "export_memory", "Export", show=True),
        Binding("ctrl+p", "command_palette", "Palette"),
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_fullscreen", "Fullscreen"),
        # Vim-style navigation
        Binding("j", "vim_down", "Down", show=False),
        Binding("k", "vim_up", "Up", show=False),
        Binding("g", "vim_top", "Top", show=False),
        Binding("G", "vim_bottom", "Bottom", show=False),
    ]

    CSS_PATH = "textual_styles.tcss"

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.screens = {}
        
        # Register custom themes
        self.register_theme(VINTAGE)
        self.register_theme(DARK)

    def on_mount(self) -> None:
        """Initialize the application."""
        # Pre-create screens for faster switching
        self.screens = {
            "dashboard": DashboardScreen(self.data_manager),
            "short_memory": ShortMemoryScreen(self.data_manager),
            "long_memory": LongMemoryScreen(self.data_manager),
            "memory_logs": MemoryLogsScreen(self.data_manager),
            "health": HealthScreen(self.data_manager),
            "help": HelpScreen(),
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

    def action_show_help(self) -> None:
        """Show help screen."""
        self.push_screen("help")

    def action_export_memory(self) -> None:
        """Export selected memories to JSON file."""
        try:
            # Get current screen
            current_screen = self.screen
            
            # Check if screen has memory table widget
            if not hasattr(current_screen, 'query_one'):
                self.notify("Export not available on this screen", severity="warning")
                return
            
            # Try to get selected memory from current screen
            try:
                from .textual_widgets import MemoryTableWidget
                table_widget = current_screen.query_one(MemoryTableWidget)
                
                if not table_widget.current_memories:
                    self.notify("No memories to export", severity="warning")
                    return
                
                # Export all visible memories
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"orka_memories_{timestamp}.json"
                filepath = Path.cwd() / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(table_widget.current_memories, f, indent=2, default=str)
                
                self.notify(f"Exported {len(table_widget.current_memories)} memories to {filename}", timeout=3.0)
            except Exception:
                # If no table widget, export all data
                all_data = self.data_manager.memory_data
                if not all_data:
                    self.notify("No data to export", severity="warning")
                    return
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"orka_data_{timestamp}.json"
                filepath = Path.cwd() / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, indent=2, default=str)
                
                self.notify(f"Exported {len(all_data)} entries to {filename}", timeout=3.0)
                
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")

    def action_vim_down(self) -> None:
        """Vim-style down navigation (j)."""
        try:
            # Try to focus on current widget and send down key
            if hasattr(self.focused, 'action_cursor_down'):
                self.focused.action_cursor_down()
        except Exception:
            pass

    def action_vim_up(self) -> None:
        """Vim-style up navigation (k)."""
        try:
            if hasattr(self.focused, 'action_cursor_up'):
                self.focused.action_cursor_up()
        except Exception:
            pass

    def action_vim_top(self) -> None:
        """Vim-style jump to top (g)."""
        try:
            if hasattr(self.focused, 'action_scroll_home'):
                self.focused.action_scroll_home()
        except Exception:
            pass

    def action_vim_bottom(self) -> None:
        """Vim-style jump to bottom (G)."""
        try:
            if hasattr(self.focused, 'action_scroll_end'):
                self.focused.action_scroll_end()
        except Exception:
            pass

    def on_screen_resume(self, event) -> None:
        """Handle screen resume events."""
        # Refresh data when switching screens
        self.refresh_current_screen()
