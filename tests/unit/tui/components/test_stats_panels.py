# OrKa: Orchestrator Kit Agents
# Tests for StatsPanelMixin

import pytest
from unittest.mock import MagicMock

from orka.tui.components.stats_panels import StatsPanelMixin


class MockStats:
    """Mock stats object."""

    def __init__(self, current=None):
        self._current = current or {}

    @property
    def current(self):
        return self._current

    def get_trend(self, key):
        return "→"

    def get_rate(self, key):
        return 0.0


class ConcreteStatsPanel(StatsPanelMixin):
    """Concrete implementation for testing."""

    def __init__(self, stats_data=None, performance_history=None):
        self._stats = MockStats(stats_data)
        self._memory_logger = MagicMock()
        self._memory_logger.client = MagicMock()
        self._backend = "redis"
        self._performance_history = performance_history or []

    @property
    def stats(self):
        return self._stats

    @property
    def memory_logger(self):
        return self._memory_logger

    @property
    def backend(self):
        return self._backend

    @property
    def performance_history(self):
        return self._performance_history


class TestStatsPanelMixin:
    """Tests for StatsPanelMixin."""

    @pytest.fixture
    def builder(self):
        return ConcreteStatsPanel(
            stats_data={
                "total_entries": 100,
                "stored_memories": 50,
                "orchestration_logs": 50,
                "active_entries": 80,
                "expired_entries": 20,
                "decay_enabled": True,
            }
        )

    def test_create_compact_stats_panel_loading(self):
        """Test compact stats panel when loading."""
        builder = ConcreteStatsPanel(stats_data=None)
        builder._stats = MockStats(None)
        result = builder.create_compact_stats_panel()
        assert result is not None

    def test_create_compact_stats_panel(self, builder):
        """Test compact stats panel creation."""
        result = builder.create_compact_stats_panel()
        assert result is not None

    def test_create_stats_panel(self, builder):
        """Test full stats panel creation."""
        result = builder.create_stats_panel()
        assert result is not None

    def test_stats_panel_with_performance(self):
        """Test stats panel includes performance info."""
        builder = ConcreteStatsPanel(
            stats_data={"total_entries": 100, "decay_enabled": True},
            performance_history=[{"average_search_time": 0.05}],
        )
        result = builder.create_compact_stats_panel()
        assert result is not None

    def test_stats_panel_performance_indicators(self):
        """Test different performance indicator thresholds."""
        # Fast
        builder_fast = ConcreteStatsPanel(
            stats_data={"total_entries": 100, "decay_enabled": True},
            performance_history=[{"average_search_time": 0.05}],
        )
        result_fast = builder_fast.create_stats_panel()
        
        # Slow
        builder_slow = ConcreteStatsPanel(
            stats_data={"total_entries": 100, "decay_enabled": True},
            performance_history=[{"average_search_time": 1.0}],
        )
        result_slow = builder_slow.create_stats_panel()
        
        assert result_fast is not None
        assert result_slow is not None

