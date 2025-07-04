# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Test CLI Memory Commands
========================

Tests for memory management CLI commands including statistics, cleanup, and configuration.
"""

import json
import os
from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock, patch

from orka.cli.memory.commands import memory_cleanup, memory_configure, memory_stats


class TestMemoryStats:
    """Test cases for memory_stats command."""

    def test_memory_stats_success(self):
        """Test memory_stats with successful execution."""
        args = Namespace(backend="redis", json=False)

        mock_memory = MagicMock()
        mock_stats = {
            "backend": "redis",
            "decay_enabled": True,
            "total_streams": 10,
            "total_entries": 100,
            "expired_entries": 5,
        }
        mock_memory.get_memory_stats.return_value = mock_stats

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_stats(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "=== OrKa Memory Statistics ===" in output
            assert "Backend: redis" in output
            assert "Total Entries: 100" in output

    def test_memory_stats_json_format(self):
        """Test memory_stats with JSON output."""
        args = Namespace(backend="redis", json=True)

        mock_memory = MagicMock()
        mock_stats = {"backend": "redis", "total_entries": 50}
        mock_memory.get_memory_stats.return_value = mock_stats

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_stats(args)

            assert result == 0
            output = mock_stdout.getvalue()
            json_output = json.loads(output)
            assert json_output["stats"]["backend"] == "redis"
            assert json_output["stats"]["total_entries"] == 50

    def test_memory_stats_error(self):
        """Test memory_stats with error handling."""
        args = Namespace(backend="redis", json=False)

        with (
            patch("orka.cli.memory.commands.create_memory_logger") as mock_create,
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            mock_create.side_effect = Exception("Connection failed")

            result = memory_stats(args)

            assert result == 1
            stderr_output = mock_stderr.getvalue()
            assert "Error getting memory statistics: Connection failed" in stderr_output

    def test_memory_stats_comprehensive_output(self):
        """Test memory_stats with comprehensive stats output."""
        args = Namespace(backend="redis", json=False)

        mock_memory = MagicMock()
        mock_stats = {
            "backend": "redis",
            "decay_enabled": True,
            "total_streams": 10,
            "total_entries": 100,
            "expired_entries": 5,
            "entries_by_type": {"event": 50, "decision": 30, "output": 20},
            "entries_by_memory_type": {"short_term": 70, "long_term": 30},
            "entries_by_category": {"planning": 40, "execution": 35, "monitoring": 25},
            "decay_config": {
                "short_term_hours": 1.0,
                "long_term_hours": 24.0,
                "check_interval_minutes": 30,
                "last_decay_check": "2024-01-01T12:00:00Z",
            },
        }
        mock_memory.get_memory_stats.return_value = mock_stats

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_stats(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "Entries by Type:" in output
            assert "event: 50" in output
            assert "Entries by Memory Type:" in output
            assert "short_term: 70" in output
            assert "Entries by Category:" in output
            assert "planning: 40" in output
            assert "Decay Configuration:" in output
            assert "Short-term retention: 1.0h" in output
            assert "Last cleanup: 2024-01-01T12:00:00Z" in output

    def test_memory_stats_no_backend_args(self):
        """Test memory_stats with no backend attribute in args."""
        args = Namespace(json=False)  # No backend attribute

        mock_memory = MagicMock()
        mock_stats = {"backend": "redisstack", "total_entries": 75}
        mock_memory.get_memory_stats.return_value = mock_stats

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
            patch.dict(os.environ, {"ORKA_MEMORY_BACKEND": "redisstack"}),
        ):
            result = memory_stats(args)

            assert result == 0

    def test_memory_stats_redisstack_fallback(self):
        """Test memory_stats with redisstack fallback to redis."""
        args = Namespace(backend="redisstack", json=False)

        mock_memory = MagicMock()
        mock_stats = {"backend": "redis", "total_entries": 25}
        mock_memory.get_memory_stats.return_value = mock_stats

        with (
            patch("orka.cli.memory.commands.create_memory_logger") as mock_create,
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            # First call raises ImportError, second succeeds
            mock_create.side_effect = [ImportError("RedisStack not available"), mock_memory]

            result = memory_stats(args)

            assert result == 0
            stderr_output = mock_stderr.getvalue()
            assert "RedisStack not available" in stderr_output
            assert "falling back to Redis" in stderr_output
            assert mock_create.call_count == 2


class TestMemoryCleanup:
    """Test cases for memory_cleanup command."""

    def test_memory_cleanup_success(self):
        """Test memory_cleanup with successful execution."""
        args = Namespace(backend="redis", dry_run=False, json=False, verbose=False)

        mock_memory = MagicMock()
        mock_result = {
            "status": "completed",
            "deleted_count": 15,
            "streams_processed": 5,
            "total_entries_checked": 100,
        }
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "=== Memory Cleanup ===" in output
            assert "Deleted Entries: 15" in output

    def test_memory_cleanup_dry_run(self):
        """Test memory_cleanup with dry run mode."""
        args = Namespace(backend="redis", dry_run=True, json=False, verbose=False)

        mock_memory = MagicMock()
        mock_result = {"status": "dry_run", "deleted_count": 0}
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "=== Dry Run: Memory Cleanup Preview ===" in output

    def test_memory_cleanup_json_output(self):
        """Test memory_cleanup with JSON output."""
        args = Namespace(backend="redis", dry_run=False, json=True, verbose=False)

        mock_memory = MagicMock()
        mock_result = {"status": "completed", "deleted_count": 10}
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            # JSON output should contain cleanup result info
            assert "cleanup_result" in output

    def test_memory_cleanup_with_errors(self):
        """Test memory_cleanup with error count."""
        args = Namespace(backend="redis", dry_run=False, json=False, verbose=False)

        mock_memory = MagicMock()
        mock_result = {
            "status": "completed",
            "deleted_count": 5,
            "error_count": 2,
            "duration_seconds": 3.5,
        }
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "Errors: 2" in output
            assert "Duration: 3.50s" in output

    def test_memory_cleanup_verbose(self):
        """Test memory_cleanup with verbose output."""
        args = Namespace(backend="redis", dry_run=False, json=False, verbose=True)

        mock_memory = MagicMock()
        mock_result = {
            "status": "completed",
            "deleted_count": 3,
            "deleted_entries": [
                {"agent_id": "agent1", "event_type": "event", "stream": "stream1"},
                {"agent_id": "agent2", "event_type": "decision", "stream": "stream2"},
                {"agent_id": "agent3", "event_type": "output"},
            ],
        }
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "Deleted Entries:" in output
            assert "stream1: agent1 - event" in output
            assert "agent3 - output" in output

    def test_memory_cleanup_verbose_many_entries(self):
        """Test memory_cleanup with verbose output and many entries."""
        args = Namespace(backend="redis", dry_run=False, json=False, verbose=True)

        mock_memory = MagicMock()
        deleted_entries = [
            {"agent_id": f"agent{i}", "event_type": "event", "stream": f"stream{i}"}
            for i in range(15)
        ]
        mock_result = {
            "status": "completed",
            "deleted_count": 15,
            "deleted_entries": deleted_entries,
        }
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_cleanup(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "Deleted Entries:" in output
            assert "... and 5 more" in output

    def test_memory_cleanup_fallback_to_redis(self):
        """Test memory_cleanup with fallback from redisstack to redis."""
        args = Namespace(backend="redisstack", dry_run=False, json=False, verbose=False)

        mock_memory = MagicMock()
        mock_result = {"status": "completed", "deleted_count": 5}
        mock_memory.cleanup_expired_memories.return_value = mock_result

        with (
            patch("orka.cli.memory.commands.create_memory_logger") as mock_create,
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            mock_create.side_effect = [ImportError("RedisStack not available"), mock_memory]

            result = memory_cleanup(args)

            assert result == 0
            stderr_output = mock_stderr.getvalue()
            assert "RedisStack not available" in stderr_output
            assert "falling back to Redis" in stderr_output

    def test_memory_cleanup_error_handling(self):
        """Test memory_cleanup with error handling."""
        args = Namespace(backend="redis", dry_run=False, json=False, verbose=False)

        with (
            patch("orka.cli.memory.commands.create_memory_logger") as mock_create,
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
        ):
            mock_create.side_effect = Exception("Connection failed")

            result = memory_cleanup(args)

            assert result == 1
            stderr_output = mock_stderr.getvalue()
            assert "Error during memory cleanup: Connection failed" in stderr_output


class TestMemoryConfigure:
    """Test cases for memory_configure command."""

    def test_memory_configure_success(self):
        """Test memory_configure with successful execution."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.get_memory_stats.return_value = {"total_entries": 100}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "=== OrKa Memory Configuration Test ===" in output
            assert "Backend: redis" in output

    def test_memory_configure_redis_detailed(self):
        """Test memory_configure with Redis backend detailed tests."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = {
            "enabled": True,
            "default_short_term_hours": 1.0,
            "default_long_term_hours": 24.0,
            "check_interval_minutes": 30,
        }
        mock_memory.client = MagicMock()
        mock_memory.client.ping.return_value = True
        mock_memory.cleanup_expired_memories.return_value = {"total_entries_checked": 50}
        mock_memory.get_memory_stats.return_value = {
            "total_entries": 100,
            "entries_by_memory_type": {"short_term": 70},
        }

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "✅ Decay Config: Enabled" in output
            assert "🔧 Redis-Specific Tests:" in output
            assert "✅ Redis Connection: Active" in output
            assert "✅ Decay Cleanup: Available" in output
            assert "Checked: 50 entries" in output

    def test_memory_configure_redisstack_detailed(self):
        """Test memory_configure with RedisStack backend detailed tests."""
        args = Namespace(backend="redisstack")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": False}
        mock_memory.client = MagicMock()
        mock_index_info = {"num_docs": 150, "indexing": True}
        mock_memory.client.ft.return_value.info.return_value = mock_index_info
        mock_memory.get_memory_stats.return_value = {"total_entries": 150, "decay_enabled": False}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "✅ Decay Config: Disabled" in output
            assert "🔍 RedisStack-Specific Tests:" in output
            assert "✅ HNSW Index: Available" in output
            assert "Documents: 150" in output
            assert "Indexing: Yes" in output

    def test_memory_configure_kafka_detailed(self):
        """Test memory_configure with Kafka backend detailed tests."""
        args = Namespace(backend="kafka")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.redis_url = "redis://localhost:6379/0"
        mock_memory.main_topic = "orka_memory_topic"
        mock_memory.get_memory_stats.return_value = {"total_entries": 75}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "📡 Kafka-Specific Tests:" in output
            assert "✅ Hybrid Backend: Kafka + Redis" in output
            assert "Kafka topic: orka_memory_topic" in output

    def test_memory_configure_no_decay_config(self):
        """Test memory_configure with no decay config."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = None
        mock_memory.get_memory_stats.return_value = {"total_entries": 25}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            # This test case causes an error due to None decay_config
            assert result == 1
            output = mock_stdout.getvalue()
            assert "Backend: redis" in output

    def test_memory_configure_redis_connection_error(self):
        """Test memory_configure with Redis connection error."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.client = MagicMock()
        mock_memory.client.ping.side_effect = Exception("Connection refused")
        mock_memory.get_memory_stats.return_value = {"total_entries": 0}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "❌ Redis Connection: Error - Connection refused" in output

    def test_memory_configure_redisstack_index_error(self):
        """Test memory_configure with RedisStack index error."""
        args = Namespace(backend="redisstack")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.client = MagicMock()
        mock_memory.client.ft.return_value.info.side_effect = Exception("Index not found")
        mock_memory.get_memory_stats.return_value = {"total_entries": 0}

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "❌ HNSW Index: Not available - Index not found" in output

    def test_memory_configure_memory_stats_error(self):
        """Test memory_configure with memory stats error."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.get_memory_stats.side_effect = Exception("Stats unavailable")

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "❌ Memory Stats: Error - Stats unavailable" in output

    def test_memory_configure_configuration_test_error(self):
        """Test memory_configure with configuration test error."""
        args = Namespace(backend="redis")

        mock_memory = MagicMock()
        mock_memory.decay_config = {"enabled": True}
        mock_memory.get_memory_stats.side_effect = Exception("Configuration test failed")

        with (
            patch("orka.cli.memory.commands.create_memory_logger", return_value=mock_memory),
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            result = memory_configure(args)

            # Memory stats error doesn't cause function to return 1
            assert result == 0
            output = mock_stdout.getvalue()
            assert "Configuration test failed" in output

    def test_memory_configure_create_memory_logger_error(self):
        """Test memory_configure with create_memory_logger error."""
        args = Namespace(backend="redis")

        with (
            patch("orka.cli.memory.commands.create_memory_logger") as mock_create,
            patch("sys.stdout", new_callable=StringIO) as mock_stdout,
        ):
            mock_create.side_effect = Exception("Logger creation failed")

            result = memory_configure(args)

            assert result == 1
            stdout_output = mock_stdout.getvalue()
            assert "Configuration test failed" in stdout_output
