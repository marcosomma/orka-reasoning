import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from pathlib import Path

from orka.cli.orchestrator.commands import run_orchestrator

@pytest.fixture
def mock_args():
    """Fixture for a mocked args object."""
    class MockArgs:
        def __init__(self):
            self.config = "valid_config.yml"
            self.input = "test_input"
            self.json = False

    return MockArgs()

@pytest.fixture
def mock_path_exists():
    """Fixture to mock Path.exists."""
    with patch.object(Path, "exists") as mock_method:
        mock_method.return_value = True
        yield mock_method

@pytest.fixture
def mock_orchestrator_instance():
    """Fixture for a mocked Orchestrator instance."""
    mock_instance = AsyncMock()
    mock_instance.run.return_value = {"status": "success", "output": "orchestrator output"}
    return mock_instance

@pytest.fixture
def mock_orchestrator(mock_orchestrator_instance):
    """Fixture to mock the Orchestrator class."""
    with patch("orka.cli.orchestrator.commands.Orchestrator") as mock_class:
        mock_class.return_value = mock_orchestrator_instance
        yield mock_class

@pytest.fixture
def mock_logger():
    """Fixture to mock the logger."""
    with patch("orka.cli.orchestrator.commands.logger") as mock_logger_obj:
        yield mock_logger_obj

class TestRunOrchestrator:
    @pytest.mark.asyncio
    async def test_run_orchestrator_success_default_output(self, mock_args, mock_path_exists, mock_orchestrator, mock_orchestrator_instance, mock_logger):
        result = await run_orchestrator(mock_args)
        assert result == 0
        mock_path_exists.assert_called_once_with()
        mock_orchestrator.assert_called_once_with(mock_args.config)
        mock_orchestrator_instance.run.assert_called_once_with(mock_args.input)
        mock_logger.info.assert_any_call("=== Orchestrator Result ===")
        mock_logger.info.assert_any_call({"status": "success", "output": "orchestrator output"})
        mock_logger.info.assert_called_with({"status": "success", "output": "orchestrator output"}) # Ensure this is the last info call

    @pytest.mark.asyncio
    async def test_run_orchestrator_success_json_output(self, mock_args, mock_path_exists, mock_orchestrator, mock_orchestrator_instance, mock_logger):
        mock_args.json = True
        result = await run_orchestrator(mock_args)
        assert result == 0
        mock_path_exists.assert_called_once_with()
        mock_orchestrator.assert_called_once_with(mock_args.config)
        mock_orchestrator_instance.run.assert_called_once_with(mock_args.input)
        mock_logger.info.assert_called_once()
        called_args, _ = mock_logger.info.call_args
        output_json = json.loads(called_args[0])
        assert output_json == {"status": "success", "output": "orchestrator output"}

    @pytest.mark.asyncio
    async def test_run_orchestrator_config_not_found(self, mock_args, mock_path_exists, mock_logger):
        mock_path_exists.return_value = False
        result = await run_orchestrator(mock_args)
        assert result == 1
        mock_path_exists.assert_called_once_with()
        mock_logger.error.assert_called_once_with(f"Configuration file not found: {mock_args.config}")

    @pytest.mark.asyncio
    async def test_run_orchestrator_orchestrator_init_error(self, mock_args, mock_path_exists, mock_orchestrator, mock_logger):
        mock_orchestrator.side_effect = Exception("Init error")
        result = await run_orchestrator(mock_args)
        assert result == 1
        mock_path_exists.assert_called_once_with()
        mock_orchestrator.assert_called_once_with(mock_args.config)
        mock_logger.error.assert_called_once_with("Error running orchestrator: Init error")

    @pytest.mark.asyncio
    async def test_run_orchestrator_run_error(self, mock_args, mock_path_exists, mock_orchestrator, mock_orchestrator_instance, mock_logger):
        mock_orchestrator_instance.run.side_effect = Exception("Run error")
        result = await run_orchestrator(mock_args)
        assert result == 1
        mock_path_exists.assert_called_once_with()
        mock_orchestrator.assert_called_once_with(mock_args.config)
        mock_orchestrator_instance.run.assert_called_once_with(mock_args.input)
        mock_logger.error.assert_called_once_with("Error running orchestrator: Run error")

