"""Test orka_cli.py comprehensively."""

import logging
from unittest.mock import Mock, patch

from orka import orka_cli as orka_cli_module


class TestModuleImports:
    """Test module imports."""

    def test_star_imports(self):
        """Test that __all__ contains expected items."""
        assert hasattr(orka_cli_module, "__all__")
        assert "cli_main" in orka_cli_module.__all__
        assert "run_cli" in orka_cli_module.__all__


class TestMainFunction:
    """Test main function."""

    def test_main_with_no_args(self):
        """Test main with no arguments."""
        parser = Mock()
        parser.parse_args.return_value = Mock(command=None, verbose=False)

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main([])
            assert result == 1
            parser.print_help.assert_called_once()

    def test_main_with_run_command(self):
        """Test main function with run command."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        # Setup mock run_cli with the correct import path
        with patch("orka.orka_cli.run_cli") as mock_run_cli:
            mock_run_cli.return_value = 0
            with patch("orka.orka_cli.create_parser", return_value=parser):
                result = orka_cli_module.main(["run", "config.yml", "test input"])
                assert result == 0
                # Verify run_cli was called with the correct arguments list
                mock_run_cli.assert_called_once_with(["run", "config.yml", "test input"])

    def test_main_with_run_command_exception(self):
        """Test main function with run command that raises exception."""
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
            func=None,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("orka.cli.core.run_cli", side_effect=Exception("Command failed")),
        ):
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 1

    def test_main_with_memory_command_no_subcommand(self):
        """Test main function with memory command but no subcommand."""
        parser = Mock()
        args = Mock(
            command="memory",
            memory_command=None,
            verbose=False,
        )
        parser.parse_args.return_value = args

        # Create a mock memory subparser
        memory_parser = Mock()
        parser._subparsers = Mock()
        parser._subparsers._group_actions = [
            Mock(dest="command", choices={"memory": memory_parser}),
        ]

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory"])
            assert result == 1
            memory_parser.print_help.assert_called_once()


class TestArgumentParsing:
    """Test argument parsing."""

    def test_create_parser(self):
        """Test create_parser function."""
        parser = orka_cli_module.create_parser()
        assert parser.description == "OrKa - Orchestrator Kit for Agents"

    def test_setup_logging(self):
        """Test setup_logging function."""
        with patch("logging.basicConfig") as mock_basic_config:
            orka_cli_module.setup_logging(verbose=True)
            mock_basic_config.assert_called_once_with(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

    def test_setup_logging_exception(self):
        """Test setup_logging with exception."""
        parser = Mock()
        args = Mock(verbose=False)
        parser.parse_args.return_value = args

        with (
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("logging.basicConfig", side_effect=Exception("Test error")),
        ):
            result = orka_cli_module.main([])
            assert result == 1


class TestErrorHandling:
    """Test error handling."""

    def test_main_with_keyboard_interrupt(self):
        """Test main with KeyboardInterrupt."""
        with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
            mock_exit.side_effect = KeyboardInterrupt()
            orka_cli_module.cli_main()
            mock_print.assert_called_with("\n🛑 Operation cancelled.")

    def test_main_with_exception(self):
        """Test main with general exception."""
        with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
            mock_exit.side_effect = Exception("Test error")
            orka_cli_module.cli_main()
            mock_print.assert_called_with("\n❌ Error: Test error")

    def test_main_with_create_parser_exception(self):
        """Test main when create_parser raises exception."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_create_parser.side_effect = Exception("Test error")
            result = orka_cli_module.main([])
            assert result == 1
