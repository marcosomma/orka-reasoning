"""Test Orchestrator Error Handling Comprehensive."""

import os
from unittest.mock import MagicMock, mock_open, patch

from orka.orchestrator.error_handling import ErrorHandler
from orka.orchestrator.metrics import MetricsCollector


class TestErrorHandler:
    """Test cases for ErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""

        # Create a combined handler with both ErrorHandler and MetricsCollector
        class CombinedHandler(ErrorHandler, MetricsCollector):
            pass

        self.handler = CombinedHandler()
        self.handler.step_index = 5
        self.handler.run_id = "test_run_123"
        self.handler.error_telemetry = {
            "errors": [],
            "retry_counters": {},
            "partial_successes": [],
            "silent_degradations": [],
            "recovery_actions": [],
            "status_codes": {},
            "critical_failures": [],
            "execution_status": "running",
        }
        self.handler.memory = MagicMock()

    def test_record_error_basic(self):
        """Test _record_error with basic parameters."""
        error_type = "agent_failure"
        agent_id = "test_agent"
        error_msg = "Test error message"

        with patch("builtins.print") as mock_print:
            self.handler._record_error(error_type, agent_id, error_msg)

        # Check error was recorded
        assert len(self.handler.error_telemetry["errors"]) == 1
        error_entry = self.handler.error_telemetry["errors"][0]

        assert error_entry["type"] == error_type
        assert error_entry["agent_id"] == agent_id
        assert error_entry["message"] == error_msg
        assert error_entry["step"] == self.handler.step_index
        assert error_entry["run_id"] == self.handler.run_id
        assert "timestamp" in error_entry

        # Check console output
        mock_print.assert_called_once()
        assert "🚨 [ORKA-ERROR]" in mock_print.call_args[0][0]
        assert error_type in mock_print.call_args[0][0]
        assert agent_id in mock_print.call_args[0][0]
        assert error_msg in mock_print.call_args[0][0]

    def test_record_error_with_exception(self):
        """Test _record_error with exception object."""
        error_type = "json_parsing"
        agent_id = "test_agent"
        error_msg = "JSON parsing failed"
        exception = ValueError("Invalid JSON format")

        with patch("builtins.print"):
            self.handler._record_error(error_type, agent_id, error_msg, exception=exception)

        error_entry = self.handler.error_telemetry["errors"][0]
        assert "exception" in error_entry
        assert error_entry["exception"]["type"] == "ValueError"
        assert error_entry["exception"]["message"] == "Invalid JSON format"
        # The traceback is stored as string "None" when no traceback exists
        assert error_entry["exception"]["traceback"] == "None"

    def test_record_error_with_exception_traceback(self):
        """Test _record_error with exception that has traceback."""
        error_type = "api_error"
        agent_id = "test_agent"
        error_msg = "API call failed"

        # Create exception with traceback
        try:
            raise RuntimeError("API timeout")
        except RuntimeError as e:
            exception = e

        with patch("builtins.print"):
            self.handler._record_error(error_type, agent_id, error_msg, exception=exception)

        error_entry = self.handler.error_telemetry["errors"][0]
        assert "exception" in error_entry
        assert error_entry["exception"]["type"] == "RuntimeError"
        assert error_entry["exception"]["message"] == "API timeout"
        assert error_entry["exception"]["traceback"] is not None
        assert error_entry["exception"]["traceback"] != "None"

    def test_record_error_with_status_code(self):
        """Test _record_error with status code."""
        error_type = "api_error"
        agent_id = "test_agent"
        error_msg = "HTTP error"
        status_code = 500

        with patch("builtins.print"):
            self.handler._record_error(error_type, agent_id, error_msg, status_code=status_code)

        error_entry = self.handler.error_telemetry["errors"][0]
        assert error_entry["status_code"] == status_code
        assert self.handler.error_telemetry["status_codes"][agent_id] == status_code

    def test_record_error_with_recovery_action(self):
        """Test _record_error with recovery action."""
        error_type = "agent_failure"
        agent_id = "test_agent"
        error_msg = "Agent failed"
        recovery_action = "retry"

        with patch("builtins.print"):
            self.handler._record_error(
                error_type, agent_id, error_msg, recovery_action=recovery_action
            )

        error_entry = self.handler.error_telemetry["errors"][0]
        assert error_entry["recovery_action"] == recovery_action

        # Check recovery action was recorded
        assert len(self.handler.error_telemetry["recovery_actions"]) == 1
        recovery_entry = self.handler.error_telemetry["recovery_actions"][0]
        assert recovery_entry["agent_id"] == agent_id
        assert recovery_entry["action"] == recovery_action
        assert "timestamp" in recovery_entry

    def test_record_error_with_custom_step(self):
        """Test _record_error with custom step number."""
        error_type = "agent_failure"
        agent_id = "test_agent"
        error_msg = "Agent failed"
        custom_step = 10

        with patch("builtins.print"):
            self.handler._record_error(error_type, agent_id, error_msg, step=custom_step)

        error_entry = self.handler.error_telemetry["errors"][0]
        assert error_entry["step"] == custom_step

    def test_record_error_all_parameters(self):
        """Test _record_error with all parameters."""
        error_type = "api_error"
        agent_id = "test_agent"
        error_msg = "Complex error"
        exception = ValueError("Test exception")
        step = 3
        status_code = 429
        recovery_action = "backoff"

        with patch("builtins.print"):
            self.handler._record_error(
                error_type,
                agent_id,
                error_msg,
                exception=exception,
                step=step,
                status_code=status_code,
                recovery_action=recovery_action,
            )

        error_entry = self.handler.error_telemetry["errors"][0]
        assert error_entry["type"] == error_type
        assert error_entry["agent_id"] == agent_id
        assert error_entry["message"] == error_msg
        assert error_entry["step"] == step
        assert error_entry["status_code"] == status_code
        assert error_entry["recovery_action"] == recovery_action
        assert "exception" in error_entry

        # Check status code and recovery action were recorded
        assert self.handler.error_telemetry["status_codes"][agent_id] == status_code
        assert len(self.handler.error_telemetry["recovery_actions"]) == 1

    def test_record_retry_new_agent(self):
        """Test _record_retry for a new agent."""
        agent_id = "test_agent"

        self.handler._record_retry(agent_id)

        assert self.handler.error_telemetry["retry_counters"][agent_id] == 1

    def test_record_retry_existing_agent(self):
        """Test _record_retry for an existing agent."""
        agent_id = "test_agent"
        self.handler.error_telemetry["retry_counters"][agent_id] = 2

        self.handler._record_retry(agent_id)

        assert self.handler.error_telemetry["retry_counters"][agent_id] == 3

    def test_record_partial_success(self):
        """Test _record_partial_success."""
        agent_id = "test_agent"
        retry_count = 3

        self.handler._record_partial_success(agent_id, retry_count)

        assert len(self.handler.error_telemetry["partial_successes"]) == 1
        success_entry = self.handler.error_telemetry["partial_successes"][0]
        assert success_entry["agent_id"] == agent_id
        assert success_entry["retry_count"] == retry_count
        assert "timestamp" in success_entry

    def test_record_silent_degradation(self):
        """Test _record_silent_degradation."""
        agent_id = "test_agent"
        degradation_type = "json_parsing_failure"
        details = {"attempted_field": "result", "fallback_used": "raw_text"}

        self.handler._record_silent_degradation(agent_id, degradation_type, details)

        assert len(self.handler.error_telemetry["silent_degradations"]) == 1
        degradation_entry = self.handler.error_telemetry["silent_degradations"][0]
        assert degradation_entry["agent_id"] == agent_id
        assert degradation_entry["type"] == degradation_type
        assert degradation_entry["details"] == details
        assert "timestamp" in degradation_entry

    def test_save_error_report_with_final_error(self):
        """Test _save_error_report with final error."""
        logs = [
            {"agent_id": "agent1", "duration": 1.0, "payload": {"result": "success"}},
            {"agent_id": "agent2", "duration": 2.0, "payload": {"result": "failed"}},
        ]
        final_error = Exception("Critical failure")

        # Mock file operations
        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print") as mock_print,
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            with patch.dict(os.environ, {"ORKA_LOG_DIR": "/tmp/test_logs"}):
                result_path = self.handler._save_error_report(logs, final_error)

        # Check execution status was set to failed
        assert self.handler.error_telemetry["execution_status"] == "failed"

        # Check critical failure was recorded
        assert len(self.handler.error_telemetry["critical_failures"]) == 1
        critical_failure = self.handler.error_telemetry["critical_failures"][0]
        assert critical_failure["error"] == str(final_error)
        assert critical_failure["step"] == self.handler.step_index
        assert "timestamp" in critical_failure

        # Check file operations
        mock_file.assert_called()
        mock_json_dump.assert_called()

        # Check return path
        assert "orka_error_report_" in result_path
        assert ".json" in result_path

    def test_save_error_report_partial_success(self):
        """Test _save_error_report with partial success (has errors but no final error)."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        # Add some errors to simulate partial success
        self.handler.error_telemetry["errors"] = [
            {"type": "minor_error", "agent_id": "agent1", "message": "Minor issue"},
        ]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            self.handler._save_error_report(logs)

        # Check execution status was set to partial
        assert self.handler.error_telemetry["execution_status"] == "partial"

    def test_save_error_report_completed_success(self):
        """Test _save_error_report with completed success (no errors)."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            self.handler._save_error_report(logs)

        # Check execution status was set to completed
        assert self.handler.error_telemetry["execution_status"] == "completed"

    def test_save_error_report_meta_report_generation_fails(self):
        """Test _save_error_report when meta report generation fails."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_generate_meta_report") as mock_meta_report,
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_meta_report.side_effect = Exception("Meta report failed")
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            self.handler._save_error_report(logs)

        # Check error was recorded for meta report failure
        assert len(self.handler.error_telemetry["errors"]) == 1
        error_entry = self.handler.error_telemetry["errors"][0]
        assert error_entry["type"] == "meta_report_generation"
        assert error_entry["agent_id"] == "meta_report"
        assert "Failed to generate meta report" in error_entry["message"]

    def test_save_error_report_file_save_fails(self):
        """Test _save_error_report when file save fails."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print") as mock_print,
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}
            mock_json_dump.side_effect = Exception("File save failed")

            self.handler._save_error_report(logs)

        # Check error message was printed
        mock_print.assert_any_call("❌ Failed to save error report: File save failed")

    def test_save_error_report_memory_save_fails(self):
        """Test _save_error_report when memory save fails."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print") as mock_print,
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}
            self.handler.memory.save_to_file.side_effect = Exception("Memory save failed")

            self.handler._save_error_report(logs)

        # Check error message was printed
        mock_print.assert_any_call("⚠️ Failed to save trace to memory backend: Memory save failed")

    def test_save_error_report_with_retries(self):
        """Test _save_error_report includes retry counts in report."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        # Add retry counters
        self.handler.error_telemetry["retry_counters"] = {
            "agent1": 3,
            "agent2": 1,
        }

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            self.handler._save_error_report(logs)

        # Check JSON dump was called with correct retry total
        json_call_args = mock_json_dump.call_args[0][0]
        assert json_call_args["orka_execution_report"]["total_retries"] == 4

    def test_save_error_report_with_multiple_errors(self):
        """Test _save_error_report with multiple errors from different agents."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        # Add multiple errors
        self.handler.error_telemetry["errors"] = [
            {"type": "error1", "agent_id": "agent1", "message": "Error 1"},
            {"type": "error2", "agent_id": "agent2", "message": "Error 2"},
            {"type": "error3", "agent_id": "agent1", "message": "Error 3"},
        ]

        with (
            patch("os.makedirs"),
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            self.handler._save_error_report(logs)

        # Check JSON dump was called with correct error counts
        json_call_args = mock_json_dump.call_args[0][0]
        assert json_call_args["orka_execution_report"]["total_errors"] == 3
        assert set(json_call_args["orka_execution_report"]["agents_with_errors"]) == {
            "agent1",
            "agent2",
        }

    def test_capture_memory_snapshot_with_memory(self):
        """Test _capture_memory_snapshot with memory data."""
        # Mock memory with data
        self.handler.memory.memory = [
            {"entry": 1, "data": "test1"},
            {"entry": 2, "data": "test2"},
            {"entry": 3, "data": "test3"},
        ]

        result = self.handler._capture_memory_snapshot()

        assert result["total_entries"] == 3
        assert result["last_10_entries"] == self.handler.memory.memory
        assert result["backend_type"] == "MagicMock"

    def test_capture_memory_snapshot_with_many_entries(self):
        """Test _capture_memory_snapshot with more than 10 entries."""
        # Mock memory with many entries
        entries = [{"entry": i, "data": f"test{i}"} for i in range(15)]
        self.handler.memory.memory = entries

        result = self.handler._capture_memory_snapshot()

        assert result["total_entries"] == 15
        assert result["last_10_entries"] == entries[-10:]
        assert result["backend_type"] == "MagicMock"

    def test_capture_memory_snapshot_no_memory_attribute(self):
        """Test _capture_memory_snapshot when memory has no memory attribute."""
        # Remove memory attribute
        del self.handler.memory.memory

        result = self.handler._capture_memory_snapshot()

        assert result["status"] == "no_memory_data"

    def test_capture_memory_snapshot_no_memory_data(self):
        """Test _capture_memory_snapshot when memory is empty."""
        self.handler.memory.memory = None

        result = self.handler._capture_memory_snapshot()

        assert result["status"] == "no_memory_data"

    def test_capture_memory_snapshot_exception(self):
        """Test _capture_memory_snapshot when an exception occurs."""
        # Mock memory to raise exception
        self.handler.memory.memory = MagicMock()
        self.handler.memory.memory.__len__.side_effect = Exception("Memory error")

        result = self.handler._capture_memory_snapshot()

        assert "error" in result
        assert "Failed to capture memory snapshot" in result["error"]

    def test_save_error_report_default_log_dir(self):
        """Test _save_error_report uses default log directory when env var not set."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]

        with (
            patch("os.makedirs") as mock_makedirs,
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            # Ensure ORKA_LOG_DIR is not set
            with patch.dict(os.environ, {}, clear=True):
                self.handler._save_error_report(logs)

        # Check default logs directory was used
        mock_makedirs.assert_called_with("logs", exist_ok=True)

    def test_save_error_report_custom_log_dir(self):
        """Test _save_error_report uses custom log directory from env var."""
        logs = [{"agent_id": "agent1", "duration": 1.0}]
        custom_log_dir = "/custom/logs"

        with (
            patch("os.makedirs") as mock_makedirs,
            patch("builtins.open", mock_open()) as mock_file,
            patch("json.dump") as mock_json_dump,
            patch("builtins.print"),
            patch.object(self.handler, "_capture_memory_snapshot") as mock_memory_snapshot,
        ):
            mock_memory_snapshot.return_value = {"test": "memory_snapshot"}

            with patch.dict(os.environ, {"ORKA_LOG_DIR": custom_log_dir}):
                self.handler._save_error_report(logs)

        # Check custom log directory was used
        mock_makedirs.assert_called_with(custom_log_dir, exist_ok=True)
