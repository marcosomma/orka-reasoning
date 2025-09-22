# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Comprehensive Tests for GraphScout Agent
========================================

Bulletproof testing suite for the GraphScout intelligent routing agent.
Tests all components, edge cases, error handling, and integration scenarios.
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from orka.nodes.graph_scout_agent import (
    GraphScoutAgent,
    GraphScoutConfig,
    PathCandidate,
    ScoutDecision,
)
from orka.orchestrator.graph_api import EdgeDescriptor, GraphState, NodeDescriptor


class TestGraphScoutConfig:
    """Test GraphScout configuration handling."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GraphScoutConfig()

        assert config.k_beam == 3
        assert config.max_depth == 2
        assert config.commit_margin == 0.15
        assert config.cost_budget_tokens == 800
        assert config.latency_budget_ms == 1200
        assert config.safety_profile == "default"
        assert config.safety_threshold == 0.2
        assert config.max_preview_tokens == 192
        assert config.tool_policy == "mock_all"
        assert config.use_priors is True
        assert config.ttl_days == 21
        assert config.log_previews == "head64"
        assert config.log_components is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GraphScoutConfig(
            k_beam=5,
            max_depth=3,
            commit_margin=0.2,
            cost_budget_tokens=1000,
            latency_budget_ms=1500,
            safety_profile="strict",
            safety_threshold=0.1,
            max_preview_tokens=256,
            tool_policy="allow_all",
            use_priors=False,
            ttl_days=30,
            log_previews="full",
            log_components=False,
        )

        assert config.k_beam == 5
        assert config.max_depth == 3
        assert config.commit_margin == 0.2
        assert config.cost_budget_tokens == 1000
        assert config.latency_budget_ms == 1500
        assert config.safety_profile == "strict"
        assert config.safety_threshold == 0.1
        assert config.max_preview_tokens == 256
        assert config.tool_policy == "allow_all"
        assert config.use_priors is False
        assert config.ttl_days == 30
        assert config.log_previews == "full"
        assert config.log_components is False

    def test_score_weights_default(self):
        """Test default score weights."""
        config = GraphScoutConfig()

        assert config.score_weights is not None
        assert config.score_weights["llm"] == 0.45
        assert config.score_weights["heuristics"] == 0.20
        assert config.score_weights["prior"] == 0.20
        assert config.score_weights["cost"] == 0.10
        assert config.score_weights["latency"] == 0.05

    def test_score_weights_custom(self):
        """Test custom score weights."""
        custom_weights = {
            "llm": 0.5,
            "heuristics": 0.3,
            "prior": 0.1,
            "cost": 0.05,
            "latency": 0.05,
        }
        config = GraphScoutConfig(score_weights=custom_weights)

        assert config.score_weights == custom_weights


class TestGraphScoutInitialization:
    """Test GraphScout agent initialization."""

    def test_basic_initialization(self):
        """Test basic GraphScout initialization."""
        agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

        assert agent.node_id == "test_scout"
        assert agent.prompt == "Test prompt"
        assert agent.queue == []
        assert isinstance(agent.config, GraphScoutConfig)
        assert agent.config.k_beam == 3  # default
        assert agent.config.max_depth == 2  # default

    def test_initialization_with_params(self):
        """Test GraphScout initialization with custom parameters."""
        params = {
            "k_beam": 5,
            "max_depth": 3,
            "commit_margin": 0.25,
            "cost_budget_tokens": 1200,
            "latency_budget_ms": 2000,
            "safety_profile": "strict",
            "safety_threshold": 0.1,
            "max_preview_tokens": 300,
            "tool_policy": "allow_safe",
            "use_priors": False,
            "ttl_days": 14,
            "log_previews": "summary",
            "log_components": False,
        }

        agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[], params=params)

        assert agent.config.k_beam == 5
        assert agent.config.max_depth == 3
        assert agent.config.commit_margin == 0.25
        assert agent.config.cost_budget_tokens == 1200
        assert agent.config.latency_budget_ms == 2000
        assert agent.config.safety_profile == "strict"
        assert agent.config.safety_threshold == 0.1
        assert agent.config.max_preview_tokens == 300
        assert agent.config.tool_policy == "allow_safe"
        assert agent.config.use_priors is False
        assert agent.config.ttl_days == 14
        assert agent.config.log_previews == "summary"
        assert agent.config.log_components is False

    def test_initialization_with_score_weights(self):
        """Test GraphScout initialization with custom score weights."""
        score_weights = {"llm": 0.6, "heuristics": 0.2, "prior": 0.1, "cost": 0.05, "latency": 0.05}

        agent = GraphScoutAgent(
            node_id="test_scout",
            prompt="Test prompt",
            queue=[],
            params={"score_weights": score_weights},
        )

        assert agent.config.score_weights == score_weights

    def test_component_initialization_state(self):
        """Test that components are initially None."""
        agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

        assert agent.graph_api is None
        assert agent.introspector is None
        assert agent.scorer is None
        assert agent.smart_evaluator is None
        assert agent.safety_controller is None
        assert agent.budget_controller is None
        assert agent.decision_engine is None

    @pytest.mark.asyncio
    async def test_component_initialization_success(self):
        """Test successful component initialization."""
        agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

        await agent.initialize()

        assert agent.graph_api is not None
        assert agent.introspector is not None
        assert agent.scorer is not None
        assert agent.smart_evaluator is not None
        assert agent.safety_controller is not None
        assert agent.budget_controller is not None
        assert agent.decision_engine is not None

    @pytest.mark.asyncio
    async def test_component_initialization_failure(self):
        """Test component initialization failure handling."""
        agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

        # Mock a component to fail during initialization
        with patch("orka.nodes.graph_scout_agent.GraphAPI") as mock_graph_api:
            mock_graph_api.side_effect = Exception("Initialization failed")

            with pytest.raises(Exception, match="Initialization failed"):
                await agent.initialize()


class TestGraphScoutQuestionExtraction:
    """Test question extraction from various context formats."""

    def setup_method(self):
        """Set up test agent."""
        self.agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

    def test_extract_from_formatted_prompt(self):
        """Test extracting question from formatted_prompt."""
        context = {"formatted_prompt": "What is artificial intelligence?"}
        question = self.agent._extract_question(context)
        assert question == "What is artificial intelligence?"

    def test_extract_from_input_string(self):
        """Test extracting question from input string."""
        context = {"input": "How does machine learning work?"}
        question = self.agent._extract_question(context)
        assert question == "How does machine learning work?"

    def test_extract_from_input_dict(self):
        """Test extracting question from nested input dict."""
        context = {"input": {"input": "What is deep learning?"}}
        question = self.agent._extract_question(context)
        assert question == "What is deep learning?"

    def test_extract_with_whitespace(self):
        """Test extracting question with whitespace."""
        context = {"input": "  What is neural network?  "}
        question = self.agent._extract_question(context)
        assert question == "What is neural network?"

    def test_extract_from_non_string_input(self):
        """Test extracting question from non-string input."""
        context = {"input": 12345}
        question = self.agent._extract_question(context)
        assert question == "12345"

    def test_extract_empty_input(self):
        """Test extracting question from empty input."""
        context = {}
        question = self.agent._extract_question(context)
        assert question == ""

    def test_extract_priority_formatted_prompt_over_input(self):
        """Test that formatted_prompt takes priority over input."""
        context = {"formatted_prompt": "Priority question", "input": "Secondary question"}
        question = self.agent._extract_question(context)
        assert question == "Priority question"

    def test_extract_complex_nested_structure(self):
        """Test extracting from complex nested structure."""
        context = {"input": {"input": "Nested question", "metadata": {"source": "test"}}}
        question = self.agent._extract_question(context)
        assert question == "Nested question"


class TestGraphScoutErrorHandling:
    """Test GraphScout error handling methods."""

    def setup_method(self):
        """Set up test agent."""
        self.agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

    def test_handle_no_candidates(self):
        """Test handling when no candidates are found."""
        context = {"run_id": "test_run"}
        result = self.agent._handle_no_candidates(context)

        assert result["decision"] == "fallback"
        assert result["target"] is None
        assert result["confidence"] == 0.0
        assert "No viable paths found" in result["reasoning"]
        assert result["status"] == "no_candidates"

    def test_handle_budget_exceeded(self):
        """Test handling when budget is exceeded."""
        context = {"run_id": "test_run"}
        result = self.agent._handle_budget_exceeded(context)

        assert result["decision"] == "shortlist"
        assert result["target"] == []
        assert result["confidence"] == 0.0
        assert "exceed budget constraints" in result["reasoning"]
        assert result["status"] == "budget_exceeded"

    def test_handle_safety_violation(self):
        """Test handling when safety checks fail."""
        context = {"run_id": "test_run"}
        result = self.agent._handle_safety_violation(context)

        assert result["decision"] == "human_gate"
        assert result["target"] is None
        assert result["confidence"] == 0.0
        assert "failed safety assessment" in result["reasoning"]
        assert result["status"] == "safety_violation"


class TestGraphScoutTraceBuilding:
    """Test GraphScout trace building functionality."""

    def setup_method(self):
        """Set up test agent."""
        self.agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

    def test_build_basic_trace(self):
        """Test building basic trace dictionary."""
        question = "What is AI?"
        candidates = [
            {"node_id": "agent_1", "path": ["agent_1"]},
            {"node_id": "agent_2", "path": ["agent_2"]},
        ]
        scored_candidates = [
            {"node_id": "agent_1", "score": 0.8, "components": {"llm": 0.7, "heuristics": 0.9}},
            {"node_id": "agent_2", "score": 0.6, "components": {"llm": 0.5, "heuristics": 0.7}},
        ]
        decision_result = {
            "decision_type": "commit_next",
            "target": "agent_1",
            "confidence": 0.8,
            "reasoning": "Clear winner based on scores",
        }
        context = {"run_id": "test_run", "step_index": 5}

        trace = self.agent._build_trace_dict(
            question, candidates, scored_candidates, decision_result, context
        )

        # Verify trace structure
        assert trace["graph_scout_version"] == "1.0.0"
        assert "timestamp" in trace
        assert trace["question"] == question

        # Verify config section
        config = trace["config"]
        assert config["k_beam"] == self.agent.config.k_beam
        assert config["max_depth"] == self.agent.config.max_depth
        assert config["commit_margin"] == self.agent.config.commit_margin
        assert config["score_weights"] == self.agent.config.score_weights

        # Verify discovery section
        discovery = trace["discovery"]
        assert discovery["total_candidates"] == 2
        assert discovery["candidate_nodes"] == ["agent_1", "agent_2"]

        # Verify scoring section
        scoring = trace["scoring"]
        assert scoring["scored_candidates"] == 2
        assert len(scoring["top_scores"]) == 2
        assert scoring["top_scores"][0]["node_id"] == "agent_1"
        assert scoring["top_scores"][0]["score"] == 0.8

        # Verify decision section
        decision = trace["decision"]
        assert decision["type"] == "commit_next"
        assert decision["target"] == "agent_1"
        assert decision["confidence"] == 0.8
        assert decision["reasoning"] == "Clear winner based on scores"

        # Verify execution metadata
        metadata = trace["execution_metadata"]
        assert metadata["node_id"] == "test_scout"
        assert metadata["run_id"] == "test_run"
        assert metadata["step_index"] == 5

    def test_build_trace_with_missing_data(self):
        """Test building trace with missing or incomplete data."""
        question = "Test question"
        candidates = []
        scored_candidates = []
        decision_result = {}
        context = {}

        trace = self.agent._build_trace_dict(
            question, candidates, scored_candidates, decision_result, context
        )

        # Should handle missing data gracefully
        assert trace["question"] == question
        assert trace["discovery"]["total_candidates"] == 0
        assert trace["discovery"]["candidate_nodes"] == []
        assert trace["scoring"]["scored_candidates"] == 0
        assert trace["scoring"]["top_scores"] == []
        assert trace["decision"]["type"] is None
        assert trace["decision"]["target"] is None
        assert trace["execution_metadata"]["run_id"] == "unknown"
        assert trace["execution_metadata"]["step_index"] == 0

    def test_build_trace_with_unknown_candidates(self):
        """Test building trace with candidates missing node_id."""
        question = "Test question"
        candidates = [
            {"path": ["agent_1"]},  # Missing node_id
            {"node_id": "agent_2", "path": ["agent_2"]},
        ]
        scored_candidates = [
            {"score": 0.8, "components": {}},  # Missing node_id
            {"node_id": "agent_2", "score": 0.6, "components": {}},
        ]
        decision_result = {"decision_type": "shortlist"}
        context = {}

        trace = self.agent._build_trace_dict(
            question, candidates, scored_candidates, decision_result, context
        )

        # Should handle missing node_ids gracefully
        assert trace["discovery"]["candidate_nodes"] == ["unknown", "agent_2"]
        assert trace["scoring"]["top_scores"][0]["node_id"] == "unknown"
        assert trace["scoring"]["top_scores"][1]["node_id"] == "agent_2"


class TestGraphScoutRunMethod:
    """Test GraphScout main run method."""

    def setup_method(self):
        """Set up test agent."""
        self.agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

    @pytest.mark.asyncio
    async def test_run_missing_orchestrator(self):
        """Test run method with missing orchestrator."""
        context = {"input": "Test question", "previous_outputs": {}}

        result = await self.agent.run(context)

        assert result["status"] == "error"
        assert result["decision"] == "fallback"
        assert result["target"] is None
        assert result["confidence"] == 0.0
        assert "GraphScout requires orchestrator context" in result["reasoning"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_successful_workflow(self):
        """Test successful run workflow with mocked components."""
        # Mock all components
        with patch.object(self.agent, "initialize", new_callable=AsyncMock) as mock_init:
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:
                    with patch.object(self.agent, "budget_controller") as mock_budget:
                        with patch.object(self.agent, "smart_evaluator") as mock_evaluator:
                            with patch.object(self.agent, "safety_controller") as mock_safety:
                                with patch.object(self.agent, "scorer") as mock_scorer:
                                    with patch.object(
                                        self.agent, "decision_engine"
                                    ) as mock_decision:

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
                                        mock_evaluator.simulate_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "path": ["agent_1"],
                                                    "llm_evaluation": {
                                                        "final_scores": {"relevance": 0.8}
                                                    },
                                                }
                                            ]
                                        )
                                        mock_safety.assess_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "path": ["agent_1"],
                                                    "safety_score": 0.9,
                                                }
                                            ]
                                        )
                                        mock_scorer.score_candidates = AsyncMock(
                                            return_value=[
                                                {
                                                    "node_id": "agent_1",
                                                    "score": 0.85,
                                                    "components": {"llm": 0.8, "safety": 0.9},
                                                }
                                            ]
                                        )
                                        mock_decision.make_decision = AsyncMock(
                                            return_value={
                                                "decision_type": "commit_next",
                                                "target": "agent_1",
                                                "confidence": 0.85,
                                                "reasoning": "Best candidate found",
                                            }
                                        )

                                        context = {
                                            "input": "Test question",
                                            "orchestrator": Mock(),
                                            "run_id": "test_run",
                                            "step_index": 1,
                                            "previous_outputs": {},
                                        }

                                        result = await self.agent.run(context)

                                        # Verify successful result
                                        assert result["status"] == "success"
                                        assert result["decision"] == "commit_next"
                                        assert result["target"] == "agent_1"
                                        assert result["confidence"] == 0.85
                                        assert result["reasoning"] == "Best candidate found"
                                        assert "trace" in result
                                        assert "input" in result
                                        assert "previous_outputs" in result
                                        assert "result" in result

                                        # Verify all components were called
                                        mock_graph_api.get_graph_state.assert_called_once()
                                        mock_introspector.discover_paths.assert_called_once()
                                        mock_budget.filter_candidates.assert_called_once()
                                        mock_evaluator.simulate_candidates.assert_called_once()
                                        mock_safety.assess_candidates.assert_called_once()
                                        mock_scorer.score_candidates.assert_called_once()
                                        mock_decision.make_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_no_candidates_discovered(self):
        """Test run method when no candidates are discovered."""
        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:

                    mock_graph_api.get_graph_state = AsyncMock(return_value=Mock())
                    mock_introspector.discover_paths = AsyncMock(return_value=[])

                    context = {
                        "input": "Test question",
                        "orchestrator": Mock(),
                        "run_id": "test_run",
                    }

                    result = await self.agent.run(context)

                    assert result["decision"] == "fallback"
                    assert result["status"] == "no_candidates"
                    assert result["target"] is None
                    assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_run_budget_exceeded(self):
        """Test run method when budget is exceeded."""
        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:
                    with patch.object(self.agent, "budget_controller") as mock_budget:

                        mock_graph_api.get_graph_state = AsyncMock(return_value=Mock())
                        mock_introspector.discover_paths = AsyncMock(
                            return_value=[{"node_id": "agent_1", "path": ["agent_1"]}]
                        )
                        mock_budget.filter_candidates = AsyncMock(return_value=[])

                        context = {
                            "input": "Test question",
                            "orchestrator": Mock(),
                            "run_id": "test_run",
                        }

                        result = await self.agent.run(context)

                        assert result["decision"] == "shortlist"
                        assert result["status"] == "budget_exceeded"
                        assert result["target"] == []
                        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_run_safety_violation(self):
        """Test run method when safety checks fail."""
        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:
                    with patch.object(self.agent, "budget_controller") as mock_budget:
                        with patch.object(self.agent, "smart_evaluator") as mock_evaluator:
                            with patch.object(self.agent, "safety_controller") as mock_safety:

                                mock_graph_api.get_graph_state = AsyncMock(return_value=Mock())
                                mock_introspector.discover_paths = AsyncMock(
                                    return_value=[{"node_id": "agent_1", "path": ["agent_1"]}]
                                )
                                mock_budget.filter_candidates = AsyncMock(
                                    return_value=[{"node_id": "agent_1", "path": ["agent_1"]}]
                                )
                                mock_evaluator.simulate_candidates = AsyncMock(
                                    return_value=[{"node_id": "agent_1", "path": ["agent_1"]}]
                                )
                                mock_safety.assess_candidates = AsyncMock(return_value=[])

                                context = {
                                    "input": "Test question",
                                    "orchestrator": Mock(),
                                    "run_id": "test_run",
                                }

                                result = await self.agent.run(context)

                                assert result["decision"] == "human_gate"
                                assert result["status"] == "safety_violation"
                                assert result["target"] is None
                                assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_run_exception_handling(self):
        """Test run method exception handling."""
        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:

                # Make graph_api raise an exception
                mock_graph_api.get_graph_state = AsyncMock(
                    side_effect=Exception("Graph API failed")
                )

                context = {"input": "Test question", "orchestrator": Mock(), "run_id": "test_run"}

                result = await self.agent.run(context)

                assert result["status"] == "error"
                assert result["decision"] == "fallback"
                assert result["target"] is None
                assert result["confidence"] == 0.0
                assert "GraphScout failed" in result["reasoning"]
                assert result["error"] == "Graph API failed"

    @pytest.mark.asyncio
    async def test_run_context_propagation(self):
        """Test that context is properly propagated to components."""
        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:
                    with patch.object(self.agent, "budget_controller") as mock_budget:
                        with patch.object(self.agent, "smart_evaluator") as mock_evaluator:
                            with patch.object(self.agent, "safety_controller") as mock_safety:
                                with patch.object(self.agent, "scorer") as mock_scorer:
                                    with patch.object(
                                        self.agent, "decision_engine"
                                    ) as mock_decision:

                                        # Setup minimal mocks
                                        mock_graph_api.get_graph_state = AsyncMock(
                                            return_value=Mock()
                                        )
                                        mock_introspector.discover_paths = AsyncMock(
                                            return_value=[{"node_id": "agent_1"}]
                                        )
                                        mock_budget.filter_candidates = AsyncMock(
                                            return_value=[{"node_id": "agent_1"}]
                                        )
                                        mock_evaluator.simulate_candidates = AsyncMock(
                                            return_value=[{"node_id": "agent_1"}]
                                        )
                                        mock_safety.assess_candidates = AsyncMock(
                                            return_value=[{"node_id": "agent_1"}]
                                        )
                                        mock_scorer.score_candidates = AsyncMock(
                                            return_value=[{"node_id": "agent_1", "score": 0.8}]
                                        )
                                        mock_decision.make_decision = AsyncMock(
                                            return_value={
                                                "decision_type": "commit_next",
                                                "target": "agent_1",
                                                "confidence": 0.8,
                                            }
                                        )

                                        context = {
                                            "input": "Test question",
                                            "orchestrator": Mock(),
                                            "run_id": "test_run",
                                            "step_index": 2,
                                            "previous_outputs": {"agent_0": "previous result"},
                                        }

                                        await self.agent.run(context)

                                        # Verify context propagation
                                        # Introspector should get executing_node
                                        args, kwargs = mock_introspector.discover_paths.call_args
                                        assert kwargs["executing_node"] == "test_scout"

                                        # Smart evaluator should get current_agent_id
                                        args, kwargs = mock_evaluator.simulate_candidates.call_args
                                        evaluation_context = args[2]  # context parameter
                                        assert (
                                            evaluation_context["current_agent_id"] == "test_scout"
                                        )

                                        # Decision engine should get current_agent_id
                                        args, kwargs = mock_decision.make_decision.call_args
                                        decision_context = args[1]  # context parameter
                                        assert decision_context["current_agent_id"] == "test_scout"


class TestGraphScoutDataClasses:
    """Test GraphScout data classes."""

    def test_path_candidate_creation(self):
        """Test PathCandidate data class."""
        candidate = PathCandidate(
            node_id="test_agent",
            path=["test_agent"],
            score=0.85,
            components={"llm": 0.8, "heuristics": 0.9},
            preview="Test preview",
            rationale="Good candidate",
            expected_cost=0.01,
            expected_latency=100,
            safety_score=0.95,
            confidence=0.8,
        )

        assert candidate.node_id == "test_agent"
        assert candidate.path == ["test_agent"]
        assert candidate.score == 0.85
        assert candidate.components == {"llm": 0.8, "heuristics": 0.9}
        assert candidate.preview == "Test preview"
        assert candidate.rationale == "Good candidate"
        assert candidate.expected_cost == 0.01
        assert candidate.expected_latency == 100
        assert candidate.safety_score == 0.95
        assert candidate.confidence == 0.8

    def test_scout_decision_creation(self):
        """Test ScoutDecision data class."""
        decision = ScoutDecision(
            decision_type="commit_next",
            target="best_agent",
            confidence=0.9,
            trace={"step": 1, "candidates": 3},
            reasoning="Clear winner identified",
        )

        assert decision.decision_type == "commit_next"
        assert decision.target == "best_agent"
        assert decision.confidence == 0.9
        assert decision.trace == {"step": 1, "candidates": 3}
        assert decision.reasoning == "Clear winner identified"


class TestGraphScoutEdgeCases:
    """Test GraphScout edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test agent."""
        self.agent = GraphScoutAgent(node_id="test_scout", prompt="Test prompt", queue=[])

    def test_extract_question_with_none_values(self):
        """Test question extraction with None values."""
        context = {"formatted_prompt": None, "input": None}
        question = self.agent._extract_question(context)
        assert question == "None"

    def test_extract_question_with_empty_dict(self):
        """Test question extraction with empty nested dict."""
        context = {"input": {}}
        question = self.agent._extract_question(context)
        assert question == "{}"

    def test_build_trace_with_large_candidate_list(self):
        """Test trace building with many candidates (should limit to top 3)."""
        question = "Test question"
        candidates = [{"node_id": f"agent_{i}"} for i in range(10)]
        scored_candidates = [
            {"node_id": f"agent_{i}", "score": 0.9 - i * 0.1, "components": {}} for i in range(10)
        ]
        decision_result = {"decision_type": "shortlist"}
        context = {}

        trace = self.agent._build_trace_dict(
            question, candidates, scored_candidates, decision_result, context
        )

        # Should only include top 3 scores
        assert len(trace["scoring"]["top_scores"]) == 3
        assert trace["scoring"]["top_scores"][0]["node_id"] == "agent_0"
        assert trace["scoring"]["top_scores"][1]["node_id"] == "agent_1"
        assert trace["scoring"]["top_scores"][2]["node_id"] == "agent_2"

    @pytest.mark.asyncio
    async def test_run_with_minimal_context(self):
        """Test run method with minimal context."""
        context = {"orchestrator": Mock()}

        with patch.object(self.agent, "initialize", new_callable=AsyncMock):
            with patch.object(self.agent, "graph_api") as mock_graph_api:
                with patch.object(self.agent, "introspector") as mock_introspector:

                    mock_graph_api.get_graph_state = AsyncMock(return_value=Mock())
                    mock_introspector.discover_paths = AsyncMock(return_value=[])

                    result = await self.agent.run(context)

                    # Should handle minimal context gracefully
                    assert result["status"] == "no_candidates"
                    # Note: _handle_no_candidates doesn't include input in result
                    # This is expected behavior for error cases

    @pytest.mark.asyncio
    async def test_run_with_auto_initialization(self):
        """Test that run method auto-initializes components if needed."""
        context = {"input": "Test question", "orchestrator": Mock(), "run_id": "test_run"}

        # Don't pre-initialize components
        assert self.agent.graph_api is None

        # Track initialization by checking if components are created after run
        await self.agent.run(context)

        # Should have auto-initialized components during run
        assert self.agent.graph_api is not None
        assert self.agent.introspector is not None
        assert self.agent.scorer is not None
        assert self.agent.smart_evaluator is not None
        assert self.agent.safety_controller is not None
        assert self.agent.budget_controller is not None
        assert self.agent.decision_engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
