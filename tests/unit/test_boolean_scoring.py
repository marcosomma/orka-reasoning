# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for Boolean Scoring System
=================================

Tests preset loading, score calculation, and determinism.
"""

import pytest

from orka.scoring import BooleanScoreCalculator, PRESETS, load_preset


class TestPresetLoading:
    """Test loading of scoring presets."""

    def test_load_strict_preset(self):
        """Test loading strict preset."""
        preset = load_preset("strict")

        assert "weights" in preset
        assert "thresholds" in preset
        assert preset["thresholds"]["approved"] == 0.90
        assert preset["thresholds"]["needs_improvement"] == 0.75

    def test_load_moderate_preset(self):
        """Test loading moderate preset."""
        preset = load_preset("moderate")

        assert "weights" in preset
        assert "thresholds" in preset
        assert preset["thresholds"]["approved"] == 0.85
        assert preset["thresholds"]["needs_improvement"] == 0.70

    def test_load_lenient_preset(self):
        """Test loading lenient preset."""
        preset = load_preset("lenient")

        assert "weights" in preset
        assert "thresholds" in preset
        assert preset["thresholds"]["approved"] == 0.80
        assert preset["thresholds"]["needs_improvement"] == 0.65

    def test_load_invalid_preset(self):
        """Test loading invalid preset raises error."""
        with pytest.raises(ValueError, match="Unknown scoring preset"):
            load_preset("nonexistent")

    def test_all_presets_have_required_dimensions(self):
        """Test all presets have required validation dimensions."""
        required_dimensions = ["completeness", "efficiency", "safety", "coherence"]

        for preset_name, preset_config in PRESETS.items():
            weights = preset_config["weights"]

            for dimension in required_dimensions:
                assert dimension in weights, f"{preset_name} missing {dimension}"


class TestBooleanScoreCalculator:
    """Test BooleanScoreCalculator functionality."""

    def test_initialization_with_default_preset(self):
        """Test calculator initialization with default preset."""
        calculator = BooleanScoreCalculator()

        assert calculator.preset_name == "moderate"
        assert len(calculator.flat_weights) > 0

    def test_initialization_with_custom_preset(self):
        """Test calculator initialization with custom preset."""
        calculator = BooleanScoreCalculator(preset="strict")

        assert calculator.preset_name == "strict"
        assert calculator.thresholds["approved"] == 0.90

    def test_perfect_score(self):
        """Test calculation with all criteria passing."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": True,
                "handles_edge_cases": True,
                "includes_fallback_path": True,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": True,
                "optimizes_cost": True,
                "optimizes_latency": True,
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": True,
                "has_timeout_protection": True,
                "avoids_risky_combinations": True,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": True,
                "no_conflicting_actions": True,
            },
        }

        result = calculator.calculate(evaluations)

        assert result["score"] == 1.0
        assert result["assessment"] == "APPROVED"
        assert result["passed_count"] == result["total_criteria"]
        assert len(result["failed_criteria"]) == 0

    def test_zero_score(self):
        """Test calculation with all criteria failing."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": False,
                "addresses_all_query_aspects": False,
                "handles_edge_cases": False,
                "includes_fallback_path": False,
            },
            "efficiency": {
                "minimizes_redundant_calls": False,
                "uses_appropriate_agents": False,
                "optimizes_cost": False,
                "optimizes_latency": False,
            },
            "safety": {
                "validates_inputs": False,
                "handles_errors_gracefully": False,
                "has_timeout_protection": False,
                "avoids_risky_combinations": False,
            },
            "coherence": {
                "logical_agent_sequence": False,
                "proper_data_flow": False,
                "no_conflicting_actions": False,
            },
        }

        result = calculator.calculate(evaluations)

        assert result["score"] == 0.0
        assert result["assessment"] == "REJECTED"
        assert result["failed_count"] == result["total_criteria"]
        assert len(result["passed_criteria"]) == 0

    def test_partial_score(self):
        """Test calculation with some criteria passing."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": True,
                "handles_edge_cases": False,
                "includes_fallback_path": False,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": True,
                "optimizes_cost": False,
                "optimizes_latency": False,
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": False,
                "has_timeout_protection": False,
                "avoids_risky_combinations": False,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": False,
                "no_conflicting_actions": False,
            },
        }

        result = calculator.calculate(evaluations)

        assert 0.0 < result["score"] < 1.0
        assert result["passed_count"] > 0
        assert result["failed_count"] > 0
        assert result["passed_count"] + result["failed_count"] == result["total_criteria"]

    def test_determinism(self):
        """Test that same input always produces same output."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": False,
                "handles_edge_cases": True,
                "includes_fallback_path": False,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": True,
                "optimizes_cost": True,
                "optimizes_latency": False,
            },
            "safety": {
                "validates_inputs": False,
                "handles_errors_gracefully": True,
                "has_timeout_protection": False,
                "avoids_risky_combinations": True,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": True,
                "no_conflicting_actions": True,
            },
        }

        result1 = calculator.calculate(evaluations)
        result2 = calculator.calculate(evaluations)
        result3 = calculator.calculate(evaluations)

        assert result1["score"] == result2["score"] == result3["score"]
        assert result1["assessment"] == result2["assessment"] == result3["assessment"]
        assert result1["passed_criteria"] == result2["passed_criteria"] == result3["passed_criteria"]

    def test_assessment_thresholds(self):
        """Test assessment categories based on thresholds."""
        calculator = BooleanScoreCalculator(preset="moderate")

        score_approved = calculator._score_to_assessment(0.90)
        score_needs_improvement = calculator._score_to_assessment(0.75)
        score_rejected = calculator._score_to_assessment(0.60)

        assert score_approved == "APPROVED"
        assert score_needs_improvement == "NEEDS_IMPROVEMENT"
        assert score_rejected == "REJECTED"

    def test_custom_weights(self):
        """Test custom weight overrides."""
        custom_weights = {
            "completeness.has_all_required_steps": 0.50,
        }

        calculator = BooleanScoreCalculator(preset="moderate", custom_weights=custom_weights)

        assert calculator.flat_weights["completeness.has_all_required_steps"] == 0.50

    def test_dimension_scores(self):
        """Test dimension-level score calculation."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": True,
                "handles_edge_cases": True,
                "includes_fallback_path": True,
            },
            "efficiency": {
                "minimizes_redundant_calls": False,
                "uses_appropriate_agents": False,
                "optimizes_cost": False,
                "optimizes_latency": False,
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": True,
                "has_timeout_protection": False,
                "avoids_risky_combinations": False,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": True,
                "no_conflicting_actions": True,
            },
        }

        result = calculator.calculate(evaluations)

        assert "dimension_scores" in result
        assert "completeness" in result["dimension_scores"]
        assert "efficiency" in result["dimension_scores"]

        completeness_score = result["dimension_scores"]["completeness"]["percentage"]
        efficiency_score = result["dimension_scores"]["efficiency"]["percentage"]

        assert completeness_score == 100.0
        assert efficiency_score == 0.0

    def test_breakdown_format(self):
        """Test breakdown formatting."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": False,
                "handles_edge_cases": False,
                "includes_fallback_path": False,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": False,
                "optimizes_cost": False,
                "optimizes_latency": False,
            },
            "safety": {
                "validates_inputs": False,
                "handles_errors_gracefully": False,
                "has_timeout_protection": False,
                "avoids_risky_combinations": False,
            },
            "coherence": {
                "logical_agent_sequence": False,
                "proper_data_flow": False,
                "no_conflicting_actions": False,
            },
        }

        result = calculator.calculate(evaluations)
        breakdown = calculator.get_breakdown(result)

        assert "Score:" in breakdown
        assert "Passed:" in breakdown
        assert "COMPLETENESS:" in breakdown
        assert "✓" in breakdown
        assert "✗" in breakdown

    def test_get_failed_criteria(self):
        """Test extraction of failed criteria."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": False,
                "handles_edge_cases": False,
                "includes_fallback_path": True,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": True,
                "optimizes_cost": True,
                "optimizes_latency": True,
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": True,
                "has_timeout_protection": True,
                "avoids_risky_combinations": True,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": True,
                "no_conflicting_actions": True,
            },
        }

        result = calculator.calculate(evaluations)
        failed = calculator.get_failed_criteria(result)

        assert "completeness.addresses_all_query_aspects" in failed
        assert "completeness.handles_edge_cases" in failed
        assert len(failed) == 2

    def test_missing_boolean_values(self):
        """Test handling of missing boolean values."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
            },
            "efficiency": {},
            "safety": {
                "validates_inputs": True,
            },
            "coherence": {},
        }

        result = calculator.calculate(evaluations)

        assert result["score"] < 1.0
        assert len(result["failed_criteria"]) > 0

    def test_string_boolean_values(self):
        """Test handling of string boolean values."""
        calculator = BooleanScoreCalculator(preset="moderate")

        evaluations = {
            "completeness": {
                "has_all_required_steps": "true",
                "addresses_all_query_aspects": "yes",
                "handles_edge_cases": "false",
                "includes_fallback_path": "no",
            },
            "efficiency": {
                "minimizes_redundant_calls": "1",
                "uses_appropriate_agents": "0",
                "optimizes_cost": "pass",
                "optimizes_latency": "fail",
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": False,
                "has_timeout_protection": True,
                "avoids_risky_combinations": False,
            },
            "coherence": {
                "logical_agent_sequence": True,
                "proper_data_flow": False,
                "no_conflicting_actions": True,
            },
        }

        result = calculator.calculate(evaluations)

        assert result["score"] > 0.0
        assert "completeness.has_all_required_steps" in result["passed_criteria"]
        assert "completeness.handles_edge_cases" in result["failed_criteria"]

