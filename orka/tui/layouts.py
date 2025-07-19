"""
Layout management and view coordination for TUI interface.

DEPRECATED: This is now a fallback component. The primary interface uses Textual.
"""

import warnings
from typing import Any, Union

try:
    from rich.layout import Layout

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class LayoutManager:
    """
    Manages layout composition and view switching for the TUI interface.

    DEPRECATED: This is now a fallback component. The primary interface uses Textual.
    """

    def __init__(self, component_builder: Any) -> None:
        """
        Initialize the LayoutManager.

        Args:
            component_builder: Component builder instance for creating UI components.
        """
        warnings.warn(
            "LayoutManager is deprecated. Use the Textual interface for modern TUI experience.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.components = component_builder

    def create_dashboard(self) -> Layout:
        """
        Create a compact dashboard that fits in standard terminal windows.

        Returns:
            A Rich Layout object configured for the dashboard view.
        """
        layout = Layout()

        # Split into header, main content, and footer (more compact)
        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="main"),
            Layout(name="footer", size=2),
        )

        # Split main content into two columns only for better fit
        layout["main"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2),
        )

        # Split left column: stats and memories only
        layout["left"].split_column(
            Layout(name="stats", size=10),
            Layout(name="memories"),
        )

        # Right column: performance only (compact)
        layout["right"].update(self.components.create_compact_performance_panel())

        # Create compact panels
        layout["header"].update(self.components.create_compact_header())
        layout["stats"].update(self.components.create_compact_stats_panel())
        layout["memories"].update(self.components.create_compact_memories_panel())
        layout["footer"].update(self.components.create_compact_footer())

        return layout

    def create_memory_browser(self) -> Layout:
        """
        Create memory browser view with full table display.

        Returns:
            A Rich Layout object configured for the memory browser view.
        """
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Main content for memory browser
        layout["main"].split_column(
            Layout(name="stats", size=8),
            Layout(name="memories"),
        )

        # Use full components for browser view
        layout["header"].update(self.components.create_header())
        layout["stats"].update(self.components.create_stats_panel())
        layout["memories"].update(self.components.create_recent_memories_panel())
        layout["footer"].update(self.components.create_footer())

        return layout

    def create_performance_view(self) -> Any:
        """
        Create performance monitoring view.

        Returns:
            A Rich renderable object for the performance view.
        """
        return self.components.create_performance_panel()

    def create_config_view(self) -> Any:
        """
        Create configuration and system diagnostics view.

        Returns:
            A Rich renderable object for the configuration view.
        """
        return self.components.create_config_view()

    def get_view(self, view_name: str) -> Union[Layout, Any]:
        """
        Get the appropriate view based on the view name.

        Args:
            view_name: The name of the view to create.

        Returns:
            Either a Rich Layout object or a Rich renderable object depending on the view type.
        """
        if view_name == "dashboard":
            return self.create_dashboard()
        elif view_name == "memories":
            return self.create_memory_browser()
        elif view_name == "performance":
            return self.create_performance_view()
        elif view_name == "config":
            return self.create_config_view()
        else:
            # Default to dashboard
            return self.create_dashboard()
