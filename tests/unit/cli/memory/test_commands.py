import pytest
from unittest.mock import patch, MagicMock
import json
import os

from orka.cli.memory.commands import memory_stats, memory_cleanup, memory_configure

@pytest.fixture
def mock_memory_logger():
    """Fixture for a mocked memory logger instance."""
    mock_logger = MagicMock()
    mock_logger.get_memory_stats.return_value = {
        "backend": "redisstack",
        "decay_enabled": True,
        "total_streams": 5,
        "total_entries": 100,
        "expired_entries": 10,
        "entries_by_type": {"event1": 50, "event2": 50},
        "entries_by_memory_type": {"short_term": 70, "long_term": 30},
        "entries_by_category": {"category1": 60, "category2": 40},
        "decay_config": {
            "short_term_hours": 1.0,
            "long_term_hours": 24.0,
            "check_interval_minutes": 30,
            "last_decay_check": "2025-11-15T10:00:00Z",
        },
    }
    mock_logger.cleanup_expired_memories.return_value = {
        "status": "completed",
        "deleted_count": 5,
        "streams_processed": 2,
        "total_entries_checked": 50,
        "error_count": 0,
        "duration_seconds": 0.5,
        "deleted_entries": [
            {"stream": "stream1", "agent_id": "agentA", "event_type": "typeX"},
            {"stream": "stream2", "agent_id": "agentB", "event_type": "typeY"},
        ],
    }
    mock_logger.decay_config = {
        "enabled": True,
        "default_short_term_hours": 1.0,
        "default_long_term_hours": 24.0,
        "check_interval_minutes": 30,
    }
    mock_logger.client = MagicMock()
    mock_logger.client.ft.return_value.info.return_value = {"num_docs": 10, "indexing": False}
    mock_logger.client.ping.return_value = True
    return mock_logger

@pytest.fixture
def mock_create_memory_logger(mock_memory_logger):
    """Fixture for mocking create_memory_logger function."""
    with patch("orka.cli.memory.commands.create_memory_logger") as mock_func:
        mock_func.return_value = mock_memory_logger
        yield mock_func

@pytest.fixture
def mock_args():
    """Fixture for a mocked args object."""
    class MockArgs:
        def __init__(self):
            self.json = False
            self.backend = None
            self.dry_run = False
            self.verbose = False

    return MockArgs()

