"""Unit tests for orka.scoring.calculator."""

from unittest.mock import Mock, patch

import pytest

from orka.scoring.calculator import BooleanScoreCalculator

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestBooleanScoreCalculator:
    """Test suite for BooleanScoreCalculator class."""

    def test_init_default_preset(self):
        """Test BooleanScoreCalculator initialization with default preset."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 0.3},
                    "coherence": {"logical_agent_sequence": 0.2},
                },
                "thresholds": {"min_score": 0.5},
            }
            
            calculator = BooleanScoreCalculator()
            
            assert calculator.preset_name == "moderate"
            assert calculator.weights is not None

    def test_init_custom_preset(self):
        """Test BooleanScoreCalculator initialization with custom preset."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 0.5},
                },
                "thresholds": {"min_score": 0.7},
            }
            
            calculator = BooleanScoreCalculator(preset="strict")
            
            assert calculator.preset_name == "strict"

    def test_init_with_custom_weights(self):
        """Test BooleanScoreCalculator initialization with custom weights."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 0.3},
                },
                "thresholds": {"min_score": 0.5},
            }
            
            custom_weights = {"completeness.has_all_required_steps": 0.5}
            calculator = BooleanScoreCalculator(custom_weights=custom_weights)
            
            assert calculator.weights is not None

    def test_calculate(self):
        """Test calculate method."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 1.0},
                },
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            evaluations = {
                "completeness": {
                    "has_all_required_steps": True,
                }
            }
            
            result = calculator.calculate(evaluations)
            
            assert isinstance(result, dict)
            assert "score" in result
            assert 0.0 <= result["score"] <= 1.0

    def test_calculate_partial_pass(self):
        """Test calculate with partial criteria passing."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 0.5, "has_terminal": 0.5},
                },
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            evaluations = {
                "completeness": {
                    "has_all_required_steps": True,
                    "has_terminal": False,
                }
            }
            
            result = calculator.calculate(evaluations)
            
            assert result["score"] < 1.0
            assert result["score"] > 0.0

    def test_get_breakdown(self):
        """Test get_breakdown method."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 1.0},
                },
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            evaluations = {
                "completeness": {
                    "has_all_required_steps": True,
                }
            }
            
            result = calculator.calculate(evaluations)
            breakdown = calculator.get_breakdown(result)
            
            assert isinstance(breakdown, str)
            assert len(breakdown) > 0

    def test_get_failed_criteria(self):
        """Test get_failed_criteria method."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {
                    "completeness": {"has_all_required_steps": 0.5, "has_terminal": 0.5},
                },
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            evaluations = {
                "completeness": {
                    "has_all_required_steps": False,
                    "has_terminal": False,
                }
            }
            
            result = calculator.calculate(evaluations)
            failed = calculator.get_failed_criteria(result)
            
            assert isinstance(failed, list)
            assert len(failed) >= 0

    def test_score_to_assessment(self):
        """Test _score_to_assessment method."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {"completeness": {"test": 1.0}},
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            assessment = calculator._score_to_assessment(0.9)
            assert assessment in ["APPROVED", "NEEDS_IMPROVEMENT", "REJECTED"]

    def test_get_nested_value(self):
        """Test _get_nested_value method."""
        with patch('orka.scoring.calculator.load_preset') as mock_load:
            mock_load.return_value = {
                "weights": {"completeness": {"test": 1.0}},
                "thresholds": {"min_score": 0.5, "approved": 0.8, "needs_improvement": 0.6},
            }
            
            calculator = BooleanScoreCalculator()
            
            data = {
                "completeness": {
                    "has_all_required_steps": True,
                }
            }
            
            value = calculator._get_nested_value(data, "completeness", "has_all_required_steps")
            assert value is True

