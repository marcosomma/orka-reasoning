"""Unit tests for orka.orchestrator.base."""

import os
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from uuid import UUID

import pytest

from orka.orchestrator.base import OrchestratorBase

# Mark all tests in this module for unit testing with auto-mocking
pytestmark = [pytest.mark.unit]


class TestOrchestratorBase:
    """Test suite for OrchestratorBase class."""

    def create_temp_config(self, content):
        """Helper to create temporary config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(content)
            return f.name

    def cleanup_file(self, filepath):
        """Helper to safely cleanup temp files."""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception:
            pass  # Ignore cleanup errors

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_init_with_valid_config(self, mock_fork_manager, mock_create_memory):
        """Test initialization with a valid configuration file."""
        config_content = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
    prompt: "Test prompt"
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "strategy": "sequential",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm", "prompt": "Test prompt"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                MockLoader.assert_called_once_with(temp_file)
                mock_loader_instance.validate.assert_called_once()
                assert orchestrator.orchestrator_cfg["id"] == "test_orchestrator"
                assert len(orchestrator.agent_cfgs) == 1
                assert orchestrator.agent_cfgs[0]["id"] == "test_agent"
                assert orchestrator.queue == ["test_agent"]
                
        finally:
            self.cleanup_file(temp_file)

    def test_init_with_invalid_config(self):
        """Test initialization with an invalid configuration file raises ValueError."""
        config_content = """
orchestrator:
  id: test_orchestrator
# Missing agents section
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.validate.side_effect = ValueError("Missing 'agents' section")
                MockLoader.return_value = mock_loader_instance
                
                with pytest.raises(ValueError, match="Missing 'agents' section"):
                    OrchestratorBase(temp_file)
                    
        finally:
            self.cleanup_file(temp_file)

    def test_init_with_nonexistent_file(self):
        """Test initialization with a nonexistent file raises FileNotFoundError."""
        with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
            MockLoader.side_effect = FileNotFoundError("File not found")
            
            with pytest.raises(FileNotFoundError):
                OrchestratorBase("/nonexistent/config.yml")

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_run_id_generation(self, mock_fork_manager, mock_create_memory):
        """Test that run_id is properly generated as a UUID."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                # Verify run_id is a valid UUID string
                assert isinstance(orchestrator.run_id, str)
                # Should be able to parse as UUID
                uuid_obj = UUID(orchestrator.run_id)
                assert str(uuid_obj) == orchestrator.run_id
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_initialization_state(self, mock_fork_manager, mock_create_memory):
        """Test that initial state variables are properly set."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                # Check initial state
                assert orchestrator.step_index == 0
                assert orchestrator.queue == ["test_agent"]
                assert orchestrator.memory == mock_memory_instance
                assert orchestrator.fork_manager == mock_fork_instance
                assert hasattr(orchestrator, 'error_telemetry')
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_fork_group_manager_initialization(self, mock_fork_manager, mock_create_memory):
        """Test that ForkGroupManager is properly initialized."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                mock_fork_manager.assert_called_once_with(mock_memory_instance.redis)
                assert orchestrator.fork_manager == mock_fork_instance
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_config_extraction(self, mock_fork_manager, mock_create_memory):
        """Test that orchestrator and agents configurations are properly extracted."""
        config_content = """
orchestrator:
  id: complex_orchestrator
  strategy: parallel
  max_retries: 3
  timeout: 300
  agents:
    - agent1
    - agent2
agents:
  - id: agent1
    type: local_llm
    prompt: "Agent 1 prompt"
  - id: agent2
    type: llm
    model: "gpt-4"
    prompt: "Agent 2 prompt"
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                orchestrator_cfg = {
                    "id": "complex_orchestrator",
                    "strategy": "parallel",
                    "max_retries": 3,
                    "timeout": 300,
                    "agents": ["agent1", "agent2"]
                }
                agents_cfg = [
                    {"id": "agent1", "type": "local_llm", "prompt": "Agent 1 prompt"},
                    {"id": "agent2", "type": "llm", "model": "gpt-4", "prompt": "Agent 2 prompt"}
                ]
                mock_loader_instance.get_orchestrator.return_value = orchestrator_cfg
                mock_loader_instance.get_agents.return_value = agents_cfg
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                assert orchestrator.orchestrator_cfg == orchestrator_cfg
                assert orchestrator.agent_cfgs == agents_cfg
                assert orchestrator.orchestrator_cfg["strategy"] == "parallel"
                assert orchestrator.orchestrator_cfg["max_retries"] == 3
                assert len(orchestrator.agent_cfgs) == 2
                assert orchestrator.queue == ["agent1", "agent2"]
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_multiple_instances_have_unique_run_ids(self, mock_fork_manager, mock_create_memory):
        """Test that multiple orchestrator instances have unique run IDs."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator1 = OrchestratorBase(temp_file)
                orchestrator2 = OrchestratorBase(temp_file)
                
                assert orchestrator1.run_id != orchestrator2.run_id
                # Both should be valid UUIDs
                UUID(orchestrator1.run_id)
                UUID(orchestrator2.run_id)
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_empty_agents_config(self, mock_fork_manager, mock_create_memory):
        """Test handling of empty agents configuration."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents: []
agents: []
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": []
                }
                mock_loader_instance.get_agents.return_value = []
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                assert orchestrator.agent_cfgs == []
                assert len(orchestrator.agent_cfgs) == 0
                assert orchestrator.queue == []
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_memory_logger_initialization(self, mock_fork_manager, mock_create_memory):
        """Test that memory logger is properly initialized."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader:
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                # Verify memory logger was created with expected parameters
                mock_create_memory.assert_called_once()
                call_kwargs = mock_create_memory.call_args[1]
                assert call_kwargs["backend"] == "redisstack"
                assert "redis_url" in call_kwargs
                assert orchestrator.memory == mock_memory_instance
                
        finally:
            self.cleanup_file(temp_file)

    @patch('orka.orchestrator.base.create_memory_logger')
    @patch('orka.orchestrator.base.ForkGroupManager')
    def test_decay_config_initialization(self, mock_fork_manager, mock_create_memory):
        """Test that decay configuration is properly initialized."""
        config_content = """
orchestrator:
  id: test_orchestrator
  agents:
    - test_agent
agents:
  - id: test_agent
    type: local_llm
"""
        temp_file = self.create_temp_config(config_content)
        
        try:
            # Mock memory logger
            mock_memory_instance = Mock()
            mock_memory_instance.redis = Mock()
            mock_create_memory.return_value = mock_memory_instance
            
            # Mock fork manager
            mock_fork_instance = Mock()
            mock_fork_manager.return_value = mock_fork_instance
            
            with patch('orka.orchestrator.base.YAMLLoader') as MockLoader, \
                 patch.object(OrchestratorBase, '_init_decay_config') as mock_decay:
                mock_decay.return_value = {"test": "decay_config"}
                
                mock_loader_instance = Mock()
                mock_loader_instance.get_orchestrator.return_value = {
                    "id": "test_orchestrator",
                    "agents": ["test_agent"]
                }
                mock_loader_instance.get_agents.return_value = [
                    {"id": "test_agent", "type": "local_llm"}
                ]
                mock_loader_instance.validate.return_value = True
                MockLoader.return_value = mock_loader_instance
                
                orchestrator = OrchestratorBase(temp_file)
                
                # Verify decay config was initialized
                mock_decay.assert_called_once()
                # Verify it was passed to memory logger
                call_kwargs = mock_create_memory.call_args[1]
                assert call_kwargs["decay_config"] == {"test": "decay_config"}
                
        finally:
            self.cleanup_file(temp_file)