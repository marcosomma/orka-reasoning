"""
Basic orchestrator integration tests for OrKa.
Tests fundamental orchestrator and agent integration without complex workflows.
"""

from unittest.mock import MagicMock, patch

import pytest

from orka.loader import YAMLLoader
from orka.orchestrator import Orchestrator


class TestOrchestratorBasicIntegration:
    """Test basic orchestrator and agent integration."""

    @pytest.fixture
    def minimal_config(self, tmp_path):
        """Create minimal working configuration."""
        config_content = """
orchestrator:
  id: basic_test
  strategy: sequential
  queue: orka:basic
  agents:
    - simple_agent

agents:
  - id: simple_agent
    type: binary
    queue: orka:simple
    prompt: "Is this a question: {{ input }}"

memory:
  backend: redis
  url: redis://localhost:6380
  namespace: basic_test
"""
        config_file = tmp_path / "basic.yml"
        config_file.write_text(config_content)
        return str(config_file)

    def test_orchestrator_initialization(self, minimal_config):
        """Test that orchestrator can be initialized with valid config."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            orchestrator = Orchestrator(minimal_config)

            # Verify basic initialization
            assert orchestrator is not None
            assert hasattr(orchestrator, "agents")
            assert "simple_agent" in orchestrator.agents
            assert orchestrator.orchestrator_cfg["id"] == "basic_test"

    def test_config_loading_integration(self, minimal_config):
        """Test that YAML config loading works with orchestrator."""
        loader = YAMLLoader(minimal_config)
        config = loader.config

        # Verify config structure
        assert "orchestrator" in config
        assert "agents" in config
        assert config["orchestrator"]["id"] == "basic_test"
        assert len(config["agents"]) == 1
        assert config["agents"][0]["type"] == "binary"

    def test_agent_creation_integration(self, minimal_config):
        """Test that agents are properly created from config."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            orchestrator = Orchestrator(minimal_config)

            # Verify agent creation
            assert "simple_agent" in orchestrator.agents
            agent = orchestrator.agents["simple_agent"]
            assert agent is not None
            assert hasattr(agent, "agent_id")
            assert agent.agent_id == "simple_agent"

    def test_openai_agent_creation(self, tmp_path):
        """Test OpenAI agent creation and initialization."""
        config_content = """
orchestrator:
  id: openai_test
  strategy: sequential
  queue: orka:openai
  agents:
    - openai_agent

agents:
  - id: openai_agent
    type: openai-answer
    queue: orka:openai
    prompt: "Answer this: {{ input }}"
    config:
      model: "gpt-4"
      temperature: 0.5

memory:
  backend: redis
  url: redis://localhost:6380
  namespace: openai_test
"""
        config_file = tmp_path / "openai.yml"
        config_file.write_text(config_content)

        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            orchestrator = Orchestrator(str(config_file))

            # Verify OpenAI agent creation
            assert "openai_agent" in orchestrator.agents
            agent = orchestrator.agents["openai_agent"]
            assert agent.agent_id == "openai_agent"
            # Verify agent has OpenAI-specific attributes
            assert hasattr(agent, "prompt")

    def test_multiple_agents_creation(self, tmp_path):
        """Test creating multiple different agent types."""
        config_content = """
orchestrator:
  id: multi_test
  strategy: sequential
  queue: orka:multi
  agents:
    - binary_agent
    - classification_agent
    - openai_agent

agents:
  - id: binary_agent
    type: binary
    queue: orka:binary
    prompt: "Is this true: {{ input }}"
    
  - id: classification_agent
    type: classification
    queue: orka:classify
    prompt: "Classify: {{ input }}"
    options: [positive, negative, neutral]
    
  - id: openai_agent
    type: openai-answer
    queue: orka:openai
    prompt: "Answer: {{ input }}"
    config:
      model: "gpt-4"

memory:
  backend: redis
  url: redis://localhost:6380
  namespace: multi_test
"""
        config_file = tmp_path / "multi.yml"
        config_file.write_text(config_content)

        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            orchestrator = Orchestrator(str(config_file))

            # Verify all agents were created
            assert len(orchestrator.agents) == 3
            assert "binary_agent" in orchestrator.agents
            assert "classification_agent" in orchestrator.agents
            assert "openai_agent" in orchestrator.agents

            # Verify agent types
            binary_agent = orchestrator.agents["binary_agent"]
            classify_agent = orchestrator.agents["classification_agent"]
            openai_agent = orchestrator.agents["openai_agent"]

            assert binary_agent.agent_id == "binary_agent"
            assert classify_agent.agent_id == "classification_agent"
            assert openai_agent.agent_id == "openai_agent"

    def test_memory_backend_initialization(self, minimal_config):
        """Test that memory backend is properly initialized."""
        with patch("orka.memory.redisstack_logger.redis.ConnectionPool") as mock_pool:
            with patch("orka.memory.redisstack_logger.redis.Redis") as mock_redis:
                mock_redis_client = MagicMock()
                mock_redis.return_value = mock_redis_client
                mock_redis_client.ping.return_value = True

                orchestrator = Orchestrator(minimal_config)

                # Verify memory was initialized
                assert hasattr(orchestrator, "memory")
                assert orchestrator.memory is not None

                # Verify Redis connection pool was created for memory setup
                assert mock_pool.called or mock_redis.called

    def test_error_handling_invalid_config(self, tmp_path):
        """Test error handling for invalid configurations."""
        # Missing agents section
        bad_config = tmp_path / "bad.yml"
        bad_config.write_text(
            """
orchestrator:
  id: bad_test
  strategy: sequential
"""
        )

        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            with pytest.raises(ValueError, match="Missing 'agents' section"):
                loader = YAMLLoader(str(bad_config))
                loader.validate()

    def test_error_handling_unknown_agent_type(self, tmp_path):
        """Test error handling for unknown agent types."""
        bad_config = tmp_path / "unknown_agent.yml"
        bad_config.write_text(
            """
orchestrator:
  id: unknown_test
  strategy: sequential
  queue: orka:unknown
  agents:
    - unknown_agent

agents:
  - id: unknown_agent
    type: nonexistent_type
    queue: orka:unknown
    prompt: "Test"

memory:
  backend: redis
  url: redis://localhost:6380
"""
        )

        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            with pytest.raises(ValueError, match="Unsupported agent type"):
                Orchestrator(str(bad_config))

    def test_config_validation_integration(self, minimal_config):
        """Test that config validation works end-to-end."""
        loader = YAMLLoader(minimal_config)

        # Should validate successfully
        assert loader.validate() is True

        # Should be able to create orchestrator after validation
        with patch("redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            orchestrator = Orchestrator(minimal_config)
            assert orchestrator is not None
