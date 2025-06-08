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

"""
Test cases for orchestrator error wrapper functionality
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from orka.orchestrator_error_wrapper import OrkaErrorHandler, run_orchestrator_with_error_handling


class TestOrkaErrorHandler:
    """Test suite for OrkaErrorHandler functionality"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator for testing"""
        orchestrator = MagicMock()
        orchestrator.run_id = "test_run_123"
        orchestrator.step_index = 5
        orchestrator.memory = MagicMock()
        orchestrator.memory.memory = [
            {"agent_id": "test_agent", "event": "test_event", "timestamp": "2025-01-01T00:00:00Z"},
        ]
        orchestrator.memory.save_to_file = MagicMock()
        orchestrator.memory.close = MagicMock()
        orchestrator._generate_meta_report = MagicMock(
            return_value={"total_cost": 0.05, "total_tokens": 150},
        )
        orchestrator.run = AsyncMock()
        return orchestrator

    @pytest.fixture
    def error_handler(self, mock_orchestrator):
        """Create an error handler instance for testing"""
        return OrkaErrorHandler(mock_orchestrator)

    def test_initialization(self, mock_orchestrator):
        """Test error handler initialization"""
        handler = OrkaErrorHandler(mock_orchestrator)

        assert handler.orchestrator == mock_orchestrator
        assert isinstance(handler.error_telemetry, dict)
        assert handler.error_telemetry["execution_status"] == "running"
        assert handler.error_telemetry["errors"] == []
        assert handler.error_telemetry["retry_counters"] == {}
        assert handler.error_telemetry["partial_successes"] == []
        assert handler.error_telemetry["silent_degradations"] == []
        assert handler.error_telemetry["status_codes"] == {}
        assert handler.error_telemetry["critical_failures"] == []
        assert handler.error_telemetry["recovery_actions"] == []

    def test_record_error_basic(self, error_handler):
        """Test basic error recording"""
        with patch("builtins.print") as mock_print:
            error_handler.record_error(
                error_type="test_error",
                agent_id="test_agent",
                error_msg="Test error message",
            )

        assert len(error_handler.error_telemetry["errors"]) == 1
        error = error_handler.error_telemetry["errors"][0]
        assert error["type"] == "test_error"
        assert error["agent_id"] == "test_agent"
        assert error["message"] == "Test error message"
        assert error["step"] == 5
        assert error["run_id"] == "test_run_123"
        assert "timestamp" in error

        mock_print.assert_called_once_with(
            "🚨 [ORKA-ERROR] test_error in test_agent: Test error message",
        )

    def test_record_error_with_exception(self, error_handler):
        """Test error recording with exception details"""
        test_exception = ValueError("Test exception")

        with patch("builtins.print"), patch("traceback.format_exc", return_value="Mock traceback"):
            error_handler.record_error(
                error_type="exception_error",
                agent_id="test_agent",
                error_msg="Error with exception",
                exception=test_exception,
                step=10,
                status_code=500,
                recovery_action="retry_agent",
            )

        error = error_handler.error_telemetry["errors"][0]
        assert error["step"] == 10
        assert error["status_code"] == 500
        assert error["recovery_action"] == "retry_agent"
        assert error["exception"]["type"] == "ValueError"
        assert error["exception"]["message"] == "Test exception"
        assert error["exception"]["traceback"] == "Mock traceback"

        assert error_handler.error_telemetry["status_codes"]["test_agent"] == 500
        assert len(error_handler.error_telemetry["recovery_actions"]) == 1
        assert error_handler.error_telemetry["recovery_actions"][0]["action"] == "retry_agent"

    def test_record_silent_degradation(self, error_handler):
        """Test recording silent degradations"""
        error_handler.record_silent_degradation(
            agent_id="test_agent",
            degradation_type="json_parsing_failure",
            details="Failed to parse JSON response, using raw text",
        )

        assert len(error_handler.error_telemetry["silent_degradations"]) == 1
        degradation = error_handler.error_telemetry["silent_degradations"][0]
        assert degradation["agent_id"] == "test_agent"
        assert degradation["type"] == "json_parsing_failure"
        assert degradation["details"] == "Failed to parse JSON response, using raw text"
        assert "timestamp" in degradation

    def test_capture_memory_snapshot_success(self, error_handler):
        """Test successful memory snapshot capture"""
        error_handler.orchestrator.memory.memory = [
            {"agent": "agent1", "data": "data1"},
            {"agent": "agent2", "data": "data2"},
        ]

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 2
        assert snapshot["last_10_entries"] == error_handler.orchestrator.memory.memory
        assert snapshot["backend_type"] == "MagicMock"

    def test_capture_memory_snapshot_large_memory(self, error_handler):
        """Test memory snapshot with large memory"""
        # Create memory with more than 10 entries
        large_memory = [{"agent": f"agent{i}", "data": f"data{i}"} for i in range(15)]
        error_handler.orchestrator.memory.memory = large_memory

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 15
        assert len(snapshot["last_10_entries"]) == 10
        assert snapshot["last_10_entries"] == large_memory[-10:]

    def test_capture_memory_snapshot_no_memory(self, error_handler):
        """Test memory snapshot when no memory available"""
        error_handler.orchestrator.memory.memory = None

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot == {"status": "no_memory_data"}

    def test_capture_memory_snapshot_exception(self, error_handler):
        """Test memory snapshot when exception occurs"""

        # Make hasattr fail to trigger exception path
        def failing_hasattr(*args, **kwargs):
            raise AttributeError("Test exception")

        with patch("builtins.hasattr", side_effect=failing_hasattr):
            snapshot = error_handler._capture_memory_snapshot()

        assert "error" in snapshot
        assert "Failed to capture memory snapshot" in snapshot["error"]

    def test_get_execution_summary(self, error_handler):
        """Test execution summary generation"""
        # Add some test data
        error_handler.error_telemetry["errors"] = [{"test": "error1"}, {"test": "error2"}]
        error_handler.error_telemetry["retry_counters"] = {"agent1": 2, "agent2": 1}
        error_handler.error_telemetry["execution_status"] = "partial"

        logs = [{"agent": "agent1"}, {"agent": "agent2"}, {"agent": "agent3"}]
        summary = error_handler._get_execution_summary(logs)

        assert summary["total_agents_executed"] == 3
        assert summary["total_errors"] == 2
        assert summary["total_retries"] == 3
        assert summary["execution_status"] == "partial"

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.orchestrator_error_wrapper.datetime")
    def test_save_comprehensive_error_report_success(
        self,
        mock_datetime,
        mock_file,
        mock_makedirs,
        error_handler,
    ):
        """Test successful error report saving"""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"
        mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        logs = [{"agent_id": "test_agent", "result": "success"}]

        with patch("builtins.print") as mock_print:
            with patch.dict(os.environ, {"ORKA_LOG_DIR": "/test/logs"}):
                report_path = error_handler.save_comprehensive_error_report(logs)

        # Use os.path.join to handle Windows vs Unix path separators
        expected_path = os.path.join("/test/logs", "orka_error_report_20250101_120000.json")
        assert report_path == expected_path
        mock_makedirs.assert_called_once_with("/test/logs", exist_ok=True)
        mock_file.assert_called()
        error_handler.orchestrator.memory.save_to_file.assert_called_once()

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.orchestrator_error_wrapper.datetime")
    def test_save_comprehensive_error_report_with_final_error(
        self,
        mock_datetime,
        mock_file,
        mock_makedirs,
        error_handler,
    ):
        """Test error report saving with final error"""
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"
        mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        logs = [{"agent_id": "test_agent", "result": "success"}]
        final_error = RuntimeError("Critical failure")

        with patch("builtins.print"):
            report_path = error_handler.save_comprehensive_error_report(logs, final_error)

        assert error_handler.error_telemetry["execution_status"] == "failed"
        assert len(error_handler.error_telemetry["critical_failures"]) == 1
        assert error_handler.error_telemetry["critical_failures"][0]["error"] == "Critical failure"

    @patch("os.makedirs")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("orka.orchestrator_error_wrapper.datetime")
    def test_save_comprehensive_error_report_file_error(
        self,
        mock_datetime,
        mock_file,
        mock_makedirs,
        error_handler,
    ):
        """Test error report saving when file operation fails"""
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

        logs = [{"agent_id": "test_agent", "result": "success"}]

        with patch("builtins.print") as mock_print:
            report_path = error_handler.save_comprehensive_error_report(logs)

        # Should still return the intended path even if save failed
        expected_path = os.path.join("logs", "orka_error_report_20250101_120000.json")
        assert report_path == expected_path
        mock_print.assert_any_call("❌ Failed to save error report: Permission denied")

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.orchestrator_error_wrapper.datetime")
    def test_save_comprehensive_error_report_meta_report_failure(
        self,
        mock_datetime,
        mock_file,
        mock_makedirs,
        error_handler,
    ):
        """Test error report saving when meta report generation fails"""
        mock_datetime.now.return_value.strftime.return_value = "20250101_120000"
        mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Make meta report generation fail
        error_handler.orchestrator._generate_meta_report.side_effect = Exception(
            "Meta report failed",
        )

        logs = [{"agent_id": "test_agent", "result": "success"}]

        with patch("builtins.print"):
            error_handler.save_comprehensive_error_report(logs)

        # Should have recorded the meta report error
        meta_errors = [
            e
            for e in error_handler.error_telemetry["errors"]
            if e["type"] == "meta_report_generation"
        ]
        assert len(meta_errors) == 1
        assert "Failed to generate meta report" in meta_errors[0]["message"]

    @pytest.mark.asyncio
    async def test_run_with_error_handling_success(self, error_handler):
        """Test successful orchestrator run with error handling"""
        # Mock successful execution
        test_logs = [{"agent_id": "agent1", "result": "success"}]
        error_handler.orchestrator.run.return_value = test_logs

        with patch.object(
            error_handler,
            "save_comprehensive_error_report",
            return_value="/test/report.json",
        ):
            result = await error_handler.run_with_error_handling("test_input")

        assert result["status"] == "success"
        assert result["execution_logs"] == test_logs
        assert "error_telemetry" in result
        assert "summary" in result
        assert result["report_path"] == "/test/report.json"
        assert error_handler.error_telemetry["execution_status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_with_error_handling_with_errors(self, error_handler):
        """Test orchestrator run with errors but successful completion"""
        test_logs = [{"agent_id": "agent1", "result": "success"}]
        error_handler.orchestrator.run.return_value = test_logs

        # Add some errors to telemetry
        error_handler.error_telemetry["errors"] = [{"type": "test_error", "agent_id": "agent1"}]

        with patch.object(
            error_handler,
            "save_comprehensive_error_report",
            return_value="/test/report.json",
        ):
            with patch("builtins.print"):
                result = await error_handler.run_with_error_handling("test_input")

        assert result["status"] == "success"
        assert error_handler.error_telemetry["execution_status"] == "partial"

    @pytest.mark.asyncio
    async def test_run_with_error_handling_critical_failure(self, error_handler):
        """Test orchestrator run with critical failure"""
        # Make orchestrator run fail
        critical_error = RuntimeError("Orchestrator crashed")
        error_handler.orchestrator.run.side_effect = critical_error

        with patch.object(
            error_handler,
            "save_comprehensive_error_report",
            return_value="/test/error_report.json",
        ):
            with patch("builtins.print"):
                with patch("traceback.format_exc", return_value="Mock traceback"):
                    result = await error_handler.run_with_error_handling("test_input")

        assert result["status"] == "critical_failure"
        assert result["error"] == "Orchestrator crashed"
        assert result["error_report_path"] == "/test/error_report.json"
        assert "error_telemetry" in result
        assert "traceback" in result

        # Should have recorded the critical error
        critical_errors = [
            e for e in error_handler.error_telemetry["errors"] if e["type"] == "critical_failure"
        ]
        assert len(critical_errors) == 1

    @pytest.mark.asyncio
    async def test_run_with_error_handling_cleanup_failure(self, error_handler):
        """Test orchestrator run with cleanup failure"""
        critical_error = RuntimeError("Orchestrator crashed")
        error_handler.orchestrator.run.side_effect = critical_error
        error_handler.orchestrator.memory.close.side_effect = Exception("Cleanup failed")

        with patch.object(
            error_handler,
            "save_comprehensive_error_report",
            return_value="/test/error_report.json",
        ):
            with patch("builtins.print") as mock_print:
                with patch("traceback.format_exc", return_value="Mock traceback"):
                    result = await error_handler.run_with_error_handling("test_input")

        assert result["status"] == "critical_failure"
        mock_print.assert_any_call("⚠️ Failed to cleanup memory backend: Cleanup failed")

    @pytest.mark.asyncio
    async def test_run_with_error_handling_already_error_result(self, error_handler):
        """Test when orchestrator returns an error result dict"""
        error_result = {"status": "error", "message": "Orchestrator error"}
        error_handler.orchestrator.run.return_value = error_result

        result = await error_handler.run_with_error_handling("test_input")

        assert result["status"] == "error"
        assert result["message"] == "Orchestrator error"
        assert "error_telemetry" in result

    def test_patch_orchestrator_for_error_tracking(self, error_handler):
        """Test orchestrator patching method"""
        # This method is currently a no-op, just test it doesn't raise
        error_handler._patch_orchestrator_for_error_tracking()
        # No assertions needed as it's currently empty


class TestOrkaErrorHandlerStandalone:
    """Test standalone function"""

    @pytest.mark.asyncio
    async def test_run_orchestrator_with_error_handling_function(self):
        """Test the standalone wrapper function"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.run = AsyncMock(return_value=[{"agent_id": "test", "result": "success"}])
        mock_orchestrator.run_id = "test_run"
        mock_orchestrator.step_index = 1
        mock_orchestrator.memory = MagicMock()
        mock_orchestrator.memory.memory = []
        mock_orchestrator._generate_meta_report = MagicMock(return_value={"cost": 0.01})

        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler") as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.run_with_error_handling = AsyncMock(return_value={"status": "success"})
            mock_handler_class.return_value = mock_handler

            result = await run_orchestrator_with_error_handling(mock_orchestrator, "test_input")

        assert result["status"] == "success"
        mock_handler_class.assert_called_once_with(mock_orchestrator)
        mock_handler.run_with_error_handling.assert_called_once_with("test_input")
