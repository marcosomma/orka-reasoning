"""Unit tests for orka.scoring.presets."""

import pytest

from orka.scoring.presets import get_criteria_description, load_preset, PRESETS

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestPresets:
    """Test suite for scoring presets."""

    def test_presets_structure(self):
        """Test that PRESETS dictionary has expected structure."""
        # After refactoring, PRESETS is now context-based
        assert "graphscout" in PRESETS
        assert "quality" in PRESETS
        assert "loop_convergence" in PRESETS
        assert "validation" in PRESETS
        
        # Each context should have severity levels
        for context_name, context_data in PRESETS.items():
            assert "strict" in context_data
            assert "moderate" in context_data
            assert "lenient" in context_data
            
            # Each severity level should have expected structure
            for severity, preset_data in context_data.items():
                assert "description" in preset_data
                assert "weights" in preset_data
                assert "thresholds" in preset_data
                assert "context" in preset_data

    def test_load_preset_strict(self):
        """Test load_preset with strict preset."""
        preset = load_preset("strict")
        
        assert preset["description"] is not None
        assert "weights" in preset
        assert "thresholds" in preset
        assert preset["thresholds"]["approved"] == 0.90

    def test_load_preset_moderate(self):
        """Test load_preset with moderate preset."""
        preset = load_preset("moderate")
        
        assert preset["description"] is not None
        assert preset["thresholds"]["approved"] == 0.85

    def test_load_preset_lenient(self):
        """Test load_preset with lenient preset."""
        preset = load_preset("lenient")
        
        assert preset["description"] is not None
        assert preset["thresholds"]["approved"] == 0.80

    def test_load_preset_invalid(self):
        """Test load_preset with invalid preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown scoring preset"):
            load_preset("invalid_preset")

    def test_get_criteria_description(self):
        """Test get_criteria_description function."""
        descriptions = get_criteria_description("strict")
        
        assert isinstance(descriptions, dict)
        assert "completeness.has_all_required_steps" in descriptions
        assert len(descriptions) > 0

    def test_preset_weights_sum_to_one(self):
        """Test that preset weights approximately sum to 1.0."""
        # Test all contexts and severity levels
        for context_name in PRESETS:
            for preset_name in ["strict", "moderate", "lenient"]:
                preset = load_preset(preset_name, context=context_name)
                weights = preset["weights"]
                
                total = sum(
                    sum(criteria.values()) for criteria in weights.values()
                )
                
                # Should be approximately 1.0 (allowing small floating point errors)
                assert abs(total - 1.0) < 0.01, f"Preset {preset_name} (context {context_name}) weights sum to {total}, not 1.0"

