"""
Comprehensive tests for CLI orchestrator commands module to improve coverage.
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

import orka.cli.orchestrator.commands as commands_module


class TestRunOrchestrator:
    """Test the run_orchestrator function."""

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_success_with_json_output(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test successful orchestrator run with JSON output."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = {"result": "success", "data": "test"}
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = True

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0
        mock_path.assert_called_once_with("test_config.yml")
        mock_orchestrator_class.assert_called_once_with("test_config.yml")
        mock_orchestrator.run.assert_called_once_with("test input")

        # Check JSON output
        output = mock_stdout.getvalue()
        expected_json = json.dumps({"result": "success", "data": "test"}, indent=2)
        assert output.strip() == expected_json

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_success_with_regular_output(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test successful orchestrator run with regular output."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = "Simple result string"
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = False

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0
        mock_path.assert_called_once_with("test_config.yml")
        mock_orchestrator_class.assert_called_once_with("test_config.yml")
        mock_orchestrator.run.assert_called_once_with("test input")

        # Check regular output
        output = mock_stdout.getvalue()
        assert "=== Orchestrator Result ===" in output
        assert "Simple result string" in output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_config_file_not_found(self, mock_path):
        """Test orchestrator run when config file doesn't exist."""
        # Setup mocks
        mock_path.return_value.exists.return_value = False

        # Setup args
        args = Mock()
        args.config = "nonexistent_config.yml"
        args.input = "test input"
        args.json = False

        # Capture stderr
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 1
        mock_path.assert_called_once_with("nonexistent_config.yml")

        # Check error message
        error_output = mock_stderr.getvalue()
        assert "Configuration file not found: nonexistent_config.yml" in error_output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_orchestrator_creation_exception(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test orchestrator run when Orchestrator creation raises exception."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator_class.side_effect = Exception("Failed to create orchestrator")

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = False

        # Capture stderr
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 1
        mock_path.assert_called_once_with("test_config.yml")
        mock_orchestrator_class.assert_called_once_with("test_config.yml")

        # Check error message
        error_output = mock_stderr.getvalue()
        assert "Error running orchestrator: Failed to create orchestrator" in error_output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_run_exception(self, mock_path, mock_orchestrator_class):
        """Test orchestrator run when orchestrator.run raises exception."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.side_effect = Exception("Orchestrator run failed")
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = False

        # Capture stderr
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 1
        mock_path.assert_called_once_with("test_config.yml")
        mock_orchestrator_class.assert_called_once_with("test_config.yml")
        mock_orchestrator.run.assert_called_once_with("test input")

        # Check error message
        error_output = mock_stderr.getvalue()
        assert "Error running orchestrator: Orchestrator run failed" in error_output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_with_complex_result(self, mock_path, mock_orchestrator_class):
        """Test orchestrator run with complex result structure."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        complex_result = {
            "agents": [
                {"id": "agent1", "result": "success"},
                {"id": "agent2", "result": "completed"},
            ],
            "metadata": {
                "total_time": 1.5,
                "status": "completed",
            },
        }
        mock_orchestrator.run.return_value = complex_result
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "complex_config.yml"
        args.input = "complex input"
        args.json = True

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0
        mock_orchestrator.run.assert_called_once_with("complex input")

        # Check JSON output
        output = mock_stdout.getvalue()
        expected_json = json.dumps(complex_result, indent=2)
        assert output.strip() == expected_json

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_with_none_result(self, mock_path, mock_orchestrator_class):
        """Test orchestrator run when result is None."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = None
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = True

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0

        # Check JSON output for None
        output = mock_stdout.getvalue()
        expected_json = json.dumps(None, indent=2)
        assert output.strip() == expected_json

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_with_empty_input(self, mock_path, mock_orchestrator_class):
        """Test orchestrator run with empty input."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = "Result with empty input"
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = ""
        args.json = False

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0
        mock_orchestrator.run.assert_called_once_with("")

        # Check output
        output = mock_stdout.getvalue()
        assert "Result with empty input" in output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_with_special_characters_in_config(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test orchestrator run with special characters in config path."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = "Success"
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args with special characters
        args = Mock()
        args.config = "config with spaces & symbols.yml"
        args.input = "test input"
        args.json = False

        # Capture stdout
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 0
        mock_path.assert_called_once_with("config with spaces & symbols.yml")
        mock_orchestrator_class.assert_called_once_with("config with spaces & symbols.yml")

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_json_serialization_error(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test orchestrator run when JSON serialization fails."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()

        # Create a result that can't be JSON serialized (e.g., with circular reference)
        class NonSerializable:
            def __init__(self):
                self.self_ref = self

        mock_orchestrator.run.return_value = NonSerializable()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Setup args
        args = Mock()
        args.config = "test_config.yml"
        args.input = "test input"
        args.json = True

        # Capture stderr
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 1

        # Check error message
        error_output = mock_stderr.getvalue()
        assert "Error running orchestrator:" in error_output

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_with_different_config_extensions(
        self,
        mock_path,
        mock_orchestrator_class,
    ):
        """Test orchestrator run with different config file extensions."""
        # Setup mocks
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = "Success"
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test with different extensions
        extensions = [".yml", ".yaml", ".json", ".toml"]

        for ext in extensions:
            args = Mock()
            args.config = f"config{ext}"
            args.input = "test input"
            args.json = False

            result = await commands_module.run_orchestrator(args)
            assert result == 0

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_path_check_with_pathlib(self, mock_path):
        """Test that Path is used correctly for file existence check."""
        # Setup mocks
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        # Setup args
        args = Mock()
        args.config = "/absolute/path/to/config.yml"
        args.input = "test input"
        args.json = False

        # Test
        result = await commands_module.run_orchestrator(args)

        # Assertions
        assert result == 1
        mock_path.assert_called_once_with("/absolute/path/to/config.yml")
        mock_path_instance.exists.assert_called_once()


class TestModuleImports:
    """Test module-level imports and structure."""

    def test_imports_available(self):
        """Test that all required imports are available."""
        # Test that required modules are imported
        assert hasattr(commands_module, "json")
        assert hasattr(commands_module, "sys")
        assert hasattr(commands_module, "Path")
        assert hasattr(commands_module, "Orchestrator")

        # Test that main function is available
        assert hasattr(commands_module, "run_orchestrator")
        assert callable(commands_module.run_orchestrator)

    def test_module_docstring(self):
        """Test that module has appropriate docstring."""
        assert commands_module.__doc__ is not None
        assert "Orchestrator CLI Commands" in commands_module.__doc__

    def test_module_structure(self):
        """Test module structure and attributes."""
        # Test that json module is available
        assert commands_module.json is json

        # Test that sys module is available
        assert commands_module.sys is sys

        # Test that Path is from pathlib
        assert commands_module.Path is Path


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_run_orchestrator_is_async(self):
        """Test that run_orchestrator is an async function."""
        import inspect

        assert inspect.iscoroutinefunction(commands_module.run_orchestrator)

    def test_function_signature(self):
        """Test that run_orchestrator has the expected signature."""
        import inspect

        sig = inspect.signature(commands_module.run_orchestrator)
        params = list(sig.parameters.keys())
        assert params == ["args"]

    @pytest.mark.asyncio
    @patch("orka.cli.orchestrator.commands.Orchestrator")
    @patch("orka.cli.orchestrator.commands.Path")
    async def test_run_orchestrator_return_values(self, mock_path, mock_orchestrator_class):
        """Test that run_orchestrator returns appropriate values."""
        # Test success case
        mock_path.return_value.exists.return_value = True
        mock_orchestrator = AsyncMock()
        mock_orchestrator.run.return_value = "Success"
        mock_orchestrator_class.return_value = mock_orchestrator

        args = Mock(config="test.yml", input="test", json=False)

        with patch("sys.stdout", new_callable=StringIO):
            result = await commands_module.run_orchestrator(args)

        assert result == 0
        assert isinstance(result, int)

        # Test failure case
        mock_path.return_value.exists.return_value = False

        with patch("sys.stderr", new_callable=StringIO):
            result = await commands_module.run_orchestrator(args)

        assert result == 1
        assert isinstance(result, int)
