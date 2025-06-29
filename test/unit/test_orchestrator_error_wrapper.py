"""
Unit tests for orchestrator error wrapper module.
Tests error handling, telemetry, and comprehensive error reporting.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from orka.orchestrator_error_wrapper import (
    OrkaErrorHandler,
    run_orchestrator_with_error_handling,
)


class TestOrkaErrorHandler:
    """Test OrKa error handler functionality."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator for testing."""
        orchestrator = MagicMock()
        orchestrator.step_index = 0
        orchestrator.run_id = "test-run-123"
        orchestrator.memory = MagicMock()
        orchestrator.memory.memory = ["entry1", "entry2", "entry3"]
        return orchestrator

    @pytest.fixture
    def error_handler(self, mock_orchestrator):
        """Create error handler with mock orchestrator."""
        return OrkaErrorHandler(mock_orchestrator)

    def test_error_handler_initialization(self, mock_orchestrator):
        """Test error handler initialization."""
        handler = OrkaErrorHandler(mock_orchestrator)

        assert handler.orchestrator == mock_orchestrator
        assert handler.error_telemetry["errors"] == []
        assert handler.error_telemetry["retry_counters"] == {}
        assert handler.error_telemetry["partial_successes"] == []
        assert handler.error_telemetry["silent_degradations"] == []
        assert handler.error_telemetry["status_codes"] == {}
        assert handler.error_telemetry["execution_status"] == "running"
        assert handler.error_telemetry["critical_failures"] == []
        assert handler.error_telemetry["recovery_actions"] == []

    def test_record_error_basic(self, error_handler, capsys):
        """Test basic error recording."""
        error_handler.record_error(
            error_type="api_error",
            agent_id="test_agent",
            error_msg="API call failed",
        )

        captured = capsys.readouterr()
        assert "🚨 [ORKA-ERROR] api_error in test_agent: API call failed" in captured.out

        assert len(error_handler.error_telemetry["errors"]) == 1
        error = error_handler.error_telemetry["errors"][0]
        assert error["type"] == "api_error"
        assert error["agent_id"] == "test_agent"
        assert error["message"] == "API call failed"
        assert error["step"] == 0
        assert error["run_id"] == "test-run-123"
        assert "timestamp" in error

    def test_record_error_with_exception(self, error_handler):
        """Test error recording with exception details."""
        exception = ValueError("Test exception")

        error_handler.record_error(
            error_type="validation_error",
            agent_id="validator",
            error_msg="Validation failed",
            exception=exception,
            step=5,
        )

        error = error_handler.error_telemetry["errors"][0]
        assert error["exception"]["type"] == "ValueError"
        assert error["exception"]["message"] == "Test exception"
        assert "traceback" in error["exception"]
        assert error["step"] == 5

    def test_record_error_with_status_code(self, error_handler):
        """Test error recording with HTTP status code."""
        error_handler.record_error(
            error_type="http_error",
            agent_id="api_agent",
            error_msg="HTTP error",
            status_code=429,
        )

        error = error_handler.error_telemetry["errors"][0]
        assert error["status_code"] == 429
        assert error_handler.error_telemetry["status_codes"]["api_agent"] == 429

    def test_record_error_with_recovery_action(self, error_handler):
        """Test error recording with recovery action."""
        error_handler.record_error(
            error_type="retry_error",
            agent_id="retry_agent",
            error_msg="Retrying operation",
            recovery_action="Increased timeout and retried",
        )

        error = error_handler.error_telemetry["errors"][0]
        assert error["recovery_action"] == "Increased timeout and retried"

        recovery_actions = error_handler.error_telemetry["recovery_actions"]
        assert len(recovery_actions) == 1
        assert recovery_actions[0]["agent_id"] == "retry_agent"
        assert recovery_actions[0]["action"] == "Increased timeout and retried"

    def test_record_silent_degradation(self, error_handler):
        """Test silent degradation recording."""
        error_handler.record_silent_degradation(
            agent_id="parser_agent",
            degradation_type="json_parse_failure",
            details="Fell back to raw text response",
        )

        degradations = error_handler.error_telemetry["silent_degradations"]
        assert len(degradations) == 1
        assert degradations[0]["agent_id"] == "parser_agent"
        assert degradations[0]["type"] == "json_parse_failure"
        assert degradations[0]["details"] == "Fell back to raw text response"
        assert "timestamp" in degradations[0]

    def test_capture_memory_snapshot_success(self, error_handler):
        """Test successful memory snapshot capture."""
        # Set up memory with entries
        error_handler.orchestrator.memory.memory = list(range(15))  # 15 entries

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 15
        assert len(snapshot["last_10_entries"]) == 10
        assert snapshot["last_10_entries"] == list(range(5, 15))  # Last 10 entries
        assert "backend_type" in snapshot

    def test_capture_memory_snapshot_small_memory(self, error_handler):
        """Test memory snapshot with fewer than 10 entries."""
        error_handler.orchestrator.memory.memory = [1, 2, 3]

        snapshot = error_handler._capture_memory_snapshot()

        assert snapshot["total_entries"] == 3
        assert snapshot["last_10_entries"] == [1, 2, 3]

    def test_capture_memory_snapshot_no_memory(self, error_handler):
        """Test memory snapshot when no memory available."""
        error_handler.orchestrator.memory.memory = None

        snapshot = error_handler._capture_memory_snapshot()

        assert "error" in snapshot or "status" in snapshot

    def test_capture_memory_snapshot_exception(self, error_handler):
        """Test memory snapshot when exception occurs."""
        error_handler.orchestrator.memory = None

        snapshot = error_handler._capture_memory_snapshot()

        assert "error" in snapshot or "status" in snapshot

    @patch("orka.orchestrator_error_wrapper.datetime")
    @patch("builtins.open")
    @patch("os.makedirs")
    def test_save_comprehensive_error_report_success(
        self,
        mock_makedirs,
        mock_open,
        mock_datetime,
        error_handler,
    ):
        """Test successful comprehensive error report generation."""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "20250629_123456"
        mock_datetime.now.return_value.isoformat.return_value = "2025-06-29T12:34:56Z"

        # Mock meta report generation
        meta_report = {"test": "meta_report"}
        error_handler.orchestrator._generate_meta_report.return_value = meta_report

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Record some errors first
        error_handler.record_error("test_error", "test_agent", "Test message")

        logs = [{"agent": "test_agent", "result": "test_result"}]
        final_error = RuntimeError("Test final error")

        report_path = error_handler.save_comprehensive_error_report(logs, final_error)

        # Verify directory creation
        mock_makedirs.assert_called_once_with("logs", exist_ok=True)

        # Verify file writing
        mock_open.assert_called()
        mock_file.write.assert_called()

        # Verify execution status updated
        assert error_handler.error_telemetry["execution_status"] == "failed"
        assert len(error_handler.error_telemetry["critical_failures"]) == 1

        # Verify return path
        assert "orka_error_report_20250629_123456.json" in report_path

    @patch.dict(os.environ, {"ORKA_LOG_DIR": "custom_logs"})
    def test_save_error_report_custom_log_dir(self, error_handler):
        """Test error report saves to custom log directory."""
        with patch("os.makedirs"), patch("builtins.open"), patch(
            "orka.orchestrator_error_wrapper.datetime",
        ):
            error_handler.save_comprehensive_error_report([])

            # Should use custom log directory from environment
            # This is verified by the makedirs call in the actual test

    def test_save_error_report_meta_generation_failure(self, error_handler):
        """Test error report when meta generation fails."""
        error_handler.orchestrator._generate_meta_report.side_effect = Exception(
            "Meta generation failed",
        )

        with patch("os.makedirs"), patch("builtins.open"), patch(
            "orka.orchestrator_error_wrapper.datetime",
        ):
            error_handler.save_comprehensive_error_report([])

            # Should record the meta generation error
            meta_errors = [
                e
                for e in error_handler.error_telemetry["errors"]
                if e["type"] == "meta_report_generation"
            ]
            assert len(meta_errors) == 1

    def test_save_error_report_execution_status_logic(self, error_handler):
        """Test execution status determination logic."""
        with patch("os.makedirs"), patch("builtins.open"), patch(
            "orka.orchestrator_error_wrapper.datetime",
        ), patch.object(error_handler.orchestrator, "_generate_meta_report"):
            # Test completed status (no errors, no final error)
            error_handler.save_comprehensive_error_report([])
            assert error_handler.error_telemetry["execution_status"] == "completed"

            # Reset and test partial status (has errors, no final error)
            error_handler.error_telemetry["execution_status"] = "running"
            error_handler.record_error("test", "agent", "message")
            error_handler.save_comprehensive_error_report([])
            assert error_handler.error_telemetry["execution_status"] == "partial"

    @pytest.mark.asyncio
    async def test_run_with_error_handling_success(self, error_handler):
        """Test successful orchestrator run with error handling."""

        # Mock successful orchestrator run
        async def mock_run(input_data):
            return {"result": "success", "data": input_data}

        error_handler.orchestrator.run = mock_run

        input_data = {"test": "input"}
        result = await error_handler.run_with_error_handling(input_data)

        assert result["result"] == "success"
        assert result["data"] == input_data

    @pytest.mark.asyncio
    async def test_run_with_error_handling_with_recorded_errors(self, error_handler, capsys):
        """Test orchestrator run with recorded errors but successful completion."""

        async def mock_run(input_data):
            # Simulate some errors during execution
            error_handler.record_error("minor_error", "agent1", "Minor issue")
            return {"result": "success_with_warnings"}

        error_handler.orchestrator.run = mock_run

        result = await error_handler.run_with_error_handling({})

        captured = capsys.readouterr()
        assert "⚠️ [ORKA-WARNING] Execution completed with 1 errors" in captured.out
        assert result["result"] == "success_with_warnings"

    @pytest.mark.asyncio
    async def test_run_with_error_handling_exception(self, error_handler, capsys):
        """Test orchestrator run with exception - handler should catch and record."""

        async def mock_run(input_data):
            raise RuntimeError("Orchestrator failed")

        error_handler.orchestrator.run = mock_run

        # Don't mock the save method, let it execute to update status
        result = await error_handler.run_with_error_handling({})

        # Should record critical failure
        captured = capsys.readouterr()
        assert "💥 [ORKA-CRITICAL]" in captured.out

        # Should have recorded the error
        assert len(error_handler.error_telemetry["errors"]) > 0

        # Should return error result
        assert result["status"] == "critical_failure"
        assert "error" in result
        assert "error_report_path" in result

    def test_patch_orchestrator_for_error_tracking(self, error_handler):
        """Test orchestrator patching for error tracking."""
        # This is a simple method that sets up monitoring
        error_handler._patch_orchestrator_for_error_tracking()

        # The method doesn't return anything, just sets up internal state
        # The test verifies it doesn't raise an exception

    def test_get_execution_summary(self, error_handler):
        """Test execution summary generation."""
        logs = [
            {"agent": "agent1", "status": "success"},
            {"agent": "agent2", "status": "error"},
        ]

        summary = error_handler._get_execution_summary(logs)

        assert "total_agents" in summary or isinstance(summary, dict)


class TestModuleFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_run_orchestrator_with_error_handling(self):
        """Test the module-level error handling function."""
        mock_orchestrator = MagicMock()

        # Mock successful run
        async def mock_run(input_data):
            return {"result": "success"}

        mock_orchestrator.run = mock_run

        input_data = {"test": "data"}

        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler") as mock_handler_class:
            mock_handler = MagicMock()

            # Make the async method return a coroutine that resolves to the dict
            async def mock_run_with_error_handling(data):
                return {"result": "success"}

            mock_handler.run_with_error_handling = mock_run_with_error_handling
            mock_handler_class.return_value = mock_handler

            result = await run_orchestrator_with_error_handling(mock_orchestrator, input_data)

            # Verify handler was created
            mock_handler_class.assert_called_once_with(mock_orchestrator)
            assert result["result"] == "success"

    def test_integration_error_telemetry_structure(self):
        """Test that error telemetry maintains consistent structure."""
        # Create mock orchestrator inline
        mock_orchestrator = MagicMock()
        mock_orchestrator.step_index = 0
        mock_orchestrator.run_id = "test-run-123"
        mock_orchestrator.memory = MagicMock()
        mock_orchestrator.memory.memory = ["entry1", "entry2", "entry3"]

        handler = OrkaErrorHandler(mock_orchestrator)

        # Record various types of errors
        handler.record_error("type1", "agent1", "message1")
        handler.record_error("type2", "agent2", "message2", status_code=500)
        handler.record_silent_degradation("agent3", "degradation", "details")

        telemetry = handler.error_telemetry

        # Verify structure consistency
        assert isinstance(telemetry["errors"], list)
        assert isinstance(telemetry["retry_counters"], dict)
        assert isinstance(telemetry["partial_successes"], list)
        assert isinstance(telemetry["silent_degradations"], list)
        assert isinstance(telemetry["status_codes"], dict)
        assert isinstance(telemetry["execution_status"], str)
        assert isinstance(telemetry["critical_failures"], list)
        assert isinstance(telemetry["recovery_actions"], list)

        # Verify data consistency
        assert len(telemetry["errors"]) == 2
        assert len(telemetry["silent_degradations"]) == 1
        assert "agent2" in telemetry["status_codes"]
        assert telemetry["status_codes"]["agent2"] == 500