class TestMemoryCommands:
    @patch("orka.cli.memory.commands.logger")
    def test_memory_stats_default(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        result = memory_stats(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_memory_logger.get_memory_stats.assert_called_once()
        mock_logger.info.assert_any_call("=== OrKa Memory Statistics ===")
        mock_logger.info.assert_any_call("Backend: redisstack")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_stats_json_output(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.json = True
        result = memory_stats(mock_args)
        assert result == 0
        mock_logger.info.assert_called_once()
        called_args, _ = mock_logger.info.call_args
        output_json = json.loads(called_args[0])
        assert "stats" in output_json
        assert output_json["stats"]["backend"] == "redisstack"

    @patch("orka.cli.memory.commands.logger")
    def test_memory_stats_custom_backend(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redis"
        result = memory_stats(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redis", redis_url="redis://localhost:6380/0")
        mock_logger.info.assert_any_call("Backend: redisstack") # Still redisstack from mock_memory_logger.get_memory_stats.return_value

    @patch("orka.cli.memory.commands.logger")
    def test_memory_stats_import_error_fallback(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_create_memory_logger.side_effect = [ImportError("redisstack not found"), mock_memory_logger]
        result = memory_stats(mock_args)
        assert result == 0
        assert mock_create_memory_logger.call_count == 2
        mock_create_memory_logger.assert_any_call(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_create_memory_logger.assert_any_call(backend="redis", redis_url="redis://localhost:6380/0")
        mock_logger.info.assert_any_call("RedisStack not available (redisstack not found), falling back to Redis")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_stats_general_exception(self, mock_logger, mock_create_memory_logger, mock_args):
        mock_create_memory_logger.side_effect = Exception("Connection error")
        result = memory_stats(mock_args)
        assert result == 1
        mock_logger.error.assert_called_once_with("Error getting memory statistics: Connection error")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_default(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        result = memory_cleanup(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_memory_logger.cleanup_expired_memories.assert_called_once_with(dry_run=False)
        mock_logger.info.assert_any_call("=== Memory Cleanup ===")
        mock_logger.info.assert_any_call("Status: completed")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_dry_run(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.dry_run = True
        result = memory_cleanup(mock_args)
        assert result == 0
        mock_memory_logger.cleanup_expired_memories.assert_called_once_with(dry_run=True)
        mock_logger.info.assert_any_call("=== Dry Run: Memory Cleanup Preview ===")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_json_output(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.json = True
        result = memory_cleanup(mock_args)
        assert result == 0
        output_json = {"cleanup_result": mock_memory_logger.cleanup_expired_memories.return_value}
        mock_logger.info.assert_any_call(json.dumps(output_json, indent=2))
        called_args, _ = mock_logger.info.call_args_list[1] # Get the second call for JSON output
        output_json_logged = json.loads(called_args[0])
        assert "cleanup_result" in output_json_logged
        assert output_json_logged["cleanup_result"]["status"] == "completed"

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_custom_backend(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redis"
        result = memory_cleanup(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redis", redis_url="redis://localhost:6380/0")
        mock_logger.info.assert_any_call("Backend: redis")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_import_error_fallback(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_create_memory_logger.side_effect = [ImportError("redisstack not found"), mock_memory_logger]
        result = memory_cleanup(mock_args)
        assert result == 0
        assert mock_create_memory_logger.call_count == 2
        mock_create_memory_logger.assert_any_call(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_create_memory_logger.assert_any_call(backend="redis", redis_url="redis://localhost:6380/0")
        mock_logger.info.assert_any_call("⚠️ RedisStack not available (redisstack not found), falling back to Redis")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_general_exception(self, mock_logger, mock_create_memory_logger, mock_args):
        mock_create_memory_logger.side_effect = Exception("Cleanup error")
        result = memory_cleanup(mock_args)
        assert result == 1
        mock_logger.error.assert_called_once_with("Error during memory cleanup: Cleanup error")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_cleanup_verbose_output(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.verbose = True
        result = memory_cleanup(mock_args)
        assert result == 0
        mock_logger.info.assert_any_call("\nDeleted Entries:")
        mock_logger.info.assert_any_call("  stream1: agentA - typeX")
        mock_logger.info.assert_any_call("  stream2: agentB - typeY")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_default(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        result = memory_configure(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_logger.info.assert_any_call("=== OrKa Memory Configuration Test ===")
        mock_logger.info.assert_any_call("Backend: redisstack")
        mock_logger.info.assert_any_call("\n🧪 Testing Configuration:")
        mock_logger.info.assert_any_call("✅ Decay Config: Enabled")
        mock_logger.info.assert_any_call("\n✅ Configuration test completed")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_redisstack_specific(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redisstack"
        result = memory_configure(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redisstack", redis_url="redis://localhost:6380/0")
        mock_memory_logger.client.ft.return_value.info.assert_any_call()
        mock_logger.info.assert_any_call("\n🔍 RedisStack-Specific Tests:")
        mock_logger.info.assert_any_call("✅ HNSW Index: Available")
        mock_logger.info.assert_any_call("   Documents: 10")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_redis_specific(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redis"
        result = memory_configure(mock_args)
        assert result == 0
        mock_create_memory_logger.assert_called_once_with(backend="redis", redis_url="redis://localhost:6380/0")
        mock_memory_logger.client.ping.assert_called_once()
        mock_memory_logger.cleanup_expired_memories.assert_called_once_with(dry_run=True)
        mock_logger.info.assert_any_call("\n🔧 Redis-Specific Tests:")
        mock_logger.info.assert_any_call("✅ Redis Connection: Active")
        mock_logger.info.assert_any_call("✅ Decay Cleanup: Available")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_general_exception(self, mock_logger, mock_create_memory_logger, mock_args):
        mock_create_memory_logger.side_effect = Exception("Config error")
        result = memory_configure(mock_args)
        assert result == 1
        mock_logger.error.assert_called_once_with("❌ Configuration test failed: Config error")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_decay_disabled(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_memory_logger.decay_config["enabled"] = False
        result = memory_configure(mock_args)
        assert result == 0
        mock_logger.info.assert_any_call("✅ Decay Config: Disabled")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_hnsw_index_not_available(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redisstack"
        mock_memory_logger.client.ft.return_value.info.side_effect = Exception("Index not found")
        result = memory_configure(mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("❌ HNSW Index: Not available - Index not found")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_redis_connection_error(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redis"
        mock_memory_logger.client.ping.side_effect = Exception("Connection refused")
        result = memory_configure(mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("❌ Redis Connection: Error - Connection refused")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_decay_cleanup_error(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_args.backend = "redis"
        mock_memory_logger.cleanup_expired_memories.side_effect = Exception("Cleanup failed")
        result = memory_configure(mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("❌ Decay Cleanup: Error - Cleanup failed")

    @patch("orka.cli.memory.commands.logger")
    def test_memory_configure_memory_stats_error(self, mock_logger, mock_create_memory_logger, mock_args, mock_memory_logger):
        mock_memory_logger.get_memory_stats.side_effect = Exception("Stats error")
        result = memory_configure(mock_args)
        assert result == 0
        mock_logger.error.assert_any_call("\n❌ Memory Stats: Error - Stats error")
