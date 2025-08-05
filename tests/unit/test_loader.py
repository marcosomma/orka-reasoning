"""
Unit tests for the orka.loader module.
Tests configuration loading and validation functionality.
"""

import pytest
import yaml

from orka.loader import YAMLLoader


class TestYAMLLoader:
    """Test the YAMLLoader class functionality."""

    def test_yaml_loader_init_success(self, temp_yaml_config):
        """Test successful YAMLLoader initialization."""
        loader = YAMLLoader(temp_yaml_config)

        # Should have loaded config
        assert loader.path == temp_yaml_config
        assert isinstance(loader.config, dict)
        assert "orchestrator" in loader.config
        assert "agents" in loader.config

    def test_yaml_loader_init_file_not_found(self):
        """Test error handling when config file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            YAMLLoader("/nonexistent/config.yml")

    def test_yaml_loader_init_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML syntax."""
        # Create invalid YAML file
        invalid_yaml = tmp_path / "invalid.yml"
        invalid_yaml.write_text("invalid: yaml: content: [unclosed")

        with pytest.raises(yaml.YAMLError):
            YAMLLoader(str(invalid_yaml))

    def test_get_orchestrator_success(self, temp_yaml_config):
        """Test successful orchestrator config retrieval."""
        loader = YAMLLoader(temp_yaml_config)
        orchestrator = loader.get_orchestrator()

        assert isinstance(orchestrator, dict)
        assert orchestrator["id"] == "test_orchestrator"
        assert orchestrator["strategy"] == "sequential"
        assert orchestrator["queue"] == "orka:test"

    def test_get_agents_success(self, temp_yaml_config):
        """Test successful agents config retrieval."""
        loader = YAMLLoader(temp_yaml_config)
        agents = loader.get_agents()

        assert isinstance(agents, list)
        assert len(agents) == 1
        assert agents[0]["id"] == "test_agent"
        assert agents[0]["type"] == "openai-answer"

    def test_get_orchestrator_missing_section(self, tmp_path):
        """Test get_orchestrator with missing orchestrator section."""
        config_content = """
agents:
  - id: test_agent
    type: openai-answer
"""
        config_file = tmp_path / "no_orchestrator.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))
        orchestrator = loader.get_orchestrator()

        # Should return empty dict when section is missing
        assert orchestrator == {}

    def test_get_agents_missing_section(self, tmp_path):
        """Test get_agents with missing agents section."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
"""
        config_file = tmp_path / "no_agents.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))
        agents = loader.get_agents()

        # Should return empty list when section is missing
        assert agents == []

    def test_validate_success(self, temp_yaml_config):
        """Test successful validation."""
        loader = YAMLLoader(temp_yaml_config)
        result = loader.validate()

        assert result is True

    def test_validate_missing_orchestrator(self, tmp_path):
        """Test validation error when orchestrator section is missing."""
        config_content = """
agents:
  - id: test_agent
    type: openai-answer
"""
        config_file = tmp_path / "no_orchestrator.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))

        with pytest.raises(ValueError, match="Missing 'orchestrator' section"):
            loader.validate()

    def test_validate_missing_agents(self, tmp_path):
        """Test validation error when agents section is missing."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
"""
        config_file = tmp_path / "no_agents.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))

        with pytest.raises(ValueError, match="Missing 'agents' section"):
            loader.validate()

    def test_validate_agents_not_list(self, tmp_path):
        """Test validation error when agents is not a list."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
agents: "not a list"
"""
        config_file = tmp_path / "agents_not_list.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))

        with pytest.raises(ValueError, match="'agents' should be a list"):
            loader.validate()

    def test_validate_empty_agents_list(self, tmp_path):
        """Test validation with empty agents list."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
agents: []
"""
        config_file = tmp_path / "empty_agents.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))
        result = loader.validate()

        # Should pass validation even with empty agents list
        assert result is True

    def test_complex_config_structure(self, tmp_path):
        """Test loading a more complex configuration structure."""
        config_content = """
orchestrator:
  id: complex_orchestrator
  strategy: parallel
  queue: orka:complex
  max_parallel: 5
  timeout: 300

agents:
  - id: classifier
    type: openai-classification
    queue: orka:classifier
    prompt: "Classify: {{ input }}"
    options:
      - tech
      - science
      
  - id: router
    type: router
    params:
      decision_key: classifier
      routing_map:
        tech: ["answer_builder"]
        science: ["answer_builder"]
        
  - id: answer_builder
    type: openai-answer
    queue: orka:answer
    prompt: "Answer: {{ input }}"
    depends_on:
      - router

memory:
  backend: redis
  url: redis://localhost:6379
  
nodes:
  - type: memory-writer
    id: mem_writer
    queue: orka:memory
"""
        config_file = tmp_path / "complex.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))

        # Test validation
        assert loader.validate() is True

        # Test complex structure retrieval
        orchestrator = loader.get_orchestrator()
        agents = loader.get_agents()

        assert orchestrator["strategy"] == "parallel"
        assert orchestrator["max_parallel"] == 5
        assert len(agents) == 3
        assert "memory" in loader.config
        assert "nodes" in loader.config

    def test_special_characters_config(self, tmp_path):
        """Test loading config with basic special characters."""
        config_content = """
orchestrator:
  id: special_test_config
  strategy: sequential
  description: "Test with underscores_and-dashes"

agents:
  - id: test_agent_with_underscores
    type: openai-answer
    prompt: "Process this input: {{ input }}"
"""
        config_file = tmp_path / "special.yml"
        config_file.write_text(config_content)

        loader = YAMLLoader(str(config_file))

        assert loader.validate() is True

        orchestrator = loader.get_orchestrator()
        agents = loader.get_agents()

        assert orchestrator["id"] == "special_test_config"
        assert "underscores_and-dashes" in orchestrator["description"]
        assert agents[0]["id"] == "test_agent_with_underscores"

    def test_empty_config_file(self, tmp_path):
        """Test error handling for empty config file."""
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        # Empty YAML file should load as None, which becomes an empty dict
        loader = YAMLLoader(str(empty_file))
        # This will likely cause a TypeError when trying to call .get() on None
        with pytest.raises((TypeError, AttributeError)):
            loader.get_orchestrator()

    def test_yaml_loader_path_attribute(self, temp_yaml_config):
        """Test that path attribute is set correctly."""
        loader = YAMLLoader(temp_yaml_config)
        assert loader.path == temp_yaml_config

    def test_yaml_loader_config_attribute(self, temp_yaml_config):
        """Test that config attribute contains loaded data."""
        loader = YAMLLoader(temp_yaml_config)
        assert hasattr(loader, "config")
        assert isinstance(loader.config, dict)
        assert len(loader.config) > 0
