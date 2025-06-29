"""
Unit tests for the orchestrator.py composition class.
Tests the main Orchestrator class that inherits from multiple mixins.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from orka.orchestrator import Orchestrator


class TestOrchestratorComposition:
    """Test suite for the Orchestrator composition class."""

    def create_test_config(self):
        """Create a test YAML configuration file."""
        config = {
            "orchestrator": {
                "memory_backend": "redis",
                "redis_url": "redis://localhost:6379",
                "log_level": "INFO",
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai",
                    "prompt": "Test prompt: {{ input }}",
                    "model": "gpt-3.5-turbo",
                },
            ],
        }

        # Create temporary config file
        fd, path = tempfile.mkstemp(suffix=".yml")
        try:
            with os.fdopen(fd, "w") as tmp_file:
                yaml.dump(config, tmp_file)
            return path
        except:
            os.close(fd)
            raise

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_initialization(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test orchestrator initialization with mixins."""
        # Mock the base initialization
        mock_base_init.return_value = None
        mock_init_agents.return_value = {"test_agent": Mock()}

        config_path = self.create_test_config()
        try:
            orchestrator = Orchestrator(config_path)

            # Verify base initialization was called
            mock_base_init.assert_called_once_with(config_path)

            # Verify agents were initialized
            mock_init_agents.assert_called_once()

            # Verify agents attribute is set
            assert hasattr(orchestrator, "agents")
            assert orchestrator.agents == {
                "test_agent": mock_init_agents.return_value["test_agent"]
            }

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_inheritance_chain(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test that orchestrator properly inherits from all mixin classes."""
        # Mock the base initialization
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config_path = self.create_test_config()
        try:
            orchestrator = Orchestrator(config_path)

            # Verify inheritance from all expected mixins
            from orka.orchestrator.agent_factory import AgentFactory
            from orka.orchestrator.base import OrchestratorBase
            from orka.orchestrator.error_handling import ErrorHandler
            from orka.orchestrator.execution_engine import ExecutionEngine
            from orka.orchestrator.metrics import MetricsCollector
            from orka.orchestrator.prompt_rendering import PromptRenderer

            assert isinstance(orchestrator, OrchestratorBase)
            assert isinstance(orchestrator, AgentFactory)
            assert isinstance(orchestrator, PromptRenderer)
            assert isinstance(orchestrator, ErrorHandler)
            assert isinstance(orchestrator, MetricsCollector)
            assert isinstance(orchestrator, ExecutionEngine)

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_method_resolution_order(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test that method resolution order is correct."""
        # Mock the base initialization
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config_path = self.create_test_config()
        try:
            orchestrator = Orchestrator(config_path)

            # Check method resolution order includes all expected classes
            mro_names = [cls.__name__ for cls in orchestrator.__class__.__mro__]

            expected_classes = [
                "Orchestrator",
                "OrchestratorBase",
                "AgentFactory",
                "PromptRenderer",
                "ErrorHandler",
                "MetricsCollector",
                "ExecutionEngine",
                "object",
            ]

            for expected_class in expected_classes:
                assert expected_class in mro_names, f"{expected_class} not in MRO"

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_agents_initialization_error(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test orchestrator handles agent initialization errors."""
        # Mock the base initialization
        mock_base_init.return_value = None
        mock_init_agents.side_effect = Exception("Agent initialization failed")

        config_path = self.create_test_config()
        try:
            with pytest.raises(Exception, match="Agent initialization failed"):
                Orchestrator(config_path)

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_empty_agents(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test orchestrator with empty agents configuration."""
        # Mock the base initialization
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config_path = self.create_test_config()
        try:
            orchestrator = Orchestrator(config_path)

            # Verify empty agents dict is set
            assert orchestrator.agents == {}

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_multiple_agents(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test orchestrator with multiple agents."""
        # Mock the base initialization
        mock_base_init.return_value = None

        # Create mock agents
        mock_agents = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock(),
        }
        mock_init_agents.return_value = mock_agents

        config_path = self.create_test_config()
        try:
            orchestrator = Orchestrator(config_path)

            # Verify all agents are properly set
            assert orchestrator.agents == mock_agents
            assert len(orchestrator.agents) == 3

        finally:
            os.unlink(config_path)

    def test_orchestrator_docstring_and_class_attributes(self):
        """Test that orchestrator has proper docstring and class structure."""
        # Check that the class has a proper docstring
        assert Orchestrator.__doc__ is not None
        assert "Orchestrator" in Orchestrator.__doc__
        assert "YAML" in Orchestrator.__doc__

        # Check class name
        assert Orchestrator.__name__ == "Orchestrator"

        # Check that it has __init__ method
        assert hasattr(Orchestrator, "__init__")

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_config_path_parameter(
        self,
        mock_init_agents,
        mock_base_init,
    ):
        """Test orchestrator properly passes config_path to base class."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config_path = self.create_test_config()
        try:
            Orchestrator(config_path)

            # Verify config_path was passed to base class
            mock_base_init.assert_called_once_with(config_path)

        finally:
            os.unlink(config_path)
