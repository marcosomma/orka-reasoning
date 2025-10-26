"""
Logging Utilities
===============

This module contains shared logging utilities used across the OrKa system.
"""

import io
import logging
import os
import sys
from datetime import datetime

DEFAULT_LOG_LEVEL: str = "INFO"


def _needs_sanitization() -> bool:
    """Check if we're in an environment that needs Unicode sanitization."""
    # Don't sanitize in test environments
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False

    # Check if stdout encoding can handle Unicode
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        encoding = sys.stdout.encoding.lower()
        # Only sanitize for problematic encodings (Windows cp1252, ascii, etc.)
        if encoding in ("cp1252", "ascii", "us-ascii", "charmap"):
            return True

    return False


class SafeFormatter(logging.Formatter):
    """Formatter that handles encoding errors for console output."""

    def format(self, record):
        try:
            formatted = super().format(record)
        except (UnicodeEncodeError, UnicodeDecodeError):
            # If formatting fails due to encoding, create a basic safe message
            formatted = f"{record.levelname}: {str(record.msg)}"

        # Only sanitize if we're in a problematic environment
        if not _needs_sanitization():
            return formatted

        # Replace specific problematic Unicode characters
        replacements = {
            "\u2011": "-",  # non-breaking hyphen
            "\u2013": "-",  # en dash
            "\u2014": "--",  # em dash
            "\u2015": "--",  # horizontal bar
            "\u2018": "'",  # left single quote
            "\u2019": "'",  # right single quote
            "\u201a": ",",  # single low-9 quotation mark
            "\u201b": "'",  # single high-reversed-9 quotation mark
            "\u201c": '"',  # left double quote
            "\u201d": '"',  # right double quote
            "\u201e": '"',  # double low-9 quotation mark
            "\u2026": "...",  # ellipsis
            "\u2032": "'",  # prime
            "\u2033": '"',  # double prime
            "\xa0": " ",  # non-breaking space
        }
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)

        return formatted


def _sanitize_log_record(
    name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None, **kwargs
):
    """Custom log record factory that sanitizes all messages before formatting."""
    # Only sanitize if we're in a problematic environment
    if _needs_sanitization() and msg:
        msg_str = str(msg)
        # Replace common problematic Unicode characters
        replacements = {
            "\u2011": "-",
            "\u2013": "-",
            "\u2014": "--",
            "\u2015": "--",
            "\u2018": "'",
            "\u2019": "'",
            "\u201a": ",",
            "\u201b": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u201e": '"',
            "\u2026": "...",
            "\u2032": "'",
            "\u2033": '"',
        }
        for old, new in replacements.items():
            msg_str = msg_str.replace(old, new)
        msg = msg_str

    # Create the log record with sanitized values
    record = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    # Set custom log record factory to sanitize all messages
    logging.setLogRecordFactory(_sanitize_log_record)

    # Check environment variable first, then fall back to verbose flag
    env_level = os.getenv("ORKA_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)
    else:
        level = logging.DEBUG if verbose else logging.INFO
    # Remove all handlers associated with the root logger to prevent duplicate output
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create a StreamHandler for console output
    # SafeFormatter will handle all character encoding issues
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        SafeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    console_handler.setLevel(level)
    logging.root.addHandler(console_handler)

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Create a FileHandler for debug logs with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(log_dir, f"orka_debug_console_{timestamp}.log")
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(SafeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    file_handler.setLevel(logging.DEBUG)  # Capture all levels to file
    logging.root.addHandler(file_handler)

    logging.root.setLevel(level)

    # Set specific loggers to DEBUG level
    logging.getLogger("orka.memory.redisstack_logger").setLevel(logging.DEBUG)
    logging.getLogger("orka.memory_logger").setLevel(logging.DEBUG)
