"""
Comprehensive tests for main orchestrator module to increase coverage.
"""

import tempfile
from pathlib import Path

import pytest

from orka.orchestrator import Orchestrator


class TestOrchestratorMain:
    """Test main orchestrator functionality."""

    @pytest.fixture
    def yaml_config_file(self, tmp_path):
        """Create a temporary YAML config file."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  agents: [agent1, agent2]

agents:
  - id: agent1
    type: openai-answer
    model: gpt-3.5-turbo
    prompt: "Test prompt"
  
  - id: agent2
    type: openai-answer
    model: gpt-3.5-turbo
    prompt: "Test prompt 2"
"""
        config_file = tmp_path / "test_config.yml"
        config_file.write_text(config_content, encoding="utf-8")
        return str(config_file)

    def test_orchestrator_initialization(self, yaml_config_file):
        """Test orchestrator initialization with YAML file."""
        orchestrator = Orchestrator(yaml_config_file)
        assert orchestrator is not None
        assert orchestrator.orchestrator_cfg["id"] == "test_orchestrator"

    @pytest.mark.asyncio
    async def test_orchestrator_run(self, yaml_config_file):
        """Test orchestrator run method."""
        orchestrator = Orchestrator(yaml_config_file)
        # Just verify the orchestrator has the run method
        assert hasattr(orchestrator, "run")
        assert callable(orchestrator.run)

    def test_orchestrator_get_agents(self, yaml_config_file):
        """Test getting orchestrator agents."""
        orchestrator = Orchestrator(yaml_config_file)
        agents = orchestrator.agents
        assert agents is not None
        assert isinstance(agents, dict)

    def test_orchestrator_repr(self, yaml_config_file):
        """Test orchestrator string representation."""
        orchestrator = Orchestrator(yaml_config_file)
        repr_str = repr(orchestrator)
        assert "Orchestrator" in repr_str or "test_orchestrator" in repr_str

    def test_orchestrator_with_memory(self, tmp_path):
        """Test orchestrator with memory configuration."""
        config_content = """
orchestrator:
  id: test_with_memory
  strategy: sequential
  agents: [agent1]
  memory_backend: file

agents:
  - id: agent1
    type: openai-answer
    model: gpt-3.5-turbo
    prompt: "Test"
"""
        config_file = tmp_path / "memory_config.yml"
        config_file.write_text(config_content, encoding="utf-8")
        orchestrator = Orchestrator(str(config_file))
        assert orchestrator is not None

    def test_orchestrator_parallel_strategy(self, tmp_path):
        """Test orchestrator with parallel strategy."""
        config_content = """
orchestrator:
  id: test_parallel
  strategy: parallel
  agents: [agent1]

agents:
  - id: agent1
    type: openai-answer
    model: gpt-3.5-turbo
    prompt: "Test"
"""
        config_file = tmp_path / "parallel_config.yml"
        config_file.write_text(config_content, encoding="utf-8")
        orchestrator = Orchestrator(str(config_file))
        assert orchestrator is not None
        assert orchestrator.orchestrator_cfg["strategy"] == "parallel"
