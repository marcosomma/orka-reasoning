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

# Main imports for backward compatibility
from .tui import ModernTUIInterface

# Try to import textual for advanced interactions
try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container
    from textual.widgets import Footer, Header, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# Legacy Textual App for backward compatibility
if TEXTUAL_AVAILABLE:

    class OrKaMonitorApp(App):
        """Legacy Textual-based interactive monitoring app (kept for backward compatibility)."""

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
                self.tui.data_manager.update_data()
                content = self.query_one("#main-content", Static)

                # Simple text-based display for now
                stats = self.tui.data_manager.stats.current
                display_text = f"""
                    OrKa Memory Statistics:
                    Total Entries: {stats.get("total_entries", 0)}
                    Stored Memories: {stats.get("stored_memories", 0)}
                    Orchestration Logs: {stats.get("orchestration_logs", 0)}
                    Active Entries: {stats.get("active_entries", 0)}
                    Expired Entries: {stats.get("expired_entries", 0)}

                    Backend: {self.tui.data_manager.backend}
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


# Import the new Textual app for modern interface
if TEXTUAL_AVAILABLE:
    try:
        from .tui.textual_app import OrKaTextualApp
    except ImportError:
        OrKaTextualApp = None


# Export the main class for backward compatibility
__all__ = ["ModernTUIInterface", "OrKaMonitorApp"]
