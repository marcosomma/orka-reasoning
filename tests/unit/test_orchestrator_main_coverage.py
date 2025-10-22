"""
Comprehensive tests for main orchestrator module to increase coverage.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from orka.orchestrator import Orchestrator


class TestOrchestratorMain:
    """Test main orchestrator functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return {
            "orchestrator": {
                "id": "test_orchestrator",
                "strategy": "sequential",
                "agents": ["agent1", "agent2"]
            },
            "agents": [
                {
                    "id": "agent1",
                    "type": "mock",
                    "prompt": "Test prompt"
                },
                {
                    "id": "agent2",
                    "type": "mock",
                    "prompt": "Test prompt 2"
                }
            ]
        }

    def test_orchestrator_initialization(self, mock_config):
        """Test orchestrator initialization."""
        with patch('orka.orchestrator.ExecutionEngine'):
            orchestrator = Orchestrator(mock_config)
            assert orchestrator is not None

    def test_orchestrator_with_yaml_string(self):
        """Test orchestrator initialization with YAML string."""
        yaml_config = """
orchestrator:
  id: test
  strategy: sequential
  agents: [agent1]
agents:
  - id: agent1
    type: mock
    prompt: test
"""
        with patch('orka.orchestrator.YAMLLoader'):
            with patch('orka.orchestrator.ExecutionEngine'):
                orchestrator = Orchestrator(yaml_config)
                assert orchestrator is not None

    @pytest.mark.asyncio
    async def test_orchestrator_run(self, mock_config):
        """Test orchestrator run method."""
        with patch('orka.orchestrator.ExecutionEngine') as mock_engine:
            mock_engine.return_value.run = AsyncMock(return_value={"result": "success"})
            orchestrator = Orchestrator(mock_config)
            result = await orchestrator.run("test input")
            assert result is not None

    def test_orchestrator_get_agents(self, mock_config):
        """Test getting orchestrator agents."""
        with patch('orka.orchestrator.ExecutionEngine'):
            orchestrator = Orchestrator(mock_config)
            agents = orchestrator.get_agents()
            assert agents is not None

    def test_orchestrator_repr(self, mock_config):
        """Test orchestrator string representation."""
        with patch('orka.orchestrator.ExecutionEngine'):
            orchestrator = Orchestrator(mock_config)
            repr_str = repr(orchestrator)
            assert "Orchestrator" in repr_str

    def test_orchestrator_with_memory(self, mock_config):
        """Test orchestrator with memory configuration."""
        mock_config["orchestrator"]["memory"] = {
            "enabled": True,
            "type": "redis"
        }
        with patch('orka.orchestrator.ExecutionEngine'):
            orchestrator = Orchestrator(mock_config)
            assert orchestrator is not None

    def test_orchestrator_parallel_strategy(self):
        """Test orchestrator with parallel strategy."""
        config = {
            "orchestrator": {
                "id": "test",
                "strategy": "parallel",
                "agents": ["agent1"]
            },
            "agents": [
                {"id": "agent1", "type": "mock", "prompt": "test"}
            ]
        }
        with patch('orka.orchestrator.ExecutionEngine'):
            orchestrator = Orchestrator(config)
            assert orchestrator is not None
