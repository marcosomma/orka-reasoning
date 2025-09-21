# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for GraphScout Agent
==========================

Comprehensive tests for the GraphScout intelligent routing agent.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.nodes.graph_scout_agent import GraphScoutAgent, GraphScoutConfig
from orka.orchestrator.graph_api import EdgeDescriptor, GraphState, NodeDescriptor


class TestGraphScoutAgent:
    """Test suite for GraphScout agent functionality."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator for testing."""
        orchestrator = Mock()
        orchestrator.agents = {
            "agent_1": Mock(__class__=Mock(__name__="TestAgent1")),
            "agent_2": Mock(__class__=Mock(__name__="TestAgent2")),
            "agent_3": Mock(__class__=Mock(__name__="TestAgent3")),
        }
        orchestrator.orchestrator_cfg = {"agents": ["agent_1", "agent_2", "agent_3"]}
        orchestrator.queue = ["agent_1"]
        orchestrator.step_index = 0
        orchestrator.memory = Mock()
        return orchestrator

    @pytest.fixture
    def sample_graph_state(self):
        """Create a sample graph state for testing."""
        nodes = {
            "agent_1": NodeDescriptor(
                id="agent_1",
                type="TestAgent1",
                prompt_summary="Test agent 1",
                capabilities=["text_generation"],
                contract={},
                cost_model={"base_cost": 0.001},
                safety_tags=[],
                metadata={},
            ),
            "agent_2": NodeDescriptor(
                id="agent_2",
                type="TestAgent2",
                prompt_summary="Test agent 2",
                capabilities=["analysis"],
                contract={},
                cost_model={"base_cost": 0.002},
                safety_tags=[],
                metadata={},
            ),
        }

        edges = [EdgeDescriptor(src="agent_1", dst="agent_2", weight=1.0)]

        return GraphState(
            nodes=nodes,
            edges=edges,
            current_node="agent_1",
            visited_nodes=set(),
            runtime_state={"run_id": "test_run"},
            budgets={"max_tokens": 1000},
            constraints={},
        )

    def test_graph_scout_initialization(self):
        """Test GraphScout agent initialization."""
        agent = GraphScoutAgent(
            node_id="test_scout", params={"k_beam": 3, "max_depth": 2, "commit_margin": 0.15}
        )

        assert agent.node_id == "test_scout"
        assert agent.config.k_beam == 3
        assert agent.config.max_depth == 2
        assert agent.config.commit_margin == 0.15
        assert agent.config.score_weights is not None

    def test_config_defaults(self):
        """Test that configuration defaults are properly set."""
        config = GraphScoutConfig()

        assert config.k_beam == 3
        assert config.max_depth == 2
        assert config.commit_margin == 0.15
        assert config.score_weights is not None
        assert config.score_weights["llm"] == 0.45

    @pytest.mark.asyncio
    async def test_component_initialization(self):
        """Test that all modular components are initialized."""
        agent = GraphScoutAgent(node_id="test_scout")

        await agent.initialize()

        assert agent.graph_api is not None
        assert agent.introspector is not None
        assert agent.scorer is not None
        assert agent.dry_runner is not None
        assert agent.safety_controller is not None
        assert agent.budget_controller is not None
        assert agent.decision_engine is not None

    @pytest.mark.asyncio
    async def test_missing_orchestrator_error(self):
        """Test error handling when orchestrator is missing."""
        agent = GraphScoutAgent(node_id="test_scout")

        context = {"input": "test question", "previous_outputs": {}}

        result = await agent.run(context)

        assert result["status"] == "error"
        assert "GraphScout requires orchestrator context" in result["reasoning"]

    def test_question_extraction(self):
        """Test question extraction from various context formats."""
        agent = GraphScoutAgent(node_id="test_scout")

        # Test formatted_prompt
        context1 = {"formatted_prompt": "What is the answer?"}
        question1 = agent._extract_question(context1)
        assert question1 == "What is the answer?"

        # Test input fallback
        context2 = {"input": "Another question?"}
        question2 = agent._extract_question(context2)
        assert question2 == "Another question?"

        # Test dict input
        context3 = {"input": {"input": "Nested question?"}}
        question3 = agent._extract_question(context3)
        assert question3 == "Nested question?"

    @pytest.mark.asyncio
    async def test_no_candidates_handling(self):
        """Test handling when no candidate paths are found."""
        agent = GraphScoutAgent(node_id="test_scout")

        with patch.object(agent, "initialize", new_callable=AsyncMock):
            with patch.object(agent, "graph_api") as mock_graph_api:
                with patch.object(agent, "introspector") as mock_introspector:
                    mock_graph_api.get_graph_state = AsyncMock(return_value=Mock())
                    mock_introspector.discover_paths = AsyncMock(return_value=[])

                    context = {
                        "input": "test question",
                        "orchestrator": Mock(),
                        "run_id": "test_run",
                    }

                    result = await agent.run(context)

                    assert result["decision"] == "fallback"
                    assert result["status"] == "no_candidates"

    def test_error_handling_methods(self):
        """Test error handling helper methods."""
        agent = GraphScoutAgent(node_id="test_scout")
        context = {}

        # Test no candidates
        result1 = agent._handle_no_candidates(context)
        assert result1["decision"] == "fallback"
        assert result1["status"] == "no_candidates"

        # Test budget exceeded
        result2 = agent._handle_budget_exceeded(context)
        assert result2["decision"] == "shortlist"
        assert result2["status"] == "budget_exceeded"

        # Test safety violation
        result3 = agent._handle_safety_violation(context)
        assert result3["decision"] == "human_gate"
        assert result3["status"] == "safety_violation"

    def test_trace_building(self):
        """Test comprehensive trace building."""
        agent = GraphScoutAgent(node_id="test_scout")

        question = "test question"
        candidates = [{"node_id": "agent_1", "path": ["agent_1"]}]
        scored_candidates = [{"node_id": "agent_1", "score": 0.8, "components": {}}]
        decision_result = {
            "decision_type": "commit_next",
            "target": "agent_1",
            "confidence": 0.8,
            "reasoning": "test reasoning",
        }
        context = {"run_id": "test_run", "step_index": 1}

        trace = agent._build_trace_dict(
            question, candidates, scored_candidates, decision_result, context
        )

        assert trace["graph_scout_version"] == "1.0.0"
        assert trace["question"] == question
        assert trace["config"]["k_beam"] == agent.config.k_beam
        assert trace["discovery"]["total_candidates"] == 1
        assert trace["decision"]["type"] == "commit_next"
        assert trace["execution_metadata"]["node_id"] == "test_scout"


