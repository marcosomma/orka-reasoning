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

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for colored terminal output."""
    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


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
    """Formatter that handles encoding errors for console output and adds colors."""
    
    def __init__(self, *args, use_colors: bool = True, **kwargs):
        """
        Initialize formatter with optional color support.
        
        Args:
            use_colors: Enable ANSI color codes (default: True, auto-disabled for non-TTY)
        """
        super().__init__(*args, **kwargs)
        # Auto-detect if we should use colors (only for TTY terminals)
        self.use_colors = use_colors and (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        ) and not os.getenv("NO_COLOR")  # Respect NO_COLOR environment variable
    
    def colorize_log(self, formatted: str, levelname: str) -> str:
        """
        Apply ANSI colors to log sections separated by ' - '.
        
        Format: timestamp - logger_name - level - message
        Each section gets a distinct color for easy visual parsing.
        """
        if not self.use_colors:
            return formatted
        
        # Define level-specific color schemes
        level_colors = {
            "DEBUG": Colors.BRIGHT_BLACK,
            "INFO": Colors.BRIGHT_CYAN,
            "WARNING": Colors.BRIGHT_YELLOW,
            "ERROR": Colors.BRIGHT_RED,
            "CRITICAL": Colors.BOLD + Colors.BRIGHT_RED,
        }
        
        # Split by ' - ' delimiter
        parts = formatted.split(' - ', 3)  # Max 4 parts: timestamp, name, level, message
        
        if len(parts) >= 4:
            timestamp, logger_name, level, message = parts[0], parts[1], parts[2], parts[3]
            
            # Apply distinct colors to each section
            colored = (
                f"{Colors.BRIGHT_BLACK}{timestamp}{Colors.RESET}"  # Timestamp: dim gray
                f" {Colors.DIM}-{Colors.RESET} "
                f"{Colors.CYAN}{logger_name}{Colors.RESET}"  # Logger: cyan
                f" {Colors.DIM}-{Colors.RESET} "
                f"{level_colors.get(levelname, Colors.WHITE)}{level}{Colors.RESET}"  # Level: level-based
                f" {Colors.DIM}-{Colors.RESET} "
                f"{Colors.WHITE}{message}{Colors.RESET}"  # Message: white
            )
            return colored
        
        # Fallback: just color the level name if parsing fails
        return formatted.replace(
            levelname,
            f"{level_colors.get(levelname, Colors.WHITE)}{levelname}{Colors.RESET}"
        )

    def format(self, record):
        try:
            formatted = super().format(record)
        except (UnicodeEncodeError, UnicodeDecodeError):
            # If formatting fails due to encoding, create a basic safe message
            formatted = f"{record.levelname}: {str(record.msg)}"

        # Apply colors before sanitization
        formatted = self.colorize_log(formatted, record.levelname)

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
