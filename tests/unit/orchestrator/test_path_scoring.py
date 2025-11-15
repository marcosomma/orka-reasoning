"""Unit tests for orka.orchestrator.path_scoring."""

from unittest.mock import Mock, AsyncMock, patch

import pytest

from orka.orchestrator.path_scoring import PathScorer

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestPathScorer:
    """Test suite for PathScorer class."""

    def create_mock_config(self, scoring_mode="numeric"):
        """Helper to create mock config."""
        config = Mock()
        config.score_weights = {
            "llm_relevance": 0.4,
            "heuristics": 0.3,
            "priors": 0.2,
            "cost": 0.1,
        }
        config.scoring_mode = scoring_mode
        config.k_beam = 3
        config.max_reasonable_cost = 0.10
        config.path_length_penalty = 0.10
        config.keyword_match_boost = 0.30
        config.default_neutral_score = 0.50
        config.optimal_path_length = (2, 3)
        config.min_readiness_score = 0.30
        config.no_requirements_score = 0.90
        config.risky_capabilities = {"file_write", "code_execution"}
        config.safety_markers = {"sandboxed", "read_only"}
        config.safe_default_score = 0.70
        return config

    def test_init_numeric_mode(self):
        """Test PathScorer initialization in numeric mode."""
        config = self.create_mock_config(scoring_mode="numeric")
        scorer = PathScorer(config)
        
        assert scorer.scoring_mode == "numeric"
        assert scorer.boolean_engine is None
        assert scorer.score_weights == config.score_weights

    def test_init_boolean_mode(self):
        """Test PathScorer initialization in boolean mode."""
        config = self.create_mock_config(scoring_mode="boolean")
        scorer = PathScorer(config)
        
        assert scorer.scoring_mode == "boolean"
        assert scorer.boolean_engine is not None

    def test_init_invalid_mode(self):
        """Test PathScorer initialization with invalid mode defaults to numeric."""
        config = self.create_mock_config(scoring_mode="invalid")
        scorer = PathScorer(config)
        
        assert scorer.scoring_mode == "numeric"

    @pytest.mark.asyncio
    async def test_score_candidates_numeric(self):
        """Test score_candidates in numeric mode."""
        config = self.create_mock_config(scoring_mode="numeric")
        scorer = PathScorer(config)
        
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2"]},
        ]
        question = "Test question"
        context = {}
        
        result = await scorer.score_candidates(candidates, question, context)
        
        assert isinstance(result, list)
        assert len(result) <= len(candidates)
        for candidate in result:
            assert "score" in candidate
            assert "score_components" in candidate

    @pytest.mark.asyncio
    async def test_score_candidates_boolean(self):
        """Test score_candidates in boolean mode."""
        config = self.create_mock_config(scoring_mode="boolean")
        scorer = PathScorer(config)
        
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
        ]
        question = "Test question"
        context = {}
        
        with patch.object(scorer, '_score_candidates_boolean', return_value=candidates):
            result = await scorer.score_candidates(candidates, question, context)
            assert result == candidates

    @pytest.mark.asyncio
    async def test_score_candidate(self):
        """Test _score_candidate method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "path": ["agent1"],
            "estimated_cost": 0.001,
            "estimated_latency": 500,
        }
        question = "Test question"
        context = {}
        
        components = await scorer._score_candidate(candidate, question, context)
        
        assert isinstance(components, dict)
        assert "llm_relevance" in components or "heuristics" in components

    def test_score_path_structure(self):
        """Test _score_path_structure method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        # Optimal length path
        path1 = ["agent1", "agent2"]
        score1 = scorer._score_path_structure(path1)
        assert 0.0 <= score1 <= 1.0
        
        # Longer path
        path2 = ["agent1", "agent2", "agent3", "agent4", "agent5"]
        score2 = scorer._score_path_structure(path2)
        assert score2 < score1  # Longer paths should score lower

    def test_get_historical_score(self):
        """Test _get_historical_score method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        mock_memory = Mock()
        mock_memory.get_metric = Mock(return_value=0.8)
        
        score = scorer._get_historical_score("agent1", mock_memory)
        
        assert score == 0.8

    def test_get_historical_score_no_memory(self):
        """Test _get_historical_score when memory manager is None."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        score = scorer._get_historical_score("agent1", None)
        
        assert score == 0.6  # Default neutral score

    @pytest.mark.asyncio
    async def test_score_cost(self):
        """Test _score_cost method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {"estimated_cost": 0.05}
        context = {}
        
        score = await scorer._score_cost(candidate, context)
        
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_cost_high(self):
        """Test _score_cost with high cost."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {"estimated_cost": 0.50}  # Very high cost
        context = {}
        
        score = await scorer._score_cost(candidate, context)
        
        assert score < 0.5  # Should be penalized

    @pytest.mark.asyncio
    async def test_score_latency(self):
        """Test _score_latency method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {"estimated_latency": 1000}
        context = {}
        
        score = await scorer._score_latency(candidate, context)
        
        assert 0.0 <= score <= 1.0

    def test_calculate_final_score(self):
        """Test _calculate_final_score method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        components = {
            "llm_relevance": 0.8,
            "heuristics": 0.7,
            "priors": 0.6,
            "cost": 0.9,
        }
        
        final_score = scorer._calculate_final_score(components)
        
        assert 0.0 <= final_score <= 1.0
        # Should be weighted average
        expected = (
            0.8 * 0.4 + 0.7 * 0.3 + 0.6 * 0.2 + 0.9 * 0.1
        )
        assert abs(final_score - expected) < 0.01

    def test_calculate_confidence(self):
        """Test _calculate_confidence method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        components = {
            "llm_relevance": 0.8,
            "heuristics": 0.7,
        }
        
        confidence = scorer._calculate_confidence(components)
        
        assert 0.0 <= confidence <= 1.0

    def test_check_input_readiness(self):
        """Test _check_input_readiness method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "required_inputs": ["query"],
        }
        context = {
            "previous_outputs": {
                "previous_agent": {"result": "query data"}
            }
        }
        
        score = scorer._check_input_readiness(candidate, context)
        
        assert 0.0 <= score <= 1.0

    def test_check_input_readiness_no_requirements(self):
        """Test _check_input_readiness with no required inputs."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "required_inputs": [],
        }
        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": Mock(required_inputs=[])}
        context = {"orchestrator": mock_orchestrator}
        
        score = scorer._check_input_readiness(candidate, context)
        
        assert score >= 0.9  # Should score high when no requirements

    def test_check_safety_fit(self):
        """Test _check_safety_fit method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "capabilities": ["text_generation"],
            "safety_tags": ["safe"],
        }
        context = {}
        
        score = scorer._check_safety_fit(candidate, context)
        
        assert 0.0 <= score <= 1.0

    def test_check_safety_fit_risky(self):
        """Test _check_safety_fit with risky capabilities."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "capabilities": ["code_execution"],
            "safety_tags": [],
        }
        mock_orchestrator = Mock()
        mock_orchestrator.agents = {
            "agent1": Mock(capabilities=["code_execution"], safety_tags=[])
        }
        context = {"orchestrator": mock_orchestrator}
        
        score = scorer._check_safety_fit(candidate, context)
        
        assert score < 0.7  # Should be penalized

    def test_check_modality_fit(self):
        """Test _check_modality_fit method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "agent1",
            "capabilities": ["text_generation"],
        }
        question = "What is the weather?"
        
        score = scorer._check_modality_fit(candidate, question)
        
        assert 0.0 <= score <= 1.0

    def test_check_domain_overlap(self):
        """Test _check_domain_overlap method."""
        config = self.create_mock_config()
        scorer = PathScorer(config)
        
        candidate = {
            "node_id": "search_agent",
            "capabilities": ["web_search"],
        }
        question = "Search for information about Python"
        
        score = scorer._check_domain_overlap(candidate, question)
        
        assert 0.0 <= score <= 1.0

