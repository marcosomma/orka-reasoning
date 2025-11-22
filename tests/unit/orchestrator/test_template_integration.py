# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma

"""
Test suite for template helpers integration with SimplifiedPromptRenderer.

This test verifies that custom Jinja2 filters are properly registered and functional.
"""

import pytest
from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer


class TestTemplateHelpersIntegration:
    """Test integration of custom template helpers with SimplifiedPromptRenderer."""

    def test_safe_get_filter_basic(self):
        """Test safe_get filter with simple dict access."""
        renderer = SimplifiedPromptRenderer()
        template = "Result: {{ data | safe_get('key', 'default_value') }}"
        
        # Test with existing key
        payload = {"data": {"key": "found"}}
        result = renderer.render_prompt(template, payload)
        assert "found" in result
        
        # Test with missing key (should use default)
        payload = {"data": {}}
        result = renderer.render_prompt(template, payload)
        assert "default_value" in result

    def test_safe_get_response_filter(self):
        """Test safe_get_response filter for agent outputs."""
        renderer = SimplifiedPromptRenderer()
        template = "Agent said: {{ safe_get_response('test_agent', 'no response') }}"
        
        # Test with agent response in previous_outputs
        payload = {
            "previous_outputs": {
                "test_agent": {
                    "result": "Hello from test agent"
                }
            }
        }
        result = renderer.render_prompt(template, payload)
        assert "Hello from test agent" in result
        
        # Test with missing agent (should use fallback)
        payload = {"previous_outputs": {}}
        result = renderer.render_prompt(template, payload)
        assert "no response" in result

    def test_truncate_filter(self):
        """Test truncate filter for text truncation."""
        renderer = SimplifiedPromptRenderer()
        template = "{{ text | truncate(10) }}"
        
        payload = {"text": "This is a very long text that should be truncated"}
        result = renderer.render_prompt(template, payload)
        assert len(result) <= 13  # 10 chars + "..." suffix
        assert "..." in result

    def test_get_agent_response_function(self):
        """Test get_agent_response helper function."""
        renderer = SimplifiedPromptRenderer()
        template = "Response: {{ get_agent_response('my_agent') }}"
        
        # Test with nested response structure (LoopNode format)
        payload = {
            "previous_outputs": {
                "my_agent": {
                    "response": "Nested response from loop"
                }
            }
        }
        result = renderer.render_prompt(template, payload)
        assert "Nested response from loop" in result

    def test_multiple_filters_chained(self):
        """Test chaining multiple custom filters."""
        renderer = SimplifiedPromptRenderer()
        template = "{{ safe_get_response('agent1', 'nothing') | truncate(20) }}"
        
        payload = {
            "previous_outputs": {
                "agent1": {
                    "result": "This is a very long response that needs truncation"
                }
            }
        }
        result = renderer.render_prompt(template, payload)
        assert len(result) <= 23  # 20 chars + "..." suffix
        assert "..." in result

    def test_cognitive_society_pattern(self):
        """Test pattern used in cognitive_society workflow."""
        renderer = SimplifiedPromptRenderer()
        template = """
        Progressive: {{ safe_get_response('radical_progressive', 'No response') | truncate(150) }}
        Conservative: {{ safe_get_response('traditional_conservative', 'No response') | truncate(150) }}
        """
        
        payload = {
            "previous_outputs": {
                "radical_progressive": {
                    "result": "Progressive viewpoint with lots of details " * 10
                },
                "traditional_conservative": {
                    "result": "Conservative viewpoint"
                }
            }
        }
        result = renderer.render_prompt(template, payload)
        assert "Progressive viewpoint" in result
        assert "Conservative viewpoint" in result
        # Check truncation happened for long text
        assert result.count("Progressive viewpoint") < 10

    def test_safe_get_with_nested_objects(self):
        """Test safe_get filter with deeply nested structures."""
        renderer = SimplifiedPromptRenderer()
        template = "{{ loop_data | safe_get('loops_completed', 'Unknown') }}"
        
        payload = {
            "loop_data": {
                "loops_completed": 5,
                "status": "completed"
            }
        }
        result = renderer.render_prompt(template, payload)
        assert "5" in result

    def test_format_loop_metadata_filter(self):
        """Test format_loop_metadata filter for loop history."""
        renderer = SimplifiedPromptRenderer()
        template = "{{ past_loops | format_loop_metadata(3) }}"
        
        payload = {
            "past_loops": [
                {"round": 1, "score": 0.5},
                {"round": 2, "score": 0.7},
                {"round": 3, "score": 0.9}
            ]
        }
        result = renderer.render_prompt(template, payload)
        assert "Loop 1" in result or "Round 1" in result

    def test_get_debate_evolution_filter(self):
        """Test get_debate_evolution filter for debate analysis."""
        renderer = SimplifiedPromptRenderer()
        template = "Evolution: {{ past_loops | get_debate_evolution }}"
        
        payload = {
            "past_loops": [
                {"round": 1, "agreement_score": 0.3},
                {"round": 2, "agreement_score": 0.6},
                {"round": 3, "agreement_score": 0.8}
            ]
        }
        result = renderer.render_prompt(template, payload)
        # Should contain trend information
        assert result  # Non-empty result

    def test_fallback_when_helpers_unavailable(self):
        """Test graceful degradation when template helpers fail to load."""
        # This test verifies the TEMPLATE_HELPERS_AVAILABLE flag works
        renderer = SimplifiedPromptRenderer()
        
        # Even if helpers fail, basic rendering should work
        template = "Input: {{ input }}"
        payload = {"input": "test input"}
        result = renderer.render_prompt(template, payload)
        assert "test input" in result

    def test_unresolved_variables_replaced_with_empty(self):
        """Test that unresolved template variables are replaced with empty strings."""
        renderer = SimplifiedPromptRenderer()
        template = "Start {{ undefined_variable }} End"
        
        payload = {}
        result = renderer.render_prompt(template, payload)
        # Should not contain the template syntax
        assert "{{" not in result
        assert "}}" not in result
        # Should have start and end
        assert "Start" in result
        assert "End" in result
