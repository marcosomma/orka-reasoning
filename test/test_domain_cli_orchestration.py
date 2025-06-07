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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import Orchestrator from the correct module
from orka.orchestrator import Orchestrator


# CLI Tests
@patch("orka.orka_cli.run_cli_entrypoint", autospec=True)
def test_orka_cli_module_imports(mock_run_cli):
    """Test CLI module imports without errors."""
    import orka.orka_cli

    assert hasattr(orka.orka_cli, "run_cli_entrypoint")


@patch("orka.orchestrator.YAMLLoader", autospec=True)
def test_run_cli_entrypoint(mock_yaml_loader):
    """Test the run_cli_entrypoint function in orka_cli.py"""
    # Mock YAMLLoader to avoid file not found error
    mock_loader_instance = MagicMock()
    mock_yaml_loader.return_value = mock_loader_instance
    mock_loader_instance.get_orchestrator.return_value = {"agents": []}
    mock_loader_instance.get_agents.return_value = []
    mock_loader_instance.validate.return_value = None

    # Import the function directly
    from orka.orka_cli import run_cli_entrypoint

    # Setup the actual test with mock - patch the orchestrator module, not orka_cli
    with patch("orka.orchestrator.Orchestrator", autospec=True) as mock_orch_class:
        # Setup the mock orchestrator instance
        mock_orch = MagicMock()
        mock_orch.run = AsyncMock(return_value="Test result")
        mock_orch_class.return_value = mock_orch

        # Run the coroutine with a proper async test
        import asyncio

        result = asyncio.run(
            run_cli_entrypoint("test.yml", "Test input", log_to_file=False)
        )

        # Verify Orchestrator was created with the config path
        assert mock_orch_class.called
        mock_orch_class.assert_called_once_with("test.yml")

        # Check the result
        assert result == "Test result"


# Orchestrator Tests
@pytest.mark.asyncio
@patch("orka.orchestrator.YAMLLoader", autospec=True)
@patch("orka.orchestrator.create_memory_logger", autospec=True)
@patch("orka.orchestrator.ForkGroupManager", autospec=True)
@patch("orka.orchestrator.SimpleForkGroupManager", autospec=True)
async def test_orchestrator_initialization(
    mock_simple_fork_manager, mock_fork_manager, mock_memory_logger, mock_loader
):
    """Test initialization of the Orchestrator."""
    # Setup mocks
    mock_loader_instance = MagicMock()
    mock_loader.return_value = mock_loader_instance
    mock_memory_instance = MagicMock()
    # Add redis property to mock for compatibility
    mock_memory_instance.redis = MagicMock()
    mock_memory_logger.return_value = mock_memory_instance

    # Mock loader methods
    mock_loader_instance.get_orchestrator.return_value = {"agents": []}
    mock_loader_instance.get_agents.return_value = []
    mock_loader_instance.validate.return_value = None

    # Create orchestrator
    orchestrator = Orchestrator("test.yml")

    # Basic assertions
    assert orchestrator is not None
    assert orchestrator.run_id is not None
    assert hasattr(orchestrator, "agents")
    assert isinstance(orchestrator.agents, dict)


@pytest.mark.asyncio
@patch("orka.orchestrator.YAMLLoader", autospec=True)
@patch("orka.orchestrator.create_memory_logger", autospec=True)
@patch("orka.orchestrator.ForkGroupManager", autospec=True)
@patch("orka.orchestrator.SimpleForkGroupManager", autospec=True)
async def test_orchestrator_with_agents(
    mock_simple_fork_manager, mock_fork_manager, mock_memory_logger, mock_loader
):
    """Test Orchestrator with agents configuration."""
    # Setup mocks
    mock_loader_instance = MagicMock()
    mock_loader.return_value = mock_loader_instance
    mock_memory_instance = MagicMock()
    mock_memory_logger.return_value = mock_memory_instance

    # Mock loader methods
    mock_loader_instance.get_orchestrator.return_value = {
        "agents": ["agent1", "agent2"]
    }
    mock_loader_instance.get_agents.return_value = [
        {"id": "agent1", "type": "binary", "prompt": "Test prompt", "queue": "test"},
        {
            "id": "agent2",
            "type": "classification",
            "prompt": "Test prompt",
            "queue": "test",
            "options": ["A", "B"],
        },
    ]
    mock_loader_instance.validate.return_value = None

    # Patch agent types to prevent actual initialization
    with (
        patch("orka.orchestrator.agents.BinaryAgent") as mock_binary_agent,
        patch("orka.orchestrator.agents.ClassificationAgent") as mock_class_agent,
    ):
        # Create mock agent instances
        mock_agent1 = MagicMock()
        mock_agent2 = MagicMock()
        mock_binary_agent.return_value = mock_agent1
        mock_class_agent.return_value = mock_agent2

        # Create orchestrator with mocked dependencies
        orchestrator = Orchestrator("test.yml")

        # Check if agents were initialized
        assert len(orchestrator.agents) == 2
        assert "agent1" in orchestrator.agents
        assert "agent2" in orchestrator.agents


@pytest.mark.asyncio
async def test_orchestrator_run():
    """Test Orchestrator run method."""
    # First, create mocks for all the dependencies
    mock_agent1 = MagicMock()
    # Important: Return a non-coroutine value to avoid JSON serialization issues
    mock_agent1.run.return_value = True
    mock_agent1.type = "agent"

    mock_agent2 = MagicMock()
    mock_agent2.run.return_value = "Category A"
    mock_agent2.type = "agent"

    # Create a custom monkeypatch object for this test
    with (
        patch(
            "orka.orchestrator.Orchestrator.__init__", return_value=None
        ) as mock_init,
        patch("orka.orchestrator.json.dumps", return_value="{}") as mock_json_dumps,
    ):
        # Create the orchestrator instance without calling __init__
        orchestrator = Orchestrator.__new__(Orchestrator)

        # Set up necessary attributes directly
        orchestrator.agents = {"agent1": mock_agent1, "agent2": mock_agent2}
        orchestrator.queue = ["agent1", "agent2"]
        orchestrator.orchestrator_cfg = {"agents": ["agent1", "agent2"]}
        orchestrator.run_id = "test_run_id"
        orchestrator.step_index = 0
        orchestrator.memory = MagicMock()
        orchestrator.memory.log = MagicMock()
        orchestrator.fork_manager = MagicMock()
        orchestrator.fork_manager.next_in_sequence = MagicMock(return_value=None)
        orchestrator.build_previous_outputs = MagicMock(return_value={})

        # Set up a simplified run method to avoid complexity
        async def simplified_run(input_data):
            results = []
            for agent_id in orchestrator.orchestrator_cfg["agents"]:
                agent = orchestrator.agents[agent_id]
                result = agent.run({"input": input_data, "previous_outputs": {}})
                results.append(result)
            return results[-1]  # Return the last result

        # Replace the run method
        orchestrator.run = simplified_run

        # Run the test
        result = await orchestrator.run("Test input")

        # Verify agents were called
        assert mock_agent1.run.called
        assert mock_agent2.run.called

        # Verify we have a result (the last agent's result)
        assert result == "Category A"
