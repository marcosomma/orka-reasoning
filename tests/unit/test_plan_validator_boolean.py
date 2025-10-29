# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for PlanValidator Boolean Integration
===========================================

Tests boolean-based validation system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.agents.plan_validator import boolean_parser
from orka.agents.plan_validator.agent import PlanValidatorAgent
from orka.agents.plan_validator.prompt_builder import build_validation_prompt


class TestBooleanParser:
    """Test boolean evaluation parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = """
        {
            "completeness": {
                "has_all_required_steps": true,
                "addresses_all_query_aspects": false,
                "handles_edge_cases": true,
                "includes_fallback_path": false
            },
            "efficiency": {
                "minimizes_redundant_calls": true,
                "uses_appropriate_agents": true,
                "optimizes_cost": false,
                "optimizes_latency": true
            },
            "safety": {
                "validates_inputs": true,
                "handles_errors_gracefully": false,
                "has_timeout_protection": true,
                "avoids_risky_combinations": true
            },
            "coherence": {
                "logical_agent_sequence": true,
                "proper_data_flow": true,
                "no_conflicting_actions": true
            }
        }
        """

        result = boolean_parser.parse_boolean_evaluation(response)

        assert result["completeness"]["has_all_required_steps"] is True
        assert result["completeness"]["addresses_all_query_aspects"] is False
        assert result["efficiency"]["minimizes_redundant_calls"] is True
        assert result["safety"]["validates_inputs"] is True

    def test_parse_json_in_markdown(self):
        """Test parsing JSON in markdown code blocks."""
        response = """
        Here's my evaluation:
        
        ```json
        {
            "completeness": {
                "has_all_required_steps": true,
                "addresses_all_query_aspects": true,
                "handles_edge_cases": false,
                "includes_fallback_path": true
            },
            "efficiency": {
                "minimizes_redundant_calls": false,
                "uses_appropriate_agents": true,
                "optimizes_cost": true,
                "optimizes_latency": false
            },
            "safety": {
                "validates_inputs": true,
                "handles_errors_gracefully": true,
                "has_timeout_protection": false,
                "avoids_risky_combinations": true
            },
            "coherence": {
                "logical_agent_sequence": true,
                "proper_data_flow": false,
                "no_conflicting_actions": true
            }
        }
        ```
        """

        result = boolean_parser.parse_boolean_evaluation(response)

        assert result["completeness"]["has_all_required_steps"] is True
        assert result["efficiency"]["minimizes_redundant_calls"] is False

    def test_parse_fallback_text(self):
        """Test fallback text parsing."""
        response = """
        has_all_required_steps: true
        addresses_all_query_aspects: false
        minimizes_redundant_calls: yes
        validates_inputs: no
        """

        result = boolean_parser.parse_boolean_evaluation(response)

        assert "completeness" in result
        assert "efficiency" in result
        assert "safety" in result
        assert "coherence" in result

    def test_normalize_string_booleans(self):
        """Test normalization of string boolean values."""
        response = """
        {
            "completeness": {
                "has_all_required_steps": "true",
                "addresses_all_query_aspects": "yes",
                "handles_edge_cases": "false",
                "includes_fallback_path": "no"
            },
            "efficiency": {
                "minimizes_redundant_calls": "1",
                "uses_appropriate_agents": "0",
                "optimizes_cost": "pass",
                "optimizes_latency": "fail"
            },
            "safety": {
                "validates_inputs": true,
                "handles_errors_gracefully": false,
                "has_timeout_protection": true,
                "avoids_risky_combinations": false
            },
            "coherence": {
                "logical_agent_sequence": true,
                "proper_data_flow": false,
                "no_conflicting_actions": true
            }
        }
        """

        result = boolean_parser.parse_boolean_evaluation(response)

        assert result["completeness"]["has_all_required_steps"] is True
        assert result["completeness"]["addresses_all_query_aspects"] is True
        assert result["completeness"]["handles_edge_cases"] is False
        assert result["efficiency"]["minimizes_redundant_calls"] is True
        assert result["efficiency"]["uses_appropriate_agents"] is False


class TestPromptBuilder:
    """Test validation prompt building."""

    def test_build_basic_prompt(self):
        """Test building basic validation prompt."""
        prompt = build_validation_prompt(
            query="Search for information about AI",
            proposed_path={"agent": "search", "target": "web"},
            previous_critiques=[],
            loop_number=1,
            preset_name="moderate",
        )

        assert "Search for information about AI" in prompt
        assert "completeness" in prompt.lower()
        assert "efficiency" in prompt.lower()
        assert "safety" in prompt.lower()
        assert "coherence" in prompt.lower()
        assert "true/false" in prompt.lower()

    def test_build_prompt_with_history(self):
        """Test building prompt with previous critiques."""
        previous_critiques = [
            {
                "score": 0.65,
                "assessment": "NEEDS_IMPROVEMENT",
                "failed_criteria": ["completeness.handles_edge_cases"],
            }
        ]

        prompt = build_validation_prompt(
            query="Test query",
            proposed_path={"agent": "test"},
            previous_critiques=previous_critiques,
            loop_number=2,
            preset_name="strict",
        )

        assert "PREVIOUS CRITIQUES" in prompt
        assert "Round 1" in prompt
        assert "0.65" in prompt


class TestPlanValidatorAgent:
    """Test PlanValidatorAgent with boolean scoring."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test agent initialization with scoring preset."""
        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="strict",
        )

        assert agent.agent_id == "test_validator"
        assert agent.scoring_preset == "strict"
        assert agent.score_calculator is not None

    @pytest.mark.asyncio
    async def test_validation_with_boolean_response(self):
        """Test full validation with boolean LLM response."""
        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="moderate",
        )

        mock_llm_response = """
        {
            "completeness": {
                "has_all_required_steps": true,
                "addresses_all_query_aspects": true,
                "handles_edge_cases": true,
                "includes_fallback_path": true
            },
            "efficiency": {
                "minimizes_redundant_calls": true,
                "uses_appropriate_agents": true,
                "optimizes_cost": true,
                "optimizes_latency": true
            },
            "safety": {
                "validates_inputs": true,
                "handles_errors_gracefully": true,
                "has_timeout_protection": true,
                "avoids_risky_combinations": true
            },
            "coherence": {
                "logical_agent_sequence": true,
                "proper_data_flow": true,
                "no_conflicting_actions": true
            },
            "rationale": "The proposed path is excellent."
        }
        """

        ctx = {
            "input": "Test query",
            "previous_outputs": {
                "graph_scout": {
                    "decision_type": "agent",
                    "target": "search_agent",
                }
            },
        }

        with patch(
            "orka.agents.plan_validator.llm_client.call_llm",
            new=AsyncMock(return_value=mock_llm_response),
        ):
            result = await agent._run_impl(ctx)

        assert "validation_score" in result
        assert result["validation_score"] == 1.0
        assert result["overall_assessment"] == "APPROVED"
        assert "boolean_evaluations" in result
        assert "passed_criteria" in result
        assert result["scoring_preset"] == "moderate"

    @pytest.mark.asyncio
    async def test_validation_with_partial_pass(self):
        """Test validation with some failed criteria."""
        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="moderate",
        )

        mock_llm_response = """
        {
            "completeness": {
                "has_all_required_steps": true,
                "addresses_all_query_aspects": false,
                "handles_edge_cases": false,
                "includes_fallback_path": true
            },
            "efficiency": {
                "minimizes_redundant_calls": true,
                "uses_appropriate_agents": true,
                "optimizes_cost": false,
                "optimizes_latency": false
            },
            "safety": {
                "validates_inputs": true,
                "handles_errors_gracefully": false,
                "has_timeout_protection": false,
                "avoids_risky_combinations": true
            },
            "coherence": {
                "logical_agent_sequence": true,
                "proper_data_flow": true,
                "no_conflicting_actions": true
            },
            "rationale": "Some improvements needed."
        }
        """

        ctx = {
            "input": "Test query",
            "previous_outputs": {
                "graph_scout": {"decision_type": "agent", "target": "search_agent"}
            },
        }

        with patch(
            "orka.agents.plan_validator.llm_client.call_llm",
            new=AsyncMock(return_value=mock_llm_response),
        ):
            result = await agent._run_impl(ctx)

        assert result["validation_score"] < 1.0
        assert result["validation_score"] > 0.0
        assert len(result["failed_criteria"]) > 0
        assert "completeness.addresses_all_query_aspects" in result["failed_criteria"]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling during validation."""
        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="moderate",
        )

        ctx = {
            "input": "Test query",
            "previous_outputs": {
                "graph_scout": {"decision_type": "agent", "target": "search_agent"}
            },
        }

        with patch(
            "orka.agents.plan_validator.llm_client.call_llm",
            new=AsyncMock(side_effect=RuntimeError("LLM failed")),
        ):
            result = await agent._run_impl(ctx)

        assert result["validation_score"] == 0.0
        assert result["overall_assessment"] == "REJECTED"
        assert "error" in result
        assert "LLM failed" in result["error"]

    @pytest.mark.asyncio
    async def test_custom_weights(self):
        """Test agent with custom weights."""
        custom_weights = {
            "completeness.has_all_required_steps": 0.50,
        }

        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="moderate",
            custom_weights=custom_weights,
        )

        assert agent.score_calculator.flat_weights["completeness.has_all_required_steps"] == 0.50

    @pytest.mark.asyncio
    async def test_extract_rationale(self):
        """Test rationale extraction from LLM response."""
        agent = PlanValidatorAgent(
            agent_id="test_validator",
            scoring_preset="moderate",
        )

        response_with_rationale = '{"rationale": "This is the rationale"}'
        rationale = agent._extract_rationale(response_with_rationale)
        assert rationale == "This is the rationale"

        response_without_rationale = "Some other text"
        rationale = agent._extract_rationale(response_without_rationale)
        assert isinstance(rationale, str)
        assert len(rationale) > 0
