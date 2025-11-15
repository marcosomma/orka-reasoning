import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from orka.agents.plan_validator.agent import PlanValidatorAgent
from orka.agents.base_agent import Context
from orka.scoring import BooleanScoreCalculator

@pytest.fixture
def mock_boolean_score_calculator_class():
    """Fixture for a mocked BooleanScoreCalculator class."""
    with patch("orka.agents.plan_validator.agent.BooleanScoreCalculator") as mock_class:
        mock_instance = MagicMock(spec=BooleanScoreCalculator)
        mock_instance.calculate.return_value = {
            "score": 0.8,
            "assessment": "ACCEPTED",
            "breakdown": {"completeness": 0.9, "efficiency": 0.7},
            "passed_criteria": ["completeness_check"],
            "failed_criteria": ["efficiency_check"],
            "dimension_scores": {"completeness": 0.9, "efficiency": 0.7},
            "total_criteria": 2,
            "passed_count": 1,
        }
        mock_class.return_value = mock_instance
        yield mock_class

@pytest.fixture
def mock_llm_client():
    """Fixture for a mocked llm_client module."""
    with patch("orka.agents.plan_validator.llm_client.call_llm", new_callable=AsyncMock) as mock_call_llm:
        mock_call_llm.return_value = '{"rationale": "Test rationale.", "completeness": true}'
        yield mock_call_llm

@pytest.fixture
def mock_boolean_parser():
    """Fixture for a mocked boolean_parser module."""
    with patch("orka.agents.plan_validator.boolean_parser.parse_boolean_evaluation") as mock_parse_boolean_evaluation:
        mock_parse_boolean_evaluation.return_value = {"completeness": {"value": True, "weight": 1.0}}
        yield mock_parse_boolean_evaluation

@pytest.fixture
def mock_prompt_builder():
    """Fixture for a mocked prompt_builder module."""
    with patch("orka.agents.plan_validator.prompt_builder.build_validation_prompt") as mock_build_validation_prompt:
        mock_build_validation_prompt.return_value = "Mocked validation prompt"
        yield mock_build_validation_prompt

@pytest.fixture
def plan_validator_agent(mock_boolean_score_calculator_class):
    """Fixture for a PlanValidatorAgent instance with a mocked score calculator."""
    return PlanValidatorAgent(agent_id="test_validator")

class TestPlanValidatorAgent:
    def test_init_default_params(self, mock_boolean_score_calculator_class):
        agent = PlanValidatorAgent(agent_id="test_agent")
        assert agent.agent_id == "test_agent"
        assert agent.llm_model == "gpt-oss:20b"
        assert agent.llm_provider == "ollama"
        assert agent.llm_url == "http://localhost:11434/api/generate"
        assert agent.temperature == 0.2
        assert agent.scoring_preset == "moderate"
        mock_boolean_score_calculator_class.assert_called_once_with(preset="moderate", custom_weights=None)

    def test_init_custom_params(self, mock_boolean_score_calculator_class):
        custom_weights = {"completeness": 0.5}
        agent = PlanValidatorAgent(
            agent_id="custom_agent",
            llm_model="custom_model",
            llm_provider="openai",
            llm_url="http://custom_url",
            temperature=0.5,
            scoring_preset="strict",
            custom_weights=custom_weights,
        )
        assert agent.agent_id == "custom_agent"
        assert agent.llm_model == "custom_model"
        assert agent.llm_provider == "openai"
        assert agent.llm_url == "http://custom_url"
        assert agent.temperature == 0.5
        assert agent.scoring_preset == "strict"
        mock_boolean_score_calculator_class.assert_called_once_with(preset="strict", custom_weights=custom_weights)