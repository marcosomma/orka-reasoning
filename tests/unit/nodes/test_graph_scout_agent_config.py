from unittest.mock import MagicMock, patch

import pytest

from orka.nodes.graph_scout_agent import GraphScoutAgent


pytestmark = [pytest.mark.unit]


def test_graph_scout_agent_wires_llm_evaluation_config_from_params():
    """
    Regression: GraphScoutAgent must propagate YAML `params` into GraphScoutConfig so
    SmartPathEvaluator can read provider/model_url/evaluation_model_name at runtime.
    """
    params = {
        "k_beam": 5,
        "max_depth": 3,
        "provider": "lm_studio",
        "model_url": "http://localhost:1234",
        "evaluation_model": "local_llm",
        "evaluation_model_name": "openai/gpt-oss-20b",
        "validation_model": "local_llm",
        "validation_model_name": "openai/gpt-oss-20b",
        "llm_evaluation_enabled": True,
        "fallback_to_heuristics": True,
    }

    # Keep this test lightweight: we only want to validate config plumbing.
    with patch("orka.nodes.graph_scout_agent.GraphIntrospector", MagicMock()), patch(
        "orka.nodes.graph_scout_agent.PathScorer", MagicMock()
    ), patch("orka.nodes.graph_scout_agent.SmartPathEvaluator", MagicMock()), patch(
        "orka.nodes.graph_scout_agent.SafetyController", MagicMock()
    ), patch("orka.nodes.graph_scout_agent.BudgetController", MagicMock()), patch(
        "orka.nodes.graph_scout_agent.DecisionEngine", MagicMock()
    ), patch("orka.nodes.graph_scout_agent.GraphAPI", MagicMock()):
        agent = GraphScoutAgent(
            node_id="graph_scout_router",
            prompt="test",
            queue=[],
            params=params,
        )

    assert agent.config.provider == "lm_studio"
    assert agent.config.model_url == "http://localhost:1234"
    assert agent.config.evaluation_model_name == "openai/gpt-oss-20b"
    assert agent.config.validation_model_name == "openai/gpt-oss-20b"
    assert agent.config.llm_evaluation_enabled is True
    assert agent.config.fallback_to_heuristics is True


