import pytest
from unittest.mock import patch
from orka.agents.plan_validator.critique_parser import parse_critique

@patch("orka.agents.plan_validator.critique_parser.logger")
def test_parse_critique_json(mock_logger):
    response = """```json
    {
        "validation_score": 0.9,
        "overall_assessment": "APPROVED",
        "critiques": {
            "completeness": {"score": 0.9, "issues": [], "suggestions": []}
        },
        "recommended_changes": [],
        "approval_confidence": 0.95,
        "rationale": "The plan is well-structured."
    }
    ```"""
    result = parse_critique(response)
    assert result["validation_score"] == 0.9
    assert result["overall_assessment"] == "APPROVED"
    assert "completeness" in result["critiques"]
    mock_logger.debug.assert_any_call("Successfully extracted JSON critique")

@patch("orka.agents.plan_validator.critique_parser.logger")
def test_parse_critique_text(mock_logger):
    response = "VALIDATION_SCORE: 0.75. The plan is decent but could be improved."
    result = parse_critique(response)
    assert result["validation_score"] == 0.5
    assert result["overall_assessment"] == "REJECTED"
    assert "The plan is decent" in result["rationale"]
    mock_logger.debug.assert_any_call("Using fallback text extraction")

@patch("orka.agents.plan_validator.critique_parser.logger")
def test_parse_critique_no_score(mock_logger):
    response = "This is a critique without a score."
    result = parse_critique(response)
    assert result["validation_score"] == 0.5
    assert result["overall_assessment"] == "REJECTED"
    mock_logger.warning.assert_called_with("Could not extract validation score, using default 0.5")

