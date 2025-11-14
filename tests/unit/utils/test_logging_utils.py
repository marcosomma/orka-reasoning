"""Unit tests for orka.utils.logging_utils."""

import logging
import os
import sys
from unittest.mock import Mock, patch

import pytest

from orka.utils.logging_utils import (
    SafeFormatter,
    _needs_sanitization,
    _sanitize_log_record,
    setup_logging,
)

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestNeedsSanitization:
    """Test suite for _needs_sanitization function."""

    def test_needs_sanitization_test_env(self):
        """Test _needs_sanitization returns False in test environment."""
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"}):
            assert _needs_sanitization() is False

    def test_needs_sanitization_problematic_encoding(self):
        """Test _needs_sanitization with problematic encoding."""
        mock_stdout = Mock()
        mock_stdout.encoding = "cp1252"
        with patch.dict(os.environ, {}, clear=True), \
             patch('sys.stdout', mock_stdout):
            assert _needs_sanitization() is True


class TestSafeFormatter:
    """Test suite for SafeFormatter class."""

    def test_format_normal(self):
        """Test SafeFormatter with normal message."""
        formatter = SafeFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            "test", logging.INFO, "test.py", 1, "Test message", (), None
        )
        
        result = formatter.format(record)
        
        assert "INFO" in result
        assert "Test message" in result

    def test_format_unicode_error(self):
        """Test SafeFormatter handles UnicodeEncodeError."""
        formatter = SafeFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            "test", logging.INFO, "test.py", 1, "Test message", (), None
        )
        
        with patch.object(logging.Formatter, "format", side_effect=UnicodeEncodeError("utf-8", "test", 0, 1, "error")):
            result = formatter.format(record)
            assert "INFO" in result
            assert "Test message" in result


class TestSanitizeLogRecord:
    """Test suite for _sanitize_log_record function."""

    def test_sanitize_log_record(self):
        """Test _sanitize_log_record creates log record."""
        record = _sanitize_log_record(
            "test_logger",
            logging.INFO,
            "test.py",
            1,
            "Test message",
            (),
            None,
        )
        
        assert isinstance(record, logging.LogRecord)
        assert record.name == "test_logger"
        assert record.msg == "Test message"


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default settings."""
        with patch.dict(os.environ, {}, clear=True), \
             patch("os.makedirs"), \
             patch("builtins.open", create=True), \
             patch("logging.FileHandler"):
            setup_logging(verbose=False)
            
            # Verify logging was configured
            assert logging.root.level <= logging.INFO

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose=True."""
        with patch.dict(os.environ, {}, clear=True), \
             patch("orka.utils.logging_utils.DEFAULT_LOG_LEVEL", "INVALID"), \
             patch("os.makedirs"), \
             patch("builtins.open", create=True), \
             patch("logging.FileHandler"):
            setup_logging(verbose=True)
            
            # Verify logging was configured
            assert logging.root.level == logging.DEBUG

    def test_setup_logging_env_level(self):
        """Test setup_logging with environment variable."""
        with patch.dict(os.environ, {"ORKA_LOG_LEVEL": "ERROR"}, clear=True), \
             patch("os.makedirs"), \
             patch("builtins.open", create=True), \
             patch("logging.FileHandler"):
            setup_logging(verbose=False)
            
            # Verify logging level was set from env
            assert logging.root.level == logging.ERROR

