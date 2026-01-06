import pytest
from unittest.mock import patch, MagicMock
import json
import os
import sys

from orka.cli.memory.watch import memory_watch, _memory_watch_fallback, _memory_watch_json, _memory_watch_display

@pytest.fixture
def mock_memory_logger():
    """Fixture for a mocked memory logger instance with watch-specific methods."""
    mock_logger = MagicMock()
    mock_logger.get_memory_stats.return_value = {
        "timestamp": "2025-11-15T12:00:00Z",
        "backend": "redisstack",
        "total_entries": 100,
        "active_entries": 90,
        "expired_entries": 10,
        "stored_memories": 50,
        "orchestration_logs": 50,
    }
    mock_logger.get_recent_stored_memories.return_value = [
        {"node_id": "node1", "content": "content 1"},
        {"node_id": "node2", "content": "content 2"},
    ]
    mock_logger.search_memories.return_value = [
        {"node_id": "nodeA", "content": "search content A"},
        {"node_id": "nodeB", "content": "search content B"},
    ]
    mock_logger.get_performance_metrics.return_value = {"cpu_usage": 0.5, "memory_usage": 0.7}
    return mock_logger

@pytest.fixture
def mock_create_memory_logger(mock_memory_logger):
    """Fixture for mocking create_memory_logger function."""
    with patch("orka.cli.memory.watch.create_memory_logger") as mock_func:
        mock_func.return_value = mock_memory_logger
        yield mock_func

@pytest.fixture
def mock_args():
    """Fixture for a mocked args object."""
    class MockArgs:
        def __init__(self):
            self.fallback = False
            self.json = False
            self.backend = None
            self.interval = 0.01  # Small interval for quick tests
            self.no_clear = False

    return MockArgs()

@pytest.fixture
def mock_time_sleep():
    """Fixture to mock time.sleep."""
    with patch("time.sleep") as mock_func:
        yield mock_func

@pytest.fixture
def mock_os_system():
    """Fixture to mock os.system."""
    with patch("os.system") as mock_func:
        yield mock_func

@pytest.fixture
def mock_logger():
    """Fixture to mock the logger."""
    with patch("orka.cli.memory.watch.logger") as mock_func:
        yield mock_func

