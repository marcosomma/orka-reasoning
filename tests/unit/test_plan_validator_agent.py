"""
Unit tests for PlanValidatorAgent.
Tests agent initialization, execution, and error handling with mocked dependencies.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka.agents.plan_validator import PlanValidatorAgent, critique_parser, llm_client


class TestPlanValidatorAgent:
    """Test the PlanValidatorAgent class functionality."""

    def test_initialization_default_params(self):
        """Test PlanValidatorAgent initialization with default parameters."""
        agent = PlanValidatorAgent(agent_id="test_validator")

        assert agent.agent_id == "test_validator"
        assert agent.llm_model == "gpt-oss:20b"
        assert agent.llm_provider == "ollama"
        assert agent.llm_url == "http://localhost:11434/api/generate"
        assert agent.temperature == 0.2

    def test_initialization_custom_params(self):
        """Test PlanValidatorAgent initialization with custom parameters."""
        agent = PlanValidatorAgent(
            agent_id="custom_validator",
            llm_model="mistral",
            llm_provider="openai_compatible",
            llm_url="http://custom:8080",
            temperature=0.5,
        )

        assert agent.agent_id == "custom_validator"
        assert agent.llm_model == "mistral"
        assert agent.llm_provider == "openai_compatible"
        assert agent.llm_url == "http://custom:8080"
        assert agent.temperature == 0.5

    def test_extract_query_from_dict(self):
        """Test query extraction from dict context."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {"input": "What is the weather?"}
        query = agent._extract_query(ctx)
        assert query == "What is the weather?"

    def test_extract_query_from_nested_dict(self):
        """Test query extraction from nested dict."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {"input": {"input": "Nested query"}}
        query = agent._extract_query(ctx)
        assert query == "Nested query"

    def test_extract_proposed_path_graphscout(self):
        """Test extracting proposed path from GraphScout output."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {
            "previous_outputs": {
                "graph_scout": {
                    "decision_type": "commit_path",
                    "target": ["agent1", "agent2"],
                    "confidence": 0.9,
                }
            }
        }

        path = agent._extract_proposed_path(ctx)
        assert path["decision_type"] == "commit_path"
        assert path["target"] == ["agent1", "agent2"]

    def test_extract_proposed_path_fallback(self):
        """Test extracting proposed path using fallback logic."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {
            "previous_outputs": {
                "some_planner": {
                    "path": ["step1", "step2"],
                    "decision_type": "commit",
                }
            }
        }

        path = agent._extract_proposed_path(ctx)
        assert "path" in path

    def test_extract_proposed_path_not_found(self):
        """Test handling when no proposed path is found."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {"previous_outputs": {"irrelevant_agent": "data"}}

        path = agent._extract_proposed_path(ctx)
        assert "error" in path
        assert "No proposed path found" in path["error"]

    def test_extract_previous_critiques(self):
        """Test extracting previous critiques from past loops."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {
            "previous_outputs": {
                "past_loops": [
                    {"validation_score": 0.7, "loop_number": 1},
                    {"validation_score": 0.8, "loop_number": 2},
                ]
            }
        }

        critiques = agent._extract_previous_critiques(ctx)
        assert len(critiques) == 2

    def test_extract_previous_critiques_empty(self):
        """Test extracting critiques when none exist."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {"previous_outputs": {}}

        critiques = agent._extract_previous_critiques(ctx)
        assert len(critiques) == 0

    def test_build_validation_prompt(self):
        """Test validation prompt construction."""
        agent = PlanValidatorAgent(agent_id="test")

        query = "Test query"
        proposed_path = {"target": ["agent1"]}
        previous_critiques = []
        loop_number = 1

        prompt = agent._build_validation_prompt(
            query, proposed_path, previous_critiques, loop_number
        )

        assert "**VALIDATION ROUND:** 1" in prompt
        assert "Test query" in prompt
        assert '"target"' in prompt
        assert "completeness" in prompt
        assert "efficiency" in prompt

    def test_build_validation_prompt_with_history(self):
        """Test prompt construction with previous critiques."""
        agent = PlanValidatorAgent(agent_id="test")

        query = "Test query"
        proposed_path = {"target": ["agent1"]}
        previous_critiques = [{"validation_score": 0.7, "assessment": "NEEDS_IMPROVEMENT"}]
        loop_number = 2

        prompt = agent._build_validation_prompt(
            query, proposed_path, previous_critiques, loop_number
        )

        assert "PREVIOUS CRITIQUES:" in prompt
        assert "Round 1:" in prompt

    @pytest.mark.asyncio
    async def test_run_impl_success(self):
        """Test successful validation run."""
        agent = PlanValidatorAgent(agent_id="test")

        mock_critique = {
            "validation_score": 0.85,
            "overall_assessment": "APPROVED",
            "critiques": {},
            "recommended_changes": [],
            "approval_confidence": 0.85,
            "rationale": "Good path",
        }

        ctx = {
            "input": "Test query",
            "previous_outputs": {
                "graph_scout": {"target": ["agent1"]},
            },
            "loop_number": 1,
        }

        with patch.object(llm_client, "call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = json.dumps(mock_critique)

            with patch.object(critique_parser, "parse_critique") as mock_parser:
                mock_parser.return_value = mock_critique

                result = await agent._run_impl(ctx)

                assert result["validation_score"] == 0.85
                assert result["overall_assessment"] == "APPROVED"
                mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impl_llm_failure(self):
        """Test handling LLM call failure."""
        agent = PlanValidatorAgent(agent_id="test")

        ctx = {
            "input": "Test query",
            "previous_outputs": {
                "graph_scout": {"target": ["agent1"]},
            },
            "loop_number": 1,
        }

        with patch.object(llm_client, "call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("Connection failed")

            result = await agent._run_impl(ctx)

            assert result["validation_score"] == 0.0
            assert result["overall_assessment"] == "REJECTED"
            assert "Connection failed" in result["rationale"]

    def test_create_error_critique(self):
        """Test error critique creation."""
        agent = PlanValidatorAgent(agent_id="test")

        critique = agent._create_error_critique("Test error")

        assert critique["validation_score"] == 0.0
        assert critique["overall_assessment"] == "REJECTED"
        assert "Test error" in critique["rationale"]


class TestLLMClient:
    """Test the LLM client module."""

    @pytest.mark.asyncio
    async def test_call_llm_ollama_success(self):
        """Test successful Ollama LLM call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "Generated text"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post") as mock_post:
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                mock_thread.return_value = mock_response

                result = await llm_client.call_llm(
                    prompt="Test",
                    model="test-model",
                    url="http://test",
                    provider="ollama",
                    temperature=0.5,
                )

                assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_call_llm_request_failure(self):
        """Test handling LLM request failure."""
        import requests

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = requests.exceptions.RequestException("Connection error")

            with pytest.raises(RuntimeError, match="Failed to call LLM"):
                await llm_client.call_llm(
                    prompt="Test",
                    model="test",
                    url="http://test",
                    provider="ollama",
                )

    def test_build_ollama_payload(self):
        """Test Ollama payload construction."""
        payload = llm_client._build_ollama_payload("Test prompt", "model", 0.7)

        assert payload["model"] == "model"
        assert payload["prompt"] == "Test prompt"
        assert payload["temperature"] == 0.7
        assert payload["stream"] is False

    def test_build_openai_compatible_payload(self):
        """Test OpenAI-compatible payload construction."""
        payload = llm_client._build_openai_compatible_payload("Test", "model", 0.5)

        assert payload["model"] == "model"
        assert payload["messages"][0]["content"] == "Test"
        assert payload["temperature"] == 0.5


class TestCritiqueParser:
    """Test the critique parser module."""

    def test_parse_critique_valid_json(self):
        """Test parsing valid JSON critique."""
        response = json.dumps(
            {
                "validation_score": 0.85,
                "overall_assessment": "APPROVED",
                "critiques": {},
                "recommended_changes": ["change1"],
                "approval_confidence": 0.9,
                "rationale": "Good",
            }
        )

        result = critique_parser.parse_critique(response)

        assert result["validation_score"] == 0.85
        assert result["overall_assessment"] == "APPROVED"
        assert result["recommended_changes"] == ["change1"]

    def test_parse_critique_json_in_markdown(self):
        """Test parsing JSON from markdown code block."""
        response = """```json
{
    "validation_score": 0.75,
    "overall_assessment": "NEEDS_IMPROVEMENT"
}
```"""

        result = critique_parser.parse_critique(response)

        assert result["validation_score"] == 0.75
        assert result["overall_assessment"] == "NEEDS_IMPROVEMENT"

    def test_parse_critique_fallback(self):
        """Test fallback parsing when JSON extraction fails."""
        response = "VALIDATION_SCORE: 0.6\nSome critique text"

        result = critique_parser.parse_critique(response)

        assert result["validation_score"] == 0.6
        assert "overall_assessment" in result

    def test_extract_json_from_text(self):
        """Test JSON extraction from text."""
        text = 'Some text {"key": "value"} more text'

        result = critique_parser._extract_json_from_text(text)

        assert result == {"key": "value"}

    def test_extract_json_from_text_invalid(self):
        """Test JSON extraction with invalid JSON."""
        text = "No JSON here"

        result = critique_parser._extract_json_from_text(text)

        assert result is None

    def test_extract_score_from_text(self):
        """Test score extraction using regex."""
        text = "validation_score: 0.82"

        score = critique_parser._extract_score_from_text(text)

        assert score == 0.82

    def test_extract_score_from_text_uppercase(self):
        """Test score extraction with uppercase pattern."""
        text = "VALIDATION_SCORE: 0.91"

        score = critique_parser._extract_score_from_text(text)

        assert score == 0.91

    def test_extract_score_from_text_default(self):
        """Test default score when extraction fails."""
        text = "No score here"

        score = critique_parser._extract_score_from_text(text)

        assert score == 0.5

    def test_score_to_assessment(self):
        """Test score to assessment conversion."""
        assert critique_parser._score_to_assessment(0.95) == "APPROVED"
        assert critique_parser._score_to_assessment(0.80) == "NEEDS_IMPROVEMENT"
        assert critique_parser._score_to_assessment(0.60) == "REJECTED"
