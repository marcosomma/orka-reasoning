import asyncio
from unittest.mock import MagicMock

import pytest

from orka.nodes.loop_node import LoopNode


def test_is_valid_value_cases():
    node = LoopNode("test_node")

    assert node._is_valid_value(1)
    assert node._is_valid_value(3.14)
    assert node._is_valid_value("0.5")
    assert node._is_valid_value("  2.0  ")

    assert not node._is_valid_value("")
    assert not node._is_valid_value(None)
    assert not node._is_valid_value("not-a-number")


def test_is_valid_boolean_structure_positive_and_negative():
    node = LoopNode("test_node")

    valid_structure = {
        "completeness": {"a": True, "b": False},
        "efficiency": {"x": True, "y": False},
    }
    assert node._is_valid_boolean_structure(valid_structure)

    invalid_structure = {"completeness": {"a": True}}
    # Only one valid dimension -> should be False (requires >=2)
    assert not node._is_valid_boolean_structure(invalid_structure)


def test_extract_boolean_from_text_parses_and_normalizes():
    node = LoopNode("test_node")

    sample_text = "Here's a response: {'COMPLETENESS': {'a': True, 'b': False}, 'EFFICIENCY': {'x': True}}"

    result = node._extract_boolean_from_text(sample_text)

    assert isinstance(result, dict)
    # Keys should be normalized to lowercase
    assert "completeness" in result
    assert "efficiency" in result
    assert result["completeness"]["a"] is True


def test_try_boolean_scoring_uses_score_calculator():
    node = LoopNode("test_node")

    # Provide a fake score_calculator with a predictable return
    fake_calculator = MagicMock()
    fake_calculator.calculate.return_value = {
        "score": 0.85,
        "passed_count": 2,
        "total_criteria": 3,
    }

    node.score_calculator = fake_calculator

    # Provide a result containing boolean_evaluations structure
    result = {
        "agent_1": {
            "boolean_evaluations": {
                "completeness": {"a": True, "b": False},
                "efficiency": {"x": True, "y": False},
            }
        }
    }

    score = node._try_boolean_scoring(result)

    assert isinstance(score, float)
    assert abs(score - 0.85) < 1e-6
    fake_calculator.calculate.assert_called_once()


@pytest.mark.asyncio
async def test_extract_score_reads_high_priority_agent_pattern():
    node = LoopNode("test_node")

    # Ensure no boolean calculator so we exercise pattern-based extraction
    node.score_calculator = None

    payload = {
        "agreement_moderator": {"response": "Some text... AGREEMENT_SCORE: 0.92 more text"}
    }

    score = await node._extract_score(payload)

    assert isinstance(score, float)
    assert abs(score - 0.92) < 1e-6


@pytest.mark.asyncio
async def test_extract_score_direct_key_strategy():
    node = LoopNode("test_node")

    # Configure a direct_key strategy
    node.score_extraction_config = {"strategies": [{"type": "direct_key", "key": "some_score"}]}

    payload = {"some_score": "0.77"}

    score = await node._extract_score(payload)
    assert isinstance(score, float)
    assert abs(score - 0.77) < 1e-6


@pytest.mark.asyncio
async def test_extract_score_pattern_strategy_on_string_result():
    node = LoopNode("test_node")
    node.score_extraction_config = {"strategies": [{"type": "pattern", "patterns": [r"Score:\s*([0-9.]+)"]}]}

    payload = {"agent_x": "Score: 0.66"}
    score = await node._extract_score(payload)
    assert isinstance(score, float)
    assert abs(score - 0.66) < 1e-6


def test_extract_boolean_from_text_returns_none_on_invalid():
    node = LoopNode("test_node")
    result = node._extract_boolean_from_text("no json here")
    assert result is None
