"""
Basic performance tests for OrKa core components.
Tests performance characteristics of key operations.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from orka.loader import YAMLLoader
from orka.registry import ResourceRegistry


class TestBasicPerformance:
    """Basic performance tests for core components."""

    def test_yaml_loader_performance(self, temp_yaml_config):
        """Test YAML loading performance."""
        start_time = time.time()

        loader = YAMLLoader(temp_yaml_config)
        loader.validate()

        end_time = time.time()
        duration = end_time - start_time

        # Should load and validate in under 1 second
        assert duration < 1.0, f"YAML loading took {duration:.3f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_registry_initialization_performance(self):
        """Test registry initialization performance."""
        config = {
            f"test_resource_{i}": {
                "type": "custom",
                "config": {"module": "test.module", "class": "TestClass"},
            }
            for i in range(10)
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_class = MagicMock()
            mock_module.TestClass = mock_class
            mock_class.return_value = MagicMock()
            mock_import.return_value = mock_module

            start_time = time.time()

            registry = ResourceRegistry(config)
            await registry.initialize()

            end_time = time.time()
            duration = end_time - start_time

            # Should initialize 10 resources in under 1 second
            assert duration < 1.0, f"Registry initialization took {duration:.3f}s, expected < 1.0s"

    def test_multiple_yaml_loads_performance(self, temp_yaml_config):
        """Test performance of multiple YAML loads."""
        start_time = time.time()

        # Load the same config multiple times
        for _ in range(10):
            loader = YAMLLoader(temp_yaml_config)
            loader.validate()

        end_time = time.time()
        duration = end_time - start_time

        # Should load 10 times in under 2 seconds
        assert duration < 2.0, f"10 YAML loads took {duration:.3f}s, expected < 2.0s"

    @pytest.mark.slow
    def test_large_config_performance(self, tmp_path):
        """Test performance with large configuration (marked as slow)."""
        # Create a large config with many agents
        agents = []
        for i in range(100):
            agents.append(f"""
  - id: agent_{i}
    type: openai-answer
    queue: orka:agent_{i}
    prompt: "Agent {i}: {{{{ input }}}}"
    config:
      model: "gpt-4"
      temperature: 0.{i % 10}
""")

        config_content = f"""
orchestrator:
  id: large_test
  strategy: parallel
  queue: orka:large
  agents: {[f"agent_{i}" for i in range(100)]}
  max_parallel: 10

agents:{" ".join(agents)}

memory:
  backend: redis
  url: redis://localhost:6379

nodes:
  - type: memory-writer
    id: memory_writer
    queue: orka:memory
"""

        config_file = tmp_path / "large.yml"
        config_file.write_text(config_content)

        start_time = time.time()

        loader = YAMLLoader(str(config_file))
        loader.validate()

        end_time = time.time()
        duration = end_time - start_time

        # Should handle large config in under 5 seconds
        assert duration < 5.0, f"Large config loading took {duration:.3f}s, expected < 5.0s"

        # Verify structure
        config = loader.config
        assert len(config["agents"]) == 100
        assert len(config["orchestrator"]["agents"]) == 100
