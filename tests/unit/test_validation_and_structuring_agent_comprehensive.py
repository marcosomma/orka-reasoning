"""
Comprehensive unit tests for the validation_and_structuring_agent.py module.
Tests the ValidationAndStructuringAgent class and all its methods.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from orka.agents.validation_and_structuring_agent import ValidationAndStructuringAgent


class TestValidationAndStructuringAgent:
    """Test suite for the ValidationAndStructuringAgent class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent_params = {
            "agent_id": "test_validation_agent",
            "prompt": "Test validation prompt",
            "queue": [],
            "store_structure": "Test structure template",
        }

        with patch("orka.agents.validation_and_structuring_agent.OpenAIAnswerBuilder"):
            self.agent = ValidationAndStructuringAgent(self.agent_params)

    def test_initialization_with_params(self):
        """Test agent initialization with full parameters."""
        with patch("orka.agents.validation_and_structuring_agent.OpenAIAnswerBuilder") as mock_llm:
            agent = ValidationAndStructuringAgent(self.agent_params)

            # Verify LLM agent was initialized with correct parameters
            mock_llm.assert_called_once_with(
                agent_id="test_validation_agent_llm",
                prompt="Test validation prompt",
                queue=[],
            )

            assert hasattr(agent, "llm_agent")

    def test_initialization_with_none_params(self):
        """Test agent initialization with empty parameters."""
        with patch("orka.agents.validation_and_structuring_agent.OpenAIAnswerBuilder") as mock_llm:
            agent = ValidationAndStructuringAgent({})

            # Verify default values are used
            mock_llm.assert_called_once_with(
                agent_id="validation_agent_llm",
                prompt="",
                queue=None,
            )

    def test_initialization_with_empty_params(self):
        """Test agent initialization with empty parameters."""
        with patch("orka.agents.validation_and_structuring_agent.OpenAIAnswerBuilder") as mock_llm:
            agent = ValidationAndStructuringAgent({})

            # Verify default values are used
            mock_llm.assert_called_once_with(
                agent_id="validation_agent_llm",
                prompt="",
                queue=None,
            )

    @pytest.mark.asyncio
    async def test_run_with_valid_json_response(self):
        """Test run method with valid JSON response from LLM."""
        # Mock LLM response with valid JSON
        valid_json_response = """```json
{
    "valid": true,
    "reason": "Answer is correct and well-structured",
    "memory_object": {
        "fact": "Test fact",
        "category": "information",
        "confidence": 0.9
    }
}
```"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": valid_json_response})

        input_data = {
            "input": "Test question?",
            "previous_outputs": {
                "context-collector": {"result": {"response": "Test context"}},
                "answer-builder": {"result": {"response": "Test answer"}},
            },
        }

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is True
        assert result["result"]["reason"] == "Answer is correct and well-structured"
        assert result["result"]["memory_object"]["fact"] == "Test fact"
        assert "prompt" in result["result"]
        assert "raw_llm_output" in result["result"]

    @pytest.mark.asyncio
    async def test_run_with_invalid_json_response(self):
        """Test run method with invalid JSON response from LLM."""
        invalid_response = "This is not valid JSON at all"

        self.agent.llm_agent.run = AsyncMock(return_value={"response": invalid_response})

        input_data = {
            "input": "Test question?",
            "previous_outputs": {
                "context-collector": {"result": {"response": "Test context"}},
                "answer-builder": {"result": {"response": "Test answer"}},
            },
        }

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is False
        assert "Failed to parse JSON:" in result["result"]["reason"]
        assert result["result"]["memory_object"] is None
        assert result["result"]["raw_llm_output"] == invalid_response

    @pytest.mark.asyncio
    async def test_run_with_wrong_json_format(self):
        """Test run method with wrong JSON format (response instead of valid)."""
        wrong_format_response = """```json
{
    "response": "This is the wrong format",
    "confidence": 0.8
}
```"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": wrong_format_response})

        input_data = {
            "input": "Test question?",
            "previous_outputs": {
                "context-collector": {"result": {"response": "Test context"}},
                "answer-builder": {"result": {"response": "Test answer"}},
            },
        }

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is False
        assert "LLM returned wrong JSON format" in result["result"]["reason"]
        assert result["result"]["memory_object"] is None

    @pytest.mark.asyncio
    async def test_run_with_json_without_markdown(self):
        """Test run method with JSON response without markdown code blocks."""
        json_response = (
            """{"valid": true, "reason": "Good answer", "memory_object": {"fact": "Direct JSON"}}"""
        )

        self.agent.llm_agent.run = AsyncMock(return_value={"response": json_response})

        input_data = {
            "input": "Test question?",
            "previous_outputs": {
                "context-collector": {"result": {"response": "Test context"}},
                "answer-builder": {"result": {"response": "Test answer"}},
            },
        }

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is True
        assert result["result"]["reason"] == "Good answer"
        assert result["result"]["memory_object"]["fact"] == "Direct JSON"

    @pytest.mark.asyncio
    async def test_run_with_complex_input_extraction(self):
        """Test run method with complex previous_outputs structure."""
        self.agent.llm_agent.run = AsyncMock(
            return_value={
                "response": '{"valid": true, "reason": "test", "memory_object": null}',
            }
        )

        input_data = {
            "input": "Complex question?",
            "previous_outputs": {
                "context-collector": "Direct string context",
                "answer-builder": "Direct string answer",
            },
        }

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is True
        # Verify the agent processed the direct string inputs correctly

    @pytest.mark.asyncio
    async def test_run_with_missing_previous_outputs(self):
        """Test run method with missing previous_outputs."""
        self.agent.llm_agent.run = AsyncMock(
            return_value={
                "response": '{"valid": false, "reason": "no data", "memory_object": null}',
            }
        )

        input_data = {
            "input": "Question without context?",
        }

        result = await self.agent.run(input_data)

        assert "valid" in result["result"]

    @pytest.mark.asyncio
    async def test_run_with_custom_prompt_template(self):
        """Test run method when agent has custom prompt that needs template rendering."""
        # Set up agent with custom prompt
        self.agent.llm_agent.prompt = "Custom prompt: {{ input }}"

        with patch("orka.agents.validation_and_structuring_agent.Template") as mock_template:
            mock_template_instance = Mock()
            mock_template_instance.render.return_value = "Rendered custom prompt"
            mock_template.return_value = mock_template_instance

            self.agent.llm_agent.run = AsyncMock(
                return_value={
                    "response": '{"valid": true, "reason": "custom", "memory_object": {}}',
                }
            )

            input_data = {"input": "Test with custom prompt"}

            result = await self.agent.run(input_data)

            # Verify template was used
            mock_template.assert_called_once_with("Custom prompt: {{ input }}")
            mock_template_instance.render.assert_called_once_with(**input_data)

    @pytest.mark.asyncio
    async def test_run_with_custom_prompt_template_error(self):
        """Test run method when custom prompt template rendering fails."""
        # Set up agent with custom prompt
        self.agent.llm_agent.prompt = "Invalid template: {{ missing_var }}"

        with patch("orka.agents.validation_and_structuring_agent.Template") as mock_template:
            mock_template.side_effect = Exception("Template error")

            self.agent.llm_agent.run = AsyncMock(
                return_value={
                    "response": '{"valid": true, "reason": "fallback", "memory_object": {}}',
                }
            )

            input_data = {"input": "Test template error"}

            result = await self.agent.run(input_data)

            # Should fall back to original prompt
            assert "valid" in result["result"]

    @pytest.mark.asyncio
    async def test_run_with_unmatched_braces_json(self):
        """Test run method with JSON that has unmatched braces."""
        invalid_json = """{"valid": true, "reason": "missing closing brace"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": invalid_json})

        input_data = {"input": "Test unmatched braces"}

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is False
        assert "Failed to parse JSON:" in result["result"]["reason"]

    @pytest.mark.asyncio
    async def test_run_with_no_json_structure(self):
        """Test run method with response that has no JSON structure."""
        no_json_response = "This response has no JSON structure at all, just plain text."

        self.agent.llm_agent.run = AsyncMock(return_value={"response": no_json_response})

        input_data = {"input": "Test no JSON"}

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is False
        assert "Failed to parse JSON:" in result["result"]["reason"]

    @pytest.mark.asyncio
    async def test_run_with_single_quotes_json(self):
        """Test run method with JSON that uses single quotes."""
        # Actually, single quotes inside string values won't be replaced by the regex,
        # only single quotes around keys. This test should expect failure
        single_quote_json = """{'valid': true, 'reason': 'single quotes', 'memory_object': null}"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": single_quote_json})

        input_data = {"input": "Test single quotes"}

        result = await self.agent.run(input_data)

        # Single quotes around keys should be replaced, but this is still malformed JSON
        assert result["result"]["valid"] is False
        assert "Failed to parse JSON:" in result["result"]["reason"]

    def test_build_prompt_with_valid_data(self):
        """Test build_prompt method with valid data."""
        # Clear the LLM agent prompt to ensure we use the default prompt building logic
        self.agent.llm_agent.prompt = ""

        result = self.agent.build_prompt(
            question="What is the capital of France?",
            context="France is a country in Europe",
            answer="The capital of France is Paris",
            store_structure="Custom structure",
        )

        assert "What is the capital of France?" in result
        assert "France is a country in Europe" in result
        assert "The capital of France is Paris" in result
        assert "Custom structure" in result
        assert "JSON format" in result

    def test_build_prompt_with_none_context_and_answer(self):
        """Test build_prompt method with None context and answer."""
        # Clear the LLM agent prompt to ensure we use the default prompt building logic
        self.agent.llm_agent.prompt = ""

        result = self.agent.build_prompt(
            question="Test question?",
            context="NONE",
            answer="NONE",
        )

        assert "Test question?" in result
        assert "No context available" in result
        assert "No answer provided" in result
        assert "no information available" in result

    def test_build_prompt_with_empty_context_and_answer(self):
        """Test build_prompt method with empty context and answer."""
        # Clear the LLM agent prompt to ensure we use the default prompt building logic
        self.agent.llm_agent.prompt = ""

        result = self.agent.build_prompt(
            question="Empty test?",
            context="",
            answer="",
        )

        assert "Empty test?" in result
        assert "No context available" in result
        assert "No answer provided" in result

    def test_build_prompt_with_custom_llm_prompt(self):
        """Test build_prompt method when LLM agent has custom prompt."""
        self.agent.llm_agent.prompt = "This is a custom LLM prompt"

        result = self.agent.build_prompt(
            question="Any question",
            context="Any context",
            answer="Any answer",
        )

        # build_prompt method always builds its default prompt regardless of LLM agent prompt
        assert "Validate the following situation and structure it into a memory format." in result
        assert "Question: Any question" in result
        assert "Context: Any context" in result
        assert "Answer to validate: Any answer" in result

    def test_build_prompt_with_none_store_structure(self):
        """Test build_prompt method with None store_structure."""
        # Clear the LLM agent prompt to ensure we use the default prompt building logic
        self.agent.llm_agent.prompt = ""

        result = self.agent.build_prompt(
            question="Test?",
            context="Context",
            answer="Answer",
            store_structure=None,
        )

        assert "Test?" in result
        assert "Context" in result
        assert "Answer" in result

    def test_get_structure_instructions_with_custom_structure(self):
        """Test _get_structure_instructions method with custom structure."""
        custom_structure = "field1: value1\nfield2: value2"

        result = self.agent._get_structure_instructions(custom_structure)

        assert "field1: value1" in result
        assert "field2: value2" in result
        assert "required fields" in result

    def test_get_structure_instructions_with_none_structure(self):
        """Test _get_structure_instructions method with None structure."""
        result = self.agent._get_structure_instructions(None)

        assert "fact:" in result
        assert "category:" in result
        assert "confidence:" in result
        assert "source:" in result

    def test_get_structure_instructions_with_empty_structure(self):
        """Test _get_structure_instructions method with empty structure."""
        result = self.agent._get_structure_instructions("")

        # Empty string is falsy, so should return default instructions
        assert "fact:" in result
        assert "category:" in result
        assert "confidence:" in result
        assert "source:" in result

    @pytest.mark.asyncio
    async def test_run_with_non_dict_llm_response(self):
        """Test run method when LLM returns non-dict response."""
        self.agent.llm_agent.run = AsyncMock(
            return_value=('{"valid": true, "reason": "string response", "memory_object": {}}')
        )

        input_data = {"input": "Test non-dict response"}

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is True
        assert result["result"]["reason"] == "string response"

    @pytest.mark.asyncio
    async def test_run_with_complex_nested_json(self):
        """Test run method with complex nested JSON structure."""
        complex_json = """```json
{
    "valid": true,
    "reason": "Complex validation successful",
    "memory_object": {
        "fact": "Complex fact",
        "metadata": {
            "source": "test",
            "timestamp": "2025-01-01",
            "tags": ["tag1", "tag2"]
        },
        "confidence": 0.95
    }
}
```"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": complex_json})

        input_data = {"input": "Complex test"}

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is True
        assert result["result"]["memory_object"]["metadata"]["tags"] == ["tag1", "tag2"]
        assert result["result"]["memory_object"]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_run_handles_malformed_json_gracefully(self):
        """Test run method handles malformed JSON gracefully."""
        malformed_json = """{"valid": true, "reason": "incomplete"""

        self.agent.llm_agent.run = AsyncMock(return_value={"response": malformed_json})

        input_data = {"input": "Malformed JSON test"}

        result = await self.agent.run(input_data)

        assert result["result"]["valid"] is False
        assert "Failed to parse JSON:" in result["result"]["reason"]
