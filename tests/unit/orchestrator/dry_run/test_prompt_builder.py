# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for PromptBuilderMixin."""

import pytest

from orka.orchestrator.dry_run.prompt_builder import PromptBuilderMixin
from orka.orchestrator.dry_run.data_classes import PathEvaluation


class ConcretePromptBuilder(PromptBuilderMixin):
    """Concrete implementation for testing."""

    pass


class TestPromptBuilderMixin:
    """Tests for PromptBuilderMixin."""

    @pytest.fixture
    def builder(self):
        """Create a PromptBuilderMixin instance."""
        return ConcretePromptBuilder()

    def test_build_evaluation_prompt(self, builder):
        """Test building evaluation prompt."""
        agent_info = {
            "id": "search_agent",
            "type": "DuckDuckGoTool",
            "capabilities": ["web_search", "information_retrieval"],
            "prompt": "Search the web for information",
        }
        candidate = {
            "node_id": "search_agent",
            "path": ["search_agent", "response_builder"],
            "depth": 2,
        }
        context = {
            "current_agent_id": "router",
            "previous_outputs": {"classifier": "factual_query"},
        }

        prompt = builder._build_evaluation_prompt(
            "What is the latest news?", agent_info, candidate, context
        )

        assert "What is the latest news?" in prompt
        assert "search_agent" in prompt
        assert "DuckDuckGoTool" in prompt
        assert "web_search" in prompt
        assert "router" in prompt
        assert "RESPONSE FORMAT" in prompt

    def test_build_evaluation_prompt_includes_critical_requirements(self, builder):
        """Test that evaluation prompt includes critical requirements."""
        agent_info = {
            "id": "test",
            "type": "Test",
            "capabilities": [],
            "prompt": "Test",
        }
        candidate = {"node_id": "test", "path": ["test"]}
        context = {"current_agent_id": "current"}

        prompt = builder._build_evaluation_prompt("query", agent_info, candidate, context)

        assert "CRITICAL REQUIREMENTS" in prompt
        assert "infinite loops" in prompt.lower()

    def test_build_validation_prompt(self, builder):
        """Test building validation prompt."""
        candidate = {
            "node_id": "search_agent",
            "path": ["search_agent", "response_builder"],
        }
        evaluation = PathEvaluation(
            node_id="search_agent",
            relevance_score=0.85,
            confidence=0.9,
            reasoning="Good match for factual query",
            expected_output="Search results",
            estimated_tokens=500,
            estimated_cost=0.005,
            estimated_latency_ms=1000,
            risk_factors=["network_dependency"],
            efficiency_rating="high",
        )
        context = {}

        prompt = builder._build_validation_prompt(
            "What is happening today?", candidate, evaluation, context
        )

        assert "What is happening today?" in prompt
        assert "search_agent" in prompt
        assert "0.85" in prompt  # relevance score
        assert "high" in prompt  # efficiency rating
        assert "network_dependency" in prompt

    def test_build_comprehensive_evaluation_prompt(self, builder):
        """Test building comprehensive evaluation prompt."""
        available_agents = {
            "search_agent": {
                "id": "search_agent",
                "type": "DuckDuckGoTool",
                "description": "Web search tool",
                "capabilities": ["web_search"],
                "prompt": "Search the web",
                "cost_estimate": 0.0002,
                "latency_estimate": 800,
            },
            "response_builder": {
                "id": "response_builder",
                "type": "LocalLLMAgent",
                "description": "Response generation",
                "capabilities": ["text_generation"],
                "prompt": "Generate response",
                "cost_estimate": 0.0005,
                "latency_estimate": 4000,
            },
        }
        possible_paths = [
            {
                "path": ["search_agent"],
                "agents": [available_agents["search_agent"]],
                "total_cost": 0.0002,
                "total_latency": 800,
            },
            {
                "path": ["search_agent", "response_builder"],
                "agents": [
                    available_agents["search_agent"],
                    available_agents["response_builder"],
                ],
                "total_cost": 0.0007,
                "total_latency": 4800,
            },
        ]
        context = {
            "current_agent_id": "router",
            "previous_outputs": {},
        }

        prompt = builder._build_comprehensive_evaluation_prompt(
            "What is the latest news?", available_agents, possible_paths, context
        )

        assert "What is the latest news?" in prompt
        assert "search_agent" in prompt
        assert "response_builder" in prompt
        assert "DuckDuckGoTool" in prompt
        assert "LocalLLMAgent" in prompt
        assert "Path 1:" in prompt
        assert "Path 2:" in prompt
        assert "router" in prompt

    def test_build_comprehensive_evaluation_prompt_question_type(self, builder):
        """Test that prompt detects question type."""
        available_agents = {
            "agent1": {
                "id": "agent1",
                "type": "Test",
                "description": "Test",
                "capabilities": [],
                "prompt": "",
                "cost_estimate": 0.0,
                "latency_estimate": 0,
            }
        }
        possible_paths = []
        context = {"previous_outputs": {}}

        # Test news query detection
        prompt_news = builder._build_comprehensive_evaluation_prompt(
            "What is in the news today?", available_agents, possible_paths, context
        )
        assert "Factual information request" in prompt_news

        # Test general query detection
        prompt_general = builder._build_comprehensive_evaluation_prompt(
            "How are you?", available_agents, possible_paths, context
        )
        assert "General query" in prompt_general

    def test_build_comprehensive_evaluation_prompt_includes_criteria(self, builder):
        """Test that comprehensive prompt includes evaluation criteria."""
        available_agents = {}
        possible_paths = []
        context = {"previous_outputs": {}}

        prompt = builder._build_comprehensive_evaluation_prompt(
            "test", available_agents, possible_paths, context
        )

        assert "EVALUATION CRITERIA" in prompt
        assert "Relevance" in prompt
        assert "Completeness" in prompt
        assert "Efficiency" in prompt
        assert "Specificity" in prompt

