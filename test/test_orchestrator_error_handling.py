# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from orka.orchestrator.error_handling import ErrorHandler


class TestErrorHandler:
    """Test suite for ErrorHandler functionality"""

    @pytest.fixture
    def error_handler(self):
        """Create a mock ErrorHandler instance with necessary attributes"""
        handler = ErrorHandler()
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
        handler.step_index = 1
        handler.run_id = "test-run-123"

        # Mock memory object
        handler.memory = MagicMock()
        handler.memory.memory = ["entry1", "entry2", "entry3"]
        handler.memory.save_to_file = MagicMock()

        return handler

    def test_record_error_basic(self, error_handler):
        """Test basic error recording"""
        error_handler._record_error(
            error_type="test_error",
            agent_id="test_agent",
            error_msg="Test error message",
        )

        assert len(error_handler.error_telemetry["errors"]) == 1
        error_entry = error_handler.error_telemetry["errors"][0]

        assert error_entry["type"] == "test_error"
        assert error_entry["agent_id"] == "test_agent"
        assert error_entry["message"] == "Test error message"
        assert error_entry["step"] == 1
        assert error_entry["run_id"] == "test-run-123"
        assert "timestamp" in error_entry

    def test_record_error_with_exception(self, error_handler):
        """Test error recording with exception details"""
        test_exception = ValueError("Test exception")

        error_handler._record_error(
            error_type="validation_error",
            agent_id="validator",
            error_msg="Validation failed",
            exception=test_exception,
            step=5,
        )

        error_entry = error_handler.error_telemetry["errors"][0]

        assert error_entry["step"] == 5
        assert "exception" in error_entry
        assert error_entry["exception"]["type"] == "ValueError"
        assert error_entry["exception"]["message"] == "Test exception"

    def test_record_error_with_status_code(self, error_handler):
        """Test error recording with HTTP status code"""
        error_handler._record_error(
            error_type="api_error",
            agent_id="api_agent",
            error_msg="API call failed",
            status_code=500,
        )

        error_entry = error_handler.error_telemetry["errors"][0]

        assert error_entry["status_code"] == 500
        assert error_handler.error_telemetry["status_codes"]["api_agent"] == 500

    def test_record_error_with_recovery_action(self, error_handler):
        """Test error recording with recovery action"""
        error_handler._record_error(
            error_type="timeout_error",
            agent_id="slow_agent",
            error_msg="Operation timed out",
            recovery_action="retry",
        )

        error_entry = error_handler.error_telemetry["errors"][0]
        recovery_actions = error_handler.error_telemetry["recovery_actions"]

        assert error_entry["recovery_action"] == "retry"
        assert len(recovery_actions) == 1
        assert recovery_actions[0]["agent_id"] == "slow_agent"
        assert recovery_actions[0]["action"] == "retry"

    def test_record_retry(self, error_handler):
        """Test retry counter recording"""
        # First retry
        error_handler._record_retry("test_agent")
        assert error_handler.error_telemetry["retry_counters"]["test_agent"] == 1

        # Second retry
        error_handler._record_retry("test_agent")
        assert error_handler.error_telemetry["retry_counters"]["test_agent"] == 2

        # Different agent
        error_handler._record_retry("other_agent")
        assert error_handler.error_telemetry["retry_counters"]["other_agent"] == 1

    def test_record_partial_success(self, error_handler):
        """Test partial success recording"""
        error_handler._record_partial_success("test_agent", 3)

        partial_successes = error_handler.error_telemetry["partial_successes"]
        assert len(partial_successes) == 1

        success_entry = partial_successes[0]
        assert success_entry["agent_id"] == "test_agent"
        assert success_entry["retry_count"] == 3
        assert "timestamp" in success_entry

    def test_record_silent_degradation(self, error_handler):
        """Test silent degradation recording"""
        error_handler._record_silent_degradation(
            "parser_agent",
            "json_parsing_failure",
            {"original": "invalid json", "fallback": "empty object"},
        )

        degradations = error_handler.error_telemetry["silent_degradations"]
        assert len(degradations) == 1

        degradation_entry = degradations[0]
        assert degradation_entry["agent_id"] == "parser_agent"
        assert degradation_entry["type"] == "json_parsing_failure"
        assert degradation_entry["details"]["fallback"] == "empty object"

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_error_report_success(
        self,
        mock_json_dump,
        mock_file_open,
        mock_makedirs,
        error_handler,
    ):
        """Test successful error report saving"""
        # Setup
        logs = [{"agent_id": "test", "result": "success"}]
        error_handler._generate_meta_report = MagicMock(return_value={"meta": "data"})

        with patch.dict(os.environ, {"ORKA_LOG_DIR": "/test/logs"}):
            report_path = error_handler._save_error_report(logs)

        # Verify directory creation
        mock_makedirs.assert_called_with("/test/logs", exist_ok=True)

        # Verify file operations
        assert mock_file_open.called
        assert mock_json_dump.called

        # Check report structure
        call_args = mock_json_dump.call_args[0]
        report_data = call_args[0]

        assert "orka_execution_report" in report_data
        report = report_data["orka_execution_report"]
        assert report["run_id"] == "test-run-123"
        assert report["execution_logs"] == logs
        assert "timestamp" in report

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_error_report_with_final_error(
        self,
        mock_json_dump,
        mock_file_open,
        mock_makedirs,
        error_handler,
    ):
        """Test error report saving with final error"""
        logs = []
        final_error = Exception("Critical failure")
        error_handler._generate_meta_report = MagicMock(return_value={"meta": "data"})

        error_handler._save_error_report(logs, final_error)

        # Check that execution status was set to failed
        assert error_handler.error_telemetry["execution_status"] == "failed"

        # Check that critical failure was recorded
        critical_failures = error_handler.error_telemetry["critical_failures"]
        assert len(critical_failures) == 1
        assert "Critical failure" in critical_failures[0]["error"]

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_error_report_with_meta_report_failure(
        self,
        mock_json_dump,
        mock_file_open,
        mock_makedirs,
        error_handler,
    ):
        """Test error report saving when meta report generation fails"""
        logs = []
        error_handler._generate_meta_report = MagicMock(side_effect=Exception("Meta report failed"))

        error_handler._save_error_report(logs)

        # Should still create report with partial data
        call_args = mock_json_dump.call_args[0]
        report_data = call_args[0]
        meta_report = report_data["orka_execution_report"]["meta_report"]

        assert meta_report["error"] == "Failed to generate meta report"
        assert "partial_data" in meta_report

    @patch("os.makedirs")
    @patch("builtins.open", side_effect=OSError("File write failed"))
    def test_save_error_report_file_error(self, mock_file_open, mock_makedirs, error_handler):
        """Test error report saving when file operations fail"""
        logs = []
        error_handler._generate_meta_report = MagicMock(return_value={"meta": "data"})

        # Should not raise exception, just handle gracefully
        result = error_handler._save_error_report(logs)

        # Should still return a path even if saving failed
        assert result is not None

    def test_capture_memory_snapshot_success(self, error_handler):
        """Test successful memory snapshot capture"""
        # Setup memory with more than 10 entries
        error_handler.memory.memory = [f"entry_{i}" for i in range(15)]

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 15
        assert len(snapshot["last_10_entries"]) == 10
        assert snapshot["backend_type"] == "MagicMock"

    def test_capture_memory_snapshot_small_memory(self, error_handler):
        """Test memory snapshot with less than 10 entries"""
        error_handler.memory.memory = ["entry1", "entry2", "entry3"]

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 3
        assert snapshot["last_10_entries"] == ["entry1", "entry2", "entry3"]

    def test_capture_memory_snapshot_no_memory(self, error_handler):
        """Test memory snapshot when memory is not available"""
        error_handler.memory = None

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["status"] == "no_memory_data"

    def test_capture_memory_snapshot_exception(self, error_handler):
        """Test memory snapshot when exception occurs"""
        # Mock the memory object to raise an exception when accessing memory attribute
        error_handler.memory = MagicMock()
        error_handler.memory.memory = MagicMock()
        # Make len() raise an exception
        error_handler.memory.memory.__len__.side_effect = Exception("Memory error")

        snapshot = error_handler._capture_memory_snapshot()

        assert "error" in snapshot
        assert "Memory error" in snapshot["error"]

    @patch("builtins.print")
    def test_record_error_console_logging(self, mock_print, error_handler):
        """Test that errors are logged to console"""
        error_handler._record_error(
            error_type="test_error",
            agent_id="test_agent",
            error_msg="Test message",
        )

        mock_print.assert_called_with("🚨 [ORKA-ERROR] test_error in test_agent: Test message")

    def test_error_telemetry_structure(self, error_handler):
        """Test that error telemetry maintains correct structure"""
        # Add various types of errors and data
        error_handler._record_error("error1", "agent1", "message1")
        error_handler._record_retry("agent1")
        error_handler._record_partial_success("agent1", 2)
        error_handler._record_silent_degradation("agent1", "degradation", {"key": "value"})

        telemetry = error_handler.error_telemetry

        # Check all expected keys exist
        expected_keys = [
            "errors",
            "retry_counters",
            "partial_successes",
            "silent_degradations",
            "status_codes",
            "recovery_actions",
            "critical_failures",
            "execution_status",
        ]

        for key in expected_keys:
            assert key in telemetry

        # Check data consistency
        assert len(telemetry["errors"]) == 1
        assert telemetry["retry_counters"]["agent1"] == 1
        assert len(telemetry["partial_successes"]) == 1
        assert len(telemetry["silent_degradations"]) == 1

    def test_execution_status_determination(self, error_handler):
        """Test execution status determination logic in save_error_report"""
        error_handler._generate_meta_report = MagicMock(return_value={})

        with patch("os.makedirs"), patch("builtins.open", mock_open()), patch(
            "json.dump",
        ) as mock_json_dump:
            # Test completed status (no errors)
            error_handler._save_error_report([])
            assert error_handler.error_telemetry["execution_status"] == "completed"

            # Reset and test partial status (has errors but no final error)
            error_handler.error_telemetry["execution_status"] = "running"
            error_handler.error_telemetry["errors"] = [
                {"agent_id": "test_agent", "type": "test_error"},
            ]
            error_handler._save_error_report([])
            assert error_handler.error_telemetry["execution_status"] == "partial"

            # Reset and test failed status (has final error)
            error_handler.error_telemetry["execution_status"] = "running"
            error_handler._save_error_report([], final_error=Exception("Final error"))
            assert error_handler.error_telemetry["execution_status"] == "failed"

    @patch.dict(os.environ, {"ORKA_LOG_DIR": "/custom/path"})
    def test_custom_log_directory(self, error_handler):
        """Test that custom log directory is used when set"""
        error_handler._generate_meta_report = MagicMock(return_value={})

        with patch("os.makedirs") as mock_makedirs, patch("builtins.open", mock_open()), patch(
            "json.dump",
        ):
            error_handler._save_error_report([])
            mock_makedirs.assert_called_with("/custom/path", exist_ok=True)

    def test_memory_save_to_file_called(self, error_handler):
        """Test that memory save_to_file is called during error report saving"""
        error_handler._generate_meta_report = MagicMock(return_value={})

        with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("json.dump"):
            error_handler._save_error_report([])

            # Verify memory save_to_file was called
            error_handler.memory.save_to_file.assert_called_once()

    def test_memory_save_failure_handling(self, error_handler):
        """Test handling of memory save failures"""
        error_handler._generate_meta_report = MagicMock(return_value={})
        error_handler.memory.save_to_file.side_effect = Exception("Save failed")

        with patch("os.makedirs"), patch("builtins.open", mock_open()), patch("json.dump"), patch(
            "builtins.print",
        ) as mock_print:
            # Should not raise exception
            error_handler._save_error_report([])

            # Should print warning
            mock_print.assert_any_call("⚠️ Failed to save trace to memory backend: Save failed")
