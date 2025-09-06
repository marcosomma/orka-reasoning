"""
Logging Utilities
===============

This module contains shared logging utilities used across the OrKa system.
"""

import logging
import os
import sys
from datetime import datetime

DEFAULT_LOG_LEVEL: str = "INFO"


class SafeFormatter(logging.Formatter):
    """Formatter that handles encoding errors."""

    def format(self, record):
        # Ensure the message is a string before encoding
        msg = str(record.msg)
        # Encode to UTF-8 and decode back, replacing unencodable characters
        record.msg = msg.encode("utf-8", "replace").decode("utf-8")
        return super().format(record)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    # Check environment variable first, then fall back to verbose flag
    env_level = os.getenv("ORKA_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    if env_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = getattr(logging, env_level)
    else:
        level = logging.DEBUG if verbose else logging.INFO
    # Remove all handlers associated with the root logger to prevent duplicate output
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Create a StreamHandler with UTF-8 encoding
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
