"""Unit tests for orka.loader - simplified version."""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock
from orka.loader import YAMLLoader


# Skip auto-mocking for this test
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestYAMLLoaderSimple:
    """Simplified test suite for YAMLLoader class."""

    def test_init_and_basic_functionality(self):
        """Test initialization and basic functionality."""
        config_content = """
orchestrator:
  id: test_workflow
  strategy: sequential
agents:
  - id: test_agent
    type: local_llm
    prompt: "Test: {{ input }}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            # Test initialization
            loader = YAMLLoader(temp_file)
            
            # Test attributes
            assert loader.path == temp_file
            assert loader.config is not None
            assert isinstance(loader.config, dict)
            
            # Test get_orchestrator
            orchestrator_config = loader.get_orchestrator()
            assert orchestrator_config["id"] == "test_workflow"
            assert orchestrator_config["strategy"] == "sequential"
            
            # Test get_agents
            agents_config = loader.get_agents()
            assert len(agents_config) == 1
            assert agents_config[0]["id"] == "test_agent"
            assert agents_config[0]["type"] == "local_llm"
            
        finally:
            os.unlink(temp_file)

    def test_nonexistent_file(self):
        """Test with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            YAMLLoader("/nonexistent/file.yml")

    def test_validation_success(self):
        """Test validation with valid config."""
        config_content = """
orchestrator:
  id: test_workflow
agents:
  - id: test_agent
    type: local_llm
    prompt: "Valid template: {{ input }}"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            # Mock the template validator to avoid dependency issues
            with patch('orka.utils.template_validator.TemplateValidator') as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate_template.return_value = (True, "", [])
                mock_validator_class.return_value = mock_validator
                
                loader = YAMLLoader(temp_file)
                result = loader.validate()
                
                assert result is True
                mock_validator.validate_template.assert_called()
                
        finally:
            os.unlink(temp_file)

    def test_validation_missing_orchestrator(self):
        """Test validation with missing orchestrator."""
        config_content = """
agents:
  - id: test_agent
    type: local_llm
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            loader = YAMLLoader(temp_file)
            with pytest.raises(ValueError, match="Missing 'orchestrator' section"):
                loader.validate()
        finally:
            os.unlink(temp_file)

    def test_validation_missing_agents(self):
        """Test validation with missing agents."""
        config_content = """
orchestrator:
  id: test_workflow
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            loader = YAMLLoader(temp_file)
            with pytest.raises(ValueError, match="Missing 'agents' section"):
                loader.validate()
        finally:
            os.unlink(temp_file)

    def test_validation_agents_not_list(self):
        """Test validation when agents is not a list."""
        config_content = """
orchestrator:
  id: test_workflow
agents:
  test_agent:
    type: local_llm
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            loader = YAMLLoader(temp_file)
            with pytest.raises(ValueError, match="'agents' should be a list"):
                loader.validate()
        finally:
            os.unlink(temp_file)

    def test_template_validation_failure(self):
        """Test template validation failure."""
        config_content = """
orchestrator:
  id: test_workflow
agents:
  - id: test_agent
    type: local_llm
    prompt: "Invalid template"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            with patch('orka.utils.template_validator.TemplateValidator') as mock_validator_class:
                mock_validator = Mock()
                mock_validator.validate_template.return_value = (False, "Template error", [])
                mock_validator_class.return_value = mock_validator
                
                loader = YAMLLoader(temp_file)
                with pytest.raises(ValueError, match="Template validation failed"):
                    loader.validate()
                    
        finally:
            os.unlink(temp_file)

    def test_get_methods_with_missing_sections(self):
        """Test get methods when sections are missing."""
        config_content = """
some_other_section:
  value: test
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_file = f.name
        
        try:
            loader = YAMLLoader(temp_file)
            
            # Should return empty dict/list for missing sections
            assert loader.get_orchestrator() == {}
            assert loader.get_agents() == []
            
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
