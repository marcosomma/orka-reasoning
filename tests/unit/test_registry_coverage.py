"""
Comprehensive tests for registry module to increase coverage.
"""
import pytest
from unittest.mock import MagicMock, patch
from orka.registry import AgentRegistry, RegistrationError


class TestAgentRegistry:
    """Test agent registry functionality."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = AgentRegistry()
        assert registry is not None
        assert hasattr(registry, '_agents')

    def test_register_agent(self):
        """Test registering an agent."""
        registry = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry.register("test_agent", MockAgent)
        assert "test_agent" in registry._agents

    def test_register_duplicate_agent(self):
        """Test registering duplicate agent raises error."""
        registry = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry.register("test_agent", MockAgent)
        
        with pytest.raises(RegistrationError):
            registry.register("test_agent", MockAgent)

    def test_get_agent(self):
        """Test getting a registered agent."""
        registry = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry.register("test_agent", MockAgent)
        agent_class = registry.get("test_agent")
        assert agent_class == MockAgent

    def test_get_nonexistent_agent(self):
        """Test getting nonexistent agent returns None."""
        registry = AgentRegistry()
        agent_class = registry.get("nonexistent")
        assert agent_class is None

    def test_list_agents(self):
        """Test listing all registered agents."""
        registry = AgentRegistry()
        
        class MockAgent1:
            agent_type = "test1"
            
        class MockAgent2:
            agent_type = "test2"
            
        registry.register("test1", MockAgent1)
        registry.register("test2", MockAgent2)
        
        agents = registry.list_agents()
        assert "test1" in agents
        assert "test2" in agents

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry.register("test_agent", MockAgent)
        registry.unregister("test_agent")
        assert "test_agent" not in registry._agents

    def test_clear_registry(self):
        """Test clearing all registered agents."""
        registry = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry.register("test_agent", MockAgent)
        registry.clear()
        assert len(registry._agents) == 0

    def test_registry_singleton(self):
        """Test that registry behaves as singleton."""
        registry1 = AgentRegistry()
        registry2 = AgentRegistry()
        
        class MockAgent:
            agent_type = "test_agent"
            
        registry1.register("test_agent", MockAgent)
        
        # Both instances should see the registration
        assert "test_agent" in registry2._agents
