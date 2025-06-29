"""
TUI package - exports the main interface class for backward compatibility.
"""

from .interface import ModernTUIInterface

# Export new Textual components if available
try:
    from .textual_app import OrKaTextualApp
    from .textual_screens import (
        DashboardScreen,
        HealthScreen,
        LongMemoryScreen,
        MemoryLogsScreen,
        ShortMemoryScreen,
    )
    from .textual_widgets import (
        HealthWidget,
        LogsWidget,
        MemoryTableWidget,
        StatsWidget,
    )

    __all__ = [
        "DashboardScreen",
        "HealthScreen",
        "HealthWidget",
        "LogsWidget",
        "LongMemoryScreen",
        "MemoryLogsScreen",
        "MemoryTableWidget",
        "ModernTUIInterface",
        "OrKaTextualApp",
        "ShortMemoryScreen",
        "StatsWidget",
    ]
except ImportError:
    # Fallback to basic exports if Textual components not available
    __all__ = ["ModernTUIInterface"]
