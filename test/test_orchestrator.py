"""
Tests for the main orchestrator.py file.
This test specifically targets the orka/orchestrator.py file to achieve 100% coverage.
"""

import importlib.util
import os
import sys
import tempfile
from unittest.mock import patch


class TestOrchestratorPyFile:
    """Test the main Orchestrator class from orchestrator.py file specifically."""

    def test_orchestrator_py_file_direct_import(self):
        """Test directly importing the orchestrator.py file to achieve coverage."""
        # Add the project root to sys.path to enable relative imports
        project_root = os.path.abspath(".")
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            # Load the orchestrator.py file directly using importlib
            spec = importlib.util.spec_from_file_location(
                "orka_orchestrator_py_module",
                "orka/orchestrator.py",
            )
            orchestrator_py_module = importlib.util.module_from_spec(spec)

            # Add the module to sys.modules to support relative imports
            sys.modules["orka_orchestrator_py_module"] = orchestrator_py_module

            # Execute the module - this will trigger all the import statements
            spec.loader.exec_module(orchestrator_py_module)

            # Test that the module was loaded correctly
            assert hasattr(orchestrator_py_module, "Orchestrator")
            assert hasattr(orchestrator_py_module, "logger")
            assert hasattr(orchestrator_py_module, "AgentFactory")
            assert hasattr(orchestrator_py_module, "OrchestratorBase")
            assert hasattr(orchestrator_py_module, "ErrorHandler")
            assert hasattr(orchestrator_py_module, "ExecutionEngine")
            assert hasattr(orchestrator_py_module, "MetricsCollector")
            assert hasattr(orchestrator_py_module, "PromptRenderer")

            # Test the logger
            assert orchestrator_py_module.logger.name == "orka_orchestrator_py_module"

            # Test the Orchestrator class
            Orchestrator = orchestrator_py_module.Orchestrator
            assert issubclass(Orchestrator, orchestrator_py_module.OrchestratorBase)
            assert issubclass(Orchestrator, orchestrator_py_module.AgentFactory)
            assert issubclass(Orchestrator, orchestrator_py_module.PromptRenderer)
            assert issubclass(Orchestrator, orchestrator_py_module.ErrorHandler)
            assert issubclass(Orchestrator, orchestrator_py_module.MetricsCollector)
            assert issubclass(Orchestrator, orchestrator_py_module.ExecutionEngine)

        finally:
            # Clean up
            if "orka_orchestrator_py_module" in sys.modules:
                del sys.modules["orka_orchestrator_py_module"]
            if project_root in sys.path:
                sys.path.remove(project_root)

    def test_orchestrator_py_initialization(self):
        """Test that the Orchestrator class from orchestrator.py can be initialized."""
        # Add the project root to sys.path
        project_root = os.path.abspath(".")
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            # Load the orchestrator.py file directly
            spec = importlib.util.spec_from_file_location(
                "orka_orchestrator_py_init",
                "orka/orchestrator.py",
            )
            orchestrator_py_module = importlib.util.module_from_spec(spec)
            sys.modules["orka_orchestrator_py_init"] = orchestrator_py_module
            spec.loader.exec_module(orchestrator_py_module)

            Orchestrator = orchestrator_py_module.Orchestrator

            # Create a temporary YAML config file
            config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-answer
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
"""

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                f.write(config_content)
                config_path = f.name

            try:
                # Mock the dependencies to avoid actual initialization
                with patch("orka.orchestrator.base.OrchestratorBase.__init__") as mock_base_init:
                    with patch.object(Orchestrator, "_init_agents") as mock_init_agents:
                        mock_base_init.return_value = None
                        mock_init_agents.return_value = {}

                        # Test initialization - this will exercise the __init__ method
                        orchestrator = Orchestrator(config_path)

                        # Verify the initialization was called
                        mock_base_init.assert_called_once_with(config_path)
                        mock_init_agents.assert_called_once()

                        # Verify the agents attribute is set
                        assert hasattr(orchestrator, "agents")
                        assert orchestrator.agents == {}

            finally:
                # Clean up the temporary file
                os.unlink(config_path)

        finally:
            # Clean up
            if "orka_orchestrator_py_init" in sys.modules:
                del sys.modules["orka_orchestrator_py_init"]
            if project_root in sys.path:
                sys.path.remove(project_root)

    def test_orchestrator_py_method_resolution_order(self):
        """Test that the MRO is correct for the Orchestrator class in orchestrator.py."""
        # Add the project root to sys.path
        project_root = os.path.abspath(".")
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            # Load the orchestrator.py file directly
            spec = importlib.util.spec_from_file_location(
                "orka_orchestrator_py_mro",
                "orka/orchestrator.py",
            )
            orchestrator_py_module = importlib.util.module_from_spec(spec)
            sys.modules["orka_orchestrator_py_mro"] = orchestrator_py_module
            spec.loader.exec_module(orchestrator_py_module)

            Orchestrator = orchestrator_py_module.Orchestrator
            mro = Orchestrator.__mro__

            # The MRO should start with Orchestrator itself
            assert mro[0] == Orchestrator

            # Verify that all expected classes are in the MRO
            mro_names = [cls.__name__ for cls in mro]
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
                assert expected_class in mro_names, f"{expected_class} not found in MRO"

        finally:
            # Clean up
            if "orka_orchestrator_py_mro" in sys.modules:
                del sys.modules["orka_orchestrator_py_mro"]
            if project_root in sys.path:
                sys.path.remove(project_root)
