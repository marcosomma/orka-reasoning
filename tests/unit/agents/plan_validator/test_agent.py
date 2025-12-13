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
        assert agent.llm_url == "http://localhost:1234"
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

    def test_extract_proposed_path_from_graphscout_router(self, plan_validator_agent):
        """Test extracting GraphScout output from 'graphscout_router' key."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "graphscout_router": {
                    "decision": "commit_path",
                    "target": ["agent1", "agent2"],
                    "confidence": 0.92,
                    "reasoning": "Best path selected",
                    "result": {
                        "decision": "commit_path",
                        "target": ["agent1", "agent2"],
                        "confidence": 0.92,
                    }
                }
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        # Should extract nested 'result' when available
        assert "decision" in result
        assert result["decision"] == "commit_path"
        assert result["target"] == ["agent1", "agent2"]
        assert result["confidence"] == 0.92

    def test_extract_proposed_path_from_nested_result(self, plan_validator_agent):
        """Test extracting from nested 'result' field in GraphScout output."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "graph_scout": {
                    "status": "success",
                    "metrics": {"time": 1.5},
                    "result": {
                        "decision": "shortlist",
                        "target": [["path1"], ["path2"]],
                        "confidence": 0.78,
                        "reasoning": "Multiple good options"
                    }
                }
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        assert result["decision"] == "shortlist"
        assert result["target"] == [["path1"], ["path2"]]
        assert result["confidence"] == 0.78

    def test_extract_proposed_path_top_level_fields(self, plan_validator_agent):
        """Test extracting when decision fields are at top level."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "path_proposer": {
                    "decision": "commit_next",
                    "target": "agent3",
                    "confidence": 0.88
                }
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        assert result["decision"] == "commit_next"
        assert result["target"] == "agent3"
        assert result["confidence"] == 0.88

    def test_extract_proposed_path_fallback_to_any_agent(self, plan_validator_agent):
        """Test fallback logic finds path in any agent output."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "some_custom_agent": {
                    "result": {
                        "decision_type": "custom",
                        "path": ["step1", "step2"],
                        "score": 0.85
                    }
                }
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        # Should find in nested result via fallback
        assert result["decision_type"] == "custom"
        assert result["path"] == ["step1", "step2"]

    def test_extract_proposed_path_no_valid_output(self, plan_validator_agent):
        """Test error handling when no valid path is found."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "unrelated_agent": {"some_data": "value"}
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        assert "error" in result
        assert result["error"] == "No proposed path found"
        assert "available_keys" in result
        assert "unrelated_agent" in result["available_keys"]

    def test_extract_proposed_path_from_response_field(self, plan_validator_agent):
        """Test extraction from 'response' field used by LoopNode."""
        context: Context = {
            "input": "test query",
            "previous_outputs": {
                "plan_proposer": {
                    "response": {
                        "decision": "shortlist",
                        "target": [
                            {"node_id": "agent1", "path": ["agent1"]},
                            {"node_id": "agent2", "path": ["agent2"]}
                        ]
                    }
                }
            }
        }
        result = plan_validator_agent._extract_proposed_path(context)
        
        # Should find in nested response field
        assert result["decision"] == "shortlist"
        assert len(result["target"]) == 2
        assert result["target"][0]["node_id"] == "agent1"
