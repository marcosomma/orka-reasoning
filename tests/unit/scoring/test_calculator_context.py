"""
Tests for context-aware BooleanScoreCalculator.

Tests that the calculator properly uses context-specific presets.
"""

import pytest
from orka.scoring.calculator import BooleanScoreCalculator


class TestCalculatorWithContext:
    """Test BooleanScoreCalculator with different contexts."""

    def test_calculator_with_explicit_context(self):
        """Calculator should accept explicit context parameter."""
        calc = BooleanScoreCalculator(preset="strict", context="quality")
        assert calc.preset_name == "strict"
        assert calc.context == "quality"

    def test_calculator_defaults_to_graphscout(self):
        """Calculator without context should default to graphscout."""
        calc = BooleanScoreCalculator(preset="moderate")
        assert calc.context == "graphscout"

    def test_calculator_loads_correct_criteria_for_context(self):
        """Calculator should load context-specific criteria."""
        graphscout_calc = BooleanScoreCalculator(preset="strict", context="graphscout")
        quality_calc = BooleanScoreCalculator(preset="strict", context="quality")
        
        # GraphScout should have efficiency criteria
        assert any("efficiency" in key for key in graphscout_calc.flat_weights.keys())
        
        # Quality should have accuracy criteria  
        assert any("accuracy" in key for key in quality_calc.flat_weights.keys())
        
        # They should have different criteria
        assert graphscout_calc.flat_weights.keys() != quality_calc.flat_weights.keys()

    def test_all_contexts_can_initialize_calculator(self):
        """Calculator should work with all available contexts."""
        from orka.scoring import get_available_contexts
        
        for context in get_available_contexts():
            for severity in ["strict", "moderate", "lenient"]:
                calc = BooleanScoreCalculator(preset=severity, context=context)
                assert calc is not None
                assert len(calc.flat_weights) > 0


class TestBackwardCompatibility:
    """Test that old code still works."""

    def test_old_api_without_context(self):
        """Old calculator usage should still work."""
        # This is how existing code uses the calculator
        calc = BooleanScoreCalculator(preset="moderate")
        assert calc is not None
        assert len(calc.flat_weights) > 0

    def test_old_graphscout_scoring_works(self):
        """Old GraphScout scoring should still produce valid results."""
        calc = BooleanScoreCalculator(preset="strict")
        
        # Old-style boolean evaluations
        evaluations = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": True,
                "handles_edge_cases": False,
                "includes_fallback_path": True,
            },
            "efficiency": {
                "minimizes_redundant_calls": True,
                "uses_appropriate_agents": True,
                "optimizes_cost": True,
                "optimizes_latency": False,
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
        
        result = calc.calculate(evaluations)
        assert "score" in result  # The calculator returns "score", not "total_score"
        assert 0.0 <= result["score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
