"""Unit tests for orka.observability.metrics."""

from datetime import datetime

import pytest

from orka.observability.metrics import GraphScoutMetrics, PathExecutorMetrics

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestGraphScoutMetrics:
    """Test suite for GraphScoutMetrics dataclass."""

    def test_init(self):
        """Test GraphScoutMetrics initialization."""
        metrics = GraphScoutMetrics(run_id="test_run_123")
        
        assert metrics.run_id == "test_run_123"
        assert metrics.candidates_discovered == 0
        assert isinstance(metrics.timestamp, datetime)

    def test_to_dict(self):
        """Test to_dict method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        metrics.candidates_discovered = 10
        metrics.selected_path = ["agent1", "agent2"]
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result["run_id"] == "test_run"
        assert result["path_discovery"]["candidates_discovered"] == 10

    def test_to_json(self):
        """Test to_json method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        
        json_str = metrics.to_json()
        
        assert isinstance(json_str, str)
        assert "test_run" in json_str

    def test_calculate_reduction_rate(self):
        """Test _calculate_reduction_rate method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        metrics.candidates_discovered = 10
        metrics.candidates_after_safety = 5
        
        rate = metrics._calculate_reduction_rate()
        
        assert rate == 0.5  # 50% reduction

    def test_calculate_reduction_rate_zero(self):
        """Test _calculate_reduction_rate with zero candidates."""
        metrics = GraphScoutMetrics(run_id="test_run")
        metrics.candidates_discovered = 0
        
        rate = metrics._calculate_reduction_rate()
        
        assert rate == 0.0

    def test_add_error(self):
        """Test add_error method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        
        metrics.add_error("Test error")
        
        assert len(metrics.errors) == 1
        assert "Test error" in metrics.errors

    def test_add_warning(self):
        """Test add_warning method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        
        metrics.add_warning("Test warning")
        
        assert len(metrics.warnings) == 1
        assert "Test warning" in metrics.warnings

    def test_summary(self):
        """Test summary method."""
        metrics = GraphScoutMetrics(run_id="test_run")
        metrics.candidates_discovered = 10
        metrics.selected_path = ["agent1"]
        metrics.selection_confidence = 0.9
        metrics.total_time_ms = 100.0
        
        summary = metrics.summary()
        
        assert "test_run" in summary
        assert "10" in summary
        assert "0.9" in summary


class TestPathExecutorMetrics:
    """Test suite for PathExecutorMetrics dataclass."""

    def test_init(self):
        """Test PathExecutorMetrics initialization."""
        metrics = PathExecutorMetrics(run_id="test_run_123")
        
        assert metrics.run_id == "test_run_123"
        assert metrics.successful_agents == 0
        assert isinstance(metrics.timestamp, datetime)

    def test_to_dict(self):
        """Test to_dict method."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.planned_path = ["agent1", "agent2"]
        metrics.executed_path = ["agent1"]
        metrics.successful_agents = 1
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result["run_id"] == "test_run"
        assert len(result["execution"]["planned_path"]) == 2

    def test_to_json(self):
        """Test to_json method."""
        metrics = PathExecutorMetrics(run_id="test_run")
        
        json_str = metrics.to_json()
        
        assert isinstance(json_str, str)
        assert "test_run" in json_str

    def test_calculate_completion_rate(self):
        """Test _calculate_completion_rate method."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.planned_path = ["agent1", "agent2", "agent3"]
        metrics.executed_path = ["agent1", "agent2"]
        
        rate = metrics._calculate_completion_rate()
        
        assert rate == 2.0 / 3.0

    def test_calculate_completion_rate_empty(self):
        """Test _calculate_completion_rate with empty planned path."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.planned_path = []
        
        rate = metrics._calculate_completion_rate()
        
        assert rate == 0.0

    def test_calculate_average_time(self):
        """Test _calculate_average_time method."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.agent_execution_times = {
            "agent1": 100.0,
            "agent2": 200.0,
        }
        
        avg = metrics._calculate_average_time()
        
        assert avg == 150.0

    def test_calculate_average_time_empty(self):
        """Test _calculate_average_time with empty times."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.agent_execution_times = {}
        
        avg = metrics._calculate_average_time()
        
        assert avg == 0.0

    def test_summary(self):
        """Test summary method."""
        metrics = PathExecutorMetrics(run_id="test_run")
        metrics.planned_path = ["agent1", "agent2"]
        metrics.executed_path = ["agent1"]
        metrics.successful_agents = 1
        metrics.failed_agents = 0
        metrics.total_execution_time_ms = 150.0
        
        summary = metrics.summary()
        
        assert "test_run" in summary
        assert "1/2" in summary
        assert "150" in summary

