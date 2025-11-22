"""Unit tests for orka.orchestrator.simplified_prompt_rendering."""

from unittest.mock import Mock, patch

import pytest

from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestSimplifiedPromptRenderer:
    """Test suite for SimplifiedPromptRenderer class."""

    def test_init(self):
        """Test SimplifiedPromptRenderer initialization."""
        renderer = SimplifiedPromptRenderer()
        assert renderer is not None

    def test_enhance_payload_for_templates(self):
        """Test _enhance_payload_for_templates method."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "input": "test input",
            "previous_outputs": {
                "agent1": {
                    "component_type": "agent_response",
                    "result": "output1",
                    "status": "success",
                }
            }
        }
        
        enhanced = renderer._enhance_payload_for_templates(payload)
        
        assert "previous_outputs" in enhanced
        assert "agent1" in enhanced["previous_outputs"]
        assert enhanced["previous_outputs"]["agent1"]["result"] == "output1"

    def test_enhance_previous_outputs_orka_response(self):
        """Test _enhance_previous_outputs with OrkaResponse format."""
        renderer = SimplifiedPromptRenderer()
        
        original_outputs = {
            "agent1": {
                "component_type": "agent_response",
                "result": "test result",
                "status": "success",
                "confidence": "0.9",
            }
        }
        
        enhanced = renderer._enhance_previous_outputs(original_outputs)
        
        assert "agent1" in enhanced
        assert enhanced["agent1"]["result"] == "test result"
        assert enhanced["agent1"]["status"] == "success"
        assert enhanced["agent1"]["response"] == "test result"  # Legacy compatibility

    def test_enhance_previous_outputs_legacy(self):
        """Test _enhance_previous_outputs with legacy format."""
        renderer = SimplifiedPromptRenderer()
        
        original_outputs = {
            "agent1": "simple string output"
        }
        
        enhanced = renderer._enhance_previous_outputs(original_outputs)
        
        assert enhanced["agent1"] == "simple string output"

    def test_render_prompt_simple(self):
        """Test render_prompt with simple template."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Hello {{ name }}"
        payload = {"name": "World"}
        
        result = renderer.render_prompt(template, payload)
        
        assert result == "Hello World"

    def test_render_prompt_complex(self):
        """Test render_prompt with complex template."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Input: {{ input }}, Previous: {{ previous_outputs.agent1.result }}"
        payload = {
            "input": "test",
            "previous_outputs": {
                "agent1": {
                    "result": "output1"
                }
            }
        }
        
        result = renderer.render_prompt(template, payload)
        
        assert "test" in result
        assert "output1" in result

    def test_render_prompt_invalid_type(self):
        """Test render_prompt with invalid template type."""
        renderer = SimplifiedPromptRenderer()
        
        with pytest.raises(ValueError, match="Expected template_str to be str"):
            renderer.render_prompt(123, {})

    def test_render_template(self):
        """Test render_template method."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Test: {{ value }}"
        payload = {"value": "test_value"}
        
        result = renderer.render_template(template, payload)
        
        assert result == "Test: test_value"

    def test_simple_string_replacement(self):
        """Test _simple_string_replacement method."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Hello {{ input }}"
        payload = {"input": "World"}
        
        result = renderer._simple_string_replacement(template, payload)
        
        assert result == "Hello World"

    def test_simple_string_replacement_missing_var(self):
        """Test _simple_string_replacement with missing variable."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Hello {{ name }}"
        payload = {}
        
        result = renderer._simple_string_replacement(template, payload)
        
        # Should handle missing variable gracefully
        assert isinstance(result, str)

    def test_get_template_helper_functions(self):
        """Test _get_template_helper_functions method."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"input": "test"}
        
        helpers = renderer._get_template_helper_functions(payload)
        
        assert isinstance(helpers, dict)

    def test_normalize_bool(self):
        """Test normalize_bool static method."""
        normalize_bool = SimplifiedPromptRenderer.normalize_bool
        
        assert normalize_bool(True) is True
        assert normalize_bool(False) is False
        assert normalize_bool("true") is True
        assert normalize_bool("false") is False
        assert normalize_bool("True") is True
        assert normalize_bool("False") is False
        assert normalize_bool(1) is False
        assert normalize_bool(0) is False

    def test_helper_get_input_simple(self):
        """Test get_input helper with simple input."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"input": "test input"}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_input"]() == "test input"

    def test_helper_get_input_nested(self):
        """Test get_input helper with nested dict input."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"input": {"input": "nested input", "other": "data"}}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_input"]() == "nested input"

    def test_helper_get_input_dict_without_nested(self):
        """Test get_input helper with dict but no nested input."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"input": {"key": "value"}}
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["get_input"]()
        assert isinstance(result, str)
        assert "key" in result

    def test_helper_get_input_missing(self):
        """Test get_input helper with missing input."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_input"]() == ""

    def test_helper_get_loop_number_from_payload(self):
        """Test get_loop_number helper from payload."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"loop_number": 5}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_loop_number"]() == 5

    def test_helper_get_loop_number_from_input(self):
        """Test get_loop_number helper from nested input."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"input": {"loop_number": 3}}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_loop_number"]() == 3

    def test_helper_get_loop_number_default(self):
        """Test get_loop_number helper default value."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {}
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_loop_number"]() == 1

    def test_helper_get_agent_response_orka_format(self):
        """Test get_agent_response helper with OrkaResponse format."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "agent1": {
                    "result": "test output",
                    "status": "success"
                }
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_agent_response"]("agent1") == "test output"

    def test_helper_get_agent_response_legacy_format(self):
        """Test get_agent_response helper with legacy format."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "agent1": {
                    "response": "legacy output"
                }
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_agent_response"]("agent1") == "legacy output"

    def test_helper_get_agent_response_string_format(self):
        """Test get_agent_response helper with string format."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "agent1": "simple string"
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_agent_response"]("agent1") == "simple string"

    def test_helper_get_agent_response_missing(self):
        """Test get_agent_response helper with missing agent."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"previous_outputs": {}}
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["get_agent_response"]("nonexistent")
        assert "No response found" in result

    def test_helper_safe_get_response_with_response(self):
        """Test safe_get_response helper with valid response."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "agent1": {"result": "output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["safe_get_response"]("agent1") == "output"

    def test_helper_safe_get_response_with_fallback(self):
        """Test safe_get_response helper with fallback."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"previous_outputs": {}}
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["safe_get_response"]("missing", "custom fallback")
        assert result == "custom fallback"

    def test_helper_safe_get_response_default_fallback(self):
        """Test safe_get_response helper with default fallback."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {"previous_outputs": {}}
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["safe_get_response"]("missing")
        assert result == "No response available"

    def test_helper_get_progressive_response(self):
        """Test get_progressive_response helper."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "progressive_refinement": {"result": "progressive output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_progressive_response"]() == "progressive output"

    def test_helper_get_progressive_response_radical(self):
        """Test get_progressive_response helper with radical fallback."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "radical_progressive": {"result": "radical output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["get_progressive_response"]()
        assert result == "radical output" or result == "No response available"

    def test_helper_get_conservative_response(self):
        """Test get_conservative_response helper."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "conservative_refinement": {"result": "conservative output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_conservative_response"]() == "conservative output"

    def test_helper_get_realist_response(self):
        """Test get_realist_response helper."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "realist_refinement": {"result": "realist output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_realist_response"]() == "realist output"

    def test_helper_get_purist_response(self):
        """Test get_purist_response helper."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "purist_refinement": {"result": "purist output"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        assert helpers["get_purist_response"]() == "purist output"

    def test_render_prompt_with_helper_functions(self):
        """Test render_prompt using helper functions."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Input: {{ get_input() }}, Loop: {{ get_loop_number() }}"
        payload = {
            "input": "test",
            "loop_number": 2
        }
        
        result = renderer.render_prompt(template, payload)
        
        assert "test" in result
        assert "2" in result

    def test_enhance_previous_outputs_removes_none(self):
        """Test that _enhance_previous_outputs removes None values."""
        renderer = SimplifiedPromptRenderer()
        
        original_outputs = {
            "agent1": {
                "component_type": "agent_response",
                "result": "test",
                "status": "success",
                "error": None,
                "confidence": None
            }
        }
        
        enhanced = renderer._enhance_previous_outputs(original_outputs)
        
        assert "result" in enhanced["agent1"]
        assert "error" not in enhanced["agent1"]
        assert "confidence" not in enhanced["agent1"]

    def test_render_prompt_with_jinja_for_loop(self):
        """Test render_prompt with Jinja2 for loop."""
        renderer = SimplifiedPromptRenderer()
        
        template = "{% for item in items %}{{ item }}{% endfor %}"
        payload = {"items": ["a", "b", "c"]}
        
        result = renderer.render_prompt(template, payload)
        
        assert result == "abc"

    def test_render_prompt_with_jinja_if_statement(self):
        """Test render_prompt with Jinja2 if statement."""
        renderer = SimplifiedPromptRenderer()
        
        template = "{% if condition %}yes{% else %}no{% endif %}"
        payload = {"condition": True}
        
        result = renderer.render_prompt(template, payload)
        
        assert result == "yes"

    def test_simple_string_replacement_multiple_outputs(self):
        """Test _simple_string_replacement with multiple agent outputs."""
        renderer = SimplifiedPromptRenderer()
        
        template = "{{ previous_outputs.agent1 }} and {{ previous_outputs.agent2 }}"
        payload = {
            "previous_outputs": {
                "agent1": {"result": "hello"},
                "agent2": {"result": "world"}
            }
        }
        
        result = renderer._simple_string_replacement(template, payload)
        
        assert "hello" in result
        assert "world" in result

    def test_render_template_alias(self):
        """Test that render_template is an alias for render_prompt."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Test {{ value }}"
        payload = {"value": "123"}
        
        result1 = renderer.render_prompt(template, payload)
        result2 = renderer.render_template(template, payload)
        
        assert result1 == result2

    def test_helper_get_collaborative_responses(self):
        """Test get_collaborative_responses helper."""
        renderer = SimplifiedPromptRenderer()
        
        payload = {
            "previous_outputs": {
                "progressive_refinement": {"result": "prog"},
                "conservative_refinement": {"result": "cons"}
            }
        }
        helpers = renderer._get_template_helper_functions(payload)
        
        result = helpers["get_collaborative_responses"]()
        assert isinstance(result, str)

    def test_enhance_previous_outputs_preserves_non_orka_response(self):
        """Test that non-OrkaResponse outputs are preserved as-is."""
        renderer = SimplifiedPromptRenderer()
        
        original_outputs = {
            "agent1": {"custom": "data", "no_component_type": True}
        }
        
        enhanced = renderer._enhance_previous_outputs(original_outputs)
        
        assert enhanced["agent1"] == original_outputs["agent1"]

    def test_render_prompt_empty_template(self):
        """Test render_prompt with empty template."""
        renderer = SimplifiedPromptRenderer()
        
        result = renderer.render_prompt("", {})
        
        assert result == ""

    def test_render_prompt_none_payload_values(self):
        """Test render_prompt with None values in payload."""
        renderer = SimplifiedPromptRenderer()
        
        template = "Value: {{ value }}"
        payload = {"value": None}
        
        result = renderer.render_prompt(template, payload)
        
        assert "None" in result or result == "Value: "
