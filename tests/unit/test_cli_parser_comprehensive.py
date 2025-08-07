"""
Comprehensive tests for CLI parser module to improve coverage.
"""

import argparse

import pytest

from orka.cli.parser import create_parser, setup_subcommands


class TestCreateParser:
    """Test the create_parser function."""

    def test_create_parser_basic(self):
        """Test basic parser creation."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description == "OrKa - Orchestrator Kit for Agents"
        assert parser.formatter_class == argparse.RawDescriptionHelpFormatter

    def test_create_parser_global_options(self):
        """Test that global options are properly configured."""
        parser = create_parser()

        # Test verbose option
        args = parser.parse_args(["-v"])
        assert args.verbose is True

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

        args = parser.parse_args([])
        assert args.verbose is False

    def test_create_parser_json_option(self):
        """Test JSON output option."""
        parser = create_parser()

        # Test JSON option
        args = parser.parse_args(["--json"])
        assert args.json is True

        args = parser.parse_args([])
        assert args.json is False

    def test_create_parser_combined_options(self):
        """Test combining global options."""
        parser = create_parser()

        args = parser.parse_args(["-v", "--json"])
        assert args.verbose is True
        assert args.json is True

        args = parser.parse_args(["--verbose", "--json"])
        assert args.verbose is True
        assert args.json is True


class TestSetupSubcommands:
    """Test the setup_subcommands function."""

    def test_setup_subcommands_basic(self):
        """Test basic subcommand setup."""
        parser = create_parser()
        parser_with_subs = setup_subcommands(parser)

        assert parser_with_subs is parser  # Should return the same parser
        assert hasattr(parser_with_subs, "_subparsers")

    def test_run_command_setup(self):
        """Test run command configuration."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test run command with required arguments
        args = parser.parse_args(["run", "config.yaml", "test_input"])
        assert args.command == "run"
        assert args.config == "config.yaml"
        assert args.input == "test_input"
        assert hasattr(args, "func")

    def test_run_command_missing_arguments(self):
        """Test run command with missing arguments."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test missing config argument
        with pytest.raises(SystemExit):
            parser.parse_args(["run"])

        # Test missing input argument
        with pytest.raises(SystemExit):
            parser.parse_args(["run", "config.yaml"])

    def test_memory_command_setup(self):
        """Test memory command configuration."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test memory command without subcommand
        args = parser.parse_args(["memory"])
        assert args.command == "memory"
        assert args.memory_command is None

    def test_memory_stats_command(self):
        """Test memory stats subcommand."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test stats without backend
        args = parser.parse_args(["memory", "stats"])
        assert args.command == "memory"
        assert args.memory_command == "stats"
        assert args.backend is None
        assert hasattr(args, "func")

        # Test stats with backend
        args = parser.parse_args(["memory", "stats", "--backend", "redis"])
        assert args.backend == "redis"

        args = parser.parse_args(["memory", "stats", "--backend", "redisstack"])
        assert args.backend == "redisstack"

        args = parser.parse_args(["memory", "stats", "--backend", "kafka"])
        assert args.backend == "kafka"

    def test_memory_stats_invalid_backend(self):
        """Test memory stats with invalid backend."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid backend
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "stats", "--backend", "invalid"])

    def test_memory_cleanup_command(self):
        """Test memory cleanup subcommand."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test cleanup without options
        args = parser.parse_args(["memory", "cleanup"])
        assert args.command == "memory"
        assert args.memory_command == "cleanup"
        assert args.backend is None
        assert args.dry_run is False
        assert hasattr(args, "func")

        # Test cleanup with backend
        args = parser.parse_args(["memory", "cleanup", "--backend", "redis"])
        assert args.backend == "redis"

        # Test cleanup with dry-run
        args = parser.parse_args(["memory", "cleanup", "--dry-run"])
        assert args.dry_run is True

        # Test cleanup with both options
        args = parser.parse_args(["memory", "cleanup", "--backend", "kafka", "--dry-run"])
        assert args.backend == "kafka"
        assert args.dry_run is True

    def test_memory_cleanup_invalid_backend(self):
        """Test memory cleanup with invalid backend."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid backend
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "cleanup", "--backend", "invalid"])

    def test_memory_configure_command(self):
        """Test memory configure subcommand."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test configure without backend
        args = parser.parse_args(["memory", "configure"])
        assert args.command == "memory"
        assert args.memory_command == "configure"
        assert args.backend is None
        assert hasattr(args, "func")

        # Test configure with backend
        args = parser.parse_args(["memory", "configure", "--backend", "redisstack"])
        assert args.backend == "redisstack"

    def test_memory_configure_invalid_backend(self):
        """Test memory configure with invalid backend."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid backend
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "configure", "--backend", "invalid"])

    def test_memory_watch_command(self):
        """Test memory watch subcommand."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test watch without options
        args = parser.parse_args(["memory", "watch"])
        assert args.command == "memory"
        assert args.memory_command == "watch"
        assert args.backend is None
        assert args.interval == 5
        assert args.no_clear is False
        assert args.compact is False
        assert args.use_rich is False
        assert args.fallback is False
        assert hasattr(args, "func")

    def test_memory_watch_with_backend(self):
        """Test memory watch with backend option."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test each backend
        for backend in ["redis", "redisstack", "kafka"]:
            args = parser.parse_args(["memory", "watch", "--backend", backend])
            assert args.backend == backend

    def test_memory_watch_with_interval(self):
        """Test memory watch with interval option."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test integer interval
        args = parser.parse_args(["memory", "watch", "--interval", "10"])
        assert args.interval == 10.0

        # Test float interval
        args = parser.parse_args(["memory", "watch", "--interval", "2.5"])
        assert args.interval == 2.5

    def test_memory_watch_invalid_interval(self):
        """Test memory watch with invalid interval."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid interval
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "watch", "--interval", "invalid"])

    def test_memory_watch_boolean_options(self):
        """Test memory watch boolean options."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test no-clear option
        args = parser.parse_args(["memory", "watch", "--no-clear"])
        assert args.no_clear is True

        # Test compact option
        args = parser.parse_args(["memory", "watch", "--compact"])
        assert args.compact is True

        # Test use-rich option
        args = parser.parse_args(["memory", "watch", "--use-rich"])
        assert args.use_rich is True

        # Test fallback option
        args = parser.parse_args(["memory", "watch", "--fallback"])
        assert args.fallback is True

    def test_memory_watch_all_options(self):
        """Test memory watch with all options combined."""
        parser = create_parser()
        setup_subcommands(parser)

        args = parser.parse_args(
            [
                "memory",
                "watch",
                "--backend",
                "redis",
                "--interval",
                "3.0",
                "--no-clear",
                "--compact",
                "--use-rich",
                "--fallback",
            ],
        )

        assert args.backend == "redis"
        assert args.interval == 3.0
        assert args.no_clear is True
        assert args.compact is True
        assert args.use_rich is True
        assert args.fallback is True

    def test_memory_watch_invalid_backend(self):
        """Test memory watch with invalid backend."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid backend
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "watch", "--backend", "invalid"])

    def test_invalid_command(self):
        """Test parsing with invalid command."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid command
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_command"])

    def test_invalid_memory_subcommand(self):
        """Test parsing with invalid memory subcommand."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test invalid memory subcommand
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "invalid_subcommand"])

    def test_global_options_with_subcommands(self):
        """Test global options combined with subcommands."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test global options with run command
        args = parser.parse_args(["-v", "--json", "run", "config.yaml", "input"])
        assert args.verbose is True
        assert args.json is True
        assert args.command == "run"
        assert args.config == "config.yaml"
        assert args.input == "input"

        # Test global options with memory command
        args = parser.parse_args(["--verbose", "memory", "stats", "--backend", "redis"])
        assert args.verbose is True
        assert args.json is False
        assert args.command == "memory"
        assert args.memory_command == "stats"
        assert args.backend == "redis"

    def test_help_output(self):
        """Test help output doesn't crash."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test main help
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

        # Test run help
        with pytest.raises(SystemExit):
            parser.parse_args(["run", "--help"])

        # Test memory help
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "--help"])

        # Test memory stats help
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "stats", "--help"])

        # Test memory cleanup help
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "cleanup", "--help"])

        # Test memory configure help
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "configure", "--help"])

        # Test memory watch help
        with pytest.raises(SystemExit):
            parser.parse_args(["memory", "watch", "--help"])


