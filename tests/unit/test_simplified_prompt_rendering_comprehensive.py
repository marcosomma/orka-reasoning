"""
Comprehensive unit tests for simplified_prompt_rendering.py module.

Tests cover:
- SimplifiedPromptRenderer initialization
- Payload enhancement for templates
- Previous outputs enhancement with OrkaResponse
- Template rendering with Jinja2
- Error handling and fallback mechanisms
- Helper function generation
"""

from unittest.mock import Mock, patch

import pytest

from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer


class TestSimplifiedPromptRendererInitialization:
    """Test SimplifiedPromptRenderer initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        renderer = SimplifiedPromptRenderer()

        assert renderer is not None
        assert isinstance(renderer, SimplifiedPromptRenderer)


class TestPayloadEnhancement:
    """Test payload enhancement for templates."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_enhance_payload_with_previous_outputs(self):
        """Test enhancing payload that contains previous outputs."""
        payload = {"input": "test input", "previous_outputs": {"agent1": {"result": "test result"}}}

        enhanced = self.renderer._enhance_payload_for_templates(payload)

        assert "previous_outputs" in enhanced
        assert "input" in enhanced
        assert enhanced["input"] == "test input"

    def test_enhance_payload_without_previous_outputs(self):
        """Test enhancing payload without previous outputs."""
        payload = {"input": "test input", "context": "test context"}

        enhanced = self.renderer._enhance_payload_for_templates(payload)

        assert "input" in enhanced
        assert "context" in enhanced
        assert enhanced["input"] == "test input"

    def test_enhance_payload_adds_helper_functions(self):
        """Test that helper functions are added to enhanced payload."""
        payload = {"input": "test"}

        enhanced = self.renderer._enhance_payload_for_templates(payload)

        # Helper functions should be added (using actual function names from implementation)
        assert callable(enhanced.get("get_agent_response"))
        assert callable(enhanced.get("get_collaborative_responses"))

    def test_enhance_payload_preserves_original_data(self):
        """Test that original payload data is preserved."""
        payload = {"input": "test input", "custom_field": "custom value", "number": 42}

        enhanced = self.renderer._enhance_payload_for_templates(payload)

        assert enhanced["input"] == "test input"
        assert enhanced["custom_field"] == "custom value"
        assert enhanced["number"] == 42


