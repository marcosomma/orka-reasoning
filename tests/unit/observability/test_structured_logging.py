"""Unit tests for orka.observability.structured_logging."""

import json
import logging
from unittest.mock import Mock, patch

import pytest

from orka.observability.structured_logging import StructuredLogger

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestStructuredLogger:
    """Test suite for StructuredLogger class."""

    def test_init(self):
        """Test StructuredLogger initialization."""
        logger = StructuredLogger("orka.nodes.graph_scout_agent")
        
        assert logger.component == "graph_scout_agent"
        assert logger.logger is not None

    def test_log_event(self):
        """Test log_event method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.log_event(
                logging.INFO,
                "test_event",
                message="Test message",
                key1="value1"
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.INFO
            
            # Verify JSON structure
            log_data = json.loads(call_args[0][1])
            assert log_data["event_type"] == "test_event"
            assert log_data["message"] == "Test message"
            assert log_data["key1"] == "value1"

    def test_log_graphscout_decision(self):
        """Test log_graphscout_decision method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_graphscout_decision(
                decision_type="commit_path",
                target=["agent1", "agent2"],
                confidence=0.9,
                run_id="test_run"
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["decision_type"] == "commit_path"
            assert call_kwargs["target"] == ["agent1", "agent2"]
            assert call_kwargs["confidence"] == 0.9

    def test_log_path_execution(self):
        """Test log_path_execution method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_path_execution(
                path=["agent1", "agent2"],
                status="success",
                run_id="test_run",
                execution_time_ms=150.0
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["path"] == ["agent1", "agent2"]
            assert call_kwargs["status"] == "success"

    def test_log_validation_result(self):
        """Test log_validation_result method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_validation_result(
                path=["agent1"],
                score=0.85,
                passed=True,
                run_id="test_run"
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["score"] == 0.85
            assert call_kwargs["passed"] is True

    def test_log_llm_fallback(self):
        """Test log_llm_fallback method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_llm_fallback(
                reason="JSON parse error",
                fallback_type="deterministic",
                run_id="test_run"
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["reason"] == "JSON parse error"
            assert call_kwargs["fallback_type"] == "deterministic"

    def test_log_agent_error(self):
        """Test log_agent_error method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_agent_error(
                agent_id="agent1",
                error="Test error",
                run_id="test_run"
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["agent_id"] == "agent1"
            assert call_kwargs["error"] == "Test error"

    def test_log_performance_metrics(self):
        """Test log_performance_metrics method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_performance_metrics(
                operation="path_scoring",
                duration_ms=50.0,
                run_id="test_run",
                candidates=10
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["operation"] == "path_scoring"
            assert call_kwargs["duration_ms"] == 50.0

    def test_log_configuration(self):
        """Test log_configuration method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.log_configuration(
                config_name="scoring_config",
                config_values={"threshold": 0.5},
                run_id="test_run"
            )
            
            mock_log_event.assert_called_once()
            call_kwargs = mock_log_event.call_args[1]
            assert call_kwargs["config_name"] == "scoring_config"

    def test_info(self):
        """Test info convenience method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.info("Test message", key="value")
            
            mock_log_event.assert_called_once()
            assert mock_log_event.call_args[0][0] == logging.INFO

    def test_warning(self):
        """Test warning convenience method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.warning("Test warning")
            
            mock_log_event.assert_called_once()
            assert mock_log_event.call_args[0][0] == logging.WARNING

    def test_error(self):
        """Test error convenience method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.error("Test error")
            
            mock_log_event.assert_called_once()
            assert mock_log_event.call_args[0][0] == logging.ERROR

    def test_debug(self):
        """Test debug convenience method."""
        logger = StructuredLogger("test.component")
        
        with patch.object(logger, 'log_event') as mock_log_event:
            logger.debug("Test debug")
            
            mock_log_event.assert_called_once()
            assert mock_log_event.call_args[0][0] == logging.DEBUG

