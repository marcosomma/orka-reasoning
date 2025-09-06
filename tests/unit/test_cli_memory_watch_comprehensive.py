"""Test CLI Memory Watch Comprehensive."""

import json
import logging
import os
from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from orka.cli.memory.watch import (
    _memory_watch_display,
    _memory_watch_fallback,
    _memory_watch_json,
    memory_watch,
)


class LogCaptureHandler(logging.StreamHandler):
    """Custom handler that captures log output for testing."""

    def __init__(self):
        super().__init__()
        self.stream = StringIO()
        self.setFormatter(logging.Formatter("%(message)s"))

    def get_output(self):
        """Get the captured output."""
        return self.stream.getvalue()

    def reset(self):
        """Reset the capture buffer."""
        self.stream = StringIO()


@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging capture for tests."""
    # Create and configure handler
    handler = LogCaptureHandler()
    logger = logging.getLogger("orka.cli.memory.watch")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Yield the handler for test use
    yield handler

    # Cleanup
    logger.removeHandler(handler)
    handler.close()


class TestMemoryWatch:
    """Test cases for memory watch functionality."""

    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_success(self, mock_tui_class):
        """Test memory_watch with successful TUI interface."""
        mock_tui = MagicMock()
        mock_tui.run.return_value = 0
        mock_tui_class.return_value = mock_tui

        args = Namespace(fallback=False)
        result = memory_watch(args)

        assert result == 0
        mock_tui_class.assert_called_once()
        mock_tui.run.assert_called_once_with(args)

    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_import_error(self, mock_tui_class, setup_logging):
        """Test memory_watch with TUI import error falling back to basic."""
        mock_tui_class.side_effect = ImportError("No TUI module")

        args = Namespace(fallback=False, backend="redis")

        with patch("orka.cli.memory.watch._memory_watch_fallback") as mock_fallback:
            mock_fallback.return_value = 0
            result = memory_watch(args)

            assert result == 0
            mock_fallback.assert_called_once_with(args)
            output = setup_logging.get_output()
            assert "Could not import TUI interface" in output
            assert "Falling back to basic terminal interface" in output

    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_runtime_error(self, mock_tui_class, setup_logging):
        """Test memory_watch with TUI runtime error."""
        mock_tui = MagicMock()
        mock_tui.run.side_effect = Exception("Runtime error")
        mock_tui_class.return_value = mock_tui

        args = Namespace(fallback=False)

        with patch("traceback.print_exc") as mock_traceback:
            result = memory_watch(args)

            assert result == 1
            output = setup_logging.get_output()
            assert "Error starting memory watch" in output
            mock_traceback.assert_called_once()

    def test_memory_watch_explicit_fallback(self, setup_logging):
        """Test memory_watch with explicit fallback request."""
        args = Namespace(fallback=True)

        with patch("orka.cli.memory.watch._memory_watch_fallback") as mock_fallback:
            mock_fallback.return_value = 0
            result = memory_watch(args)

            assert result == 0
            mock_fallback.assert_called_once_with(args)
            output = setup_logging.get_output()
            assert "Using basic terminal interface as requested" in output

    def test_memory_watch_fallback_success(self, setup_logging):
        """Test _memory_watch_fallback with successful execution."""
        args = Namespace(backend="redis", json=False)

        with (
            patch("orka.cli.memory.watch.create_memory_logger") as mock_create,
            patch("orka.cli.memory.watch._memory_watch_display") as mock_display,
            patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6380/0"}),
        ):
            mock_memory = MagicMock()
            mock_create.return_value = mock_memory
            mock_display.return_value = 0

            result = _memory_watch_fallback(args)

            assert result == 0
            mock_create.assert_called_once_with(
                backend="redis",
                redis_url="redis://localhost:6380/0",
            )
            mock_display.assert_called_once_with(mock_memory, "redis", args)
            output = setup_logging.get_output()
            assert "Using Redis backend" in output

    def test_memory_watch_fallback_redisstack_url(self, setup_logging):
        """Test _memory_watch_fallback with redisstack backend uses correct URL."""
        args = Namespace(backend="redisstack", json=False)

        with (
            patch("orka.cli.memory.watch.create_memory_logger") as mock_create,
            patch("orka.cli.memory.watch._memory_watch_display") as mock_display,
            patch.dict(os.environ, {}, clear=True),
        ):
            mock_memory = MagicMock()
            mock_create.return_value = mock_memory
            mock_display.return_value = 0

            result = _memory_watch_fallback(args)

            assert result == 0
            mock_create.assert_called_once_with(
                backend="redisstack",
                redis_url="redis://localhost:6380/0",  # All backends use the same port now
            )
            output = setup_logging.get_output()
            assert "Using Redisstack backend" in output

    def test_memory_watch_fallback_default_backend(self, setup_logging):
        """Test _memory_watch_fallback with default backend from environment."""
        args = Namespace(json=False)  # No backend specified

        with (
            patch("orka.cli.memory.watch.create_memory_logger") as mock_create,
            patch("orka.cli.memory.watch._memory_watch_display") as mock_display,
            patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "redisstack"}, clear=True),
        ):
            mock_memory = MagicMock()
            mock_create.return_value = mock_memory
            mock_display.return_value = 0

            result = _memory_watch_fallback(args)

            assert result == 0
            mock_create.assert_called_once_with(
                backend="redisstack",
                redis_url="redis://localhost:6380/0",
            )
            output = setup_logging.get_output()
            assert "Using Redisstack backend" in output

    def test_memory_watch_fallback_json_mode(self, setup_logging):
        """Test _memory_watch_fallback with JSON mode."""
        args = Namespace(backend="redis", json=True)

        with (
            patch("orka.cli.memory.watch.create_memory_logger") as mock_create,
            patch("orka.cli.memory.watch._memory_watch_json") as mock_json,
        ):
            mock_memory = MagicMock()
            mock_create.return_value = mock_memory
            mock_json.return_value = 0

            result = _memory_watch_fallback(args)

            assert result == 0
            mock_json.assert_called_once_with(mock_memory, "redis", args)
            output = setup_logging.get_output()
            assert "Using Redis backend" in output
            assert "Using JSON output mode" in output

    def test_memory_watch_fallback_error(self, setup_logging):
        """Test _memory_watch_fallback with error handling."""
        args = Namespace(backend="redis")

        with patch("orka.cli.memory.watch.create_memory_logger") as mock_create:
            mock_create.side_effect = Exception("Connection failed")

            result = _memory_watch_fallback(args)

            assert result == 1
            output = setup_logging.get_output()
            assert "Error in fallback memory watch" in output
            assert "Connection failed" in output

    def test_memory_watch_json_basic_output(self, setup_logging):
        """Test _memory_watch_json basic output functionality."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {
            "total_entries": 100,
            "timestamp": "2023-01-01T00:00:00Z",
        }

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            # Mock sleep to raise KeyboardInterrupt after first iteration
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            # Parse JSON output
            json_output = json.loads(output)
            assert json_output["backend"] == "redis"
            assert json_output["stats"]["total_entries"] == 100
            assert json_output["timestamp"] == "2023-01-01T00:00:00Z"

    def test_memory_watch_json_with_recent_memories(self, setup_logging):
        """Test _memory_watch_json with recent memories."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 50}
        mock_memory.get_recent_stored_memories.return_value = [
            {"content": "memory1", "node_id": "node1"},
            {"content": "memory2", "node_id": "node2"},
        ]

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            json_output = json.loads(output)
            assert len(json_output["recent_stored_memories"]) == 2
            assert json_output["recent_stored_memories"][0]["content"] == "memory1"

    def test_memory_watch_json_fallback_to_search(self, setup_logging):
        """Test _memory_watch_json fallback to search_memories."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 50}
        # Remove get_recent_stored_memories method
        del mock_memory.get_recent_stored_memories
        mock_memory.search_memories.return_value = [
            {"content": "searched_memory", "node_id": "search_node"},
        ]

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            json_output = json.loads(output)
            assert json_output["recent_stored_memories"][0]["content"] == "searched_memory"
            mock_memory.search_memories.assert_called_once_with(
                query=" ",
                num_results=5,
                log_type="memory",
            )

    def test_memory_watch_json_no_recent_memories_method(self, setup_logging):
        """Test _memory_watch_json when no recent memories method exists."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 50}
        # Remove both methods
        del mock_memory.get_recent_stored_memories
        del mock_memory.search_memories

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            json_output = json.loads(output)
            assert json_output["recent_stored_memories"] == []

    def test_memory_watch_json_recent_memories_error(self, setup_logging):
        """Test _memory_watch_json with recent memories error."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 50}
        mock_memory.get_recent_stored_memories.side_effect = Exception("Memory error")

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            json_output = json.loads(output)
            assert json_output["recent_memories_error"] == "Memory error"

    def test_memory_watch_json_redisstack_performance(self, setup_logging):
        """Test _memory_watch_json with RedisStack performance metrics."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 50}
        mock_memory.get_performance_metrics.return_value = {"cpu_usage": 20.5}

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_json(mock_memory, "redisstack", args)

            assert result == 0
            output = setup_logging.get_output()

            json_output = json.loads(output)
            assert json_output["performance"]["cpu_usage"] == 20.5

    def test_memory_watch_json_stats_error(self, setup_logging):
        """Test _memory_watch_json with stats error."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.side_effect = Exception("Stats error")

        args = Namespace(interval=1)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt()]  # One error, then exit

            result = _memory_watch_json(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()
            assert "Stats error" in output

    def test_memory_watch_display_basic_output(self, setup_logging):
        """Test _memory_watch_display basic output functionality."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {
            "total_entries": 100,
            "active_entries": 80,
            "expired_entries": 20,
            "stored_memories": 50,
            "orchestration_logs": 30,
        }
        mock_memory.get_recent_stored_memories.return_value = [
            {"content": "test memory", "node_id": "test_node"},
        ]

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "OrKa Memory Watch" in output
            assert "Backend: redis" in output
            assert "Total Entries: 100" in output
            assert "Active Entries: 80" in output
            assert "test memory" in output
            assert "test_node" in output

    def test_memory_watch_display_clear_screen(self, setup_logging):
        """Test _memory_watch_display with screen clearing."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 0}
        mock_memory.get_recent_stored_memories.return_value = []

        args = Namespace(interval=1)  # no_clear not set

        with (
            patch("os.system") as mock_system,
            patch("os.name", "nt"),  # Windows
            patch("time.sleep") as mock_sleep,
        ):
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            mock_system.assert_called_once_with("cls")
            output = setup_logging.get_output()
            assert "OrKa Memory Watch" in output

    def test_memory_watch_display_clear_screen_unix(self, setup_logging):
        """Test _memory_watch_display with Unix screen clearing."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 0}
        mock_memory.get_recent_stored_memories.return_value = []

        args = Namespace(interval=1)

        with (
            patch("os.system") as mock_system,
            patch("os.name", "posix"),  # Unix
            patch("time.sleep") as mock_sleep,
        ):
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            mock_system.assert_called_once_with("clear")
            output = setup_logging.get_output()
            assert "OrKa Memory Watch" in output

    def test_memory_watch_display_handle_bytes_content(self, setup_logging):
        """Test _memory_watch_display handles bytes content correctly."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 1}
        mock_memory.get_recent_stored_memories.return_value = [
            {"content": b"byte content", "node_id": b"byte_node"},
        ]

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "byte content" in output
            assert "byte_node" in output

    def test_memory_watch_display_truncate_long_content(self, setup_logging):
        """Test _memory_watch_display truncates long content."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 1}
        long_content = "a" * 150  # Content longer than 100 chars
        mock_memory.get_recent_stored_memories.return_value = [
            {"content": long_content, "node_id": "long_node"},
        ]

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "..." in output  # Truncation indicator
            assert long_content not in output  # Full content not shown

    def test_memory_watch_display_fallback_to_search(self, setup_logging):
        """Test _memory_watch_display fallback to search_memories."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 1}
        # Remove get_recent_stored_memories method
        del mock_memory.get_recent_stored_memories
        mock_memory.search_memories.return_value = [
            {"content": "searched content", "node_id": "search_node"},
        ]

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "searched content" in output
            mock_memory.search_memories.assert_called_once_with(
                query=" ",
                num_results=5,
                log_type="memory",
            )

    def test_memory_watch_display_no_memories(self, setup_logging):
        """Test _memory_watch_display when no memories are found."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 0}
        mock_memory.get_recent_stored_memories.return_value = []

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "No stored memories found" in output

    def test_memory_watch_display_memory_error(self, setup_logging):
        """Test _memory_watch_display handles memory retrieval errors."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.return_value = {"total_entries": 1}
        mock_memory.get_recent_stored_memories.side_effect = Exception("Memory retrieval error")

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = KeyboardInterrupt()

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()

            assert "Error retrieving memories" in output
            assert "Memory retrieval error" in output

    def test_memory_watch_display_stats_error(self, setup_logging):
        """Test _memory_watch_display handles stats errors."""
        mock_memory = MagicMock()
        mock_memory.get_memory_stats.side_effect = Exception("Stats error")

        args = Namespace(interval=1, no_clear=True)

        with patch("time.sleep") as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt()]  # One error, then exit

            result = _memory_watch_display(mock_memory, "redis", args)

            assert result == 0
            output = setup_logging.get_output()
            assert "Error in memory watch: Stats error" in output
