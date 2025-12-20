import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from orka.nodes.loop_node import LoopNode
from orka.agents.plan_validator.agent import PlanValidatorAgent
from orka.scoring import BooleanScoreCalculator


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


@pytest.mark.asyncio
async def test_extract_score_percentage_from_high_priority_agent():
    node = LoopNode("test_node")

    # Ensure no boolean calculator so we exercise pattern-based extraction
    node.score_calculator = None

    payload = {"agreement_moderator": {"response": "Agreement: 15% observed in outcomes"}}

    score = await node._extract_score(payload)

    assert isinstance(score, float)
    assert abs(score - 0.15) < 1e-6


@pytest.mark.asyncio
async def test_extract_score_pattern_percentage_strategy():
    node = LoopNode("test_node")
    node.score_extraction_config = {"strategies": [{"type": "pattern", "patterns": [r"(\d+\.?\d*)%"]}]}

    payload = {"agent_x": "Value: 15%"}
    score = await node._extract_score(payload)
    assert isinstance(score, float)
    assert abs(score - 0.15) < 1e-6


@pytest.mark.asyncio
async def test_extract_score_out_of_ten_pattern():
    node = LoopNode("test_node")
    node.score_extraction_config = {"strategies": [{"type": "pattern", "patterns": [r"(\d+\.?\d*)/10"]}]}

    payload = {"agent_x": "Score: 8/10"}
    score = await node._extract_score(payload)
    assert isinstance(score, float)
    assert abs(score - 0.8) < 1e-6


@pytest.mark.asyncio
async def test_extract_score_direct_key_normalizes_large_values():
    node = LoopNode("test_node")
    node.score_extraction_config = {"strategies": [{"type": "direct_key", "key": "some_score"}]}

    # Raw score of 150 should be clamped to 1.0 (out of expected range)
    payload = {"some_score": "150"}
    score = await node._extract_score(payload)
    assert isinstance(score, float)
    assert abs(score - 1.0) < 1e-6


def test_extract_boolean_from_text_returns_none_on_invalid():
    node = LoopNode("test_node")
    result = node._extract_boolean_from_text("no json here")
    assert result is None


def test_skip_boolean_scoring_when_no_join_or_routing():
    node = LoopNode(node_id="loop_processor", prompt="", queue=[], memory_logger=MagicMock())
    # Provide a fake score_calculator so _try_boolean_scoring would normally attempt
    # but boolean_evaluations are sparse.
    node.score_calculator = MagicMock()
    node.score_calculator.flat_weights = {f"improvement.k{i}": 0.1 for i in range(7)}

    # Agent includes boolean_evaluations but there is no routing/join data
    result = {
        "loop_convergence_validator": {
            "boolean_evaluations": {},
            "response": "I cannot evaluate, no join results were provided"
        }
    }

    score = node._try_boolean_scoring(result)
    assert score is None


@pytest.mark.asyncio
async def test_loop_node_uses_synthesized_booleans_from_plan_validator(
    mock_prompt_builder, mock_boolean_score_calculator_class
):
    """Integration: PlanValidator synthesizes booleans -> LoopNode uses boolean scoring."""
    # Patch LLM to return a text indicating improvement and stability
    with patch("orka.agents.plan_validator.llm_client.call_llm", new_callable=AsyncMock) as mock_llm_call:
        mock_llm_call.return_value = "The proposed path improves accuracy by 6% and shows stable behavior with no regressions."

        # Patch boolean parser to return empty -> force synthesis
        with patch("orka.agents.plan_validator.boolean_parser.parse_boolean_evaluation") as mock_parse:
            mock_parse.return_value = {}

            pv = PlanValidatorAgent(agent_id="pv", llm_model="m", llm_provider="p", llm_url="u")
            ctx = {"input": "test", "previous_outputs": {}, "loop_number": 1, "scoring_context": "loop_convergence"}
            result = await pv._run_impl(ctx)

            assert "boolean_evaluations" in result
            be = result["boolean_evaluations"]
            assert "improvement" in be and be["improvement"].get("significant_delta") is True

            # Now feed into LoopNode and ensure boolean scoring picks it up
            node = LoopNode("loop_node")
            # Initialize score_calculator with loop_convergence preset to ensure scoring runs
            node.scoring_preset = "moderate"
            node.score_calculator = BooleanScoreCalculator(preset="moderate", context="loop_convergence")

            score = await node._extract_score({"loop_convergence_validator": result})
            assert isinstance(score, float)
            # Expect a non-zero score due to synthesized booleans
            assert score > 0.0
