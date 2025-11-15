"""Unit tests for orka.agents.base_agent."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.agents.base_agent import BaseAgent

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""
    
    async def _run_impl(self, ctx):
        """Implementation for testing."""
        return f"Processed: {ctx.get('input', '')}"


class TestBaseAgent:
    """Test suite for BaseAgent class."""

    def test_init(self):
        """Test BaseAgent initialization."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test prompt")
        
        assert agent.agent_id == "test_agent"
        assert agent.prompt == "Test prompt"

    def test_init_with_registry(self):
        """Test BaseAgent initialization with registry."""
        mock_registry = Mock()
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test", registry=mock_registry)
        
        assert agent.registry == mock_registry

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test")
        
        # Should not raise exception
        await agent.initialize()

    @pytest.mark.asyncio
    async def test_run_success(self):
        """Test run method with successful execution."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test")
        
        with patch('orka.agents.base_agent.ResponseBuilder.create_success_response') as mock_create:
            mock_create.return_value = {
                "component_type": "agent",
                "status": "success",
                "result": "Processed: test input",
            }
            
            ctx = {"input": "test input"}
            result = await agent.run(ctx)
            
            assert result["status"] == "success"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_exception(self):
        """Test run method handles exceptions."""
        class FailingAgent(BaseAgent):
            async def _run_impl(self, ctx):
                raise ValueError("Test error")
        
        agent = FailingAgent(agent_id="failing_agent", prompt="Test")
        
        with patch('orka.agents.base_agent.ResponseBuilder.create_error_response') as mock_create:
            mock_create.return_value = {
                "component_type": "agent",
                "status": "error",
                "error": "Test error",
            }
            
            ctx = {"input": "test"}
            result = await agent.run(ctx)
            
            assert result["status"] == "error"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_timeout(self):
        """Test run method with timeout."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test", timeout=1.0)
        
        with patch('orka.agents.base_agent.ResponseBuilder.create_success_response') as mock_create:
            mock_create.return_value = {"status": "success", "result": "output"}
            
            ctx = {"input": "test"}
            result = await agent.run(ctx)
            
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test")
        
        # Should not raise exception
        await agent.cleanup()

    def test_repr(self):
        """Test __repr__ method."""
        agent = ConcreteAgent(agent_id="test_agent", prompt="Test")
        
        repr_str = repr(agent)
        
        assert "ConcreteAgent" in repr_str
        assert "test_agent" in repr_str

