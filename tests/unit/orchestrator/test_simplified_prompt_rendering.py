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

