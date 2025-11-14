"""Unit tests for orka.agents.agents."""

import pytest

from orka.agents.agents import BinaryAgent, ClassificationAgent

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestBinaryAgent:
    """Test suite for BinaryAgent class."""

    def test_init(self):
        """Test BinaryAgent initialization."""
        agent = BinaryAgent(agent_id="binary_agent", prompt="Test")
        
        assert agent.agent_id == "binary_agent"

    @pytest.mark.asyncio
    async def test_run_impl_positive(self):
        """Test _run_impl returns True for positive indicators."""
        agent = BinaryAgent(agent_id="binary_agent", prompt="Test")
        
        ctx = {"input": "Yes, that is correct"}
        result = await agent._run_impl(ctx)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_run_impl_negative(self):
        """Test _run_impl returns False for negative indicators."""
        agent = BinaryAgent(agent_id="binary_agent", prompt="Test")
        
        ctx = {"input": "No, that is wrong"}
        result = await agent._run_impl(ctx)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_run_impl_case_insensitive(self):
        """Test _run_impl is case insensitive."""
        agent = BinaryAgent(agent_id="binary_agent", prompt="Test")
        
        ctx = {"input": "TRUE"}
        result = await agent._run_impl(ctx)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_run_impl_non_string_input(self):
        """Test _run_impl handles non-string input."""
        agent = BinaryAgent(agent_id="binary_agent", prompt="Test")
        
        ctx = {"input": 123}
        result = await agent._run_impl(ctx)
        
        assert isinstance(result, bool)


class TestClassificationAgent:
    """Test suite for ClassificationAgent class."""

    def test_init(self):
        """Test ClassificationAgent initialization."""
        agent = ClassificationAgent(agent_id="classifier", prompt="Test")
        
        assert agent.agent_id == "classifier"

    @pytest.mark.asyncio
    async def test_run_impl_deprecated(self):
        """Test _run_impl returns deprecated message."""
        agent = ClassificationAgent(agent_id="classifier", prompt="Test")
        
        ctx = {"input": "test input"}
        result = await agent._run_impl(ctx)
        
        assert result == "deprecated"