class TestParserIntegration:
    """Test parser integration scenarios."""

    def test_parser_integration_create_and_setup(self):
        """Test creating parser and setting up subcommands together."""
        parser = create_parser()
        parser_with_subs = setup_subcommands(parser)

        # Verify it's the same parser object
        assert parser is parser_with_subs

        # Test that both global and subcommand options work
        args = parser.parse_args(["-v", "--json", "memory", "watch", "--interval", "1.5"])
        assert args.verbose is True
        assert args.json is True
        assert args.command == "memory"
        assert args.memory_command == "watch"
        assert args.interval == 1.5

    def test_parser_function_assignments(self):
        """Test that functions are properly assigned to subcommands."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test run command function
        args = parser.parse_args(["run", "test.yaml", "input"])
        assert hasattr(args, "func")
        assert args.func.__name__ == "run_orchestrator"

        # Test memory stats function
        args = parser.parse_args(["memory", "stats"])
        assert hasattr(args, "func")
        assert args.func.__name__ == "memory_stats"

        # Test memory cleanup function
        args = parser.parse_args(["memory", "cleanup"])
        assert hasattr(args, "func")
        assert args.func.__name__ == "memory_cleanup"

        # Test memory configure function
        args = parser.parse_args(["memory", "configure"])
        assert hasattr(args, "func")
        assert args.func.__name__ == "memory_configure"

        # Test memory watch function
        args = parser.parse_args(["memory", "watch"])
        assert hasattr(args, "func")
        assert args.func.__name__ == "memory_watch"

    def test_parser_edge_cases(self):
        """Test parser edge cases."""
        parser = create_parser()
        setup_subcommands(parser)

        # Test empty args - may or may not exit depending on argparse configuration
        try:
            args = parser.parse_args([])
            # If it doesn't exit, check that command is None or empty
            assert args.command is None
        except SystemExit:
            # This is also acceptable behavior
            pass

        # Test minimum valid run command
        args = parser.parse_args(["run", "a", "b"])
        assert args.config == "a"
        assert args.input == "b"

        # Test minimum valid memory command
        args = parser.parse_args(["memory", "stats"])
        assert args.memory_command == "stats"

    def test_parser_namespace_isolation(self):
        """Test that different subcommands don't interfere with each other."""
        parser = create_parser()
        setup_subcommands(parser)

        # Parse run command
        run_args = parser.parse_args(["run", "config.yaml", "input"])
        assert not hasattr(run_args, "backend")
        assert not hasattr(run_args, "dry_run")
        assert not hasattr(run_args, "interval")

        # Parse memory stats command
        stats_args = parser.parse_args(["memory", "stats", "--backend", "redis"])
        assert not hasattr(stats_args, "config")
        assert not hasattr(stats_args, "input")
        assert not hasattr(stats_args, "dry_run")
        assert not hasattr(stats_args, "interval")

        # Parse memory cleanup command
        cleanup_args = parser.parse_args(["memory", "cleanup", "--dry-run"])
        assert not hasattr(cleanup_args, "config")
        assert not hasattr(cleanup_args, "input")
        assert not hasattr(cleanup_args, "interval")

        # Parse memory watch command
        watch_args = parser.parse_args(["memory", "watch", "--interval", "2"])
        assert not hasattr(watch_args, "config")
        assert not hasattr(watch_args, "input")
        assert not hasattr(watch_args, "dry_run")
