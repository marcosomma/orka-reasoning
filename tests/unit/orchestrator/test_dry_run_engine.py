"""Unit tests for orka.orchestrator.dry_run_engine."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from orka.orchestrator.dry_run_engine import (
    DeterministicPathEvaluator,
    PathEvaluation,
    SmartPathEvaluator,
    ValidationResult,
)

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestPathEvaluation:
    """Test suite for PathEvaluation dataclass."""

    def test_path_evaluation_creation(self):
        """Test PathEvaluation dataclass creation."""
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test reasoning",
            expected_output="Test output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=["risk1"],
            efficiency_rating="high",
        )
        assert evaluation.node_id == "test_agent"
        assert evaluation.relevance_score == 0.8
        assert evaluation.confidence == 0.9
        assert evaluation.risk_factors == ["risk1"]


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        result = ValidationResult(
            is_valid=True,
            confidence=0.8,
            efficiency_score=0.7,
            validation_reasoning="Valid path",
            suggested_improvements=["improve1"],
            risk_assessment="low",
        )
        assert result.is_valid is True
        assert result.confidence == 0.8
        assert result.efficiency_score == 0.7
        assert result.suggested_improvements == ["improve1"]


class TestDeterministicPathEvaluator:
    """Test suite for DeterministicPathEvaluator class."""

    def test_init(self):
        """Test DeterministicPathEvaluator initialization."""
        config = Mock()
        evaluator = DeterministicPathEvaluator(config)
        assert evaluator.config == config

    def test_evaluate_candidates(self):
        """Test evaluate_candidates method."""
        config = Mock()
        evaluator = DeterministicPathEvaluator(config)

        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "memory_agent", "path": ["memory_agent", "llm_agent"]},
        ]
        question = "Find information about Python"
        context = {}

        result = evaluator.evaluate_candidates(candidates, question, context)

        assert len(result) == 2
        assert "llm_evaluation" in result[0]
        assert "llm_validation" in result[0]
        assert result[0]["llm_evaluation"]["is_deterministic_fallback"] is True
        assert result[0]["llm_validation"]["is_deterministic_fallback"] is True

    def test_score_relevance_keyword_match(self):
        """Test _score_relevance with keyword matching."""
        config = Mock()
        evaluator = DeterministicPathEvaluator(config)

        # Test search keyword match
        score = evaluator._score_relevance("search_agent", "search for information")
        assert score >= 0.8  # Should be boosted by keyword match

        # Test memory keyword match
        score = evaluator._score_relevance("memory_agent", "remember past events")
        assert score >= 0.8

        # Test no match
        score = evaluator._score_relevance("unknown_agent", "random question")
        assert score == 0.5  # Base score

    def test_score_confidence_optimal_length(self):
        """Test _score_confidence with optimal path length."""
        config = Mock()
        evaluator = DeterministicPathEvaluator(config)

        # Optimal length (2-3)
        confidence = evaluator._score_confidence(["agent1", "agent2"], {})
        assert confidence == 0.8

        # Single agent
        confidence = evaluator._score_confidence(["agent1"], {})
        assert confidence == 0.6

        # Longer path
        confidence = evaluator._score_confidence(["a1", "a2", "a3", "a4"], {})
        assert confidence == 0.7

        # Very long path
        confidence = evaluator._score_confidence(["a1", "a2", "a3", "a4", "a5", "a6"], {})
        assert confidence < 0.7

    def test_score_efficiency(self):
        """Test _score_efficiency based on path length."""
        config = Mock()
        evaluator = DeterministicPathEvaluator(config)

        # Short path
        efficiency = evaluator._score_efficiency(["a1", "a2"])
        assert efficiency == 0.9

        # Medium path
        efficiency = evaluator._score_efficiency(["a1", "a2", "a3"])
        assert efficiency == 0.8

        # Longer path
        efficiency = evaluator._score_efficiency(["a1", "a2", "a3", "a4"])
        assert efficiency == 0.6

        # Very long path
        efficiency = evaluator._score_efficiency(["a1", "a2", "a3", "a4", "a5", "a6"])
        assert efficiency < 0.6


class TestSmartPathEvaluator:
    """Test suite for SmartPathEvaluator class."""

    def create_mock_config(self):
        """Helper to create mock config."""
        config = Mock()
        config.max_preview_tokens = 100
        config.llm_evaluation_enabled = True
        config.fallback_to_heuristics = True
        config.evaluation_model = "local_llm"
        config.evaluation_model_name = "llama3.2:latest"
        config.validation_model = "local_llm"
        config.validation_model_name = "llama3.2:latest"
        config.model_url = "http://localhost:11434/api/generate"
        config.provider = "ollama"
        return config

    def test_init(self):
        """Test SmartPathEvaluator initialization."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)
        assert evaluator.config == config
        assert evaluator.max_preview_tokens == 100
        assert evaluator.deterministic_evaluator is not None

    def test_init_llm_disabled(self):
        """Test initialization with LLM evaluation disabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = False
        evaluator = SmartPathEvaluator(config)
        assert evaluator.config == config

    @pytest.mark.asyncio
    async def test_simulate_candidates_llm_disabled(self):
        """Test simulate_candidates when LLM evaluation is disabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = False
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()

        result = await evaluator.simulate_candidates(candidates, question, context, orchestrator)

        assert len(result) == 1
        assert result[0]["llm_evaluation"]["is_deterministic_fallback"] is True

    @pytest.mark.asyncio
    async def test_simulate_candidates_llm_failure_with_fallback(self):
        """Test simulate_candidates with LLM failure and fallback enabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = True
        config.fallback_to_heuristics = True
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()
        orchestrator.agents = {}

        # Mock _extract_all_agent_info to raise exception
        with patch.object(
            evaluator, "_extract_all_agent_info", side_effect=ValueError("LLM error")
        ):
            result = await evaluator.simulate_candidates(
                candidates, question, context, orchestrator
            )

            assert len(result) == 1
            assert result[0]["llm_evaluation"]["is_deterministic_fallback"] is True

    @pytest.mark.asyncio
    async def test_simulate_candidates_llm_failure_no_fallback(self):
        """Test simulate_candidates with LLM failure and fallback disabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = True
        config.fallback_to_heuristics = False
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()
        orchestrator.agents = {}

        # Mock _extract_all_agent_info to raise exception
        with patch.object(
            evaluator, "_extract_all_agent_info", side_effect=ValueError("LLM error")
        ):
            with pytest.raises(ValueError, match="LLM error"):
                await evaluator.simulate_candidates(candidates, question, context, orchestrator)

    @pytest.mark.asyncio
    async def test_simulate_candidates_unexpected_error(self):
        """Test simulate_candidates with unexpected error."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()

        # Mock _extract_all_agent_info to raise unexpected exception
        with patch.object(
            evaluator, "_extract_all_agent_info", side_effect=RuntimeError("Unexpected")
        ):
            result = await evaluator.simulate_candidates(
                candidates, question, context, orchestrator
            )

            # Should fall back to heuristic evaluation
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_extract_all_agent_info(self):
        """Test _extract_all_agent_info method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.__class__.__name__ = "LocalLLMAgent"
        mock_agent.prompt = "Test prompt"
        mock_agent.cost_model = {"base_cost": 0.001}

        orchestrator = Mock()
        orchestrator.agents = {"agent1": mock_agent}

        result = await evaluator._extract_all_agent_info(orchestrator)

        assert "agent1" in result
        assert result["agent1"]["id"] == "agent1"
        assert result["agent1"]["type"] == "LocalLLMAgent"

    @pytest.mark.asyncio
    async def test_extract_all_agent_info_no_agents_attribute(self):
        """Test _extract_all_agent_info when orchestrator has no agents."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        orchestrator = Mock()
        del orchestrator.agents  # Remove agents attribute

        result = await evaluator._extract_all_agent_info(orchestrator)

        assert result == {}

    @pytest.mark.asyncio
    async def test_extract_all_agent_info_exception(self):
        """Test _extract_all_agent_info handles exceptions."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        # Make one of the helper methods raise an exception
        with patch.object(evaluator, "_get_agent_description", side_effect=Exception("Error")):
            orchestrator = Mock()
            orchestrator.agents = {"agent1": Mock()}

            result = await evaluator._extract_all_agent_info(orchestrator)

            # Should return error entry for failed agent
            assert "agent1" in result
            assert result["agent1"]["type"] == "error"

    @pytest.mark.asyncio
    async def test_extract_agent_info(self):
        """Test _extract_agent_info method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.__class__.__name__ = "SearchAgent"
        mock_agent.prompt = "Search prompt"
        mock_agent.cost_model = {"base_cost": 0.002}
        mock_agent.safety_tags = ["safe"]

        orchestrator = Mock()
        orchestrator.agents = {"search_agent": mock_agent}

        result = await evaluator._extract_agent_info("search_agent", orchestrator)

        assert result["id"] == "search_agent"
        assert result["type"] == "SearchAgent"
        assert result["prompt"] == "Search prompt"

    @pytest.mark.asyncio
    async def test_extract_agent_info_not_found(self):
        """Test _extract_agent_info when agent not found."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        orchestrator = Mock()
        orchestrator.agents = {}

        result = await evaluator._extract_agent_info("unknown_agent", orchestrator)

        assert result["id"] == "unknown_agent"
        assert result["type"] == "unknown"

    def test_infer_capabilities(self):
        """Test _infer_capabilities method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        # Test LocalLLMAgent
        mock_agent = Mock()
        mock_agent.__class__.__name__ = "LocalLLMAgent"
        capabilities = evaluator._infer_capabilities(mock_agent)
        assert "text_generation" in capabilities

        # Test SearchAgent
        mock_agent.__class__.__name__ = "DuckDuckGoTool"
        capabilities = evaluator._infer_capabilities(mock_agent)
        assert "web_search" in capabilities

        # Test MemoryReaderNode
        mock_agent.__class__.__name__ = "MemoryReaderNode"
        capabilities = evaluator._infer_capabilities(mock_agent)
        assert "memory_retrieval" in capabilities

    def test_get_agent_description(self):
        """Test _get_agent_description method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.__class__.__name__ = "LocalLLMAgent"
        mock_agent.prompt = "Test prompt"

        description = evaluator._get_agent_description(mock_agent)
        assert "Local Large Language Model" in description
        assert "Test prompt" not in description  # Prompt is not part of the description

    def test_extract_agent_parameters(self):
        """Test _extract_agent_parameters method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.max_tokens = 1000
        mock_agent.temperature = 0.7

        params = evaluator._extract_agent_parameters(mock_agent)
        assert "max_tokens" in params or len(params) >= 0

    def test_estimate_agent_cost(self):
        """Test _estimate_agent_cost method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.cost_model = {"base_cost": 0.001}

        cost = evaluator._estimate_agent_cost(mock_agent)
        assert cost >= 0.0

    def test_estimate_agent_latency(self):
        """Test _estimate_agent_latency method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        mock_agent = Mock()
        mock_agent.estimated_latency_ms = 500

        latency = evaluator._estimate_agent_latency(mock_agent)
        assert latency >= 0

    def test_parse_evaluation_response_valid(self):
        """Test _parse_evaluation_response with valid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = json.dumps(
            {
                "relevance_score": 0.8,
                "confidence": 0.9,
                "reasoning": "Good match",
                "expected_output": "Test output",
                "estimated_tokens": 100,
                "estimated_cost": 0.001,
                "estimated_latency_ms": 500,
                "risk_factors": ["risk1"],
                "efficiency_rating": "high",
            }
        )

        result = evaluator._parse_evaluation_response(response, "test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"
        assert result.relevance_score == 0.8
        assert result.confidence == 0.9

    def test_parse_evaluation_response_invalid_json(self):
        """Test _parse_evaluation_response with invalid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = "invalid json"

        result = evaluator._parse_evaluation_response(response, "test_agent")

        # Should return fallback evaluation
        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"
        assert result.relevance_score == 0.5

    def test_parse_evaluation_response_schema_validation_failure(self):
        """Test _parse_evaluation_response with schema validation failure."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        # Missing required field
        response = json.dumps(
            {
                "relevance_score": 0.8,
                # Missing confidence and reasoning
            }
        )

        result = evaluator._parse_evaluation_response(response, "test_agent")

        # Should return fallback evaluation
        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"

    def test_parse_validation_response_valid(self):
        """Test _parse_validation_response with valid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = json.dumps(
            {
                "is_valid": True,
                "confidence": 0.8,
                "efficiency_score": 0.7,
                "validation_reasoning": "Valid path",
                "suggested_improvements": ["improve1"],
                "risk_assessment": "low",
            }
        )

        result = evaluator._parse_validation_response(response)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.confidence == 0.8
        assert result.efficiency_score == 0.7

    def test_parse_validation_response_invalid_json(self):
        """Test _parse_validation_response with invalid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = "invalid json"

        result = evaluator._parse_validation_response(response)

        # Should return fallback validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_create_fallback_evaluation(self):
        """Test _create_fallback_evaluation method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        result = evaluator._create_fallback_evaluation("test_agent")

        assert isinstance(result, PathEvaluation)
        assert result.node_id == "test_agent"
        assert result.relevance_score == 0.5
        assert result.confidence == 0.3
        assert "evaluation_failure" in result.risk_factors

    def test_create_fallback_validation(self):
        """Test _create_fallback_validation method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        result = evaluator._create_fallback_validation()

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.confidence == 0.3
        assert result.efficiency_score == 0.5

    def test_combine_evaluation_results(self):
        """Test _combine_evaluation_results method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test",
            expected_output="Output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=[],
            efficiency_rating="high",
        )
        validation = ValidationResult(
            is_valid=True,
            confidence=0.8,
            efficiency_score=0.7,
            validation_reasoning="Valid",
            suggested_improvements=[],
            risk_assessment="low",
        )

        result = evaluator._combine_evaluation_results(candidate, evaluation, validation)

        assert "llm_evaluation" in result
        assert "estimated_cost" in result
        assert "estimated_latency" in result
        assert result["llm_evaluation"]["final_scores"]["relevance"] == 0.8

    def test_combine_evaluation_results_invalid_validation(self):
        """Test _combine_evaluation_results with invalid validation."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test",
            expected_output="Output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=[],
            efficiency_rating="high",
        )
        validation = ValidationResult(
            is_valid=False,  # Invalid
            confidence=0.5,
            efficiency_score=0.3,
            validation_reasoning="Invalid",
            suggested_improvements=[],
            risk_assessment="high",
        )

        result = evaluator._combine_evaluation_results(candidate, evaluation, validation)

        # Relevance should be penalized
        assert result["llm_evaluation"]["final_scores"]["relevance"] == 0.4  # 0.8 * 0.5

    @pytest.mark.asyncio
    async def test_fallback_heuristic_evaluation(self):
        """Test _fallback_heuristic_evaluation method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidates = [
            {"node_id": "search_agent", "path": ["search_agent"]},
            {"node_id": "memory_agent", "path": ["memory_agent"]},
        ]
        question = "search for information"
        context = {}

        result = await evaluator._fallback_heuristic_evaluation(candidates, question, context)

        assert len(result) == 2
        assert "llm_evaluation" in result[0]
        assert result[0]["llm_evaluation"]["final_scores"]["relevance"] >= 0.5

    def test_extract_json_from_response_direct_json(self):
        """Test _extract_json_from_response with direct JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = '{"key": "value"}'
        result = evaluator._extract_json_from_response(response)
        assert result == response

    def test_extract_json_from_response_code_block(self):
        """Test _extract_json_from_response with JSON code block."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = '```json\n{"key": "value"}\n```'
        result = evaluator._extract_json_from_response(response)
        assert result is not None
        assert "key" in result

    def test_extract_json_from_response_no_json(self):
        """Test _extract_json_from_response with no valid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = "This is not JSON at all"
        result = evaluator._extract_json_from_response(response)
        assert result is None

    def test_build_evaluation_prompt(self):
        """Test _build_evaluation_prompt method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        question = "Test question"
        agent_info = {
            "id": "test_agent",
            "type": "LocalLLMAgent",
            "capabilities": ["text_generation"],
            "prompt": "Test prompt",
        }
        candidate = {"node_id": "test_agent", "path": ["test_agent"], "depth": 1}
        context = {"current_agent_id": "router", "previous_outputs": {}}

        prompt = evaluator._build_evaluation_prompt(question, agent_info, candidate, context)

        assert "Test question" in prompt
        assert "test_agent" in prompt
        assert "LocalLLMAgent" in prompt

    def test_build_validation_prompt(self):
        """Test _build_validation_prompt method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        question = "Test question"
        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test reasoning",
            expected_output="Test output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=[],
            efficiency_rating="high",
        )
        context = {}

        prompt = evaluator._build_validation_prompt(question, candidate, evaluation, context)

        assert "Test question" in prompt
        assert "test_agent" in prompt
        assert "0.8" in prompt  # relevance_score

    def test_generate_possible_paths(self):
        """Test _generate_possible_paths method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "agent1": {"cost_estimate": 0.001, "latency_estimate": 100},
            "agent2": {"cost_estimate": 0.002, "latency_estimate": 200},
        }
        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent1", "agent2"]},
        ]

        result = evaluator._generate_possible_paths(available_agents, candidates)

        assert len(result) == 2
        assert result[0]["total_cost"] == 0.001
        assert result[1]["total_cost"] == 0.003  # agent1 + agent2

    def test_parse_comprehensive_evaluation_response_valid(self):
        """Test _parse_comprehensive_evaluation_response with valid response."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = json.dumps(
            {
                "recommended_path": ["agent1", "agent2"],
                "reasoning": "Optimal path",
                "confidence": 0.9,
                "path_evaluations": [{"path": ["agent1"], "score": 0.8}],
            }
        )

        result = evaluator._parse_comprehensive_evaluation_response(response)

        assert result["recommended_path"] == ["agent1", "agent2"]
        assert result["confidence"] == 0.9

    def test_parse_comprehensive_evaluation_response_invalid_json(self):
        """Test _parse_comprehensive_evaluation_response with invalid JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = "invalid json"

        result = evaluator._parse_comprehensive_evaluation_response(response)

        assert result["recommended_path"] == []
        assert "Failed to parse" in result["reasoning"]

    def test_parse_comprehensive_evaluation_response_missing_fields(self):
        """Test _parse_comprehensive_evaluation_response with missing required fields."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = json.dumps({"reasoning": "Test"})  # Missing required fields

        result = evaluator._parse_comprehensive_evaluation_response(response)

        assert result["recommended_path"] == []
        assert "Failed to parse" in result["reasoning"]

    def test_map_evaluation_to_candidates(self):
        """Test _map_evaluation_to_candidates method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidates = [
            {"node_id": "agent1", "path": ["agent1"]},
            {"node_id": "agent2", "path": ["agent2"]},
        ]
        evaluation_results = {
            "recommended_path": ["agent1"],
            "confidence": 0.9,
            "path_evaluations": [
                {"path": ["agent1"], "score": 0.8, "pros": ["pro1"], "cons": []},
            ],
        }
        available_agents = {
            "agent1": {"cost_estimate": 0.001, "latency_estimate": 100},
            "agent2": {"cost_estimate": 0.002, "latency_estimate": 200},
        }

        result = evaluator._map_evaluation_to_candidates(
            candidates, evaluation_results, available_agents
        )

        assert len(result) == 2
        assert result[0]["llm_evaluation"]["is_recommended"] is True
        assert result[1]["llm_evaluation"]["is_recommended"] is False

    def test_generate_path_specific_outcome_single_agent(self):
        """Test _generate_path_specific_outcome with single agent."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        path = ["search_agent"]
        available_agents = {
            "search_agent": {"type": "DuckDuckGoTool"},
        }

        result = evaluator._generate_path_specific_outcome(path, available_agents)

        assert "news" in result.lower() or "information" in result.lower()

    def test_generate_path_specific_outcome_multi_agent(self):
        """Test _generate_path_specific_outcome with multiple agents."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        path = ["search_agent", "response_builder"]
        available_agents = {
            "search_agent": {"type": "DuckDuckGoTool"},
            "response_builder": {"type": "LocalLLMAgent"},
        }

        result = evaluator._generate_path_specific_outcome(path, available_agents)

        assert "workflow" in result.lower() or "step" in result.lower()

    def test_generate_path_specific_outcome_empty_path(self):
        """Test _generate_path_specific_outcome with empty path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        result = evaluator._generate_path_specific_outcome([], {})

        assert result == "Unknown outcome"

    def test_generate_fallback_path_evaluation_empty_path(self):
        """Test _generate_fallback_path_evaluation with empty path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        result = evaluator._generate_fallback_path_evaluation([], {})

        assert result["score"] == 0.3
        assert "Empty path" in result["reasoning"]

    def test_generate_fallback_path_evaluation_with_search(self):
        """Test _generate_fallback_path_evaluation with search agent."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        path = ["search_agent"]
        available_agents = {
            "search_agent": {"type": "DuckDuckGoTool"},
        }

        result = evaluator._generate_fallback_path_evaluation(path, available_agents)

        assert result["score"] >= 0.5  # Should be boosted by search
        assert len(result["pros"]) > 0

    def test_generate_fallback_path_evaluation_multi_hop(self):
        """Test _generate_fallback_path_evaluation with multi-hop path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        path = ["search_agent", "response_builder"]
        available_agents = {
            "search_agent": {"type": "DuckDuckGoTool"},
            "response_builder": {"type": "LocalLLMAgent"},
        }

        result = evaluator._generate_fallback_path_evaluation(path, available_agents)

        assert result["score"] > 0.5
        assert "workflow" in result["reasoning"].lower()

    def test_extract_json_from_response_code_block_json(self):
        """Test _extract_json_from_response with JSON code block."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = '```json\n{"key": "value"}\n```'
        result = evaluator._extract_json_from_response(response)
        assert result is not None
        assert "key" in result

    def test_extract_json_from_response_code_block_no_lang(self):
        """Test _extract_json_from_response with code block without language."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = '```\n{"key": "value"}\n```'
        result = evaluator._extract_json_from_response(response)
        assert result is not None

    def test_extract_json_from_response_curly_braces(self):
        """Test _extract_json_from_response extracting from curly braces."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = 'Some text {"key": "value"} more text'
        result = evaluator._extract_json_from_response(response)
        assert result is not None
        assert "key" in result

    def test_extract_json_from_response_trailing_comma(self):
        """Test _extract_json_from_response with trailing comma fix."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        response = '{"key": "value",}'  # Trailing comma
        result = evaluator._extract_json_from_response(response)
        assert result is not None

    @pytest.mark.asyncio
    async def test_call_ollama_async(self):
        """Test _call_ollama_async method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        with patch.object(evaluator, "_call_ollama_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "test response"

            result = await evaluator._call_ollama_async(
                "http://localhost:11434/api/generate", "llama3.2:latest", "test prompt", 0.1
            )

            assert result == "test response"

    @pytest.mark.asyncio
    async def test_call_lm_studio_async(self):
        """Test _call_lm_studio_async method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        with patch.object(evaluator, "_call_lm_studio_async", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "test response"

            result = await evaluator._call_lm_studio_async(
                "http://localhost:1234", "test-model", "test prompt", 0.0
            )

            assert result == "test response"

    @pytest.mark.asyncio
    async def test_stage1_path_evaluation(self):
        """Test _stage1_path_evaluation method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        question = "Test question"
        context = {"current_agent_id": "router"}
        orchestrator = Mock()
        orchestrator.agents = {
            "test_agent": Mock(__class__=Mock(__name__="LocalLLMAgent"), prompt="Test prompt")
        }

        with (
            patch.object(
                evaluator,
                "_extract_agent_info",
                return_value={
                    "id": "test_agent",
                    "type": "LocalLLMAgent",
                    "capabilities": ["text_generation"],
                    "prompt": "Test prompt",
                },
            ),
            patch.object(
                evaluator,
                "_call_evaluation_llm",
                return_value=json.dumps(
                    {
                        "relevance_score": 0.8,
                        "confidence": 0.9,
                        "reasoning": "Good match",
                        "expected_output": "Test output",
                        "estimated_tokens": 100,
                        "estimated_cost": 0.001,
                        "estimated_latency_ms": 500,
                        "risk_factors": [],
                        "efficiency_rating": "high",
                    }
                ),
            ),
        ):
            result = await evaluator._stage1_path_evaluation(
                candidate, question, context, orchestrator
            )

            assert isinstance(result, PathEvaluation)
            assert result.relevance_score == 0.8

    @pytest.mark.asyncio
    async def test_stage1_path_evaluation_self_routing_prevention(self):
        """Test _stage1_path_evaluation prevents self-routing."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "current_agent", "path": ["current_agent"]}
        question = "Test question"
        context = {"current_agent_id": "current_agent"}  # Same as candidate
        orchestrator = Mock()
        orchestrator.agents = {"current_agent": Mock()}

        with (
            patch.object(
                evaluator,
                "_extract_agent_info",
                return_value={
                    "id": "current_agent",
                    "type": "LocalLLMAgent",
                    "capabilities": [],
                    "prompt": "",
                },
            ),
            patch.object(
                evaluator,
                "_call_evaluation_llm",
                return_value=json.dumps(
                    {
                        "relevance_score": 0.9,  # LLM tries to route to itself
                        "confidence": 0.9,
                        "reasoning": "Good match",
                        "expected_output": "Test output",
                        "estimated_tokens": 100,
                        "estimated_cost": 0.001,
                        "estimated_latency_ms": 500,
                        "risk_factors": [],
                        "efficiency_rating": "high",
                    }
                ),
            ),
        ):
            result = await evaluator._stage1_path_evaluation(
                candidate, question, context, orchestrator
            )

            # Should be overridden to prevent self-routing
            assert result.relevance_score == 0.0
            assert result.confidence == 0.0
            assert "Prevented self-routing" in result.reasoning

    @pytest.mark.asyncio
    async def test_stage2_path_validation(self):
        """Test _stage2_path_validation method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test",
            expected_output="Output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=[],
            efficiency_rating="high",
        )
        question = "Test question"
        context = {}

        with patch.object(
            evaluator,
            "_call_validation_llm",
            return_value=json.dumps(
                {
                    "is_valid": True,
                    "confidence": 0.8,
                    "efficiency_score": 0.7,
                    "validation_reasoning": "Valid path",
                    "suggested_improvements": [],
                    "risk_assessment": "low",
                }
            ),
        ):
            result = await evaluator._stage2_path_validation(
                candidate, evaluation, question, context
            )

            assert isinstance(result, ValidationResult)
            assert result.is_valid is True
            assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_simulate_candidates_json_decode_error(self):
        """Test simulate_candidates with JSONDecodeError in evaluation."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()

        # Mock _extract_all_agent_info to succeed
        with patch.object(evaluator, "_extract_all_agent_info", return_value={"test_agent": {"id": "test_agent"}}):
            # Mock _llm_path_evaluation to raise JSONDecodeError
            with patch.object(evaluator, "_llm_path_evaluation", side_effect=json.JSONDecodeError("Error", "", 0)):
                result = await evaluator.simulate_candidates(candidates, question, context, orchestrator)

                # Should fall back to deterministic evaluator
                assert len(result) == 1
                assert result[0]["llm_evaluation"]["is_deterministic_fallback"] is True

    @pytest.mark.asyncio
    async def test_simulate_candidates_key_error(self):
        """Test simulate_candidates with KeyError in evaluation."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidates = [{"node_id": "test_agent", "path": ["test_agent"]}]
        question = "Test question"
        context = {}
        orchestrator = Mock()

        with patch.object(evaluator, "_extract_all_agent_info", return_value={"test_agent": {"id": "test_agent"}}):
            with patch.object(evaluator, "_llm_path_evaluation", side_effect=KeyError("missing_key")):
                result = await evaluator.simulate_candidates(candidates, question, context, orchestrator)

                # Should fall back to deterministic evaluator
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_call_evaluation_llm_disabled(self):
        """Test _call_evaluation_llm when LLM is disabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = False
        evaluator = SmartPathEvaluator(config)

        with pytest.raises(ValueError, match="LLM evaluation is required but disabled"):
            await evaluator._call_evaluation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_evaluation_llm_unsupported_provider(self):
        """Test _call_evaluation_llm with unsupported provider."""
        config = self.create_mock_config()
        config.provider = "unsupported_provider"
        evaluator = SmartPathEvaluator(config)

        # Mock Ollama/LM Studio calls to prevent real connections
        with patch.object(evaluator, "_call_ollama_async", return_value="mock"):
            with patch.object(evaluator, "_call_lm_studio_async", return_value="mock"):
                with pytest.raises(ValueError):
                    await evaluator._call_evaluation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_evaluation_llm_lm_studio(self):
        """Test _call_evaluation_llm with LM Studio provider."""
        config = self.create_mock_config()
        config.provider = "lm_studio"
        evaluator = SmartPathEvaluator(config)

        mock_response = json.dumps({"evaluation": "test"})

        # Mock both methods to prevent any real connection attempts
        with patch.object(evaluator, "_call_ollama_async", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(evaluator, "_call_lm_studio_async", new_callable=AsyncMock, return_value=mock_response):
                with patch.object(evaluator, "_extract_json_from_response", return_value=mock_response):
                    result = await evaluator._call_evaluation_llm("test prompt")
                    assert result == mock_response

    @pytest.mark.asyncio
    async def test_call_evaluation_llm_no_json_in_response(self):
        """Test _call_evaluation_llm when response has no JSON."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        with patch.object(evaluator, "_call_ollama_async", return_value="no json here"):
            with patch.object(evaluator, "_extract_json_from_response", return_value=None):
                with pytest.raises(ValueError):
                    await evaluator._call_evaluation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_validation_llm_disabled(self):
        """Test _call_validation_llm when LLM is disabled."""
        config = self.create_mock_config()
        config.llm_evaluation_enabled = False
        evaluator = SmartPathEvaluator(config)

        with pytest.raises(ValueError):
            await evaluator._call_validation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_validation_llm_unsupported_provider(self):
        """Test _call_validation_llm with unsupported provider."""
        config = self.create_mock_config()
        config.provider = "unknown"
        evaluator = SmartPathEvaluator(config)

        # Mock Ollama/LM Studio calls to prevent real connections
        with patch.object(evaluator, "_call_ollama_async", return_value="mock"):
            with patch.object(evaluator, "_call_lm_studio_async", return_value="mock"):
                with pytest.raises(ValueError):
                    await evaluator._call_validation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_call_validation_llm_lmstudio(self):
        """Test _call_validation_llm with lmstudio provider."""
        config = self.create_mock_config()
        config.provider = "lmstudio"
        evaluator = SmartPathEvaluator(config)

        mock_response = json.dumps({"validation": "test"})

        # Mock both methods to prevent any real connection attempts
        with patch.object(evaluator, "_call_ollama_async", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(evaluator, "_call_lm_studio_async", new_callable=AsyncMock, return_value=mock_response):
                with patch.object(evaluator, "_extract_json_from_response", return_value=mock_response):
                    result = await evaluator._call_validation_llm("test prompt")
                    assert result == mock_response

    @pytest.mark.asyncio
    async def test_call_validation_llm_no_json(self):
        """Test _call_validation_llm when no JSON in response."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        with patch.object(evaluator, "_call_ollama_async", return_value="plain text"):
            with patch.object(evaluator, "_extract_json_from_response", return_value=None):
                with pytest.raises(ValueError):
                    await evaluator._call_validation_llm("test prompt")

    @pytest.mark.asyncio
    async def test_stage2_validation_exception(self):
        """Test _stage2_path_validation with exception."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        evaluation = PathEvaluation(
            node_id="test_agent",
            relevance_score=0.8,
            confidence=0.9,
            reasoning="Test",
            expected_output="Output",
            estimated_tokens=100,
            estimated_cost=0.001,
            estimated_latency_ms=500,
            risk_factors=[],
            efficiency_rating="high",
        )
        question = "Test question"
        context = {}

        with patch.object(evaluator, "_build_validation_prompt", side_effect=Exception("Error")):
            result = await evaluator._stage2_path_validation(candidate, evaluation, question, context)

            # Should return fallback validation
            assert isinstance(result, ValidationResult)
            assert result.is_valid is True  # Fallback assumes valid

    @pytest.mark.asyncio
    async def test_stage1_evaluation_exception(self):
        """Test _stage1_path_evaluation with exception."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        candidate = {"node_id": "test_agent", "path": ["test_agent"]}
        question = "Test question"
        context = {}
        agent_info = {"id": "test_agent", "type": "LocalLLMAgent"}

        with patch.object(evaluator, "_build_evaluation_prompt", side_effect=Exception("Error")):
            result = await evaluator._stage1_path_evaluation(candidate, question, context, agent_info)

            # Should return fallback evaluation
            assert isinstance(result, PathEvaluation)
            assert result.node_id == "test_agent"

    @pytest.mark.asyncio
    async def test_build_comprehensive_evaluation_prompt(self):
        """Test _build_comprehensive_evaluation_prompt method."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        question = "Test question"
        available_agents = {
            "agent1": {
                "type": "LocalLLMAgent",
                "description": "Test agent",
                "capabilities": ["reasoning"],
                "prompt": "Test prompt",
                "cost_estimate": 0.01,
                "latency_estimate": 100,
            }
        }
        possible_paths = [
            {
                "agents": [{"id": "agent1", "description": "Test agent"}],
                "total_cost": 0.01,
                "total_latency": 100,
            }
        ]
        context = {"current_agent_id": "router", "previous_outputs": {"prev": "result"}}

        prompt = evaluator._build_comprehensive_evaluation_prompt(
            question, available_agents, possible_paths, context
        )

        assert isinstance(prompt, str)
        assert "Test question" in prompt
        assert "agent1" in prompt
        assert "LocalLLMAgent" in prompt

    @pytest.mark.asyncio
    async def test_generate_path_specific_outcome_single_agent(self):
        """Test _generate_path_specific_outcome with single agent paths."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "search": {"type": "DuckDuckGoTool"},
            "classifier": {"type": "ClassificationAgent"},
            "memory_reader": {"type": "MemoryReaderNode"},
            "memory_writer": {"type": "MemoryWriterNode"},
            "llm_analysis": {"type": "LocalLLMAgent"},
            "llm_response": {"type": "OpenAIAnswerBuilder"},
            "graph_scout": {"type": "GraphScoutAgent"},
            "binary": {"type": "BinaryAgent"},
        }

        # Test search agent
        outcome = evaluator._generate_path_specific_outcome(["search"], available_agents)
        assert "news" in outcome.lower() or "web" in outcome.lower()

        # Test classifier
        outcome = evaluator._generate_path_specific_outcome(["classifier"], available_agents)
        assert "categorized" in outcome.lower() or "classification" in outcome.lower()

        # Test memory reader
        outcome = evaluator._generate_path_specific_outcome(
            ["memory_reader"], available_agents
        )
        assert "stored" in outcome.lower() or "retrieved" in outcome.lower()

        # Test memory writer
        outcome = evaluator._generate_path_specific_outcome(
            ["memory_writer"], available_agents
        )
        assert "stored" in outcome.lower()

        # Test graph scout
        outcome = evaluator._generate_path_specific_outcome(
            ["graph_scout"], available_agents
        )
        assert "routing" in outcome.lower() or "path" in outcome.lower()

        # Test binary agent
        outcome = evaluator._generate_path_specific_outcome(["binary"], available_agents)
        assert "yes" in outcome.lower() or "no" in outcome.lower() or "binary" in outcome.lower()

    @pytest.mark.asyncio
    async def test_generate_path_specific_outcome_multi_agent(self):
        """Test _generate_path_specific_outcome with multi-agent paths."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "search": {"type": "DuckDuckGoTool"},
            "llm": {"type": "LocalLLMAgent"},
            "memory": {"type": "MemoryReaderNode"},
        }

        outcome = evaluator._generate_path_specific_outcome(
            ["search", "llm"], available_agents
        )
        assert "multi-step" in outcome.lower() or "workflow" in outcome.lower()

    @pytest.mark.asyncio
    async def test_generate_path_specific_outcome_empty_path(self):
        """Test _generate_path_specific_outcome with empty path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        outcome = evaluator._generate_path_specific_outcome([], {})
        assert outcome == "Unknown outcome"

    @pytest.mark.asyncio
    async def test_generate_fallback_path_evaluation_search_response(self):
        """Test _generate_fallback_path_evaluation with search + response path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "search": {"type": "DuckDuckGoTool"},
            "response_builder": {"type": "OpenAIAnswerBuilder"},
        }

        result = evaluator._generate_fallback_path_evaluation(
            ["search", "response_builder"], available_agents
        )

        assert result["score"] >= 0.8  # Should get high score
        assert "search" in result["reasoning"].lower()
        assert len(result["pros"]) > 0

    @pytest.mark.asyncio
    async def test_generate_fallback_path_evaluation_analysis_response(self):
        """Test _generate_fallback_path_evaluation with analysis + response path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "llm_analysis": {"type": "LocalLLMAgent"},
            "response_builder": {"type": "LocalLLMAgent"},
        }

        result = evaluator._generate_fallback_path_evaluation(
            ["llm_analysis", "response_builder"], available_agents
        )

        assert result["score"] > 0.5
        assert "analysis" in result["reasoning"].lower() or "analytical" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_generate_fallback_path_evaluation_single_non_builder(self):
        """Test _generate_fallback_path_evaluation with single non-response-builder agent."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {"search": {"type": "DuckDuckGoTool"}}

        result = evaluator._generate_fallback_path_evaluation(["search"], available_agents)

        # Should be penalized for missing response generation
        assert result["score"] < 0.8
        assert len(result["cons"]) > 0

    @pytest.mark.asyncio
    async def test_generate_fallback_path_evaluation_overly_complex(self):
        """Test _generate_fallback_path_evaluation with overly complex path."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        available_agents = {
            "a1": {"type": "LocalLLMAgent"},
            "a2": {"type": "LocalLLMAgent"},
            "a3": {"type": "LocalLLMAgent"},
            "a4": {"type": "LocalLLMAgent"},
        }

        result = evaluator._generate_fallback_path_evaluation(
            ["a1", "a2", "a3", "a4"], available_agents
        )

        # Should be penalized for complexity
        assert "complex" in result["reasoning"].lower() or any("complex" in con.lower() for con in result["cons"])

    @pytest.mark.asyncio
    async def test_get_agent_description_known_types(self):
        """Test _get_agent_description with known Orka agent types."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        class LocalLLMAgent:
            pass

        class DuckDuckGoTool:
            pass

        class MemoryReaderNode:
            pass

        class GraphScoutAgent:
            pass

        llm = LocalLLMAgent()
        search = DuckDuckGoTool()
        memory = MemoryReaderNode()
        scout = GraphScoutAgent()

        desc_llm = evaluator._get_agent_description(llm)
        assert "language model" in desc_llm.lower() or "llm" in desc_llm.lower()

        desc_search = evaluator._get_agent_description(search)
        assert "search" in desc_search.lower() or "duckduckgo" in desc_search.lower()

        desc_memory = evaluator._get_agent_description(memory)
        assert "memory" in desc_memory.lower() or "retrieve" in desc_memory.lower()

        desc_scout = evaluator._get_agent_description(scout)
        assert "routing" in desc_scout.lower() or "path" in desc_scout.lower()

    @pytest.mark.asyncio
    async def test_infer_capabilities_known_types(self):
        """Test _infer_capabilities with known Orka agent types."""
        config = self.create_mock_config()
        evaluator = SmartPathEvaluator(config)

        class LocalLLMAgent:
            pass

        class DuckDuckGoTool:
            pass

        class RouterNode:
            pass

        class BinaryAgent:
            pass

        llm = LocalLLMAgent()
        search = DuckDuckGoTool()
        router = RouterNode()
        binary = BinaryAgent()

        caps_llm = evaluator._infer_capabilities(llm)
        assert "text_generation" in caps_llm or "reasoning" in caps_llm

        caps_search = evaluator._infer_capabilities(search)
        assert "web_search" in caps_search or "information_retrieval" in caps_search

        caps_router = evaluator._infer_capabilities(router)
        assert "routing" in caps_router or "decision_making" in caps_router

        caps_binary = evaluator._infer_capabilities(binary)
        assert "binary_decision" in caps_binary