class TestMemoryWatchFallback:
    def test_memory_watch_fallback_default_display(self, mock_logger, mock_create_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        # Simulate running for 2 iterations then KeyboardInterrupt
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        mock_args.interval = 0.01

        result = _memory_watch_fallback(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once()
        mock_logger.info.assert_any_call("Using Redisstack backend")
        assert mock_os_system.call_count == 2
        assert mock_time_sleep.call_count == 2

    def test_memory_watch_fallback_json_mode(self, mock_logger, mock_create_memory_logger, mock_args, mock_time_sleep):
        # Simulate running for 2 iterations then KeyboardInterrupt
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        mock_args.json = True
        mock_args.interval = 0.01

        result = _memory_watch_fallback(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once()
        mock_logger.info.assert_any_call("Using Redisstack backend")
        mock_logger.info.assert_any_call("Using JSON output mode")
        assert mock_time_sleep.call_count == 2
        # Check if JSON output was logged
        json_output_calls = [call_args for call_args in mock_logger.info.call_args_list if call_args[0][0].startswith('{')]
        assert len(json_output_calls) == 2
        output_json = json.loads(json_output_calls[0].args[0])
        assert "stats" in output_json
        assert output_json["backend"] == "redisstack"

    def test_memory_watch_fallback_exception(self, mock_logger, mock_create_memory_logger, mock_args):
        mock_create_memory_logger.side_effect = Exception("Connection error")
        result = _memory_watch_fallback(mock_args)
        assert result == 1
        mock_logger.error.assert_called_once_with("Error in fallback memory watch: Connection error")

class TestMemoryWatchJson:
    def test_memory_watch_json_basic(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep):
        # Simulate running for 2 iterations then KeyboardInterrupt
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        mock_args.interval = 0.01

        result = _memory_watch_json(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_memory_logger.get_memory_stats.call_count == 2
        assert mock_memory_logger.get_recent_stored_memories.call_count == 2
        assert mock_memory_logger.get_performance_metrics.call_count == 2
        assert mock_time_sleep.call_count == 2
        # Check if JSON output was logged
        json_output_calls = [call_args for call_args in mock_logger.info.call_args_list if call_args[0][0].startswith('{')]
        assert len(json_output_calls) == 2
        output_json = json.loads(json_output_calls[0][0][0])
        assert "stats" in output_json
        assert "recent_stored_memories" in output_json
        assert "performance" in output_json

    def test_memory_watch_json_keyboard_interrupt(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep):
        mock_time_sleep.side_effect = KeyboardInterrupt
        result = _memory_watch_json(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_memory_logger.get_memory_stats.assert_called_once()
        mock_time_sleep.assert_called_once()

    def test_memory_watch_json_stats_error(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep):
        mock_memory_logger.get_memory_stats.side_effect = Exception("Stats error")
        mock_time_sleep.side_effect = [None, KeyboardInterrupt] # Allow one error then exit
        result = _memory_watch_json(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_logger.error.call_count == 2
        called_args, _ = mock_logger.error.call_args
        error_json = json.loads(called_args[0])
        assert error_json["error"] == "Stats error"

    def test_memory_watch_json_recent_memories_error(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep):
        mock_memory_logger.get_recent_stored_memories.side_effect = Exception("Recent memories error")
        mock_time_sleep.side_effect = [None, KeyboardInterrupt] # Allow one error then exit
        result = _memory_watch_json(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_logger.info.call_count == 2 # One for each loop iteration
        called_args, _ = mock_logger.info.call_args
        output_json = json.loads(called_args[0])
        assert output_json["recent_memories_error"] == "Recent memories error"

    def test_memory_watch_json_no_recent_memories_method(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep):
        del mock_memory_logger.get_recent_stored_memories
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_json(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_memory_logger.search_memories.call_count == 2

class TestMemoryWatchDisplay:
    def test_memory_watch_display_basic(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        # Simulate running for 2 iterations then KeyboardInterrupt
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        mock_args.interval = 0.01

        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_os_system.call_count == 2
        assert mock_memory_logger.get_memory_stats.call_count == 2
        assert mock_memory_logger.get_recent_stored_memories.call_count == 2
        mock_logger.info.assert_any_call("=== OrKa Memory Watch ===")
        mock_logger.info.assert_any_call("[STATS] Memory Statistics:")
        mock_logger.info.assert_any_call("\n[AI] Recent Stored Memories:")
        mock_logger.info.assert_any_call("   [1] node1: content 1")
        assert mock_time_sleep.call_count == 2

    def test_memory_watch_display_no_clear(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        mock_args.no_clear = True
        mock_args.interval = 0.01

        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_os_system.assert_not_called()
        assert mock_time_sleep.call_count == 2

    def test_memory_watch_display_keyboard_interrupt(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        mock_time_sleep.side_effect = KeyboardInterrupt
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_memory_logger.get_memory_stats.assert_called_once()
        mock_time_sleep.assert_called_once()

    def test_memory_watch_display_stats_error(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        mock_memory_logger.get_memory_stats.side_effect = Exception("Stats error")
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("[FAIL] Error in memory watch: Stats error, file:" + str(sys.stderr))

    def test_memory_watch_display_recent_memories_error(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        mock_memory_logger.get_recent_stored_memories.side_effect = Exception("Recent memories error")
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("   Error retrieving memories: Recent memories error")

    def test_memory_watch_display_no_recent_memories_method(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        del mock_memory_logger.get_recent_stored_memories
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        assert mock_memory_logger.search_memories.call_count == 2

    def test_memory_watch_display_no_stored_memories(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        mock_memory_logger.get_recent_stored_memories.return_value = []
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_logger.info.assert_any_call("   No stored memories found")

    def test_memory_watch_display_long_content_truncation(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        long_content = "a" * 150
        mock_memory_logger.get_recent_stored_memories.return_value = [
            {"node_id": "node1", "content": long_content}
        ]
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        expected_content = long_content[:100] + "..."
        mock_logger.info.assert_any_call(f"   [1] node1: {expected_content}")

    def test_memory_watch_display_bytes_content_decoding(self, mock_logger, mock_memory_logger, mock_args, mock_time_sleep, mock_os_system):
        bytes_content = b"byte content"
        mock_memory_logger.get_recent_stored_memories.return_value = [
            {"node_id": b"node1_bytes", "content": bytes_content}
        ]
        mock_time_sleep.side_effect = [None, KeyboardInterrupt]
        result = _memory_watch_display(mock_memory_logger, "redisstack", mock_args)
        assert result == 0
        mock_logger.info.assert_any_call("   [1] node1_bytes: byte content")

class TestMemoryWatchMain:
    @patch("orka.cli.memory.watch._memory_watch_fallback")
    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_success(self, mock_tui_interface, mock_fallback, mock_args):
        mock_instance = mock_tui_interface.return_value
        mock_instance.run.return_value = 0
        result = memory_watch(mock_args)
        assert result == 0
        mock_tui_interface.assert_called_once()
        mock_instance.run.assert_called_once_with(mock_args)
        mock_fallback.assert_not_called()

    @patch("orka.cli.memory.watch._memory_watch_fallback")
    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_import_error_fallback(self, mock_tui_interface, mock_fallback, mock_args, mock_logger):
        mock_tui_interface.side_effect = ImportError("Textual not found")
        mock_fallback.return_value = 0
        result = memory_watch(mock_args)
        assert result == 0
        mock_tui_interface.assert_called_once()
        mock_fallback.assert_called_once_with(mock_args)
        mock_logger.error.assert_any_call("Could not import TUI interface: Textual not found")
        mock_logger.info.assert_any_call("Falling back to basic terminal interface...")

    @patch("orka.cli.memory.watch._memory_watch_fallback")
    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_tui_general_exception_fallback(self, mock_tui_interface, mock_fallback, mock_args, mock_logger):
        mock_instance = mock_tui_interface.return_value
        mock_instance.run.side_effect = Exception("TUI runtime error")
        mock_fallback.return_value = 0
        result = memory_watch(mock_args)
        assert result == 1
        mock_tui_interface.assert_called_once()
        mock_instance.run.assert_called_once_with(mock_args)
        mock_logger.error.assert_any_call("Error starting memory watch: TUI runtime error")

    @patch("orka.cli.memory.watch._memory_watch_fallback")
    @patch("orka.tui_interface.ModernTUIInterface")
    def test_memory_watch_explicit_fallback(self, mock_tui_interface, mock_fallback, mock_args, mock_logger):
        mock_args.fallback = True
        mock_fallback.return_value = 0
        result = memory_watch(mock_args)
        assert result == 0
        mock_tui_interface.assert_not_called()
        mock_fallback.assert_called_once_with(mock_args)
        mock_logger.info.assert_any_call("Using basic terminal interface as requested")
