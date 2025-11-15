import json
import os
import pytest
import traceback
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock, mock_open

from orka.orchestrator_error_wrapper import OrkaErrorHandler, run_orchestrator_with_error_handling

class TestOrkaErrorHandler:
    @pytest.fixture
    def mock_orchestrator(self):
        mock_orch = MagicMock()
        mock_orch.step_index = 0
        mock_orch.run_id = "test_run_id"
        mock_orch._generate_meta_report = MagicMock(return_value={"meta": "report"})
        mock_orch.memory = MagicMock()
        mock_orch.memory.memory = MagicMock(return_value=[])
        mock_orch.memory.save_to_file = MagicMock()
        mock_orch.memory.close = MagicMock()
        mock_orch.run = AsyncMock(return_value=[{"log": "entry"}])
        return mock_orch

    @pytest.fixture
    def error_handler(self, mock_orchestrator):
        return OrkaErrorHandler(mock_orchestrator)

    def test_init(self, error_handler):
        assert isinstance(error_handler.error_telemetry, dict)
        assert "errors" in error_handler.error_telemetry
        assert error_handler.orchestrator is not None

    def test_record_error_basic(self, error_handler, mock_orchestrator):
        with patch("orka.orchestrator_error_wrapper.logger") as mock_logger:
            error_handler.record_error("TypeError", "agent1", "Something went wrong")
            assert len(error_handler.error_telemetry["errors"]) == 1
            error = error_handler.error_telemetry["errors"][0]
            assert error["type"] == "TypeError"
            assert error["agent_id"] == "agent1"
            assert error["message"] == "Something went wrong"
            assert "exception" not in error
            mock_logger.info.assert_called_with("🚨 [ORKA-ERROR] TypeError in agent1: Something went wrong")

    def test_record_error_with_exception(self, error_handler):
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            error_handler.record_error("ValueError", "agent2", "Exception occurred", exception=e)
            assert len(error_handler.error_telemetry["errors"]) == 1
            error = error_handler.error_telemetry["errors"][0]
            assert error["exception"]["type"] == "ValueError"
            assert "traceback" in error["exception"]

    def test_record_error_with_status_code(self, error_handler):
        error_handler.record_error("HTTPError", "agent3", "API failed", status_code=500)
        assert len(error_handler.error_telemetry["errors"]) == 1
        assert error_handler.error_telemetry["errors"][0]["status_code"] == 500
        assert error_handler.error_telemetry["status_codes"]["agent3"] == 500

    def test_record_error_with_recovery_action(self, error_handler):
        error_handler.record_error("Retry", "agent4", "Retrying operation", recovery_action="retry_agent")
        assert len(error_handler.error_telemetry["errors"]) == 1
        assert error_handler.error_telemetry["errors"][0]["recovery_action"] == "retry_agent"
        assert len(error_handler.error_telemetry["recovery_actions"]) == 1
        assert error_handler.error_telemetry["recovery_actions"][0]["action"] == "retry_agent"

    def test_record_silent_degradation(self, error_handler):
        error_handler.record_silent_degradation("agent5", "JSON_PARSE_FAIL", "Invalid JSON response")
        assert len(error_handler.error_telemetry["silent_degradations"]) == 1
        degradation = error_handler.error_telemetry["silent_degradations"][0]
        assert degradation["agent_id"] == "agent5"
        assert degradation["type"] == "JSON_PARSE_FAIL"

    def test_capture_memory_snapshot_with_memory(self, error_handler):
        error_handler.orchestrator.memory.memory = ["entry1", "entry2", "entry3"]
        snapshot = error_handler._capture_memory_snapshot()
        assert snapshot["total_entries"] == 3
        assert snapshot["last_10_entries"] == ["entry1", "entry2", "entry3"]
        assert snapshot["backend_type"] == "MagicMock"

    def test_capture_memory_snapshot_no_memory_data(self, error_handler):
        error_handler.orchestrator.memory.memory = None
        snapshot = error_handler._capture_memory_snapshot()
        assert snapshot["status"] == "no_memory_data"

    def test_capture_memory_snapshot_error(self, error_handler):
        mock_memory_list = MagicMock()
        mock_memory_list.__len__.side_effect = Exception("Memory access error")
        error_handler.orchestrator.memory.memory = mock_memory_list
        snapshot = error_handler._capture_memory_snapshot()
        assert "error" in snapshot
        assert "Memory access error" in snapshot["error"]

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_completed(self, mock_logger, error_handler):
        m_open = mock_open()
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.orchestrator.memory.save_to_file = MagicMock()
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}])
                assert error_handler.error_telemetry["execution_status"] == "completed"
                m_open.assert_called_once_with("test_report.json", "w")
                mock_json_dump.assert_called_once()
                mock_logger.info.assert_any_call("📋 Comprehensive error report saved: test_report.json")
                error_handler.orchestrator.memory.save_to_file.assert_called_once()
                assert report_path == "test_report.json"

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_partial(self, mock_logger, error_handler):
        m_open = mock_open()
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.record_error("Warning", "agent1", "Minor issue")
                error_handler.orchestrator.memory.save_to_file = MagicMock()
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}])
                assert error_handler.error_telemetry["execution_status"] == "partial"
                mock_logger.info.assert_any_call("📋 Comprehensive error report saved: test_report.json")
                error_handler.orchestrator.memory.save_to_file.assert_called_once()
                assert report_path == "test_report.json"

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_failed(self, mock_logger, error_handler):
        m_open = mock_open()
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.orchestrator.memory.save_to_file = MagicMock()
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}], final_error=Exception("Critical"))
                assert error_handler.error_telemetry["execution_status"] == "failed"
                assert len(error_handler.error_telemetry["critical_failures"]) == 1
                mock_logger.info.assert_any_call("📋 Comprehensive error report saved: test_report.json")
                error_handler.orchestrator.memory.save_to_file.assert_called_once()
                assert report_path == "test_report.json"

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_meta_report_failure(self, mock_logger, error_handler):
        m_open = mock_open()
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.orchestrator._generate_meta_report.side_effect = Exception("Meta report error")
                error_handler.orchestrator.memory.save_to_file = MagicMock()
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}])
                assert len(error_handler.error_telemetry["errors"]) == 1
                assert error_handler.error_telemetry["errors"][0]["type"] == "meta_report_generation"
                mock_logger.info.assert_any_call("📋 Comprehensive error report saved: test_report.json")
                error_handler.orchestrator.memory.save_to_file.assert_called_once()
                assert report_path == "test_report.json"

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_file_write_failure(self, mock_logger, error_handler):
        m_open = mock_open()
        m_open.side_effect = IOError("File write error")
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.orchestrator.memory.save_to_file = MagicMock()
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}])
                mock_logger.info.assert_any_call("❌ Failed to save error report: File write error")
                error_handler.orchestrator.memory.save_to_file.assert_called_once()
                assert report_path == "test_report.json" # Still returns the path even if write fails

    @patch("os.makedirs", MagicMock())
    @patch("os.path.join", MagicMock(return_value="test_report.json"))
    @patch("orka.orchestrator_error_wrapper.logger")
    def test_save_comprehensive_error_report_trace_save_failure(self, mock_logger, error_handler):
        m_open = mock_open()
        with patch("builtins.open", m_open):
            with patch("json.dump") as mock_json_dump:
                error_handler.orchestrator.memory.save_to_file.side_effect = Exception("Trace save error")
                report_path = error_handler.save_comprehensive_error_report([{"log": "entry"}])
                mock_logger.info.assert_any_call("⚠️ Failed to save trace to memory backend: Trace save error")
                assert report_path == "test_report.json"

    def test_get_execution_summary(self, error_handler):
        error_handler.record_error("Test", "agent1", "msg")
        error_handler.error_telemetry["retry_counters"]["agent1"] = 2
        summary = error_handler._get_execution_summary([{"log": "entry1"}, {"log": "entry2"}])
        assert summary["total_agents_executed"] == 2
        assert summary["total_errors"] == 1
        assert summary["total_retries"] == 2
        assert summary["execution_status"] == "running" # Default status

    @pytest.mark.asyncio
    @patch("orka.orchestrator_error_wrapper.OrkaErrorHandler._patch_orchestrator_for_error_tracking", MagicMock())
    async def test_run_with_error_handling_success(self, error_handler, mock_orchestrator):
        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler.save_comprehensive_error_report", MagicMock(return_value="report.json")):
            result = await error_handler.run_with_error_handling({"input": "data"})
            mock_orchestrator.run.assert_awaited_once_with({"input": "data"})
            assert result["status"] == "success"
            assert result["execution_logs"] == [{"log": "entry"}]
            assert result["error_telemetry"]["execution_status"] == "completed"
            assert result["report_path"] == "report.json"

    @pytest.mark.asyncio
    @patch("orka.orchestrator_error_wrapper.OrkaErrorHandler._patch_orchestrator_for_error_tracking", MagicMock())
    async def test_run_with_error_handling_partial_success(self, error_handler, mock_orchestrator):
        error_handler.record_error("Warning", "agent1", "Minor issue")
        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler.save_comprehensive_error_report", MagicMock(return_value="report.json")):
            result = await error_handler.run_with_error_handling({"input": "data"})
            assert result["status"] == "success"
            assert result["error_telemetry"]["execution_status"] == "partial"

    @pytest.mark.asyncio
    @patch("orka.orchestrator_error_wrapper.OrkaErrorHandler._patch_orchestrator_for_error_tracking", MagicMock())
    async def test_run_with_error_handling_critical_failure(self, error_handler, mock_orchestrator):
        mock_orchestrator.run.side_effect = Exception("Orchestrator crashed")
        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler.save_comprehensive_error_report", MagicMock(return_value="critical_report.json")):
            with patch("orka.orchestrator_error_wrapper.logger") as mock_logger:
                result = await error_handler.run_with_error_handling({"input": "data"})
                assert result["status"] == "critical_failure"
                assert "Orchestrator crashed" in result["error"]
                assert result["error_report_path"] == "critical_report.json"
                assert error_handler.error_telemetry["execution_status"] == "failed"
                mock_logger.info.assert_any_call("💥 [ORKA-CRITICAL] Orchestrator failed: Orchestrator crashed")
                mock_orchestrator.memory.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("orka.orchestrator_error_wrapper.OrkaErrorHandler._patch_orchestrator_for_error_tracking", MagicMock())
    async def test_run_with_error_handling_orchestrator_returns_error(self, error_handler, mock_orchestrator):
        mock_orchestrator.run.return_value = {"status": "error", "message": "Orchestrator error"}
        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler.save_comprehensive_error_report", MagicMock(return_value="report.json")):
            result = await error_handler.run_with_error_handling({"input": "data"})
            assert result["status"] == "error"
            assert "error_telemetry" in result

    @pytest.mark.asyncio
    async def test_run_orchestrator_with_error_handling_wrapper(self, mock_orchestrator):
        with patch("orka.orchestrator_error_wrapper.OrkaErrorHandler.run_with_error_handling", AsyncMock(return_value={"final": "report"})) as mock_run_with_error_handling:
            result = await run_orchestrator_with_error_handling(mock_orchestrator, {"input": "data"})
            mock_run_with_error_handling.assert_awaited_once_with({"input": "data"})
            assert result == {"final": "report"}