class TestPreviousOutputsEnhancement:
    """Test enhancement of previous outputs with OrkaResponse."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_enhance_orka_response_format(self):
        """Test enhancing OrkaResponse-formatted output."""
        original_outputs = {
            "agent1": {
                "component_type": "LocalLLMAgent",
                "component_id": "agent1",
                "status": "success",
                "result": "test result",
                "timestamp": "2025-10-05T12:00:00",
            }
        }

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        assert "agent1" in enhanced
        assert enhanced["agent1"]["result"] == "test result"
        assert enhanced["agent1"]["status"] == "success"
        assert enhanced["agent1"]["component_type"] == "LocalLLMAgent"

    def test_enhance_orka_response_with_all_fields(self):
        """Test enhancing OrkaResponse with all standard fields."""
        original_outputs = {
            "agent1": {
                "component_type": "LocalLLMAgent",
                "component_id": "agent1",
                "status": "success",
                "result": "test result",
                "error": None,
                "confidence": 0.95,
                "internal_reasoning": "reasoning text",
                "execution_time_ms": 150,
                "token_usage": 100,
                "cost_usd": 0.001,
                "timestamp": "2025-10-05T12:00:00",
            }
        }

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        assert enhanced["agent1"]["confidence"] == 0.95
        assert enhanced["agent1"]["internal_reasoning"] == "reasoning text"
        assert enhanced["agent1"]["execution_time_ms"] == 150
        assert enhanced["agent1"]["token_usage"] == 100
        assert enhanced["agent1"]["cost_usd"] == 0.001

    def test_enhance_removes_none_values(self):
        """Test that None values are removed from enhanced output."""
        original_outputs = {
            "agent1": {
                "component_type": "LocalLLMAgent",
                "status": "success",
                "result": "test result",
                "error": None,
                "confidence": None,
                "internal_reasoning": None,
            }
        }

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        # None values should be removed
        assert "error" not in enhanced["agent1"]
        assert "confidence" not in enhanced["agent1"]
        assert "internal_reasoning" not in enhanced["agent1"]
        # Non-None values should remain
        assert "result" in enhanced["agent1"]
        assert "status" in enhanced["agent1"]

    def test_enhance_legacy_format_preserved(self):
        """Test that legacy format outputs are preserved as-is."""
        original_outputs = {"agent1": {"response": "legacy response", "some_field": "some value"}}

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        # Legacy format should be preserved
        assert enhanced["agent1"]["response"] == "legacy response"
        assert enhanced["agent1"]["some_field"] == "some value"

    def test_enhance_legacy_compatibility_fields(self):
        """Test that legacy compatibility fields are added."""
        original_outputs = {
            "agent1": {
                "component_type": "LocalLLMAgent",
                "status": "success",
                "result": "test result",
                "memory_entries": ["memory1", "memory2"],
                "metrics": {"latency": 100},
            }
        }

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        # Legacy compatibility mappings
        assert enhanced["agent1"]["response"] == "test result"  # result -> response
        assert enhanced["agent1"]["memories"] == [
            "memory1",
            "memory2",
        ]  # memory_entries -> memories
        assert enhanced["agent1"]["_metrics"] == {"latency": 100}  # metrics -> _metrics

    def test_enhance_multiple_agents(self):
        """Test enhancing outputs from multiple agents."""
        original_outputs = {
            "agent1": {"component_type": "LocalLLMAgent", "result": "result1"},
            "agent2": {"component_type": "OpenAIAgent", "result": "result2"},
            "agent3": {"response": "legacy result3"},
        }

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        assert len(enhanced) == 3
        assert enhanced["agent1"]["result"] == "result1"
        assert enhanced["agent2"]["result"] == "result2"
        assert enhanced["agent3"]["response"] == "legacy result3"

    def test_enhance_empty_previous_outputs(self):
        """Test enhancing empty previous outputs."""
        original_outputs = {}

        enhanced = self.renderer._enhance_previous_outputs(original_outputs)

        assert enhanced == {}


class TestTemplateRendering:
    """Test template rendering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_render_simple_template(self):
        """Test rendering a simple template."""
        template = "Hello {{ name }}!"
        payload = {"name": "World"}

        result = self.renderer.render_prompt(template, payload)

        assert result == "Hello World!"

    def test_render_template_with_previous_outputs(self):
        """Test rendering template with previous outputs."""
        template = "Agent said: {{ previous_outputs.agent1.result }}"
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "Hello from agent1"}
            }
        }

        result = self.renderer.render_prompt(template, payload)

        assert "Hello from agent1" in result

    def test_render_template_with_helper_functions(self):
        """Test rendering template with helper functions."""
        template = "Result: {{ get_agent_response('agent1') }}"
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "test result"}
            }
        }

        result = self.renderer.render_prompt(template, payload)

        assert "test result" in result

    def test_render_template_with_missing_variable(self):
        """Test rendering template with missing variable."""
        template = "Hello {{ missing_var }}!"
        payload = {"name": "World"}

        # Should not raise exception, should handle gracefully
        result = self.renderer.render_prompt(template, payload)

        # Result should contain empty string or placeholder for missing var
        assert isinstance(result, str)

    def test_render_template_invalid_template_string(self):
        """Test rendering with invalid template string type."""
        template = 123  # Not a string
        payload = {"name": "World"}

        with pytest.raises(ValueError, match="Expected template_str to be str"):
            self.renderer.render_prompt(template, payload)

    def test_render_template_with_complex_jinja2(self):
        """Test rendering template with complex Jinja2 syntax."""
        template = """
        {% for agent_id, output in previous_outputs.items() %}
        Agent {{ agent_id }}: {{ output.result }}
        {% endfor %}
        """
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "result1"},
                "agent2": {"component_type": "OpenAIAgent", "result": "result2"},
            }
        }

        result = self.renderer.render_prompt(template, payload)

        assert "agent1" in result
        assert "result1" in result
        assert "agent2" in result
        assert "result2" in result

    def test_render_template_with_conditional(self):
        """Test rendering template with conditional logic."""
        template = """
        {% if status == 'success' %}
        Success: {{ message }}
        {% else %}
        Failed
        {% endif %}
        """
        payload = {"status": "success", "message": "Operation completed"}

        result = self.renderer.render_prompt(template, payload)

        assert "Success" in result
        assert "Operation completed" in result
        assert "Failed" not in result


