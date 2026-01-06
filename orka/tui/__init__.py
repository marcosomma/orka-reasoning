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