class TestGraphScoutIntegration:
    """Integration tests for GraphScout with other components."""

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(self):
        """Test a complete GraphScout workflow with mocked components."""
        agent = GraphScoutAgent(node_id="test_scout", params={"k_beam": 2, "max_depth": 1})

        # Mock all components
        with patch.object(agent, "initialize", new_callable=AsyncMock):
            with patch.object(agent, "graph_api") as mock_graph_api:
                with patch.object(agent, "introspector") as mock_introspector:
                    with patch.object(agent, "budget_controller") as mock_budget:
                        with patch.object(agent, "dry_runner") as mock_dry_runner:
                            with patch.object(agent, "safety_controller") as mock_safety:
                                with patch.object(agent, "scorer") as mock_scorer:
                                    with patch.object(agent, "decision_engine") as mock_decision:

                                        # Setup mock returns
                                        mock_graph_api.get_graph_state = AsyncMock(
                                            return_value=Mock()
                                        )
                                        mock_introspector.discover_paths = AsyncMock(
                                            return_value=[
                                                {"node_id": "agent_1", "path": ["agent_1"]}
                                            ]
                                        )
                                        mock_budget.filter_candidates = AsyncMock(
                                            return_value=[
                                                {"node_id": "agent_1", "path": ["agent_1"]}
                                            ]
                                        )
                                        mock_dry_runner.simulate_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "path": ["agent_1"],
                                                    "preview": "test",
                                                }
                                            ]
                                        )
                                        mock_safety.assess_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "path": ["agent_1"],
                                                    "preview": "test",
                                                }
                                            ]
                                        )
                                        mock_scorer.score_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "score": 0.8,
                                                    "components": {},
                                                }
                                            ]
                                        )
                                        mock_decision.make_decision = AsyncMock(
                                            return_value={
                                                "decision_type": "commit_next",
                                                "target": "agent_1",
                                                "confidence": 0.8,
                                                "reasoning": "Clear winner",
                                            }
                                        )

                                        context = {
                                            "input": "test question",
                                            "orchestrator": Mock(),
                                            "run_id": "test_run",
                                        }

                                        result = await agent.run(context)

                                        assert result["status"] == "success"
                                        assert result["decision"] == "commit_next"
                                        assert result["target"] == "agent_1"
                                        assert result["confidence"] == 0.8

    asyncio.run(run_test())


def test_smart_path_evaluator_llm_integration():
    """Test SmartPathEvaluator with LLM integration capabilities."""

    async def run_test():
        from orka.orchestrator.dry_run_engine import SmartPathEvaluator

        # Test configuration with LLM disabled for testing
        config_mock = type(
            "Config",
            (),
            {
                "max_preview_tokens": 200,
                "llm_evaluation_enabled": False,  # Use contextual mocks
                "evaluation_model": "local_llm",
                "validation_model": "local_llm",
            },
        )()

        evaluator = SmartPathEvaluator(config_mock)

        # Test candidates
        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"], "depth": 1},
            {"node_id": "analysis_agent", "path": ["analysis_agent"], "depth": 1},
        ]

        # Mock orchestrator with agents
        mock_orch = type(
            "MockOrch",
            (),
            {
                "agents": {
                    "search_agent": type(
                        "SearchAgent", (), {"__class__": type("DuckDuckGoTool", (), {})}
                    )(),
                    "analysis_agent": type(
                        "AnalysisAgent", (), {"__class__": type("LocalLLMAgent", (), {})}
                    )(),
                }
            },
        )()

        # Test evaluation
        question = "What is artificial intelligence?"
        context = {"previous_outputs": {}}

        result = await evaluator.simulate_candidates(candidates, question, context, mock_orch)

        # Verify results
        assert len(result) == 2
        for candidate in result:
            assert "llm_evaluation" in candidate
            assert "preview" in candidate
            assert "estimated_cost" in candidate
            assert "estimated_latency" in candidate

            # Verify LLM evaluation structure
            llm_eval = candidate["llm_evaluation"]
            assert "stage1" in llm_eval
            assert "stage2" in llm_eval
            assert "final_scores" in llm_eval

            # Verify final scores
            final_scores = llm_eval["final_scores"]
            assert "relevance" in final_scores
            assert "confidence" in final_scores
            assert "efficiency" in final_scores

    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__])
