"""Test the OrKa CLI module."""

import argparse
import sys
from unittest.mock import Mock, patch

import pytest

from orka import orka_cli as orka_cli_module


class TestMainFunction:
    """Test main function."""

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    def test_main_with_no_command(
        self,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function when no command is provided."""
        # Setup mock parser
        mock_parser = Mock()
        mock_parser.parse_args.return_value = Mock(command=None, verbose=False)
        mock_create_parser.return_value = mock_parser

        # Test
        with patch.object(sys, "argv", ["orka_cli"]):
            result = orka_cli_module.main()

        # Assertions
        assert result == 1
        mock_create_parser.assert_called_once()
        mock_setup_logging.assert_called_once_with(False)
        mock_parser.print_help.assert_called_once()

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    @patch("orka.cli.core.run_cli_entrypoint")
    def test_main_with_run_command(
        self,
        mock_run_cli_entrypoint,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with run command."""
        # Setup mock
        mock_parser = Mock()
        mock_args = Mock(
            command="run",
            verbose=False,
            config="config.yml",
            input="test input",
            log_to_file=False,
        )
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Setup async mock for run_cli_entrypoint
        mock_run_cli_entrypoint.return_value = {"result": "success"}

        # Test
        with patch.object(sys, "argv", ["orka_cli", "run", "config.yml", "test input"]):
            result = orka_cli_module.main()

        # Assertions
        assert result == 0
        mock_setup_logging.assert_called_once_with(False)
        mock_run_cli_entrypoint.assert_called_once_with("config.yml", "test input", False)

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    @patch("orka.cli.core.run_cli_entrypoint")
    def test_main_with_run_command_log_to_file(
        self,
        mock_run_cli_entrypoint,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with run command and log-to-file option."""
        # Setup mock
        mock_parser = Mock()
        mock_args = Mock(
            command="run",
            verbose=False,
            config="config.yml",
            input="test input",
            log_to_file=True,
        )
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Setup async mock for run_cli_entrypoint
        mock_run_cli_entrypoint.return_value = {"result": "success"}

        # Test
        with patch.object(
            sys,
            "argv",
            ["orka_cli", "run", "config.yml", "test input", "--log-to-file"],
        ):
            result = orka_cli_module.main()

        # Assertions
        assert result == 0
        mock_setup_logging.assert_called_once_with(False)
        mock_run_cli_entrypoint.assert_called_once_with("config.yml", "test input", True)

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    def test_main_with_non_run_command(
        self,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with non-run command (sync)."""
        # Setup mock
        mock_func = Mock(return_value=0)
        mock_args = Mock(command="memory", verbose=False, memory_command="stats", func=mock_func)

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Test
        with patch.object(sys, "argv", ["orka_cli", "memory", "stats"]):
            result = orka_cli_module.main()

        # Assertions
        assert result == 0
        mock_setup_logging.assert_called_once_with(False)
        mock_func.assert_called_once_with(mock_args)

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    @patch("orka.cli.core.run_cli_entrypoint")
    def test_main_with_run_command_exception(
        self,
        mock_run_cli_entrypoint,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with run command that raises exception."""
        # Setup mock
        mock_parser = Mock()
        mock_args = Mock(
            command="run",
            verbose=False,
            config="config.yml",
            input="test input",
            log_to_file=False,
        )
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Setup async mock to raise exception
        mock_run_cli_entrypoint.side_effect = Exception("Command failed")

        # Test that exception is propagated
        with patch.object(sys, "argv", ["orka_cli", "run", "config.yml", "test input"]):
            with pytest.raises(Exception, match="Command failed"):
                orka_cli_module.main()

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    def test_main_with_memory_command_no_subcommand(
        self,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with memory command but no subcommand."""
        # Setup mock parser without subcommands
        mock_args = Mock(command="memory", memory_command=None, verbose=False)

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Test
        with patch.object(sys, "argv", ["orka_cli", "memory"]):
            result = orka_cli_module.main()

        # Should return None and print help
        assert result is None
        mock_setup_logging.assert_called_once_with(False)
        mock_parser.print_help.assert_called_once()

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    def test_main_with_command_returning_none(
        self,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with command that returns None."""
        # Setup mock
        mock_func = Mock(return_value=None)
        mock_args = Mock(command="memory", verbose=False, memory_command="stats", func=mock_func)

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Test
        with patch.object(sys, "argv", ["orka_cli", "memory", "stats"]):
            result = orka_cli_module.main()

        # Should return None
        assert result is None
        mock_setup_logging.assert_called_once_with(False)
        mock_func.assert_called_once_with(mock_args)

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    def test_main_with_verbose_logging(
        self,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test main function with verbose logging enabled."""
        # Setup mock
        mock_func = Mock(return_value=0)
        mock_args = Mock(command="memory", memory_command="stats", verbose=True, func=mock_func)

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Test
        with patch.object(sys, "argv", ["orka_cli", "-v", "memory", "stats"]):
            result = orka_cli_module.main()

        # Assertions
        assert result == 0
        mock_setup_logging.assert_called_once_with(True)
        mock_func.assert_called_once_with(mock_args)


class TestModuleImports:
    """Test module imports and structure."""

    def test_imports_available(self):
        """Test that required imports are available."""
        assert hasattr(orka_cli_module, "main")
        assert hasattr(orka_cli_module, "run_cli")
        assert hasattr(orka_cli_module, "create_parser")
        assert hasattr(orka_cli_module, "setup_logging")

    def test_module_docstring(self):
        """Test that module has a docstring."""
        assert orka_cli_module.__doc__ is not None
        assert len(orka_cli_module.__doc__) > 0

    def test_star_imports(self):
        """Test that __all__ contains expected exports."""
        assert hasattr(orka_cli_module, "__all__")
        assert "main" in orka_cli_module.__all__
        assert "run_cli" in orka_cli_module.__all__


class TestMainEntryPoint:
    """Test main entry point behavior."""

    def test_main_entry_point(self):
        """Test that main entry point exists and is callable."""
        assert callable(orka_cli_module.main)

    def test_main_entry_point_with_error(self):
        """Test main entry point with error."""
        with patch.object(sys, "argv", ["orka_cli", "--invalid-option"]):
            with pytest.raises(SystemExit):
                orka_cli_module.main()


class TestArgumentParsing:
    """Test argument parsing functionality."""

    def test_parse_args_exception(self):
        """Test handling of argument parsing exceptions."""
        with patch.object(sys, "argv", ["orka_cli", "--invalid-option"]):
            with pytest.raises(SystemExit):
                orka_cli_module.main()

    @patch("orka.orka_cli.setup_logging")
    def test_setup_logging_exception(
        self,
        mock_setup_logging,
    ):
        """Test handling of logging setup exceptions."""
        mock_setup_logging.side_effect = Exception("Logging setup failed")
        with patch.object(sys, "argv", ["orka_cli", "memory", "stats"]):
            with pytest.raises(Exception, match="Logging setup failed"):
                orka_cli_module.main()


class TestComplexScenarios:
    """Test complex scenarios and edge cases."""

    def test_command_with_custom_return_value(self):
        """Test command that returns custom value."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_func = Mock(return_value=42)
            mock_args = Mock(
                command="memory", memory_command="stats", verbose=False, func=mock_func
            )
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["memory", "stats"])
            assert result == 42

    @patch("orka.orka_cli.create_parser")
    @patch("orka.orka_cli.setup_logging")
    @patch("orka.cli.core.run_cli_entrypoint")
    def test_run_command_with_custom_return_value(
        self,
        mock_run_cli_entrypoint,
        mock_setup_logging,
        mock_create_parser,
    ):
        """Test run command that returns custom value."""
        # Setup mock
        mock_parser = Mock()
        mock_args = Mock(
            command="run",
            verbose=False,
            config="config.yml",
            input="test input",
            log_to_file=False,
        )
        mock_parser.parse_args.return_value = mock_args
        mock_create_parser.return_value = mock_parser

        # Setup async mock for run_cli_entrypoint
        mock_run_cli_entrypoint.return_value = {"custom": "value"}

        # Test
        with patch.object(sys, "argv", ["orka_cli", "run", "config.yml", "test input"]):
            result = orka_cli_module.main()

        # Assertions
        assert result == 0  # run_cli returns 0 for successful execution
        mock_setup_logging.assert_called_once_with(False)
        mock_run_cli_entrypoint.assert_called_once_with("config.yml", "test input", False)

    def test_main_with_different_command_types(self):
        """Test main function with different command types."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            # Test memory command
            mock_func = Mock(return_value=0)
            mock_args = Mock(
                command="memory",
                memory_command="stats",
                verbose=False,
                func=mock_func,
            )
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["memory", "stats"])
            assert result == 0
            mock_func.assert_called_once_with(mock_args)


class TestIntegration:
    """Integration tests for the CLI module."""

    def test_module_structure(self):
        """Test overall module structure."""
        assert hasattr(orka_cli_module, "main")
        assert hasattr(orka_cli_module, "create_parser")
        assert hasattr(orka_cli_module, "setup_logging")

    def test_backward_compatibility_imports(self):
        """Test backward compatibility imports."""
        assert "run_cli" in orka_cli_module.__all__

    def test_command_line_interface(self):
        """Test command line interface structure."""
        parser = orka_cli_module.create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_imports_from_cli_module(self):
        """Test imports from CLI module."""
        from orka.cli.core import run_cli

        assert callable(run_cli)

    def test_module_constants(self):
        """Test module constants."""
        assert isinstance(orka_cli_module.__all__, list)
        assert len(orka_cli_module.__all__) > 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_main_with_create_parser_exception(self):
        """Test main function when create_parser raises exception."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_create_parser.side_effect = Exception("Parser creation failed")
            with pytest.raises(Exception, match="Parser creation failed"):
                orka_cli_module.main()

    def test_main_with_missing_func_attribute(self):
        """Test main function when args has no func attribute."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_args = Mock(command="test", verbose=False)
            # Explicitly remove func attribute
            del mock_args.func
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["test"])
            assert result == 1


class TestMainExecution:
    """Test main execution scenarios."""

    def test_main_module_execution_path(self):
        """Test main module execution path."""
        with patch.object(sys, "argv", ["orka_cli", "--help"]):
            with pytest.raises(SystemExit):
                orka_cli_module.main()

    def test_main_execution_simulation(self):
        """Test main execution with simulated arguments."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_func = Mock(return_value=0)
            mock_args = Mock(
                command="memory",
                memory_command="stats",
                verbose=False,
                func=mock_func,
            )
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["memory", "stats"])
            assert result == 0

    def test_main_execution_with_none_return(self):
        """Test main execution with None return value."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_func = Mock(return_value=None)
            mock_args = Mock(
                command="memory",
                memory_command="stats",
                verbose=False,
                func=mock_func,
            )
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["memory", "stats"])
            assert result is None

    def test_main_execution_with_error_code(self):
        """Test main execution with error return code."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_func = Mock(return_value=1)
            mock_args = Mock(
                command="memory",
                memory_command="stats",
                verbose=False,
                func=mock_func,
            )
            mock_parser = Mock()
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            result = orka_cli_module.main(["memory", "stats"])
            assert result == 1
