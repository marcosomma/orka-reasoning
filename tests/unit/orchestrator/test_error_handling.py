"""Unit tests for orka.orchestrator.error_handling."""

import json
import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

from orka.orchestrator.error_handling import ErrorHandler

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestErrorHandler:
    """Test suite for ErrorHandler class."""

    def create_error_handler(self):
        """Helper to create an ErrorHandler instance with required attributes."""
        handler = ErrorHandler()
        handler.step_index = 0
        handler.run_id = "test-run-123"
        handler.error_telemetry = {
            "errors": [],
            "retry_counters": {},
            "partial_successes": [],
            "silent_degradations": [],
            "status_codes": {},
            "recovery_actions": [],
            "critical_failures": [],
            "execution_status": "running",
        }
        handler._generate_meta_report = Mock(return_value={"test": "meta_report"})
        handler.memory = Mock()
        return handler

    def test_record_error_basic(self):
        """Test _record_error with basic error information."""
        handler = self.create_error_handler()
        
        handler._record_error(
            error_type="agent_failure",
            agent_id="test_agent",
            error_msg="Test error message"
        )
        
        assert len(handler.error_telemetry["errors"]) == 1
        error_entry = handler.error_telemetry["errors"][0]
        assert error_entry["type"] == "agent_failure"
        assert error_entry["agent_id"] == "test_agent"
        assert error_entry["message"] == "Test error message"
        assert error_entry["step"] == 0
        assert error_entry["run_id"] == "test-run-123"
        assert "timestamp" in error_entry

    def test_record_error_with_exception(self):
        """Test _record_error with exception object."""
        handler = self.create_error_handler()
        test_exception = ValueError("Test exception message")
        
        handler._record_error(
            error_type="json_parsing",
            agent_id="test_agent",
            error_msg="Failed to parse JSON",
            exception=test_exception
        )
        
        assert len(handler.error_telemetry["errors"]) == 1
        error_entry = handler.error_telemetry["errors"][0]
        assert "exception" in error_entry
        assert error_entry["exception"]["type"] == "ValueError"
        assert error_entry["exception"]["message"] == "Test exception message"

    def test_record_error_with_status_code(self):
        """Test _record_error with HTTP status code."""
        handler = self.create_error_handler()
        
        handler._record_error(
            error_type="api_error",
            agent_id="test_agent",
            error_msg="API request failed",
            status_code=500
        )
        
        assert len(handler.error_telemetry["errors"]) == 1
        error_entry = handler.error_telemetry["errors"][0]
        assert error_entry["status_code"] == 500
        assert handler.error_telemetry["status_codes"]["test_agent"] == 500

    def test_record_error_with_recovery_action(self):
        """Test _record_error with recovery action."""
        handler = self.create_error_handler()
        
        handler._record_error(
            error_type="agent_failure",
            agent_id="test_agent",
            error_msg="Agent failed",
            recovery_action="retry"
        )
        
        assert len(handler.error_telemetry["errors"]) == 1
        error_entry = handler.error_telemetry["errors"][0]
        assert error_entry["recovery_action"] == "retry"
        assert len(handler.error_telemetry["recovery_actions"]) == 1
        assert handler.error_telemetry["recovery_actions"][0]["action"] == "retry"
        assert handler.error_telemetry["recovery_actions"][0]["agent_id"] == "test_agent"

    def test_record_error_with_custom_step(self):
        """Test _record_error with custom step number."""
        handler = self.create_error_handler()
        handler.step_index = 5
        
        handler._record_error(
            error_type="agent_failure",
            agent_id="test_agent",
            error_msg="Test error",
            step=10
        )
        
        error_entry = handler.error_telemetry["errors"][0]
        assert error_entry["step"] == 10  # Custom step, not step_index

    def test_record_error_uses_step_index_when_step_none(self):
        """Test _record_error uses step_index when step is None."""
        handler = self.create_error_handler()
        handler.step_index = 7
        
        handler._record_error(
            error_type="agent_failure",
            agent_id="test_agent",
            error_msg="Test error"
        )
        
        error_entry = handler.error_telemetry["errors"][0]
        assert error_entry["step"] == 7  # Uses step_index

    def test_record_retry(self):
        """Test _record_retry increments retry counter."""
        handler = self.create_error_handler()
        
        handler._record_retry("test_agent")
        
        assert handler.error_telemetry["retry_counters"]["test_agent"] == 1
        
        handler._record_retry("test_agent")
        
        assert handler.error_telemetry["retry_counters"]["test_agent"] == 2

    def test_record_retry_multiple_agents(self):
        """Test _record_retry for multiple agents."""
        handler = self.create_error_handler()
        
        handler._record_retry("agent1")
        handler._record_retry("agent2")
        handler._record_retry("agent1")
        
        assert handler.error_telemetry["retry_counters"]["agent1"] == 2
        assert handler.error_telemetry["retry_counters"]["agent2"] == 1

    def test_record_partial_success(self):
        """Test _record_partial_success records partial success."""
        handler = self.create_error_handler()
        
        handler._record_partial_success("test_agent", retry_count=3)
        
        assert len(handler.error_telemetry["partial_successes"]) == 1
        success_entry = handler.error_telemetry["partial_successes"][0]
        assert success_entry["agent_id"] == "test_agent"
        assert success_entry["retry_count"] == 3
        assert "timestamp" in success_entry

    def test_record_silent_degradation(self):
        """Test _record_silent_degradation records degradation."""
        handler = self.create_error_handler()
        
        handler._record_silent_degradation(
            agent_id="test_agent",
            degradation_type="json_parsing_failure",
            details={"raw_response": "invalid json"}
        )
        
        assert len(handler.error_telemetry["silent_degradations"]) == 1
        degradation_entry = handler.error_telemetry["silent_degradations"][0]
        assert degradation_entry["agent_id"] == "test_agent"
        assert degradation_entry["type"] == "json_parsing_failure"
        assert degradation_entry["details"] == {"raw_response": "invalid json"}
        assert "timestamp" in degradation_entry

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_with_final_error(self, mock_getenv, mock_makedirs):
        """Test _save_error_report with final error."""
        handler = self.create_error_handler()
        mock_getenv.return_value = "test_logs"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            logs = [{"agent": "test_agent", "output": "test"}]
            final_error = Exception("Final error")
            
            report_path = handler._save_error_report(logs, final_error)
            
            assert handler.error_telemetry["execution_status"] == "failed"
            assert len(handler.error_telemetry["critical_failures"]) == 1
            assert handler.error_telemetry["critical_failures"][0]["error"] == "Final error"
            assert os.path.exists(report_path)
            
            # Verify report content
            with open(report_path, "r") as f:
                report = json.load(f)
            
            assert "orka_execution_report" in report
            assert report["orka_execution_report"]["execution_status"] == "failed"
            assert report["orka_execution_report"]["run_id"] == "test-run-123"
            assert report["orka_execution_report"]["total_errors"] == 0

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_with_errors_but_no_final(self, mock_getenv, mock_makedirs):
        """Test _save_error_report with errors but no final error."""
        handler = self.create_error_handler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            # Add some errors
            handler._record_error("agent_failure", "agent1", "Error 1")
            handler._record_error("api_error", "agent2", "Error 2")
            
            logs = [{"agent": "test_agent", "output": "test"}]
            
            report_path = handler._save_error_report(logs, None)
            
            assert handler.error_telemetry["execution_status"] == "partial"
            assert os.path.exists(report_path)
            
            with open(report_path, "r") as f:
                report = json.load(f)
            
            assert report["orka_execution_report"]["execution_status"] == "partial"
            assert report["orka_execution_report"]["total_errors"] == 2

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_no_errors(self, mock_getenv, mock_makedirs):
        """Test _save_error_report with no errors."""
        handler = self.create_error_handler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            logs = [{"agent": "test_agent", "output": "test"}]
            
            report_path = handler._save_error_report(logs, None)
            
            assert handler.error_telemetry["execution_status"] == "completed"
            assert os.path.exists(report_path)
            
            with open(report_path, "r") as f:
                report = json.load(f)
            
            assert report["orka_execution_report"]["execution_status"] == "completed"
            assert report["orka_execution_report"]["total_errors"] == 0

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_meta_report_generation_failure(self, mock_getenv, mock_makedirs):
        """Test _save_error_report handles meta report generation failure."""
        handler = self.create_error_handler()
        handler._generate_meta_report = Mock(side_effect=Exception("Meta report failed"))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            logs = [{"agent": "test_agent", "output": "test"}]
            
            report_path = handler._save_error_report(logs, None)
            
            # Should record error for meta report generation
            assert len(handler.error_telemetry["errors"]) == 1
            assert handler.error_telemetry["errors"][0]["type"] == "meta_report_generation"
            
            # Should still save report with fallback meta report
            assert os.path.exists(report_path)
            with open(report_path, "r") as f:
                report = json.load(f)
            
            assert "meta_report" in report["orka_execution_report"]
            assert "error" in report["orka_execution_report"]["meta_report"]

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_file_save_failure(self, mock_getenv, mock_makedirs):
        """Test _save_error_report handles file save failure."""
        handler = self.create_error_handler()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            # Make file write fail
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                logs = [{"agent": "test_agent", "output": "test"}]
                
                # Should not raise exception, just log error
                report_path = handler._save_error_report(logs, None)
                
                # Should still return a path even if save failed
                assert report_path is not None

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_memory_save(self, mock_getenv, mock_makedirs):
        """Test _save_error_report saves memory trace."""
        handler = self.create_error_handler()
        handler.memory.save_to_file = Mock()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            logs = [{"agent": "test_agent", "output": "test"}]
            
            handler._save_error_report(logs, None)
            
            # Should call memory.save_to_file
            handler.memory.save_to_file.assert_called_once()
            call_args = handler.memory.save_to_file.call_args[0][0]
            assert "orka_trace_" in call_args
            assert call_args.endswith(".json")

    @patch('orka.orchestrator.error_handling.os.makedirs')
    @patch('orka.orchestrator.error_handling.os.getenv')
    def test_save_error_report_memory_save_failure(self, mock_getenv, mock_makedirs):
        """Test _save_error_report handles memory save failure."""
        handler = self.create_error_handler()
        handler.memory.save_to_file = Mock(side_effect=Exception("Memory save failed"))
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_getenv.return_value = tmpdir
            
            logs = [{"agent": "test_agent", "output": "test"}]
            
            # Should not raise exception
            report_path = handler._save_error_report(logs, None)
            
            assert report_path is not None
            assert os.path.exists(report_path)

    def test_save_error_report_retry_counters_sum(self):
        """Test _save_error_report calculates total retries correctly."""
        handler = self.create_error_handler()
        
        handler._record_retry("agent1")
        handler._record_retry("agent1")
        handler._record_retry("agent2")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('orka.orchestrator.error_handling.os.getenv', return_value=tmpdir):
                logs = []
                report_path = handler._save_error_report(logs, None)
                
                with open(report_path, "r") as f:
                    report = json.load(f)
                
                assert report["orka_execution_report"]["total_retries"] == 3

    def test_save_error_report_agents_with_errors(self):
        """Test _save_error_report lists agents with errors."""
        handler = self.create_error_handler()
        
        handler._record_error("agent_failure", "agent1", "Error 1")
        handler._record_error("api_error", "agent2", "Error 2")
        handler._record_error("agent_failure", "agent1", "Error 3")  # Duplicate agent
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('orka.orchestrator.error_handling.os.getenv', return_value=tmpdir):
                logs = []
                report_path = handler._save_error_report(logs, None)
                
                with open(report_path, "r") as f:
                    report = json.load(f)
                
                agents_with_errors = report["orka_execution_report"]["agents_with_errors"]
                assert len(agents_with_errors) == 2
                assert "agent1" in agents_with_errors
                assert "agent2" in agents_with_errors

    def test_capture_memory_snapshot_with_memory(self):
        """Test _capture_memory_snapshot with memory data."""
        handler = self.create_error_handler()
        handler.memory.memory = ["entry1", "entry2", "entry3", "entry4", "entry5"]
        
        snapshot = handler._capture_memory_snapshot()
        
        assert snapshot["total_entries"] == 5
        assert snapshot["backend_type"] == "Mock"
        assert len(snapshot["last_10_entries"]) == 5

    def test_capture_memory_snapshot_more_than_10_entries(self):
        """Test _capture_memory_snapshot with more than 10 entries."""
        handler = self.create_error_handler()
        handler.memory.memory = [f"entry{i}" for i in range(15)]
        
        snapshot = handler._capture_memory_snapshot()
        
        assert snapshot["total_entries"] == 15
        assert len(snapshot["last_10_entries"]) == 10
        assert snapshot["last_10_entries"] == [f"entry{i}" for i in range(5, 15)]

    def test_capture_memory_snapshot_no_memory_attribute(self):
        """Test _capture_memory_snapshot when memory has no memory attribute."""
        handler = self.create_error_handler()
        del handler.memory.memory
        
        snapshot = handler._capture_memory_snapshot()
        
        assert snapshot["status"] == "no_memory_data"

    def test_capture_memory_snapshot_exception(self):
        """Test _capture_memory_snapshot handles exceptions."""
        handler = self.create_error_handler()
        handler.memory.memory = Mock(side_effect=Exception("Access error"))
        
        snapshot = handler._capture_memory_snapshot()
        
        assert "error" in snapshot
        assert "Failed to capture memory snapshot" in snapshot["error"]

    def test_save_error_report_includes_all_telemetry(self):
        """Test _save_error_report includes all telemetry data."""
        handler = self.create_error_handler()
        
        # Add various telemetry data
        handler._record_error("agent_failure", "agent1", "Error 1")
        handler._record_retry("agent1")
        handler._record_partial_success("agent2", retry_count=2)
        handler._record_silent_degradation("agent3", "json_parsing", {"details": "test"})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('orka.orchestrator.error_handling.os.getenv', return_value=tmpdir):
                logs = []
                report_path = handler._save_error_report(logs, None)
                
                with open(report_path, "r") as f:
                    report = json.load(f)
                
                telemetry = report["orka_execution_report"]["error_telemetry"]
                assert len(telemetry["errors"]) == 1
                assert telemetry["retry_counters"]["agent1"] == 1
                assert len(telemetry["partial_successes"]) == 1
                assert len(telemetry["silent_degradations"]) == 1

    def test_save_error_report_step_index(self):
        """Test _save_error_report includes correct step_index."""
        handler = self.create_error_handler()
        handler.step_index = 42
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('orka.orchestrator.error_handling.os.getenv', return_value=tmpdir):
                logs = []
                report_path = handler._save_error_report(logs, None)
                
                with open(report_path, "r") as f:
                    report = json.load(f)
                
                assert report["orka_execution_report"]["total_steps_attempted"] == 42
