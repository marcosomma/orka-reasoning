"""
Tests for LoopValidatorNode.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from orka.nodes.loop_validator_node import LoopValidatorNode


class TestLoopValidatorNode:
    """Test suite for LoopValidatorNode."""

    def test_init_with_default_params(self):
        """Test initialization with default parameters."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        assert node.node_id == "validator"
        assert node.llm_model == "gpt-oss:20b"
        assert node.provider == "ollama"
        assert node.scoring_preset == "moderate"
        assert node.temperature == 0.1
        assert node.evaluation_target is None
        assert node.custom_prompt is None
        # Default is loop-focused prompt (IMPROVEMENT/STABILITY/CONVERGENCE)
        assert "IMPROVEMENT" in node.prompt_template.upper() or "better_than_previous" in node.prompt_template

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        custom_prompt = "Custom validation prompt: {content}"
        
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-4",
            provider="openai",
            model_url="https://api.openai.com",
            scoring_preset="strict",
            evaluation_target="agent1",
            temperature=0.2,
            custom_prompt=custom_prompt
        )
        
        assert node.llm_model == "gpt-4"
        assert node.provider == "openai"
        assert node.model_url == "https://api.openai.com"
        assert node.scoring_preset == "strict"
        assert node.evaluation_target == "agent1"
        assert node.temperature == 0.2
        assert node.prompt_template == custom_prompt

    def test_init_with_invalid_preset(self):
        """Test initialization with invalid scoring preset."""
        with pytest.raises(ValueError, match="Invalid scoring_preset"):
            LoopValidatorNode(
                node_id="validator",
                llm_model="gpt-oss:20b",
                provider="ollama",
                scoring_preset="invalid_preset"
            )

    def test_init_with_strict_preset(self):
        """Test initialization with strict preset."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            scoring_preset="strict"
        )
        
        assert "STRICT" in node.prompt_template.upper()
        assert "better_than_previous" in node.prompt_template

    def test_init_with_lenient_preset(self):
        """Test initialization with lenient preset."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            scoring_preset="lenient"
        )
        
        assert node.scoring_preset == "lenient"

    @pytest.mark.asyncio
    async def test_run_impl_success(self):
        """Test successful validation execution."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        # Mock LLM response with valid JSON
        mock_response = {
            "response": json.dumps({
                "improvement": {
                    "better_than_previous": True,
                    "significant_delta": True
                },
                "stability": {
                    "not_degrading": True,
                    "consistent_direction": False
                },
                "convergence": {
                    "delta_decreasing": True,
                    "within_tolerance": False
                }
            })
        }
        
        node.llm_agent.run = AsyncMock(return_value=mock_response)
        
        payload = {"input": "test content"}
        result = await node._run_impl(payload)
        
        assert "boolean_evaluations" in result
        assert "validation_score" in result
        assert "passed_criteria" in result
        assert "failed_criteria" in result
        assert "overall_assessment" in result
        assert isinstance(result["validation_score"], float)
        assert 0.0 <= result["validation_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_run_impl_with_evaluation_target(self):
        """Test validation with specific evaluation target."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            evaluation_target="agent1"
        )
        
        mock_response = {"response": json.dumps({
            "improvement": {"better_than_previous": True},
            "stability": {"not_degrading": True},
            "convergence": {"delta_decreasing": True}
        })}
        
        node.llm_agent.run = AsyncMock(return_value=mock_response)
        
        payload = {
            "input": "test",
            "previous_outputs": {
                "agent1": {"result": "agent1 output"},
                "agent2": {"result": "agent2 output"}
            }
        }
        
        result = await node._run_impl(payload)
        
        assert "boolean_evaluations" in result
        # Verify the prompt was formatted with agent1's output
        node.llm_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impl_error_handling(self):
        """Test error handling in validation execution."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        # Mock LLM to raise exception
        node.llm_agent.run = AsyncMock(side_effect=Exception("LLM error"))
        
        payload = {"input": "test"}
        result = await node._run_impl(payload)
        
        # Should return safe fallback response
        assert result["validation_score"] == 0.0
        assert result["overall_assessment"] == "ERROR"
        assert "error" in result
        assert len(result["failed_criteria"]) > 0

    def test_get_evaluation_content_with_target(self):
        """Test content extraction with evaluation target."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            evaluation_target="agent1"
        )
        
        input_data = {
            "input": "test",
            "previous_outputs": {
                "agent1": {"result": "target output"},
                "agent2": {"result": "other output"}
            }
        }
        
        content = node._get_evaluation_content(input_data)
        
        assert "target output" in content
        assert "other output" not in content

    def test_get_evaluation_content_without_target(self):
        """Test content extraction without evaluation target."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        input_data = {"input": "test input", "key": "value"}
        content = node._get_evaluation_content(input_data)
        
        assert "test input" in content
        assert "key" in content

    def test_get_evaluation_content_with_string_output(self):
        """Test content extraction when target output is a string."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            evaluation_target="agent1"
        )
        
        input_data = {
            "previous_outputs": {
                "agent1": "simple string output"
            }
        }
        
        content = node._get_evaluation_content(input_data)
        assert content == "simple string output"

    def test_extract_response_text_from_string(self):
        """Test response text extraction from string."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        response = "plain text response"
        text = node._extract_response_text(response)
        assert text == "plain text response"

    def test_extract_response_text_from_dict_response_key(self):
        """Test response text extraction from dict with 'response' key."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        response = {"response": "response text"}
        text = node._extract_response_text(response)
        assert text == "response text"

    def test_extract_response_text_from_dict_result_key(self):
        """Test response text extraction from dict with 'result' key."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        response = {"result": "result text"}
        text = node._extract_response_text(response)
        assert text == "result text"

    def test_extract_response_text_from_nested_dict(self):
        """Test response text extraction from nested dict."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        response = {"response": {"response": "nested response"}}
        text = node._extract_response_text(response)
        assert "nested response" in text

    def test_try_json_parse_valid_json(self):
        """Test JSON parsing with valid JSON."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        json_text = json.dumps({
            "improvement": {"better_than_previous": True},
            "stability": {"not_degrading": False},
            "convergence": {"delta_decreasing": True}
        })
        
        result = node._try_json_parse(json_text)
        
        assert result is not None
        assert "improvement" in result
        assert result["improvement"]["better_than_previous"] is True

    def test_try_json_parse_json_in_text(self):
        """Test JSON parsing with JSON embedded in text."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = "Here is the evaluation: " + json.dumps({
            "improvement": {"better_than_previous": True},
            "stability": {"not_degrading": True},
            "convergence": {"delta_decreasing": True}
        }) + " That's all."
        
        result = node._try_json_parse(text)
        
        assert result is not None
        assert "improvement" in result

    def test_try_json_parse_invalid_json(self):
        """Test JSON parsing with invalid JSON."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        result = node._try_json_parse("not valid json at all")
        assert result is None

    def test_try_regex_parse_success(self):
        """Test regex parsing with valid patterns."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = """
        improvement:
        better_than_previous: true
        significant_delta: false
        
        stability:
        not_degrading: true
        """
        
        result = node._try_regex_parse(text)
        
        assert result is not None
        assert "improvement" in result
        assert result["improvement"]["better_than_previous"] is True

    def test_try_regex_parse_various_formats(self):
        """Test regex parsing with various formats."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        # Test with quotes and colons (loop keys)
        text = '"better_than_previous": true'
        result = node._try_regex_parse(text)
        assert result is not None

    def test_try_keyword_parse_success(self):
        """Test keyword parsing with positive indicators."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = """
        The better_than_previous criterion is true
        For significant_delta, the answer is false
        """
        
        result = node._try_keyword_parse(text)
        
        assert result is not None
        assert "improvement" in result

    def test_try_keyword_parse_with_symbols(self):
        """Test keyword parsing with symbols (Y, N)."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = """
        better_than_previous Y
        significant_delta N
        """
        
        result = node._try_keyword_parse(text)
        assert result is not None

    def test_conservative_defaults(self):
        """Test conservative defaults returns all false."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        result = node._conservative_defaults()
        
        # Should reflect loop convergence categories
        assert "improvement" in result
        assert "stability" in result
        assert "convergence" in result
        
        # All values should be False
        for category in result.values():
            assert all(val is False for val in category.values())

    def test_validate_structure_valid(self):
        """Test structure validation with valid data."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        data = {
            "improvement": {"better_than_previous": True},
            "stability": {"not_degrading": True}
        }
        
        assert node._validate_structure(data) is True

    def test_validate_structure_invalid(self):
        """Test structure validation with invalid data."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        # Not a dict
        assert node._validate_structure("not a dict") is False
        
        # No valid categories
        assert node._validate_structure({"invalid": "data"}) is False

    def test_validate_structure_case_insensitive(self):
        """Test structure validation is case-insensitive."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        data = {
            "IMPROVEMENT": {"better_than_previous": True},
            "StAbIlItY": {"not_degrading": True}
        }
        
        assert node._validate_structure(data) is True

    def test_normalize_structure_success(self):
        """Test structure normalization with valid data."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        data = {
            "improvement": {
                "better_than_previous": True,
                "significant_delta": False
            },
            "stability": {
                "not_degrading": "true",
                "consistent_direction": "yes"
            }
        }
        
        result = node._normalize_structure(data)
        
        assert result["improvement"]["better_than_previous"] is True
        assert result["improvement"]["significant_delta"] is False
        assert result["stability"]["not_degrading"] is True
        assert result["stability"]["consistent_direction"] is True

    def test_normalize_structure_case_insensitive(self):
        """Test structure normalization handles case-insensitive keys."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        data = {
            "improvement": {
                "BETTER_THAN_PREVIOUS": True
            }
        }
        
        result = node._normalize_structure(data)
        assert "improvement" in result
        assert result["improvement"]["better_than_previous"] is True

    def test_normalize_structure_missing_category(self):
        """Test structure normalization with missing category."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        data = {
            "improvement": {"better_than_previous": True}
            # Missing other categories
        }
        
        result = node._normalize_structure(data)
        
        # Should have all categories with defaults
        assert "stability" in result
        assert "convergence" in result
        
        # Missing categories should have all false
        assert all(val is False for val in result["convergence"].values())

    def test_format_for_loop_node_success(self):
        """Test formatting output for LoopNode."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        boolean_evals = {
            "completeness": {
                "has_all_required_steps": True,
                "addresses_all_query_aspects": True
            },
            "efficiency": {
                "minimizes_redundant_calls": False,
                "uses_appropriate_agents": True
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": True
            },
            "coherence": {
                "logical_agent_sequence": False,
                "proper_data_flow": True
            }
        }
        
        result = node._format_for_loop_node(boolean_evals)
        
        assert "boolean_evaluations" in result
        assert "validation_score" in result
        assert "passed_criteria" in result
        assert "failed_criteria" in result
        assert "overall_assessment" in result
        
        # 6 passed out of 8 = 0.75
        assert result["validation_score"] == 0.75
        assert len(result["passed_criteria"]) == 6
        assert len(result["failed_criteria"]) == 2
        assert result["overall_assessment"] == "APPROVED"

    def test_format_for_loop_node_rejected(self):
        """Test formatting output with low score (rejected)."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        boolean_evals = {
            "completeness": {
                "has_all_required_steps": False,
                "addresses_all_query_aspects": False
            },
            "efficiency": {
                "minimizes_redundant_calls": False,
                "uses_appropriate_agents": False
            },
            "safety": {
                "validates_inputs": True,
                "handles_errors_gracefully": False
            },
            "coherence": {
                "logical_agent_sequence": False,
                "proper_data_flow": False
            }
        }
        
        result = node._format_for_loop_node(boolean_evals)
        
        # Only 1 passed out of 8 = 0.125
        assert result["validation_score"] < 0.7
        assert result["overall_assessment"] == "REJECTED"
    def test_path_mode_uses_path_prompts(self):
        """Ensure LoopValidatorNode can operate in 'path' mode for backward compatibility."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            mode="path",
            scoring_preset="strict",
        )

        # Path mode prompt should include path-specific criteria
        assert "has_all_required_steps" in node.prompt_template
        # The active criteria structure should reflect path mode
        assert "completeness" in node.criteria_structure

    def test_scoring_context_overrides_mode_to_path(self):
        """scoring_context='graphscout' should select path criteria even with default mode."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            scoring_context="graphscout",
            scoring_preset="moderate",
        )
        assert node.effective_mode == "path"
        assert "has_all_required_steps" in node.prompt_template
        # Also ensure the effective dynamic criteria structure is path-based
        assert "completeness" in node.criteria_structure

    def test_scoring_context_overrides_mode_to_loop(self):
        """scoring_context='loop_convergence' should select loop criteria."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama",
            scoring_context="loop_convergence",
            scoring_preset="lenient",
        )
        assert node.effective_mode == "loop"
        assert "better_than_previous" in node.prompt_template
        # The effective dynamic criteria structure should reflect loop convergence
        assert "improvement" in node.criteria_structure
    def test_safe_fallback_response(self):
        """Test safe fallback response on error."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        error_msg = "Test error message"
        result = node._safe_fallback_response(error_msg)
        
        assert result["validation_score"] == 0.0
        assert result["overall_assessment"] == "ERROR"
        assert result["error"] == error_msg
        assert len(result["passed_criteria"]) == 0
        assert len(result["failed_criteria"]) > 0
        assert "boolean_evaluations" in result

    def test_parse_with_fallbacks_json_first(self):
        """Test parse_with_fallbacks tries JSON first."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        json_text = json.dumps({
            "improvement": {"better_than_previous": True},
            "stability": {"not_degrading": True},
            "convergence": {"delta_decreasing": True}
        })

        result = node._parse_with_fallbacks(json_text)

        assert result is not None
        assert "improvement" in result
    def test_parse_with_fallbacks_regex_second(self):
        """Test parse_with_fallbacks falls back to regex."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = "has_all_required_steps: true\nminimizes_redundant_calls: false"
        result = node._parse_with_fallbacks(text)
        
        assert result is not None

    def test_parse_with_fallbacks_keyword_third(self):
        """Test parse_with_fallbacks falls back to keyword detection."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = "The has_all_required_steps is yes"
        result = node._parse_with_fallbacks(text)
        
        assert result is not None

    def test_parse_with_fallbacks_conservative_last(self):
        """Test parse_with_fallbacks uses conservative defaults as last resort."""
        node = LoopValidatorNode(
            node_id="validator",
            llm_model="gpt-oss:20b",
            provider="ollama"
        )
        
        text = "completely unparseable gibberish text"
        result = node._parse_with_fallbacks(text)
        
        assert result is not None
        # Should be all false
        assert all(
            all(val is False for val in category.values())
            for category in result.values()
        )
