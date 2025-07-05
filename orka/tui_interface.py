"""
OrKa TUI Interface
==================

Terminal User Interface for OrKa memory system monitoring and management.
Provides real-time visualizations and interactive controls for memory operations.

Overview
--------

The TUI interface offers a modern terminal-based monitoring solution for OrKa
memory systems, with support for both basic text-based displays and advanced
interactive interfaces when Textual is available.

Core Features
------------

**Real-time Monitoring**
- Live memory statistics with automatic refresh
- Connection status and backend information
- Performance metrics and system health indicators
- Error tracking and status reporting

**Memory Management**
- View stored memories and orchestration logs
- Monitor active and expired entries
- Track memory usage patterns
- Backend-specific statistics (Redis, Kafka, RedisStack)

**Interactive Interface**
- Keyboard navigation and shortcuts
- Multiple view modes (dashboard, memories, performance, config)
- Customizable refresh intervals
- Color-coded status indicators

Architecture
-----------

**Modular Design**
The TUI system is built with a modular architecture:

- `ModernTUIInterface` - Core interface class with data management
- `OrKaMonitorApp` - Legacy Textual-based interactive app (backward compatibility)
- `OrKaTextualApp` - Modern Textual app with advanced features (optional)

**Dependency Handling**
- Graceful fallback when Textual is not available
- Optional advanced features with dependency checking
- Backward compatibility with existing interfaces

**Data Management**
- Automatic data refresh with configurable intervals
- Connection pooling for backend systems
- Error handling and recovery mechanisms
- Performance optimization for large datasets

Implementation Details
---------------------

**Textual Integration**
When Textual is available, the interface provides:
- Rich terminal widgets and layouts
- Interactive keyboard bindings
- Real-time data updates
- Professional styling and themes

**Fallback Mode**
When Textual is not available:
- Basic text-based output
- Simple refresh mechanisms
- Core functionality preservation
- Minimal dependencies

**Key Bindings**
- `q` - Quit application
- `1` - Dashboard view
- `2` - Memories view
- `3` - Performance view
- `4` - Configuration view
- `r` - Force refresh

Usage Patterns
--------------

**Basic Usage**
```python
from orka.tui_interface import ModernTUIInterface

# Create TUI interface
tui = ModernTUIInterface(memory_logger=memory_backend)

# Start monitoring
tui.run()
```

**Advanced Usage with Textual**
```python
from orka.tui_interface import OrKaMonitorApp, ModernTUIInterface

# Create TUI with Textual app
tui = ModernTUIInterface(memory_logger=memory_backend)
app = OrKaMonitorApp(tui)

# Run interactive interface
app.run()
```

**Configuration Options**
```python
tui = ModernTUIInterface(
    memory_logger=memory_backend,
    refresh_interval=2.0,  # seconds
    auto_refresh=True,
    color_theme="default"
)
```

Display Information
------------------

**Memory Statistics**
- Total entries count
- Stored memories vs orchestration logs
- Active vs expired entries
- Backend type and connection status

**Performance Metrics**
- Memory usage patterns
- Search performance (for RedisStack)
- Connection health
- Error rates and patterns

**System Information**
- Backend configuration
- Connection endpoints
- Version information
- Feature availability

Error Handling
-------------

**Connection Issues**
- Automatic retry mechanisms
- Graceful degradation when backend unavailable
- Clear error messages and recovery suggestions
- Fallback to cached data when possible

**Display Errors**
- Safe error rendering in terminal
- Non-blocking error handling
- Detailed error context for debugging
- Recovery actions and suggestions

Compatibility
------------

**Backward Compatibility**
- Maintains compatibility with existing TUI interfaces
- Preserves all public APIs and methods
- Supports legacy configuration patterns
- Graceful handling of missing dependencies

**Future Extensions**
- Plugin system for custom views
- Export functionality for data analysis
- Integration with external monitoring systems
- Advanced filtering and search capabilities
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
