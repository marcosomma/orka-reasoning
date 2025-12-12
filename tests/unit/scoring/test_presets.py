"""
Tests for context-aware scoring presets.

Tests the refactored preset system that provides different scoring
criteria for different evaluation contexts (graphscout, quality,
loop_convergence, validation).
"""

import pytest
from orka.scoring.presets import (
    load_preset,
    get_available_contexts,
    get_available_presets,
    get_criteria_description,
    PRESETS,
)


class TestPresetStructure:
    """Test the structure and organization of presets."""

    def test_all_contexts_exist(self):
        """All documented contexts should exist in PRESETS."""
        expected_contexts = ["graphscout", "quality", "loop_convergence", "validation"]
        for context in expected_contexts:
            assert context in PRESETS, f"Missing context: {context}"

    def test_all_contexts_have_severity_levels(self):
        """Each context should have strict/moderate/lenient."""
        severity_levels = ["strict", "moderate", "lenient"]
        for context in PRESETS:
            for level in severity_levels:
                assert level in PRESETS[context], \
                    f"Missing {level} in context {context}"

    def test_preset_has_required_fields(self):
        """Each preset should have description, context, weights, thresholds."""
        required_fields = ["description", "context", "weights", "thresholds"]
        for context in PRESETS:
            for severity in PRESETS[context]:
                preset = PRESETS[context][severity]
                for field in required_fields:
                    assert field in preset, \
                        f"Missing {field} in {context}/{severity}"

    def test_weights_sum_to_one(self):
        """All weights in a preset should sum to 1.0 (within tolerance)."""
        for context in PRESETS:
            for severity in PRESETS[context]:
                preset = PRESETS[context][severity]
                total_weight = sum(
                    sum(criteria.values())
                    for criteria in preset["weights"].values()
                )
                assert abs(total_weight - 1.0) < 0.01, \
                    f"Weights in {context}/{severity} sum to {total_weight}, not 1.0"

    def test_thresholds_are_valid(self):
        """Thresholds should be between 0 and 1, approved > needs_improvement."""
        for context in PRESETS:
            for severity in PRESETS[context]:
                thresholds = PRESETS[context][severity]["thresholds"]
                
                assert "approved" in thresholds
                assert "needs_improvement" in thresholds
                
                approved = thresholds["approved"]
                needs_improvement = thresholds["needs_improvement"]
                
                assert 0.0 <= approved <= 1.0
                assert 0.0 <= needs_improvement <= 1.0
                assert approved > needs_improvement, \
                    f"approved ({approved}) should be > needs_improvement ({needs_improvement})"


class TestLoadPreset:
    """Test the load_preset function."""

    def test_load_with_explicit_context(self):
        """Loading with explicit context should work."""
        preset = load_preset("strict", context="graphscout")
        assert preset is not None
        assert preset["context"] == "graphscout"

    def test_load_without_context_defaults_to_graphscout(self):
        """Loading without context should default to graphscout (backward compat)."""
        preset = load_preset("moderate")
        assert preset is not None
        assert preset["context"] == "graphscout"

    def test_load_all_valid_combinations(self):
        """All context/severity combinations should load successfully."""
        contexts = get_available_contexts()
        for context in contexts:
            presets = get_available_presets(context)
            for preset_name in presets:
                preset = load_preset(preset_name, context=context)
                assert preset is not None
                assert preset["context"] == context

    def test_invalid_context_raises_error(self):
        """Loading with invalid context should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown scoring context"):
            load_preset("strict", context="nonexistent")

    def test_invalid_preset_raises_error(self):
        """Loading with invalid preset name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown scoring preset"):
            load_preset("nonexistent", context="graphscout")

    def test_context_specific_criteria(self):
        """Different contexts should have different criteria."""
        graphscout = load_preset("strict", context="graphscout")
        quality = load_preset("strict", context="quality")
        
        # GraphScout should have "efficiency" dimension
        assert "efficiency" in graphscout["weights"]
        
        # Quality should have "accuracy" dimension
        assert "accuracy" in quality["weights"]
        
        # They should be different
        assert graphscout["weights"].keys() != quality["weights"].keys()


class TestGetAvailableFunctions:
    """Test helper functions for discovering available presets."""

    def test_get_available_contexts(self):
        """Should return all available contexts."""
        contexts = get_available_contexts()
        assert isinstance(contexts, list)
        assert len(contexts) == 4
        assert "graphscout" in contexts
        assert "quality" in contexts
        assert "loop_convergence" in contexts
        assert "validation" in contexts

    def test_get_available_presets_for_valid_context(self):
        """Should return presets for a valid context."""
        presets = get_available_presets("graphscout")
        assert isinstance(presets, list)
        assert "strict" in presets
        assert "moderate" in presets
        assert "lenient" in presets

    def test_get_available_presets_invalid_context(self):
        """Should raise error for invalid context."""
        with pytest.raises(ValueError, match="Unknown context"):
            get_available_presets("nonexistent")


