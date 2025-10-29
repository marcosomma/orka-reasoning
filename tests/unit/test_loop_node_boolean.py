# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for LoopNode Boolean Scoring
===================================

Tests boolean scoring integration in LoopNode.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.nodes.loop_node import LoopNode


class TestLoopNodeBooleanScoring:
    """Test LoopNode with boolean scoring configuration."""

    def test_initialization_with_scoring_preset(self):
        """Test LoopNode initialization with scoring preset."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "strict"},
        )

        assert node.scoring_preset == "strict"
        assert node.score_calculator is not None

    def test_initialization_with_custom_weights(self):
        """Test LoopNode initialization with custom weights."""
        custom_weights = {
            "completeness.has_all_required_steps": 0.50,
        }

        node = LoopNode(
            node_id="test_loop",
            scoring={
                "preset": "moderate",
                "custom_weights": custom_weights,
            },
        )

        assert node.scoring_preset == "moderate"
        assert node.score_calculator is not None
        assert node.score_calculator.flat_weights["completeness.has_all_required_steps"] == 0.50

    def test_initialization_without_scoring_preset(self):
        """Test LoopNode initialization without scoring preset (legacy mode)."""
        node = LoopNode(node_id="test_loop")

        assert node.scoring_preset is None
        assert node.score_calculator is None

    @pytest.mark.asyncio
    async def test_boolean_scoring_extraction_from_validator(self):
        """Test boolean score extraction from PlanValidator response."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
            max_loops=1,
        )

        result = {
            "plan_validator": {
                "validation_score": 0.85,
                "overall_assessment": "APPROVED",
                "boolean_evaluations": {
                    "completeness": {
                        "has_all_required_steps": True,
                        "addresses_all_query_aspects": True,
                        "handles_edge_cases": True,
                        "includes_fallback_path": True,
                    },
                    "efficiency": {
                        "minimizes_redundant_calls": True,
                        "uses_appropriate_agents": True,
                        "optimizes_cost": False,
                        "optimizes_latency": True,
                    },
                    "safety": {
                        "validates_inputs": True,
                        "handles_errors_gracefully": True,
                        "has_timeout_protection": False,
                        "avoids_risky_combinations": True,
                    },
                    "coherence": {
                        "logical_agent_sequence": True,
                        "proper_data_flow": True,
                        "no_conflicting_actions": True,
                    },
                },
            }
        }

        score = await node._extract_score(result)

        assert score > 0.0
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_boolean_scoring_from_json_response(self):
        """Test boolean score extraction from JSON in response text."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
            max_loops=1,
        )

        result = {
            "test_agent": {
                "response": """
                {
                    "completeness": {
                        "has_all_required_steps": true,
                        "addresses_all_query_aspects": true,
                        "handles_edge_cases": false,
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
                    }
                }
                """
            }
        }

        score = await node._extract_score(result)

        assert score > 0.0
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_fallback_to_legacy_scoring(self):
        """Test fallback to legacy scoring when boolean not available."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
            max_loops=1,
        )

        result = {"test_agent": {"response": "The quality score is 0.75"}}

        score = await node._extract_score(result)

        assert score == 0.75

    @pytest.mark.asyncio
    async def test_legacy_scoring_without_preset(self):
        """Test legacy scoring still works without preset."""
        node = LoopNode(
            node_id="test_loop",
            max_loops=1,
        )

        result = {"test_agent": {"response": "score: 0.82"}}

        score = await node._extract_score(result)

        assert score == 0.82

    def test_is_valid_boolean_structure(self):
        """Test boolean structure validation."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
        )

        valid_structure = {
            "completeness": {"has_all_required_steps": True},
            "efficiency": {"minimizes_redundant_calls": False},
            "safety": {"validates_inputs": True},
        }

        assert node._is_valid_boolean_structure(valid_structure) is True

        invalid_structure = {"random_key": {"value": True}}

        assert node._is_valid_boolean_structure(invalid_structure) is False

    def test_extract_boolean_from_text(self):
        """Test boolean extraction from text."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
        )

        text = """
        {
            "completeness": {
                "has_all_required_steps": true
            },
            "efficiency": {
                "minimizes_redundant_calls": false
            },
            "safety": {
                "validates_inputs": true
            },
            "coherence": {
                "logical_agent_sequence": true
            }
        }
        """

        result = node._extract_boolean_from_text(text)

        assert result is not None
        assert "completeness" in result
        assert result["completeness"]["has_all_required_steps"] is True

    def test_extract_boolean_from_invalid_text(self):
        """Test boolean extraction from invalid text."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
        )

        text = "This is just plain text with no JSON"

        result = node._extract_boolean_from_text(text)

        assert result is None

    @pytest.mark.asyncio
    async def test_deterministic_scoring(self):
        """Test that boolean scoring is deterministic."""
        node = LoopNode(
            node_id="test_loop",
            scoring={"preset": "moderate"},
            max_loops=1,
        )

        result = {
            "test_agent": {
                "boolean_evaluations": {
                    "completeness": {
                        "has_all_required_steps": True,
                        "addresses_all_query_aspects": False,
                        "handles_edge_cases": True,
                        "includes_fallback_path": False,
                    },
                    "efficiency": {
                        "minimizes_redundant_calls": True,
                        "uses_appropriate_agents": True,
                        "optimizes_cost": False,
                        "optimizes_latency": True,
                    },
                    "safety": {
                        "validates_inputs": True,
                        "handles_errors_gracefully": False,
                        "has_timeout_protection": True,
                        "avoids_risky_combinations": True,
                    },
                    "coherence": {
                        "logical_agent_sequence": True,
                        "proper_data_flow": True,
                        "no_conflicting_actions": True,
                    },
                }
            }
        }

        score1 = await node._extract_score(result)
        score2 = await node._extract_score(result)
        score3 = await node._extract_score(result)

        assert score1 == score2 == score3
