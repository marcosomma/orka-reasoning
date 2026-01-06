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
UI component builders for TUI interface panels and displays.
"""

try:
    from rich.align import Align
    from rich.box import HEAVY, ROUNDED, SIMPLE
    from rich.layout import Layout
    from rich.markup import escape
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import mixins from components package
from orka.tui.components.header_footer import HeaderFooterMixin
from orka.tui.components.stats_panels import StatsPanelMixin
from orka.tui.components.memory_panels import MemoryPanelMixin
from orka.tui.components.performance_panels import PerformancePanelMixin
from orka.tui.components.config_view import ConfigViewMixin


class ComponentBuilder(
    HeaderFooterMixin,
    StatsPanelMixin,
    MemoryPanelMixin,
    PerformancePanelMixin,
    ConfigViewMixin,
):
    """
    Builds UI components for the TUI interface.
    
    This class composes functionality from multiple mixins:
    - HeaderFooterMixin: Header and footer creation
    - StatsPanelMixin: Memory statistics panels
    - MemoryPanelMixin: Recent memories display
    - PerformancePanelMixin: Performance metrics panels
    - ConfigViewMixin: Configuration and system health views
    """

    def __init__(self, data_manager):
        self.data_manager = data_manager

    @property
    def stats(self):
        return self.data_manager.stats

    @property
    def memory_data(self):
        return self.data_manager.memory_data

    @property
    def performance_history(self):
        return self.data_manager.performance_history

    @property
    def memory_logger(self):
        return self.data_manager.memory_logger

    @property
    def backend(self):
        return self.data_manager.backend

    @property
    def running(self):
        return getattr(self.data_manager, "running", True)
