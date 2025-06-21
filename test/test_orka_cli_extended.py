"""
Extended tests for OrKa CLI functionality to improve coverage.
"""

import json
from unittest.mock import Mock, patch

import pytest

from orka.orka_cli import (
    memory_cleanup,
    memory_stats,
    run_cli_entrypoint,
    setup_logging,
)


class TestOrkaCliSetup:
    """Test CLI setup and utility functions."""

    def test_setup_logging_default(self):
        """Test logging setup with default settings."""
        with patch("logging.basicConfig") as mock_basic_config, patch(
            "logging.getLogger",
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            setup_logging(verbose=False)

            # Verify basicConfig was called with INFO level
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == 20  # logging.INFO
            assert "format" in call_kwargs

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose mode."""
        with patch("logging.basicConfig") as mock_basic_config, patch(
            "logging.getLogger",
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            setup_logging(verbose=True)

            # Verify basicConfig was called with DEBUG level
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs["level"] == 10  # logging.DEBUG

    @pytest.mark.asyncio
    async def test_run_cli_entrypoint_success(self):
        """Test successful CLI entrypoint execution."""
        with patch("orka.orka_cli.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Create an async mock
            async def mock_run(input_text):
                return {"result": "success"}

            mock_orchestrator.run = mock_run

            result = await run_cli_entrypoint(
                config_path="test_config.yml",
                input_text="test input",
                log_to_file=False,
            )

            assert result == {"result": "success"}
            mock_orchestrator_class.assert_called_once_with("test_config.yml")

    @pytest.mark.asyncio
    async def test_run_cli_entrypoint_with_logging(self):
        """Test CLI entrypoint with file logging enabled."""
        with patch("orka.orka_cli.Orchestrator") as mock_orchestrator_class, patch(
            "builtins.open",
            create=True,
        ) as mock_open:
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Create an async mock
            async def mock_run(input_text):
                return {"result": "success"}

            mock_orchestrator.run = mock_run

            # Mock file operations
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = await run_cli_entrypoint(
                config_path="test_config.yml",
                input_text="test input",
                log_to_file=True,
            )

            # Verify file was opened for writing
            mock_open.assert_called_once_with("orka_trace.log", "w")
            mock_file.write.assert_called_once_with("{'result': 'success'}")
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_run_cli_entrypoint_orchestrator_error(self):
        """Test CLI entrypoint when orchestrator raises an exception."""
        with patch("orka.orka_cli.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator_class.side_effect = Exception("Config error")

            with pytest.raises(Exception, match="Config error"):
                await run_cli_entrypoint(
                    config_path="invalid_config.yml",
                    input_text="test input",
                    log_to_file=False,
                )


class TestMemoryStatsCommand:
    """Test memory stats CLI command."""

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_stats_success(self, mock_print, mock_create_logger):
        """Test successful memory stats command."""
        # Mock memory logger with stats
        mock_logger = Mock()
        mock_logger.get_memory_stats.return_value = {
            "backend": "redis",
            "total_entries": 100,
            "total_streams": 5,
            "entries_by_type": {"write": 60, "read": 40},
            "entries_by_agent": {"agent1": 70, "agent2": 30},
        }
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"
        args.json = False

        result = memory_stats(args)

        assert result == 0
        mock_create_logger.assert_called_once_with(backend="redis")
        mock_logger.get_memory_stats.assert_called_once()

        # Verify stats were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("=== OrKa Memory Statistics ===" in call for call in print_calls)
        assert any("Backend: redis" in call for call in print_calls)
        assert any("Total Entries: 100" in call for call in print_calls)

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_stats_json_output(self, mock_print, mock_create_logger):
        """Test memory stats command with JSON output."""
        # Mock memory logger with stats
        mock_logger = Mock()
        stats_data = {
            "backend": "kafka",
            "total_entries": 50,
            "entries_by_type": {"error": 10, "success": 40},
        }
        mock_logger.get_memory_stats.return_value = stats_data
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "kafka"
        args.json = True

        result = memory_stats(args)

        assert result == 0

        # Verify JSON was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        json_output = None
        for call in print_calls:
            try:
                json_output = json.loads(call)
                break
            except (json.JSONDecodeError, TypeError):
                continue

        assert json_output is not None
        assert "stats" in json_output
        stats = json_output["stats"]
        assert stats["backend"] == "kafka"
        assert stats["total_entries"] == 50

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_stats_logger_creation_error(self, mock_print, mock_create_logger):
        """Test memory stats command when logger creation fails."""
        mock_create_logger.side_effect = Exception("Connection failed")

        # Mock args
        args = Mock()
        args.backend = "redis"
        args.json = False

        result = memory_stats(args)

        assert result == 1

        # Verify error was printed to stderr
        print_calls = [call for call in mock_print.call_args_list]
        assert len(print_calls) > 0


class TestMemoryCleanupCommand:
    """Test memory cleanup CLI command."""

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_cleanup_success(self, mock_print, mock_create_logger):
        """Test successful memory cleanup command."""
        # Mock memory logger with cleanup functionality
        mock_logger = Mock()
        cleanup_stats = {
            "deleted_count": 25,
            "total_entries_before": 100,
            "total_entries_after": 75,
            "dry_run": False,
        }
        mock_logger.cleanup_expired_memories.return_value = cleanup_stats
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"
        args.dry_run = False
        args.json = False

        result = memory_cleanup(args)

        assert result == 0
        mock_create_logger.assert_called_once_with(backend="redis")
        mock_logger.cleanup_expired_memories.assert_called_once_with(dry_run=False)

        # Verify cleanup results were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("=== Memory Cleanup ===" in call for call in print_calls)
        assert any("Deleted Entries: 25" in call for call in print_calls)

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_cleanup_dry_run(self, mock_print, mock_create_logger):
        """Test memory cleanup command in dry run mode."""
        # Mock memory logger
        mock_logger = Mock()
        cleanup_stats = {
            "deleted_count": 15,
            "total_entries_before": 80,
            "total_entries_after": 80,  # No actual deletion in dry run
            "dry_run": True,
        }
        mock_logger.cleanup_expired_memories.return_value = cleanup_stats
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "kafka"
        args.dry_run = True
        args.json = False

        result = memory_cleanup(args)

        assert result == 0
        mock_logger.cleanup_expired_memories.assert_called_once_with(dry_run=True)

        # Verify dry run message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("=== Dry Run: Memory Cleanup Preview ===" in call for call in print_calls)
        assert any("Deleted Entries: 15" in call for call in print_calls)

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_cleanup_json_output(self, mock_print, mock_create_logger):
        """Test memory cleanup command with JSON output."""
        # Mock memory logger
        mock_logger = Mock()
        cleanup_stats = {
            "deleted_count": 10,
            "total_entries_before": 50,
            "total_entries_after": 40,
            "dry_run": False,
            "duration_seconds": 0.5,
        }
        mock_logger.cleanup_expired_memories.return_value = cleanup_stats
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"
        args.dry_run = False
        args.json = True

        result = memory_cleanup(args)

        assert result == 0

        # Verify JSON was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        json_output = None
        for call in print_calls:
            try:
                json_output = json.loads(call)
                break
            except (json.JSONDecodeError, TypeError):
                continue

        assert json_output is not None
        assert "cleanup_result" in json_output
        cleanup_result = json_output["cleanup_result"]
        assert cleanup_result["deleted_count"] == 10
        assert cleanup_result["dry_run"] is False

    @patch("orka.orka_cli.create_memory_logger")
    @patch("builtins.print")
    def test_memory_cleanup_no_decay_support(self, mock_print, mock_create_logger):
        """Test memory cleanup when logger doesn't support decay."""
        # Mock memory logger without cleanup method
        mock_logger = Mock()
        del mock_logger.cleanup_expired_memories  # Remove the method
        mock_create_logger.return_value = mock_logger

        # Mock args
        args = Mock()
        args.backend = "redis"
        args.dry_run = False
        args.json = False

        result = memory_cleanup(args)

        # Should handle gracefully and return error code
        assert result == 1


class TestYAMLLoader:
    """Test YAML loader functionality to improve coverage."""

    @patch("builtins.open", create=True)
    @patch("yaml.safe_load")
    def test_yaml_loader_success(self, mock_yaml_load, mock_open):
        """Test successful YAML loading."""
        from orka.loader import YAMLLoader

        # Mock file content
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock YAML content
        mock_config = {
            "agents": {
                "test_agent": {
                    "type": "llm",
                    "model": "gpt-3.5-turbo",
                },
            },
        }
        mock_yaml_load.return_value = mock_config

        loader = YAMLLoader("test_config.yml")

        assert loader.config == mock_config
        mock_open.assert_called_once_with("test_config.yml")
        mock_yaml_load.assert_called_once_with(mock_file)

    @patch("builtins.open", create=True)
    def test_yaml_loader_file_not_found(self, mock_open):
        """Test YAML loader with file not found."""
        from orka.loader import YAMLLoader

        mock_open.side_effect = FileNotFoundError("No such file")

        with pytest.raises(FileNotFoundError):
            YAMLLoader("nonexistent.yml")

    @patch("builtins.open", create=True)
    @patch("yaml.safe_load")
    def test_yaml_loader_invalid_yaml(self, mock_yaml_load, mock_open):
        """Test YAML loader with invalid YAML content."""
        import yaml

        from orka.loader import YAMLLoader

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock YAML parsing error
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")

        with pytest.raises(yaml.YAMLError):
            YAMLLoader("invalid.yml")

    @patch("builtins.open", create=True)
    @patch("yaml.safe_load")
    def test_yaml_loader_empty_config(self, mock_yaml_load, mock_open):
        """Test YAML loader with empty configuration."""
        from orka.loader import YAMLLoader

        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock empty YAML content
        mock_yaml_load.return_value = {}

        loader = YAMLLoader("empty.yml")

        assert loader.config == {}
        assert loader.path == "empty.yml"


class TestBaseTool:
    """Test BaseTool functionality to improve coverage."""

    def test_base_tool_initialization(self):
        """Test BaseTool initialization with all parameters."""
        from orka.tools.base_tool import BaseTool

        # Create a concrete implementation for testing
        class TestTool(BaseTool):
            def run(self, input_data):
                return f"Processed: {input_data}"

        tool = TestTool(
            tool_id="test_tool_1",
            prompt="Test prompt",
            queue=["tool2", "tool3"],
            custom_param="custom_value",
            another_param=42,
        )

        assert tool.tool_id == "test_tool_1"
        assert tool.prompt == "Test prompt"
        assert tool.queue == ["tool2", "tool3"]
        assert tool.params["custom_param"] == "custom_value"
        assert tool.params["another_param"] == 42
        assert tool.type == "testtool"

    def test_base_tool_minimal_initialization(self):
        """Test BaseTool initialization with minimal parameters."""
        from orka.tools.base_tool import BaseTool

        class MinimalTool(BaseTool):
            def run(self, input_data):
                return input_data

        tool = MinimalTool("minimal_tool")

        assert tool.tool_id == "minimal_tool"
        assert tool.prompt is None
        assert tool.queue is None
        assert tool.params == {}
        assert tool.type == "minimaltool"

    def test_base_tool_run_method(self):
        """Test that the run method works correctly."""
        from orka.tools.base_tool import BaseTool

        class EchoTool(BaseTool):
            def run(self, input_data):
                return f"Echo: {input_data}"

        tool = EchoTool("echo_tool")
        result = tool.run("test input")

        assert result == "Echo: test input"

    def test_base_tool_repr(self):
        """Test the string representation of BaseTool."""
        from orka.tools.base_tool import BaseTool

        class ReprTool(BaseTool):
            def run(self, input_data):
                return input_data

        tool = ReprTool("repr_tool")
        repr_str = repr(tool)

        assert repr_str == "<ReprTool id=repr_tool>"

    def test_base_tool_abstract_method(self):
        """Test that BaseTool cannot be instantiated directly."""
        from orka.tools.base_tool import BaseTool

        with pytest.raises(TypeError):
            BaseTool("abstract_tool")