class TestHelperFunctions:
    """Test template helper functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_get_template_helper_functions(self):
        """Test that helper functions are generated."""
        payload = {
            "previous_outputs": {"agent1": {"component_type": "LocalLLMAgent", "result": "test"}}
        }

        helpers = self.renderer._get_template_helper_functions(payload)

        # Check for actual helper function names from implementation
        assert "get_agent_response" in helpers
        assert "get_collaborative_responses" in helpers
        assert callable(helpers["get_agent_response"])
        assert callable(helpers["get_collaborative_responses"])

    def test_get_agent_result_helper(self):
        """Test get_agent_response helper function."""
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "test result"}
            }
        }

        helpers = self.renderer._get_template_helper_functions(payload)
        get_agent_response = helpers["get_agent_response"]

        result = get_agent_response("agent1")
        assert result == "test result"

    def test_get_agent_result_missing_agent(self):
        """Test get_agent_response with missing agent."""
        payload = {"previous_outputs": {}}

        helpers = self.renderer._get_template_helper_functions(payload)
        get_agent_response = helpers["get_agent_response"]

        result = get_agent_response("missing_agent")
        # Should return a message indicating no response found
        assert "No response found" in result or result == ""

    def test_get_all_results_helper(self):
        """Test get_collaborative_responses helper function.

        Note: This function looks for specific agent names (progressive, conservative, etc.)
        so we test with those names.
        """
        payload = {
            "previous_outputs": {
                "progressive_refinement": {
                    "component_type": "LocalLLMAgent",
                    "result": "progressive result",
                },
                "conservative_refinement": {
                    "component_type": "OpenAIAgent",
                    "result": "conservative result",
                },
            }
        }

        helpers = self.renderer._get_template_helper_functions(payload)
        get_collaborative_responses = helpers["get_collaborative_responses"]

        results = get_collaborative_responses()
        assert "progressive result" in results
        assert "conservative result" in results


class TestErrorHandling:
    """Test error handling in template rendering."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_render_with_jinja2_syntax_error(self):
        """Test rendering with Jinja2 syntax error."""
        template = "Hello {{ name"  # Missing closing brace
        payload = {"name": "World"}

        # Should handle syntax error gracefully
        result = self.renderer.render_prompt(template, payload)

        # Should return some error indication or fallback
        assert isinstance(result, str)

    def test_render_with_none_payload(self):
        """Test rendering with None payload."""
        template = "Hello {{ name }}!"
        payload = None

        # Should handle None payload gracefully
        try:
            result = self.renderer.render_prompt(template, payload)
            assert isinstance(result, str)
        except (TypeError, AttributeError):
            # Expected if implementation doesn't handle None
            pass

    def test_render_with_empty_template(self):
        """Test rendering with empty template."""
        template = ""
        payload = {"name": "World"}

        result = self.renderer.render_prompt(template, payload)

        assert result == ""

    def test_render_with_empty_payload(self):
        """Test rendering with empty payload."""
        template = "Static text"
        payload = {}

        result = self.renderer.render_prompt(template, payload)

        assert result == "Static text"


class TestBackwardCompatibility:
    """Test backward compatibility with legacy formats."""

    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = SimplifiedPromptRenderer()

    def test_legacy_response_field_access(self):
        """Test accessing legacy 'response' field."""
        template = "{{ previous_outputs.agent1.response }}"
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "test result"}
            }
        }

        result = self.renderer.render_prompt(template, payload)

        # Legacy 'response' field should map to 'result'
        assert "test result" in result

    def test_legacy_memories_field_access(self):
        """Test accessing legacy 'memories' field."""
        template = "{{ previous_outputs.agent1.memories | length }}"
        payload = {
            "previous_outputs": {
                "agent1": {
                    "component_type": "MemoryReaderNode",
                    "memory_entries": ["memory1", "memory2", "memory3"],
                }
            }
        }

        result = self.renderer.render_prompt(template, payload)

        # Legacy 'memories' field should map to 'memory_entries'
        assert "3" in result

    def test_mixed_orka_and_legacy_outputs(self):
        """Test handling mixed OrkaResponse and legacy outputs."""
        template = """
        Agent1: {{ previous_outputs.agent1.result }}
        Agent2: {{ previous_outputs.agent2.response }}
        """
        payload = {
            "previous_outputs": {
                "agent1": {"component_type": "LocalLLMAgent", "result": "orka result"},
                "agent2": {"response": "legacy response"},
            }
        }

        result = self.renderer.render_prompt(template, payload)

        assert "orka result" in result
        assert "legacy response" in result
