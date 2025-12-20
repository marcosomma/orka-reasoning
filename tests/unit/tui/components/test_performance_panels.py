# OrKa: Orchestrator Kit Agents
# Tests for PerformancePanelMixin

import pytest
from unittest.mock import MagicMock

from orka.tui.components.performance_panels import PerformancePanelMixin


class ConcretePerformancePanel(PerformancePanelMixin):
    """Concrete implementation for testing."""

    def __init__(self, backend="redis", performance_history=None, with_client=True):
        self._backend = backend
        self._performance_history = performance_history or []
        self._memory_logger = MagicMock() if with_client else MagicMock(spec=[])
        if with_client:
            self._memory_logger.client = MagicMock()
            self._memory_logger.get_performance_metrics = MagicMock(
                return_value={
                    "hybrid_searches": 100,
                    "vector_searches": 50,
                    "average_search_time": 0.05,
                    "cache_hits": 80,
                    "total_searches": 100,
                    "memory_writes": 50,
                    "memory_reads": 200,
                    "memory_count": 1000,
                    "index_status": {"indexing": True, "num_docs": 1000, "percent_indexed": 100},
                    "memory_quality": {
                        "avg_importance_score": 3.5,
                        "long_term_percentage": 40.0,
                        "high_quality_percentage": 60.0,
                        "avg_content_length": 150.0,
                        "score_distribution": {"high": 600, "medium": 300, "low": 100},
                    },
                }
            )

    @property
    def backend(self):
        return self._backend

    @property
    def performance_history(self):
        return self._performance_history

    @property
    def memory_logger(self):
        return self._memory_logger

    def create_footer(self):
        """Mock footer for testing."""
        from rich.panel import Panel
        return Panel("Footer")


class TestPerformancePanelMixin:
    """Tests for PerformancePanelMixin."""

    @pytest.fixture
    def builder(self):
        return ConcretePerformancePanel(
            performance_history=[{"average_search_time": 0.05}]
        )

    def test_create_compact_performance_panel_no_history(self):
        """Test compact performance panel without history."""
        builder = ConcretePerformancePanel(performance_history=[])
        result = builder.create_compact_performance_panel()
        assert result is not None

    def test_create_compact_performance_panel(self, builder):
        """Test compact performance panel creation."""
        result = builder.create_compact_performance_panel()
        assert result is not None

    def test_create_compact_performance_panel_redisstack(self):
        """Test compact performance panel with RedisStack backend."""
        builder = ConcretePerformancePanel(
            backend="redisstack",
            performance_history=[{"average_search_time": 0.05}],
        )
        builder._memory_logger.client.ft.return_value.info.return_value = {
            "num_docs": 1000,
            "indexing": True,
        }
        builder._memory_logger.client.info.return_value = {
            "used_memory_human": "10MB",
            "connected_clients": 5,
            "instantaneous_ops_per_sec": 100,
        }
        builder._memory_logger.client.execute_command.return_value = [
            [b"name", b"search", b"ver", b"20000"]
        ]
        result = builder.create_compact_performance_panel()
        assert result is not None

    def test_create_performance_view(self, builder):
        """Test performance view placeholder."""
        result = builder.create_performance_view()
        assert result is not None

    def test_create_performance_panel(self, builder):
        """Test full performance panel."""
        result = builder.create_performance_panel()
        assert result is not None

    def test_create_simple_chart_no_data(self, builder):
        """Test simple chart with no data."""
        result = builder.create_simple_chart([])
        assert "No data" in result

    def test_create_simple_chart_insufficient_data(self, builder):
        """Test simple chart with insufficient data."""
        result = builder.create_simple_chart([1])
        assert "No data" in result

    def test_create_simple_chart_stable(self, builder):
        """Test simple chart with stable data."""
        result = builder.create_simple_chart([5, 5, 5, 5, 5])
        assert "Stable" in result

    def test_create_simple_chart_varying(self, builder):
        """Test simple chart with varying data."""
        result = builder.create_simple_chart([1, 3, 2, 5, 4, 3, 6])
        assert "█" in result or "Stable" in result or result == "[dim]Stable[/dim]"

    def test_performance_indicators(self):
        """Test different performance thresholds."""
        # Fast performance
        builder_fast = ConcretePerformancePanel(
            performance_history=[{"average_search_time": 0.05}]
        )
        result_fast = builder_fast.create_compact_performance_panel()
        
        # Moderate performance
        builder_mod = ConcretePerformancePanel(
            performance_history=[{"average_search_time": 0.3}]
        )
        result_mod = builder_mod.create_compact_performance_panel()
        
        # Slow performance
        builder_slow = ConcretePerformancePanel(
            performance_history=[{"average_search_time": 1.0}]
        )
        result_slow = builder_slow.create_compact_performance_panel()
        
        assert result_fast is not None
        assert result_mod is not None
        assert result_slow is not None

