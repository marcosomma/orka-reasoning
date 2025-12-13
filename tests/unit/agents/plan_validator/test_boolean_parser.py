"""Unit tests for orka.agents.plan_validator.boolean_parser.

These tests focus on:
- JSON parsing + normalization
- Fallback text extraction
- Default filling for missing criteria

They are designed to be deterministic and not depend on external services.
"""

from unittest.mock import patch

import pytest

from orka.agents.plan_validator import boolean_parser as bp


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def test_parse_boolean_evaluation_valid_json_structure_normalizes_values():
    response = """
    {
      "completeness": {
        "has_all_required_steps": "yes",
        "handles_edge_cases": 1
      },
      "efficiency": {
        "optimizes_cost": "✓",
        "optimizes_latency": false
      },
      "coherence": {
        "proper_data_flow": "no"
      }
    }
    """

    result = bp.parse_boolean_evaluation(response)

    assert result["completeness"]["has_all_required_steps"] is True
    assert result["completeness"]["handles_edge_cases"] is True
    assert result["efficiency"]["optimizes_cost"] is True
    assert result["efficiency"]["optimizes_latency"] is False
    assert result["coherence"]["proper_data_flow"] is False


def test_parse_boolean_evaluation_json_parse_failed_falls_back_to_text_extraction():
    # Force the robust parser to report JSON failure so we exercise the fallback.
    with patch.object(bp, "parse_llm_json", return_value={"error": "json_parse_failed"}):
        response = """
        has_all_required_steps: yes
        handles_edge_cases: pass
        avoids_risky_combinations: no
        """

        result = bp.parse_boolean_evaluation(response)

    # Extracted from text
    assert result["completeness"]["has_all_required_steps"] is True
    assert result["completeness"]["handles_edge_cases"] is True
    assert result["safety"]["avoids_risky_combinations"] is False

    # Defaults should be filled for missing criteria
    assert result["efficiency"]["optimizes_cost"] is False
    assert result["coherence"]["logical_agent_sequence"] is False


def test_extract_json_from_text_supports_code_fence_and_inline_object():
    fenced = """Here is the answer:
```json
{\"completeness\": {\"has_all_required_steps\": true}}
```
"""
    assert bp._extract_json_from_text(fenced) == {
        "completeness": {"has_all_required_steps": True}
    }

    inline = "prefix {\"efficiency\": {\"optimizes_cost\": true}} suffix"
    assert bp._extract_json_from_text(inline) == {"efficiency": {"optimizes_cost": True}}


def test_extract_json_from_text_invalid_json_returns_none():
    bad = """```json
{ not valid json }
```"""
    assert bp._extract_json_from_text(bad) is None
