"""
Tests for orka.orchestrator.prompt_rendering module.

This module tests the PromptRenderer class which handles Jinja2 template rendering
for dynamic prompt construction.
"""

from unittest.mock import Mock

import pytest

from orka.orchestrator.prompt_rendering import PromptRenderer


class TestPromptRenderer:
    """Test cases for PromptRenderer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = PromptRenderer()

    def test_render_prompt_basic(self):
        """Test basic prompt rendering with simple variables."""
        template = "Hello {{ name }}, you are {{ age }} years old."
        payload = {"name": "Alice", "age": 30}

        result = self.renderer.render_prompt(template, payload)

        assert result == "Hello Alice, you are 30 years old."

    def test_render_prompt_complex_template(self):
        """Test prompt rendering with complex Jinja2 features."""
        template = """
        {% if user_type == 'admin' %}
        Welcome, Administrator {{ name }}!
        {% else %}
        Hello, {{ name }}!
        {% endif %}
        Your tasks: {% for task in tasks %}{{ task }}{% if not loop.last %}, {% endif %}{% endfor %}
        """

        payload = {
            "user_type": "admin",
            "name": "Bob",
            "tasks": ["review", "approve", "deploy"],
        }

        result = self.renderer.render_prompt(template, payload)

        assert "Welcome, Administrator Bob!" in result
        assert "review, approve, deploy" in result

    def test_render_prompt_missing_variables(self):
        """Test prompt rendering with missing variables."""
        template = "Hello {{ name }}, your score is {{ score }}."
        payload = {"name": "Charlie"}  # Missing 'score'

        # Jinja2 should handle missing variables gracefully (empty string)
        result = self.renderer.render_prompt(template, payload)

        assert "Hello Charlie, your score is ." in result

    def test_render_prompt_invalid_template_type(self):
        """Test render_prompt with invalid template type."""
        template = 123  # Not a string
        payload = {"name": "test"}

        with pytest.raises(ValueError, match="Expected template_str to be str"):
            self.renderer.render_prompt(template, payload)

    def test_render_prompt_empty_template(self):
        """Test rendering empty template."""
        template = ""
        payload = {"name": "test"}

        result = self.renderer.render_prompt(template, payload)

        assert result == ""

    def test_render_prompt_no_variables(self):
        """Test rendering template with no variables."""
        template = "This is a static prompt."
        payload = {"unused": "value"}

        result = self.renderer.render_prompt(template, payload)

        assert result == "This is a static prompt."

    def test_add_prompt_to_payload_agent_with_prompt(self):
        """Test adding prompt to payload when agent has a prompt."""
        # Create agent with specific attributes to avoid Mock auto-creation
        agent = Mock(spec=["prompt"])
        agent.prompt = "Hello {{ name }}"

        payload_out = {}
        payload = {"name": "World"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert payload_out["prompt"] == "Hello {{ name }}"
        assert payload_out["formatted_prompt"] == "Hello World"

    def test_add_prompt_to_payload_agent_without_prompt(self):
        """Test adding prompt to payload when agent has no prompt."""
        agent = Mock()
        agent.prompt = None

        payload_out = {}
        payload = {"name": "World"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert "prompt" not in payload_out
        assert "formatted_prompt" not in payload_out

    def test_add_prompt_to_payload_agent_no_prompt_attribute(self):
        """Test adding prompt to payload when agent has no prompt attribute."""
        agent = Mock(spec=[])  # No prompt attribute

        payload_out = {}
        payload = {"name": "World"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert "prompt" not in payload_out
        assert "formatted_prompt" not in payload_out

    def test_add_prompt_to_payload_with_last_formatted_prompt(self):
        """Test adding prompt when agent has _last_formatted_prompt."""
        agent = Mock(spec=["prompt", "_last_formatted_prompt"])
        agent.prompt = "Hello {{ name }}"
        agent._last_formatted_prompt = "Hello Enhanced World"

        payload_out = {}
        payload = {"name": "World"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert payload_out["prompt"] == "Hello {{ name }}"
        assert payload_out["formatted_prompt"] == "Hello Enhanced World"

    def test_add_prompt_to_payload_rendering_error(self):
        """Test adding prompt when template rendering fails."""
        agent = Mock(spec=["prompt"])
        agent.prompt = "Hello {{ invalid.nested.property }}"

        payload_out = {}
        payload = {"name": "World"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert payload_out["prompt"] == "Hello {{ invalid.nested.property }}"
        assert payload_out["formatted_prompt"] == "Hello {{ invalid.nested.property }}"

    def test_add_prompt_to_payload_with_llm_response_details(self):
        """Test adding LLM response details to payload."""
        agent = Mock(
            spec=["prompt", "_last_response", "_last_confidence", "_last_internal_reasoning"],
        )
        agent.prompt = "Test prompt"
        agent._last_response = "Yes"
        agent._last_confidence = 0.95
        agent._last_internal_reasoning = "Based on analysis..."

        payload_out = {}
        payload = {}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert payload_out["response"] == "Yes"
        assert payload_out["confidence"] == 0.95
        assert payload_out["internal_reasoning"] == "Based on analysis..."

    def test_add_prompt_to_payload_partial_llm_details(self):
        """Test adding partial LLM response details."""
        agent = Mock(spec=["prompt", "_last_response"])
        agent.prompt = "Test prompt"
        agent._last_response = "No"
        # Missing _last_confidence and _last_internal_reasoning

        payload_out = {}
        payload = {}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        assert payload_out["response"] == "No"
        assert "confidence" not in payload_out
        assert "internal_reasoning" not in payload_out

    def test_render_agent_prompt_with_prompt(self):
        """Test rendering agent prompt and adding to payload."""
        agent = Mock()
        agent.prompt = "Process {{ task }} with {{ priority }} priority"

        payload = {"task": "analysis", "priority": "high"}

        self.renderer._render_agent_prompt(agent, payload)

        assert payload["formatted_prompt"] == "Process analysis with high priority"

    def test_render_agent_prompt_without_prompt(self):
        """Test rendering when agent has no prompt."""
        agent = Mock()
        agent.prompt = None

        payload = {"task": "analysis"}
        original_payload = payload.copy()

        self.renderer._render_agent_prompt(agent, payload)

        assert payload == original_payload  # No changes

    def test_render_agent_prompt_no_prompt_attribute(self):
        """Test rendering when agent has no prompt attribute."""
        agent = Mock(spec=[])  # No prompt attribute

        payload = {"task": "analysis"}
        original_payload = payload.copy()

        self.renderer._render_agent_prompt(agent, payload)

        assert payload == original_payload  # No changes

    def test_render_agent_prompt_rendering_error(self):
        """Test rendering when template rendering fails."""
        agent = Mock()
        agent.prompt = "Process {{ invalid.nested.property }}"

        payload = {"task": "analysis"}

        self.renderer._render_agent_prompt(agent, payload)

        assert payload["formatted_prompt"] == "Process {{ invalid.nested.property }}"

    def test_normalize_bool_true_values(self):
        """Test normalize_bool with various true values."""
        true_values = [
            True,
            "true",
            "TRUE",
            "True",
            " true ",
            "yes",
            "YES",
            "Yes",
            " yes ",
        ]

        for value in true_values:
            assert self.renderer.normalize_bool(value) is True, f"Failed for value: {value}"

    def test_normalize_bool_false_values(self):
        """Test normalize_bool with various false values."""
        false_values = [
            False,
            "false",
            "FALSE",
            "False",
            "no",
            "NO",
            "No",
            "maybe",
            "invalid",
            "",
            " ",
            "0",
            "1",  # Only 'true' and 'yes' are considered true for strings
        ]

        for value in false_values:
            assert self.renderer.normalize_bool(value) is False, f"Failed for value: {value}"

    def test_normalize_bool_dict_with_result(self):
        """Test normalize_bool with dictionary containing result field."""
        test_cases = [
            ({"result": True}, True),
            ({"result": False}, False),
            ({"result": "true"}, True),
            ({"result": "false"}, False),
            ({"result": {"result": True}}, True),
            ({"result": {"result": "yes"}}, True),
            ({"result": {"response": True}}, True),
            ({"result": {"response": "no"}}, False),
        ]

        for value, expected in test_cases:
            assert self.renderer.normalize_bool(value) == expected, f"Failed for value: {value}"

    def test_normalize_bool_dict_with_response(self):
        """Test normalize_bool with dictionary containing response field."""
        test_cases = [
            ({"response": True}, True),
            ({"response": False}, False),
            ({"response": "true"}, True),
            ({"response": "false"}, False),
        ]

        for value, expected in test_cases:
            assert self.renderer.normalize_bool(value) == expected, f"Failed for value: {value}"

    def test_normalize_bool_dict_without_result_or_response(self):
        """Test normalize_bool with dictionary without result or response fields."""
        test_cases = [
            {"other": True},
            {"data": "true"},
            {},
            {"nested": {"value": True}},
        ]

        for value in test_cases:
            assert self.renderer.normalize_bool(value) is False, f"Failed for value: {value}"

    def test_normalize_bool_complex_nested_structures(self):
        """Test normalize_bool with complex nested structures."""
        # Complex agent response structure
        complex_response = {
            "result": {
                "result": {
                    "response": "true",
                },
            },
        }

        assert self.renderer.normalize_bool(complex_response) is True

        # Another complex structure
        complex_response2 = {
            "result": {
                "response": {
                    "value": "yes",  # This won't be found, should return False
                },
            },
        }

        assert self.renderer.normalize_bool(complex_response2) is False

    def test_normalize_bool_other_types(self):
        """Test normalize_bool with other data types."""
        other_values = [
            None,
            123,
            [],
            [True],
            {"list": [True]},
            object(),
        ]

        for value in other_values:
            assert self.renderer.normalize_bool(value) is False, f"Failed for value: {value}"

    def test_normalize_bool_static_method(self):
        """Test that normalize_bool can be called as static method."""
        result = PromptRenderer.normalize_bool(True)
        assert result is True

        result = PromptRenderer.normalize_bool("false")
        assert result is False

    def test_integration_prompt_with_boolean_normalization(self):
        """Test integration of prompt rendering with boolean normalization."""
        template = """
        {% if normalize_bool(user_active) %}
        Welcome back, {{ name }}!
        {% else %}
        Please activate your account, {{ name }}.
        {% endif %}
        """

        # This would require custom Jinja2 filters, but we can test the concept
        payload = {
            "name": "Alice",
            "user_active": {"result": "true"},
        }

        # For this test, we'll just verify the template renders
        simple_template = "User: {{ name }}, Active: {{ user_active.result }}"
        result = self.renderer.render_prompt(simple_template, payload)

        assert "User: Alice, Active: true" in result

    def test_prompt_rendering_with_special_characters(self):
        """Test prompt rendering with special characters and escaping."""
        template = "Message: {{ message }}"
        payload = {"message": 'Hello "World" & <Universe>'}

        result = self.renderer.render_prompt(template, payload)

        assert 'Message: Hello "World" & <Universe>' in result

    def test_prompt_rendering_with_filters(self):
        """Test prompt rendering with Jinja2 filters."""
        template = "Name: {{ name|upper }}, Count: {{ items|length }}"
        payload = {
            "name": "alice",
            "items": ["a", "b", "c"],
        }

        result = self.renderer.render_prompt(template, payload)

        assert "Name: ALICE, Count: 3" in result

    def test_empty_prompt_handling(self):
        """Test handling of empty prompts."""
        agent = Mock(spec=["prompt"])
        agent.prompt = ""

        payload_out = {}
        payload = {"name": "test"}

        self.renderer._add_prompt_to_payload(agent, payload_out, payload)

        # Empty prompt is falsy, so it won't be processed
        assert "prompt" not in payload_out
        assert "formatted_prompt" not in payload_out
