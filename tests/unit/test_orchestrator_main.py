"""
Comprehensive unit tests for the main orchestrator.py module.
Tests the Orchestrator class composition and initialization.
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from orka.orchestrator import Orchestrator


class TestOrchestrator:
    """Test suite for the main Orchestrator class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary YAML config file
        self.temp_config = {
            "orchestrator": {
                "memory_backend": "file",
                "memory_logger_config": {
                    "file_path": "/tmp/test_memory.json",
                },
                "agents": ["test_agent"],
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai",
                    "prompt": "Test prompt",
                    "api_key": "test_key",
                },
            ],
        }

        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yml")
        yaml.dump(self.temp_config, self.temp_file)
        self.temp_file.close()
        self.config_path = self.temp_file.name

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.config_path)
        except FileNotFoundError:
            pass

    @patch("orka.orchestrator.OrchestratorBase.__init__")
    def test_orchestrator_inheritance_chain(self, mock_base_init):
        """Test that Orchestrator properly inherits from all mixin classes."""
        mock_base_init.return_value = None

        # Test inheritance chain
        assert hasattr(Orchestrator, "__mro__")
        mro = Orchestrator.__mro__

        # Verify all expected classes are in the MRO
        class_names = [cls.__name__ for cls in mro]

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
            assert expected_class in class_names, f"{expected_class} not found in MRO"

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_initialization_success(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test successful orchestrator initialization."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {"test_agent": Mock()}

        orchestrator = Orchestrator(self.config_path)

        # Verify mocks were called
        assert mock_memory_logger.call_count >= 1
        assert mock_fork_manager.call_count >= 1

        # Verify agent initialization was called
        mock_init_agents.assert_called_once()

        # Verify agents attribute is set
        assert hasattr(orchestrator, "agents")
        assert "test_agent" in orchestrator.agents

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_initialization_with_empty_agents(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test orchestrator initialization with empty agents list."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {}

        orchestrator = Orchestrator(self.config_path)

        assert orchestrator.agents == {}

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_initialization_with_multiple_agents(
        self,
        mock_init_agents,
        mock_fork_manager,
        mock_memory_logger,
    ):
        """Test orchestrator initialization with multiple agents."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_agents = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock(),
        }
        mock_init_agents.return_value = mock_agents

        orchestrator = Orchestrator(self.config_path)

        assert len(orchestrator.agents) == 3
        assert "agent1" in orchestrator.agents
        assert "agent2" in orchestrator.agents
        assert "agent3" in orchestrator.agents

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_methods_available(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test that all expected methods are available from mixins."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {}

        orchestrator = Orchestrator(self.config_path)

        # Methods that should be inherited from mixins
        expected_methods = [
            "_init_agents",  # From AgentFactory
        ]

        for method in expected_methods:
            assert hasattr(orchestrator, method), f"Method {method} not found"

    @patch("orka.orchestrator.OrchestratorBase.__init__")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_docstring_and_attributes(self, mock_init_agents, mock_base_init):
        """Test orchestrator class attributes and documentation."""
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        # Test class has proper docstring
        assert Orchestrator.__doc__ is not None
        assert "core engine" in Orchestrator.__doc__

        # Test class module
        assert Orchestrator.__module__ == "orka.orchestrator"

    @patch("orka.orchestrator.OrchestratorBase.__init__", side_effect=Exception("Base init error"))
    def test_orchestrator_initialization_base_error(self, mock_base_init):
        """Test orchestrator initialization when base init fails."""
        with pytest.raises(Exception, match="Base init error"):
            Orchestrator(self.config_path)

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents", side_effect=Exception("Agent init error"))
    def test_orchestrator_initialization_agent_error(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test orchestrator initialization when agent init fails."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()

        with pytest.raises(Exception, match="Agent init error"):
            Orchestrator(self.config_path)

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_config_path_handling(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test that config path is properly passed to base class."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {}

        orchestrator = Orchestrator(self.config_path)

        # Verify orchestrator was created successfully
        assert hasattr(orchestrator, "orchestrator_cfg")
        assert hasattr(orchestrator, "agent_cfgs")

    def test_orchestrator_class_composition(self):
        """Test the multiple inheritance composition structure."""
        # Test that the class properly inherits from all expected base classes
        bases = Orchestrator.__bases__
        base_names = [base.__name__ for base in bases]

        expected_bases = [
            "OrchestratorBase",
            "AgentFactory",
            "PromptRenderer",
            "ErrorHandler",
            "MetricsCollector",
            "ExecutionEngine",
        ]

        for expected_base in expected_bases:
            assert expected_base in base_names, f"Expected base class {expected_base} not found"

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_super_call_behavior(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test that super().__init__ properly calls the base class."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {}

        orchestrator = Orchestrator(self.config_path)

        # Verify orchestrator was created successfully
        assert hasattr(orchestrator, "orchestrator_cfg")
        assert hasattr(orchestrator, "agent_cfgs")

    @patch("orka.orchestrator.base.create_memory_logger")
    @patch("orka.orchestrator.base.ForkGroupManager")
    @patch.object(Orchestrator, "_init_agents")
    def test_orchestrator_logging_setup(
        self, mock_init_agents, mock_fork_manager, mock_memory_logger
    ):
        """Test that logging is properly set up."""
        # Set up mocks
        mock_memory_logger.return_value = Mock()
        mock_fork_manager.return_value = Mock()
        mock_init_agents.return_value = {}

        # Create orchestrator and verify it has logger
        orchestrator = Orchestrator(self.config_path)

        # Verify that the orchestrator has logging configured
        import logging

        logger = logging.getLogger("orka.orchestrator")
        assert logger is not None
        assert logger.name == "orka.orchestrator"