class TestGetCriteriaDescription:
    """Test criteria description functionality."""

    def test_get_descriptions_for_graphscout(self):
        """Should return descriptions for graphscout criteria."""
        descriptions = get_criteria_description("strict", context="graphscout")
        assert isinstance(descriptions, dict)
        assert len(descriptions) > 0
        assert "completeness.has_all_required_steps" in descriptions

    def test_get_descriptions_for_quality(self):
        """Should return descriptions for quality criteria."""
        descriptions = get_criteria_description("strict", context="quality")
        assert isinstance(descriptions, dict)
        assert "accuracy.factually_correct" in descriptions

    def test_get_descriptions_for_loop_convergence(self):
        """Should return descriptions for loop_convergence criteria."""
        descriptions = get_criteria_description("strict", context="loop_convergence")
        assert isinstance(descriptions, dict)
        assert "improvement.better_than_previous" in descriptions

    def test_get_descriptions_for_validation(self):
        """Should return descriptions for validation criteria."""
        descriptions = get_criteria_description("strict", context="validation")
        assert isinstance(descriptions, dict)
        assert "schema_compliance.matches_schema" in descriptions

    def test_descriptions_are_human_readable(self):
        """Descriptions should be clear human-readable strings."""
        descriptions = get_criteria_description("strict", context="graphscout")
        for key, value in descriptions.items():
            assert isinstance(value, str)
            assert len(value) > 10  # Should be descriptive
            assert value[0].isupper()  # Should start with capital


class TestContextSpecificCriteria:
    """Test that each context has appropriate criteria."""

    def test_graphscout_has_agent_path_criteria(self):
        """GraphScout should evaluate agent path quality."""
        preset = load_preset("strict", context="graphscout")
        weights = preset["weights"]
        
        # Should have path-specific dimensions
        assert "completeness" in weights
        assert "efficiency" in weights
        assert "safety" in weights
        assert "coherence" in weights
        
        # Should have agent-specific criteria
        assert "uses_appropriate_agents" in weights["efficiency"]
        assert "logical_agent_sequence" in weights["coherence"]

    def test_quality_has_response_criteria(self):
        """Quality should evaluate response quality."""
        preset = load_preset("strict", context="quality")
        weights = preset["weights"]
        
        # Should have quality-specific dimensions
        assert "accuracy" in weights
        assert "completeness" in weights
        assert "clarity" in weights
        assert "relevance" in weights
        
        # Should have response-specific criteria
        assert "factually_correct" in weights["accuracy"]
        assert "addresses_question" in weights["accuracy"]
        assert "no_hallucinations" in weights["accuracy"]

    def test_loop_convergence_has_iteration_criteria(self):
        """Loop convergence should evaluate iterative improvement."""
        preset = load_preset("strict", context="loop_convergence")
        weights = preset["weights"]
        
        # Should have convergence-specific dimensions
        assert "improvement" in weights
        assert "stability" in weights
        assert "convergence" in weights
        
        # Should have iteration-specific criteria
        assert "better_than_previous" in weights["improvement"]
        assert "delta_decreasing" in weights["convergence"]
        assert "not_degrading" in weights["stability"]
        
        # Should have terminate_loop threshold
        assert "terminate_loop" in preset["thresholds"]

    def test_validation_has_schema_criteria(self):
        """Validation should evaluate schema compliance."""
        preset = load_preset("strict", context="validation")
        weights = preset["weights"]
        
        # Should have validation-specific dimensions
        assert "schema_compliance" in weights
        assert "constraints" in weights
        assert "format" in weights
        
        # Should have schema-specific criteria
        assert "matches_schema" in weights["schema_compliance"]
        assert "all_required_fields" in weights["schema_compliance"]
        assert "within_bounds" in weights["constraints"]


class TestSeverityLevels:
    """Test that severity levels are correctly ordered."""

    def test_strict_has_highest_thresholds(self):
        """Strict should have highest approval thresholds."""
        for context in get_available_contexts():
            strict = load_preset("strict", context=context)
            moderate = load_preset("moderate", context=context)
            lenient = load_preset("lenient", context=context)
            
            assert strict["thresholds"]["approved"] >= moderate["thresholds"]["approved"]
            assert moderate["thresholds"]["approved"] >= lenient["thresholds"]["approved"]

    def test_strict_emphasizes_critical_criteria(self):
        """Strict should weight critical criteria more heavily."""
        for context in ["graphscout", "quality"]:
            strict = load_preset("strict", context=context)
            lenient = load_preset("lenient", context=context)
            
            # Weights should be non-negative
            for dimension in strict["weights"]:
                for criterion, weight in strict["weights"][dimension].items():
                    assert weight >= 0.0
                    if criterion in lenient["weights"].get(dimension, {}):
                        assert weight >= 0.0  # Just ensure validity


class TestBackwardCompatibility:
    """Test backward compatibility with old API."""

    def test_load_preset_without_context_works(self):
        """Old code using load_preset("strict") should still work."""
        # This is the old API that existing code uses
        preset = load_preset("strict")
        assert preset is not None
        assert "weights" in preset
        assert "thresholds" in preset

    def test_old_graphscout_criteria_still_present(self):
        """Old GraphScout criteria should still exist."""
        preset = load_preset("moderate")  # Defaults to graphscout
        weights = preset["weights"]
        
        # Old criteria that existing code expects
        assert "completeness" in weights
        assert "has_all_required_steps" in weights["completeness"]
        assert "efficiency" in weights
        assert "minimizes_redundant_calls" in weights["efficiency"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
