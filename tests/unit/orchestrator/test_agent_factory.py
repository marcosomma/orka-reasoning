"""Unit tests for orka.orchestrator.agent_factory."""

from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

import pytest

from orka.orchestrator.agent_factory import AgentFactory, AGENT_TYPES

# Mark all tests in this module for unit testing with auto-mocking
pytestmark = [pytest.mark.unit]


class TestAgentFactory:
    """Test suite for AgentFactory class."""

    def create_mock_memory(self):
        """Helper to create a mock memory logger."""
        mock_memory = Mock()
        mock_memory.decay_config = {"test": "config"}
        return mock_memory

    def test_init(self):
        """Test AgentFactory initialization."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [{"id": "test_agent", "type": "local_llm"}]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        assert factory.orchestrator_cfg == orchestrator_cfg
        assert factory.agent_cfgs == agent_cfgs
        assert factory.memory == memory

    def test_agent_types_registry(self):
        """Test that AGENT_TYPES registry contains expected agent types."""
        expected_types = [
            "binary", "classification", "local_llm", "openai-answer",
            "openai-binary", "openai-classification", "plan_validator",
            "validate_and_structure", "rag", "duckduckgo", "router",
            "failover", "failing", "join", "fork", "loop", "loop_validator",
            "path_executor", "graph-scout", "memory"
        ]
        
        for agent_type in expected_types:
            assert agent_type in AGENT_TYPES
            
        # Check special handlers
        assert AGENT_TYPES["path_executor"] == "special_handler"
        assert AGENT_TYPES["memory"] == "special_handler"

    def test_init_agents_unsupported_type(self):
        """Test _init_agents with an unsupported agent type raises ValueError."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "unknown_agent",
                "type": "unknown_type",
                "prompt": "Unknown"
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        with pytest.raises(ValueError, match="Unsupported agent type: unknown_type"):
            factory._init_agents()

    def test_init_agents_empty_config(self):
        """Test _init_agents with empty agent configuration."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = []
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert instances == {}

    def test_memory_decay_config_merging(self):
        """Test that agent-specific decay config is properly merged with global config."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "memory_agent",
                "type": "memory",
                "config": {"operation": "write"},
                "decay": {"custom_setting": "agent_value"}
            }
        ]
        
        # Mock memory with global decay config
        memory = Mock()
        memory.decay_config = {"global_setting": "global_value", "custom_setting": "global_default"}
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        with patch('orka.orchestrator.agent_factory.MemoryWriterNode') as mock_writer:
            mock_writer_instance = Mock()
            mock_writer.return_value = mock_writer_instance
            
            instances = factory._init_agents()
            
            # Verify that decay config was merged correctly
            call_kwargs = mock_writer.call_args[1]
            expected_decay_config = {
                "global_setting": "global_value",
                "custom_setting": "agent_value"  # Agent value should override global
            }
            assert call_kwargs["decay_config"] == expected_decay_config

    def test_clean_config_removes_expected_fields(self):
        """Test that configuration cleaning removes expected fields."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "test_agent",
                "type": "router",
                "prompt": "Test prompt",
                "queue": ["next_agent"],
                "conditions": {"key": "value"}
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        with patch('orka.orchestrator.agent_factory.router_node.RouterNode') as mock_router:
            mock_router_instance = Mock()
            mock_router.return_value = mock_router_instance
            
            instances = factory._init_agents()
            
            # Verify RouterNode was called with cleaned config (no id, type, prompt, queue)
            call_kwargs = mock_router.call_args[1]
            assert "node_id" in call_kwargs
            assert "conditions" in call_kwargs
            # These should be removed from clean_cfg
            assert "id" not in call_kwargs
            assert "type" not in call_kwargs
            assert "prompt" not in call_kwargs
            assert "queue" not in call_kwargs

    @patch('orka.orchestrator.agent_factory.MemoryWriterNode')
    def test_memory_writer_node_creation(self, mock_memory_writer):
        """Test creation of memory writer node."""
        mock_writer_instance = Mock()
        mock_memory_writer.return_value = mock_writer_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "writer_agent",
                "type": "memory",
                "prompt": "Store data",
                "queue": ["next_agent"],
                "namespace": "test_namespace",
                "config": {"operation": "write"},
                "vector": True,
                "key_template": "test_{id}",
                "metadata": {"source": "test"}
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "writer_agent" in instances
        assert instances["writer_agent"] == mock_writer_instance
        
        # Verify call parameters
        call_kwargs = mock_memory_writer.call_args[1]
        assert call_kwargs["node_id"] == "writer_agent"
        assert call_kwargs["prompt"] == "Store data"
        assert call_kwargs["queue"] == ["next_agent"]
        assert call_kwargs["namespace"] == "test_namespace"
        assert call_kwargs["vector"] is True
        assert call_kwargs["key_template"] == "test_{id}"
        assert call_kwargs["metadata"] == {"source": "test"}
        assert call_kwargs["memory_logger"] == memory

    @patch('orka.orchestrator.agent_factory.MemoryReaderNode')
    def test_memory_reader_node_creation(self, mock_memory_reader):
        """Test creation of memory reader node."""
        mock_reader_instance = Mock()
        mock_memory_reader.return_value = mock_reader_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "reader_agent",
                "type": "memory",
                "prompt": "Read data",
                "queue": ["next_agent"],
                "namespace": "test_namespace",
                "config": {
                    "operation": "read",
                    "limit": 5,
                    "similarity_threshold": 0.8,
                    "enable_context_search": True
                }
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "reader_agent" in instances
        assert instances["reader_agent"] == mock_reader_instance
        
        # Verify call parameters
        call_kwargs = mock_memory_reader.call_args[1]
        assert call_kwargs["node_id"] == "reader_agent"
        assert call_kwargs["prompt"] == "Read data"
        assert call_kwargs["queue"] == ["next_agent"]
        assert call_kwargs["namespace"] == "test_namespace"
        assert call_kwargs["limit"] == 5
        assert call_kwargs["similarity_threshold"] == 0.8
        assert call_kwargs["enable_context_search"] is True
        assert call_kwargs["memory_logger"] == memory

    @patch('orka.orchestrator.agent_factory.router_node.RouterNode')
    def test_router_node_creation(self, mock_router):
        """Test creation of router node."""
        mock_router_instance = Mock()
        mock_router.return_value = mock_router_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "router_agent",
                "type": "router",
                "prompt": "Route based on input",
                "queue": ["agent1", "agent2"],
                "conditions": {"key": "value"}
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "router_agent" in instances
        assert instances["router_agent"] == mock_router_instance
        
        # Verify RouterNode was called with node_id and cleaned config
        call_kwargs = mock_router.call_args[1]
        assert call_kwargs["node_id"] == "router_agent"
        assert call_kwargs["conditions"] == {"key": "value"}

    @patch('orka.orchestrator.agent_factory.failing_node.FailingNode')
    def test_failing_node_creation(self, mock_failing):
        """Test creation of failing node."""
        mock_failing_instance = Mock()
        mock_failing.return_value = mock_failing_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "failing_agent",
                "type": "failing",
                "prompt": "Always fail",
                "queue": ["recovery_agent"],
                "error_message": "Simulated failure"
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "failing_agent" in instances
        assert instances["failing_agent"] == mock_failing_instance
        
        # Verify FailingNode was called with expected parameters
        call_kwargs = mock_failing.call_args[1]
        assert call_kwargs["node_id"] == "failing_agent"
        assert call_kwargs["prompt"] == "Always fail"
        assert call_kwargs["queue"] == ["recovery_agent"]
        assert call_kwargs["error_message"] == "Simulated failure"

    @patch('orka.orchestrator.agent_factory.GraphScoutAgent')
    def test_graph_scout_creation(self, mock_graph_scout):
        """Test creation of GraphScout agent."""
        mock_scout_instance = Mock()
        mock_graph_scout.return_value = mock_scout_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "scout_agent",
                "type": "graph-scout",
                "prompt": "Discover paths",
                "queue": ["validator"],
                "budget": 1000,
                "max_paths": 3
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "scout_agent" in instances
        assert instances["scout_agent"] == mock_scout_instance
        
        # Verify GraphScoutAgent was called with expected parameters
        call_kwargs = mock_graph_scout.call_args[1]
        assert call_kwargs["node_id"] == "scout_agent"
        assert call_kwargs["prompt"] == "Discover paths"
        assert call_kwargs["queue"] == ["validator"]
        assert call_kwargs["budget"] == 1000
        assert call_kwargs["max_paths"] == 3

    @patch('orka.orchestrator.agent_factory.DuckDuckGoTool')
    def test_duckduckgo_tool_creation(self, mock_ddg):
        """Test creation of DuckDuckGo search tool."""
        mock_ddg_instance = Mock()
        mock_ddg.return_value = mock_ddg_instance
        
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "search_agent",
                "type": "duckduckgo",
                "prompt": "Search the web",
                "queue": ["analyzer"],
                "max_results": 5
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        instances = factory._init_agents()
        
        assert "search_agent" in instances
        assert instances["search_agent"] == mock_ddg_instance
        
        # Verify DuckDuckGoTool was called with expected parameters
        call_kwargs = mock_ddg.call_args[1]
        assert call_kwargs["tool_id"] == "search_agent"
        assert call_kwargs["prompt"] == "Search the web"
        assert call_kwargs["queue"] == ["analyzer"]
        assert call_kwargs["max_results"] == 5

    def test_path_executor_special_handler(self):
        """Test that path_executor type is marked as special handler."""
        # This test just verifies the path executor is handled specially
        # The actual lazy import is complex to test due to circular imports
        assert AGENT_TYPES["path_executor"] == "special_handler"
        
        # Test that the agent factory recognizes path_executor as a valid type
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "executor_agent",
                "type": "path_executor",
                "path_source": "graphscout.result"
            }
        ]
        memory = self.create_mock_memory()
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        # We can't easily test the actual instantiation due to lazy import complexity
        # But we can verify the type is recognized and doesn't raise "Unsupported agent type"
        try:
            # This will fail at the import level, but not at the type recognition level
            factory._init_agents()
        except (ImportError, AttributeError):
            # Expected due to the lazy import in the actual code
            pass
        except ValueError as e:
            if "Unsupported agent type" in str(e):
                pytest.fail("path_executor should be recognized as a valid agent type")
            # Other ValueErrors are acceptable for this test

    def test_memory_no_decay_config(self):
        """Test memory agent creation when memory logger has no decay config."""
        orchestrator_cfg = {"id": "test_orchestrator"}
        agent_cfgs = [
            {
                "id": "memory_agent",
                "type": "memory",
                "config": {"operation": "write"},
                "decay": {"agent_setting": "agent_value"}
            }
        ]
        
        # Mock memory without decay_config attribute
        memory = Mock()
        del memory.decay_config  # Remove the attribute
        
        factory = AgentFactory(orchestrator_cfg, agent_cfgs, memory)
        
        with patch('orka.orchestrator.agent_factory.MemoryWriterNode') as mock_writer:
            mock_writer_instance = Mock()
            mock_writer.return_value = mock_writer_instance
            
            instances = factory._init_agents()
            
            # Verify that agent decay config was used as-is
            call_kwargs = mock_writer.call_args[1]
            expected_decay_config = {"agent_setting": "agent_value"}
            assert call_kwargs["decay_config"] == expected_decay_config
