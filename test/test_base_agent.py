# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

import pytest

from orka.agents.base_agent import BaseAgent, LegacyBaseAgent

# Modern BaseAgent Tests


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Test initialization of modern BaseAgent"""
    agent = BaseAgent(agent_id="test_agent")
    assert agent.agent_id == "test_agent"
    assert agent.timeout == 30.0
    assert agent.prompt is None
    assert agent.queue is None
    assert not agent._initialized

    # Initialize the agent
    await agent.initialize()
    assert agent._initialized


@pytest.mark.asyncio
async def test_base_agent_cleanup():
    """Test agent cleanup method"""
    agent = BaseAgent(agent_id="test_agent")
    await agent.cleanup()  # Should not raise any exceptions


@pytest.mark.asyncio
async def test_base_agent_incomplete():
    """Test that using a BaseAgent without implementing _run_impl raises an error"""
    agent = BaseAgent(agent_id="test_incomplete")

    # Run should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        await agent._run_impl({})


@pytest.mark.asyncio
async def test_base_agent_complete():
    """Test a complete BaseAgent implementation"""

    class TestAgent(BaseAgent):
        async def _run_impl(self, ctx):
            return f"Result: {ctx.get('input', '')}"

    agent = TestAgent(agent_id="test_complete")

    # Run the agent with a simple input
    result = await agent.run({"input": "test"})
    assert isinstance(result, dict)  # Output is a dict-like object
    assert result.get("result") == "Result: test"
    assert result.get("status") == "success"
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_base_agent_exception_handling():
    """Test error handling in BaseAgent"""

    class ErrorAgent(BaseAgent):
        async def _run_impl(self, ctx):
            raise ValueError("Test error")

    agent = ErrorAgent(agent_id="test_error")

    # Run the agent and check error handling
    result = await agent.run("test_input")
    assert isinstance(result, dict)
    assert result.get("result") is None
    assert result.get("status") == "error"
    assert "Test error" in result.get("error", "")


# Legacy BaseAgent Tests


def test_legacy_base_agent_instance():
    """Test instantiation of a LegacyBaseAgent"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")
    assert agent.agent_id == "legacy_id"
    assert agent.prompt == "test prompt"
    assert agent.queue == "test_queue"
    assert agent._is_legacy_agent()


def test_legacy_base_agent_run():
    """Test running a LegacyBaseAgent"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")

    # Test with string input
    result = agent.run("test_input")
    assert result == "Processed: test_input"

    # Test with dict input
    result = agent.run({"input": "test_data"})
    assert result == "Processed: {'input': 'test_data'}"


@pytest.mark.asyncio
async def test_legacy_base_agent_run_async():
    """Test running a LegacyBaseAgent through the async interface"""

    class TestLegacy(LegacyBaseAgent):
        def run(self, input_data):
            return f"Processed via legacy: {input_data}"

    agent = TestLegacy("legacy_id", "test prompt", "test_queue")

    # Call the async run method which should use the legacy implementation
    result = await BaseAgent.run(agent, "test_async")
    assert result == "Processed via legacy: test_async"
