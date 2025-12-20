# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for AgentAnalyzerMixin."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from orka.orchestrator.dry_run.agent_analyzer import AgentAnalyzerMixin


class ConcreteAgentAnalyzer(AgentAnalyzerMixin):
    """Concrete implementation for testing."""

    pass


class TestAgentAnalyzerMixin:
    """Tests for AgentAnalyzerMixin."""

    @pytest.fixture
    def analyzer(self):
        """Create an AgentAnalyzerMixin instance."""
        return ConcreteAgentAnalyzer()

    def test_infer_capabilities_local_llm(self, analyzer):
        """Test capability inference for LocalLLMAgent."""
        agent = MagicMock()
        agent.__class__.__name__ = "LocalLLMAgent"

        capabilities = analyzer._infer_capabilities(agent)

        assert "text_generation" in capabilities
        assert "reasoning" in capabilities
        assert "response_generation" in capabilities

    def test_infer_capabilities_duckduckgo(self, analyzer):
        """Test capability inference for DuckDuckGoTool."""
        agent = MagicMock()
        agent.__class__.__name__ = "DuckDuckGoTool"

        capabilities = analyzer._infer_capabilities(agent)

        assert "web_search" in capabilities
        assert "information_retrieval" in capabilities

    def test_infer_capabilities_memory_reader(self, analyzer):
        """Test capability inference for MemoryReaderNode."""
        agent = MagicMock()
        agent.__class__.__name__ = "MemoryReaderNode"

        capabilities = analyzer._infer_capabilities(agent)

        assert "memory_retrieval" in capabilities

    def test_infer_capabilities_unknown(self, analyzer):
        """Test capability inference for unknown agent type."""
        agent = MagicMock()
        agent.__class__.__name__ = "UnknownAgent"

        capabilities = analyzer._infer_capabilities(agent)

        assert capabilities == []

    def test_get_agent_description_local_llm(self, analyzer):
        """Test description generation for LocalLLMAgent."""
        agent = MagicMock()
        agent.__class__.__name__ = "LocalLLMAgent"

        description = analyzer._get_agent_description(agent)

        assert "Local Large Language Model" in description

    def test_get_agent_description_unknown(self, analyzer):
        """Test description generation for unknown agent."""
        agent = MagicMock()
        agent.__class__.__name__ = "CustomAgent"

        description = analyzer._get_agent_description(agent)

        assert "CustomAgent" in description

    def test_extract_agent_parameters(self, analyzer):
        """Test parameter extraction from agent."""
        agent = MagicMock()
        agent.model = "gpt-4"
        agent.temperature = 0.7
        agent.max_tokens = 1000

        params = analyzer._extract_agent_parameters(agent)

        assert params["model"] == "gpt-4"
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 1000

    def test_extract_agent_parameters_missing(self, analyzer):
        """Test parameter extraction with missing params."""
        agent = MagicMock(spec=[])  # No attributes

        params = analyzer._extract_agent_parameters(agent)

        assert params == {}

    def test_estimate_agent_cost_openai(self, analyzer):
        """Test cost estimation for OpenAI agent."""
        agent = MagicMock()
        agent.__class__.__name__ = "OpenAIAnswerBuilder"

        cost = analyzer._estimate_agent_cost(agent)

        assert cost == 0.003  # OpenAI is more expensive

    def test_estimate_agent_cost_local(self, analyzer):
        """Test cost estimation for local agent."""
        agent = MagicMock()
        agent.__class__.__name__ = "LocalLLMAgent"

        cost = analyzer._estimate_agent_cost(agent)

        assert cost == 0.0005  # Local is cheaper

    def test_estimate_agent_latency_openai(self, analyzer):
        """Test latency estimation for OpenAI agent."""
        agent = MagicMock()
        agent.__class__.__name__ = "OpenAIAnswerBuilder"

        latency = analyzer._estimate_agent_latency(agent)

        assert latency == 3000  # Network latency

    def test_estimate_agent_latency_memory(self, analyzer):
        """Test latency estimation for memory agent."""
        agent = MagicMock()
        agent.__class__.__name__ = "MemoryReaderNode"

        latency = analyzer._estimate_agent_latency(agent)

        assert latency == 200  # Fast Redis lookup

    @pytest.mark.asyncio
    async def test_extract_agent_info(self, analyzer):
        """Test extracting info for a single agent."""
        orchestrator = MagicMock()
        agent = MagicMock()
        agent.__class__.__name__ = "LocalLLMAgent"
        agent.prompt = "Test prompt"
        agent.cost_model = {}
        agent.safety_tags = []
        orchestrator.agents = {"test_agent": agent}

        info = await analyzer._extract_agent_info("test_agent", orchestrator)

        assert info["id"] == "test_agent"
        assert info["type"] == "LocalLLMAgent"
        assert "text_generation" in info["capabilities"]

    @pytest.mark.asyncio
    async def test_extract_agent_info_not_found(self, analyzer):
        """Test extracting info for non-existent agent."""
        orchestrator = MagicMock()
        orchestrator.agents = {}

        info = await analyzer._extract_agent_info("missing_agent", orchestrator)

        assert info["id"] == "missing_agent"
        assert info["type"] == "unknown"

    @pytest.mark.asyncio
    async def test_extract_all_agent_info(self, analyzer):
        """Test extracting info for all agents."""
        orchestrator = MagicMock()
        agent1 = MagicMock()
        agent1.__class__.__name__ = "LocalLLMAgent"
        agent1.prompt = "Prompt 1"
        agent2 = MagicMock()
        agent2.__class__.__name__ = "DuckDuckGoTool"
        agent2.prompt = "Prompt 2"
        orchestrator.agents = {"agent1": agent1, "agent2": agent2}

        info = await analyzer._extract_all_agent_info(orchestrator)

        assert len(info) == 2
        assert "agent1" in info
        assert "agent2" in info

    @pytest.mark.asyncio
    async def test_extract_all_agent_info_no_agents(self, analyzer):
        """Test extracting info when no agents attribute."""
        orchestrator = MagicMock(spec=[])  # No agents attribute

        info = await analyzer._extract_all_agent_info(orchestrator)

        assert info == {}

