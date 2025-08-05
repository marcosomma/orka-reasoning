"""
Basic integration tests for OrKa core components.
Tests how the main components work together.
"""

from unittest.mock import MagicMock, patch

import pytest

from orka.loader import YAMLLoader
from orka.orchestrator import Orchestrator
from orka.registry import ResourceRegistry, init_registry


class TestBasicIntegration:
    """Test basic integration between core components."""

    def test_yaml_loader_and_orchestrator_integration(self, temp_yaml_config):
        """Test that YAMLLoader works with Orchestrator initialization."""
        # Load config using YAMLLoader
        loader = YAMLLoader(temp_yaml_config)
        config = loader.config

        # Verify config structure
        assert "orchestrator" in config
        assert "agents" in config

        # Test that config can be validated
        assert loader.validate() is True

    @pytest.mark.asyncio
    async def test_registry_initialization_with_config(self):
        """Test ResourceRegistry initialization with various resource types."""
        config = {
            "test_redis": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
        }

        with patch("orka.registry.redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            registry = init_registry(config)
            await registry.initialize()

            # Should have initialized successfully
            assert registry._initialized
            assert "test_redis" in registry._resources

    def test_config_validation_flow(self, tmp_path):
        """Test the complete config validation flow."""
        # Create a complete config
        config_content = """
orchestrator:
  id: integration_test
  strategy: sequential
  queue: orka:integration
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-answer
    queue: orka:test_queue
    prompt: "Integration test: {{ input }}"
    config:
      model: "gpt-4"
      temperature: 0.7

memory:
  backend: redis
  url: redis://localhost:6379

nodes:
  - type: memory-writer
    id: memory_writer
    queue: orka:memory
"""
        config_file = tmp_path / "integration.yml"
        config_file.write_text(config_content)

        # Load and validate config
        loader = YAMLLoader(str(config_file))

        # Should validate successfully
        assert loader.validate() is True

        # Check structure
        config = loader.config
        assert config["orchestrator"]["id"] == "integration_test"
        assert len(config["agents"]) == 1
        assert config["agents"][0]["type"] == "openai-answer"
        assert "memory" in config
        assert "nodes" in config

    @pytest.mark.asyncio
    @patch("orka.orchestrator.OrchestratorBase.__init__")
    @patch.object(Orchestrator, "_init_agents")
    async def test_orchestrator_with_registry_integration(
        self,
        mock_init_agents,
        mock_base_init,
        temp_yaml_config,
    ):
        """Test Orchestrator working with ResourceRegistry."""
        # Mock the orchestrator initialization
        mock_base_init.return_value = None
        mock_init_agents.return_value = {}

        # Create and initialize a registry
        registry_config = {
            "openai": {
                "type": "openai",
                "config": {"api_key": "test-key"},
            },
        }

        with patch("orka.registry.AsyncOpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()

            registry = ResourceRegistry(registry_config)
            await registry.initialize()

            # Initialize orchestrator
            orchestrator = Orchestrator(temp_yaml_config)

            # Both should be properly initialized
            assert registry._initialized
            assert hasattr(orchestrator, "agents")

    def test_error_handling_integration(self, tmp_path):
        """Test error handling across components."""
        # Test invalid YAML
        invalid_config = tmp_path / "invalid.yml"
        invalid_config.write_text("invalid: yaml: [unclosed")

        with pytest.raises(Exception):  # Should raise YAML error
            YAMLLoader(str(invalid_config))

        # Test missing file
        with pytest.raises(FileNotFoundError):
            YAMLLoader("nonexistent.yml")

    def test_contract_usage_across_components(self):
        """Test that contracts work across different components."""

        # Create test data using contracts
        context = {
            "input": "test input",
            "previous_outputs": {},
            "metadata": {"test": True},
        }

        output = {
            "content": "test output",
            "success": True,
            "metadata": {"agent_id": "test_agent"},
        }

        resource_config = {
            "type": "redis",
            "config": {"url": "redis://localhost:6379"},
        }

        # All should work as regular dictionaries
        assert context["input"] == "test input"
        assert output["success"] is True
        assert resource_config["type"] == "redis"

    @pytest.mark.asyncio
    async def test_component_lifecycle_integration(self):
        """Test the complete lifecycle of components working together."""
        # 1. Create config
        config = {
            "test_resource": {
                "type": "redis",
                "config": {"url": "redis://localhost:6379"},
            },
        }

        # 2. Initialize registry
        with patch("orka.registry.redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()

            registry = ResourceRegistry(config)
            await registry.initialize()

            # 3. Use resource
            resource = registry.get("test_resource")
            assert resource is not None

            # 4. Cleanup
            await registry.close()

    def test_configuration_completeness(self, tmp_path):
        """Test that a complete configuration works end-to-end."""
        # Create a comprehensive config
        config_content = """
orchestrator:
  id: complete_test
  strategy: parallel
  queue: orka:complete
  agents:
    - classifier
    - processor
    - responder
  max_parallel: 3
  timeout: 300

agents:
  - id: classifier
    type: openai-classification
    queue: orka:classifier
    prompt: "Classify this input: {{ input }}"
    config:
      model: "gpt-4"
      options:
        - technical
        - business
        - personal
        
  - id: processor
    type: openai-answer
    queue: orka:processor
    prompt: "Process this classified input: {{ input }}"
    depends_on:
      - classifier
    config:
      model: "gpt-4"
      temperature: 0.5
      
  - id: responder
    type: openai-answer
    queue: orka:responder
    prompt: "Generate final response: {{ previous_outputs.processor }}"
    depends_on:
      - processor
    config:
      model: "gpt-4"
      temperature: 0.3

memory:
  backend: redis
  url: redis://localhost:6379
  namespace: complete_test

nodes:
  - type: memory-writer
    id: mem_writer
    queue: orka:memory
    
  - type: memory-reader
    id: mem_reader
    queue: orka:memory_read
"""

        config_file = tmp_path / "complete.yml"
        config_file.write_text(config_content)

        # Load and validate
        loader = YAMLLoader(str(config_file))
        assert loader.validate() is True

        # Check all sections
        config = loader.config
        assert len(config["agents"]) == 3
        assert config["orchestrator"]["strategy"] == "parallel"
        assert config["orchestrator"]["max_parallel"] == 3
        assert "memory" in config
        assert len(config["nodes"]) == 2

        # Verify agent dependencies
        processor = next(a for a in config["agents"] if a["id"] == "processor")
        responder = next(a for a in config["agents"] if a["id"] == "responder")

        assert "depends_on" in processor
        assert "classifier" in processor["depends_on"]
        assert "depends_on" in responder
        assert "processor" in responder["depends_on"]

    def test_module_imports_integration(self):
        """Test that all core modules can be imported together."""
        try:
            from orka.contracts import Context, Output, ResourceConfig
            from orka.loader import YAMLLoader
            from orka.orchestrator import Orchestrator
            from orka.registry import ResourceRegistry, init_registry

            # All imports should succeed
            assert Orchestrator is not None
            assert YAMLLoader is not None
            assert ResourceRegistry is not None
            assert init_registry is not None
            assert Context is not None
            assert Output is not None
            assert ResourceConfig is not None

        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")

    def test_type_compatibility_integration(self):
        """Test that types work correctly across modules."""
        # Test that ResourceConfig from contracts works with registry
        from orka.contracts import ResourceConfig

        config: ResourceConfig = {
            "type": "redis",
            "config": {"url": "redis://localhost:6379"},
        }

        # Should work without type errors
        assert config["type"] == "redis"
        assert isinstance(config["config"], dict)

    def test_error_propagation_integration(self, tmp_path):
        """Test that errors propagate correctly between components."""
        # Create config with validation error
        bad_config = tmp_path / "bad.yml"
        bad_config.write_text("""
orchestrator:
  id: test
# Missing agents section
""")

        loader = YAMLLoader(str(bad_config))

        # Should raise validation error
        with pytest.raises(ValueError, match="Missing 'agents' section"):
            loader.validate()
