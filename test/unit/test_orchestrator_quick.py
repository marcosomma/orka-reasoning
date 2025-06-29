"""Quick tests for orchestrator.py to achieve 100% coverage."""

import os
import tempfile
from unittest.mock import Mock, patch

import yaml

from orka.orchestrator import Orchestrator


class TestOrchestratorQuick:
    """Quick tests for basic orchestrator functionality."""

    def create_test_config(self):
        """Create a minimal test configuration."""
        config = {
            "orchestrator": {
                "name": "test_orchestrator",
                "backend": "redis",
                "redis_url": "redis://localhost:6379",
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "llm",
                    "model": "gpt-3.5-turbo",
                    "api_key": "test_key",
                },
            ],
            "nodes": [
                {
                    "id": "test_node",
                    "type": "agent",
                    "agent_id": "test_agent",
                    "prompt": "test prompt",
                },
            ],
        }
        return config

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_initialization(self, mock_init_agents, mock_base_init):
        """Test basic orchestrator initialization - allowing actual orchestrator.py code to run."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {"test_agent": Mock()}

        # Create a temporary config file
        config = self.create_test_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            # This should execute the actual code in orchestrator.py
            orchestrator = Orchestrator(config_path)

            # Verify base initialization was called
            mock_base_init.assert_called_once_with(config_path)

            # Verify agent initialization was called
            mock_init_agents.assert_called_once()

            # Verify agents attribute is set (this tests the actual line in orchestrator.py)
            assert hasattr(orchestrator, "agents")
            assert orchestrator.agents == mock_init_agents.return_value

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_inheritance_chain(self, mock_init_agents, mock_base_init):
        """Test that orchestrator properly inherits from all mixins."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config = self.create_test_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            orchestrator = Orchestrator(config_path)

            # Verify the class inherits from expected base classes
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
    def test_orchestrator_agents_attribute(self, mock_init_agents, mock_base_init):
        """Test that agents attribute is properly set."""
        mock_base_init.return_value = None

        # Mock agents dictionary
        mock_agents = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock(),
        }
        mock_init_agents.return_value = mock_agents

        config = self.create_test_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            orchestrator = Orchestrator(config_path)

            # Verify agents are correctly assigned (tests the line: self.agents = self._init_agents())
            assert orchestrator.agents == mock_agents
            assert len(orchestrator.agents) == 3
            assert "agent1" in orchestrator.agents
            assert "agent2" in orchestrator.agents
            assert "agent3" in orchestrator.agents

        finally:
            os.unlink(config_path)

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_super_call(self, mock_init_agents, mock_base_init):
        """Test that super().__init__ is properly called."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        config = self.create_test_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            orchestrator = Orchestrator(config_path)

            # Verify that the base class __init__ was called with correct arguments
            mock_base_init.assert_called_once_with(config_path)

        finally:
            os.unlink(config_path)

    def test_orchestrator_docstring_and_class_structure(self):
        """Test that the orchestrator class has proper documentation and structure."""
        # Verify class has proper docstring
        assert Orchestrator.__doc__ is not None
        assert "Orchestrator" in Orchestrator.__doc__
        assert "workflow" in Orchestrator.__doc__.lower()

        # Verify class has __init__ method
        assert hasattr(Orchestrator, "__init__")

        # Verify method resolution order includes all expected classes
        mro_classes = [cls.__name__ for cls in Orchestrator.__mro__]

        expected_classes = [
            "Orchestrator",
            "OrchestratorBase",
            "AgentFactory",
            "PromptRenderer",
            "ErrorHandler",
            "MetricsCollector",
            "ExecutionEngine",
        ]

        for expected_class in expected_classes:
            assert expected_class in mro_classes, f"Expected {expected_class} in MRO"

    @patch("orka.orchestrator.base.OrchestratorBase.__init__")
    @patch("orka.orchestrator.agent_factory.AgentFactory._init_agents")
    def test_orchestrator_actual_instantiation(self, mock_init_agents, mock_base_init):
        """Test actual instantiation to ensure orchestrator.py code executes."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {"mock_agent": Mock()}

        config = self.create_test_config()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            config_path = f.name

        try:
            # Direct instantiation to trigger orchestrator.py code
            orchestrator = Orchestrator(config_path)

            # Verify the orchestrator was created
            assert orchestrator is not None
            assert isinstance(orchestrator, Orchestrator)

            # This specifically tests the line: self.agents = self._init_agents()
            assert hasattr(orchestrator, "agents")
            assert orchestrator.agents is not None

        finally:
            os.unlink(config_path)
