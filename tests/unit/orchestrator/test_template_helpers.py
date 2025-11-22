"""
Tests for orchestrator template_helpers module.
Tests all helper functions with various edge cases and corner cases.
"""

import sys
from pathlib import Path

# Add the parent directory to path to import directly
import pytest
from jinja2 import Environment

# Import directly from the module file to avoid full orka import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "orka" / "orchestrator"))
import template_helpers

safe_get = template_helpers.safe_get
safe_get_response = template_helpers.safe_get_response
get_loop_output = template_helpers.get_loop_output
get_agent_response = template_helpers.get_agent_response
truncate_text = template_helpers.truncate_text
format_loop_metadata = template_helpers.format_loop_metadata
get_debate_evolution = template_helpers.get_debate_evolution
register_template_helpers = template_helpers.register_template_helpers


# Mark all tests to not use the mock_external_services fixture
pytestmark = pytest.mark.usefixtures()


class TestSafeGet:
    """Tests for safe_get function."""

    def test_safe_get_with_dict_existing_key(self):
        """Test safe_get with dict and existing key."""
        obj = {"key": "value"}
        result = safe_get(obj, "key", "default")
        assert result == "value"

    def test_safe_get_with_dict_missing_key(self):
        """Test safe_get with dict and missing key."""
        obj = {"other": "value"}
        result = safe_get(obj, "key", "default")
        assert result == "default"

    def test_safe_get_with_dict_missing_key_default_unknown(self):
        """Test safe_get with dict and missing key using default 'unknown'."""
        obj = {"other": "value"}
        result = safe_get(obj, "key")
        assert result == "unknown"

    def test_safe_get_with_none_object(self):
        """Test safe_get with None object."""
        result = safe_get(None, "key", "default")
        assert result == "default"

    def test_safe_get_with_none_object_default_unknown(self):
        """Test safe_get with None object and default 'unknown'."""
        result = safe_get(None, "key")
        assert result == "unknown"

    def test_safe_get_with_object_existing_attribute(self):
        """Test safe_get with object and existing attribute."""
        class TestObj:
            key = "value"
        
        obj = TestObj()
        result = safe_get(obj, "key", "default")
        assert result == "value"

    def test_safe_get_with_object_missing_attribute(self):
        """Test safe_get with object and missing attribute."""
        class TestObj:
            other = "value"
        
        obj = TestObj()
        result = safe_get(obj, "key", "default")
        assert result == "default"

    def test_safe_get_with_empty_dict(self):
        """Test safe_get with empty dict."""
        obj = {}
        result = safe_get(obj, "key", "default")
        assert result == "default"

    def test_safe_get_with_nested_dict(self):
        """Test safe_get with nested dict."""
        obj = {"outer": {"inner": "value"}}
        result = safe_get(obj, "outer", "default")
        assert result == {"inner": "value"}


class TestSafeGetResponse:
    """Tests for safe_get_response function."""

    def test_safe_get_response_with_none_previous_outputs(self):
        """Test safe_get_response with None previous_outputs."""
        result = safe_get_response("agent1", "default", None)
        assert result == "default"

    def test_safe_get_response_with_missing_agent_id(self):
        """Test safe_get_response with missing agent_id."""
        previous_outputs = {"other_agent": {"response": "value"}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "default"

    def test_safe_get_response_with_dict_response_field(self):
        """Test safe_get_response with dict containing 'response' field."""
        previous_outputs = {"agent1": {"response": "test response"}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "test response"

    def test_safe_get_response_with_dict_result_field(self):
        """Test safe_get_response with dict containing 'result' field."""
        previous_outputs = {"agent1": {"result": "test result"}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "test result"

    def test_safe_get_response_with_dict_output_field(self):
        """Test safe_get_response with dict containing 'output' field."""
        previous_outputs = {"agent1": {"output": "test output"}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "test output"

    def test_safe_get_response_with_nested_response_dict(self):
        """Test safe_get_response with nested response dict."""
        previous_outputs = {"agent1": {"response": {"response": "nested value"}}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "nested value"

    def test_safe_get_response_with_dict_no_standard_field(self):
        """Test safe_get_response with dict without standard fields."""
        previous_outputs = {"agent1": {"custom": "value"}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "{'custom': 'value'}"

    def test_safe_get_response_with_string_output(self):
        """Test safe_get_response with string output."""
        previous_outputs = {"agent1": "direct string"}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "direct string"

    def test_safe_get_response_with_integer_output(self):
        """Test safe_get_response with integer output."""
        previous_outputs = {"agent1": 42}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "42"

    def test_safe_get_response_with_list_output(self):
        """Test safe_get_response with list output."""
        previous_outputs = {"agent1": [1, 2, 3]}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "[1, 2, 3]"

    def test_safe_get_response_default_value_unknown(self):
        """Test safe_get_response with default 'unknown' value."""
        result = safe_get_response("agent1", previous_outputs=None)
        assert result == "unknown"

    def test_safe_get_response_with_empty_dict_output(self):
        """Test safe_get_response with empty dict output."""
        previous_outputs = {"agent1": {}}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "{}"

    def test_safe_get_response_with_none_output(self):
        """Test safe_get_response with None as output value."""
        previous_outputs = {"agent1": None}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "None"


class TestGetLoopOutput:
    """Tests for get_loop_output function."""

    def test_get_loop_output_with_none_previous_outputs(self):
        """Test get_loop_output with None previous_outputs."""
        result = get_loop_output("loop1", None)
        assert result == {}

    def test_get_loop_output_with_missing_agent_id(self):
        """Test get_loop_output with missing agent_id."""
        previous_outputs = {"other_agent": {"response": "value"}}
        result = get_loop_output("loop1", previous_outputs)
        assert result == {}

    def test_get_loop_output_with_wrapped_response_dict(self):
        """Test get_loop_output with response wrapped in 'response' field."""
        previous_outputs = {
            "loop1": {
                "response": {
                    "loops_completed": 3,
                    "final_score": 0.95,
                    "past_loops": []
                }
            }
        }
        result = get_loop_output("loop1", previous_outputs)
        assert result == {
            "loops_completed": 3,
            "final_score": 0.95,
            "past_loops": []
        }

    def test_get_loop_output_with_direct_dict(self):
        """Test get_loop_output with direct dict output."""
        previous_outputs = {
            "loop1": {
                "loops_completed": 5,
                "final_score": 0.88
            }
        }
        result = get_loop_output("loop1", previous_outputs)
        assert result == {
            "loops_completed": 5,
            "final_score": 0.88
        }

    def test_get_loop_output_with_non_dict_output(self):
        """Test get_loop_output with non-dict output."""
        previous_outputs = {"loop1": "string value"}
        result = get_loop_output("loop1", previous_outputs)
        assert result == {}

    def test_get_loop_output_with_response_non_dict(self):
        """Test get_loop_output with 'response' field containing non-dict."""
        previous_outputs = {"loop1": {"response": "string"}}
        result = get_loop_output("loop1", previous_outputs)
        assert result == {"response": "string"}

    def test_get_loop_output_with_integer_value(self):
        """Test get_loop_output with integer value."""
        previous_outputs = {"loop1": 42}
        result = get_loop_output("loop1", previous_outputs)
        assert result == {}

    def test_get_loop_output_with_empty_dict(self):
        """Test get_loop_output with empty dict."""
        previous_outputs = {"loop1": {}}
        result = get_loop_output("loop1", previous_outputs)
        assert result == {}


class TestGetAgentResponse:
    """Tests for get_agent_response function."""

    def test_get_agent_response_with_valid_agent(self):
        """Test get_agent_response with valid agent."""
        previous_outputs = {"agent1": {"response": "test value"}}
        result = get_agent_response("agent1", previous_outputs)
        assert result == "test value"

    def test_get_agent_response_with_missing_agent(self):
        """Test get_agent_response with missing agent returns empty string."""
        previous_outputs = {"other_agent": {"response": "value"}}
        result = get_agent_response("agent1", previous_outputs)
        assert result == ""

    def test_get_agent_response_with_none_previous_outputs(self):
        """Test get_agent_response with None previous_outputs."""
        result = get_agent_response("agent1", None)
        assert result == ""

    def test_get_agent_response_empty_string_default(self):
        """Test get_agent_response uses empty string as default."""
        result = get_agent_response("agent1", {})
        assert result == ""


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_text_below_length(self):
        """Test truncate_text with text below length."""
        text = "short text"
        result = truncate_text(text, 100)
        assert result == "short text"

    def test_truncate_text_exactly_at_length(self):
        """Test truncate_text with text exactly at length."""
        text = "a" * 100
        result = truncate_text(text, 100)
        assert result == "a" * 100

    def test_truncate_text_above_length(self):
        """Test truncate_text with text above length."""
        text = "a" * 150
        result = truncate_text(text, 100)
        assert result == "a" * 97 + "..."
        assert len(result) == 100

    def test_truncate_text_with_custom_suffix(self):
        """Test truncate_text with custom suffix."""
        text = "a" * 150
        result = truncate_text(text, 100, " [...]")
        assert result == "a" * 94 + " [...]"
        assert len(result) == 100

    def test_truncate_text_with_none(self):
        """Test truncate_text with None input."""
        result = truncate_text(None, 100)
        assert result == ""

    def test_truncate_text_with_empty_string(self):
        """Test truncate_text with empty string."""
        result = truncate_text("", 100)
        assert result == ""

    def test_truncate_text_with_very_short_length(self):
        """Test truncate_text with very short length."""
        text = "This is a long text"
        result = truncate_text(text, 10)
        assert result == "This is..."
        assert len(result) == 10

    def test_truncate_text_default_length(self):
        """Test truncate_text with default length."""
        text = "a" * 150
        result = truncate_text(text)
        assert len(result) == 100

    def test_truncate_text_default_suffix(self):
        """Test truncate_text with default suffix."""
        text = "a" * 150
        result = truncate_text(text, 50)
        assert result.endswith("...")


class TestFormatLoopMetadata:
    """Tests for format_loop_metadata function."""

    def test_format_loop_metadata_with_empty_list(self):
        """Test format_loop_metadata with empty list."""
        result = format_loop_metadata([])
        assert result == "No previous loops"

    def test_format_loop_metadata_with_none(self):
        """Test format_loop_metadata with None."""
        result = format_loop_metadata(None)
        assert result == "No previous loops"

    def test_format_loop_metadata_with_single_loop(self):
        """Test format_loop_metadata with single loop."""
        past_loops = [{"score": 0.85, "status": "completed"}]
        result = format_loop_metadata(past_loops)
        assert result == "Loop 1: score=0.85, status=completed"

    def test_format_loop_metadata_with_multiple_loops(self):
        """Test format_loop_metadata with multiple loops."""
        past_loops = [
            {"score": 0.75, "status": "completed"},
            {"score": 0.85, "status": "completed"},
            {"score": 0.95, "status": "completed"}
        ]
        result = format_loop_metadata(past_loops)
        expected = "Loop 1: score=0.75, status=completed\nLoop 2: score=0.85, status=completed\nLoop 3: score=0.95, status=completed"
        assert result == expected

    def test_format_loop_metadata_with_max_loops_limit(self):
        """Test format_loop_metadata respects max_loops limit."""
        past_loops = [
            {"score": 0.1, "status": "completed"},
            {"score": 0.2, "status": "completed"},
            {"score": 0.3, "status": "completed"},
            {"score": 0.4, "status": "completed"},
            {"score": 0.5, "status": "completed"},
            {"score": 0.6, "status": "completed"},
            {"score": 0.7, "status": "completed"}
        ]
        result = format_loop_metadata(past_loops, max_loops=3)
        # Should show last 3 loops
        assert "score=0.5" in result
        assert "score=0.6" in result
        assert "score=0.7" in result
        assert "score=0.1" not in result
        assert "score=0.2" not in result

    def test_format_loop_metadata_with_missing_score(self):
        """Test format_loop_metadata with missing score."""
        past_loops = [{"status": "completed"}]
        result = format_loop_metadata(past_loops)
        assert result == "Loop 1: score=N/A, status=completed"

    def test_format_loop_metadata_with_missing_status(self):
        """Test format_loop_metadata with missing status."""
        past_loops = [{"score": 0.85}]
        result = format_loop_metadata(past_loops)
        assert result == "Loop 1: score=0.85, status=completed"

    def test_format_loop_metadata_with_failed_status(self):
        """Test format_loop_metadata with failed status."""
        past_loops = [{"score": 0.45, "status": "failed"}]
        result = format_loop_metadata(past_loops)
        assert result == "Loop 1: score=0.45, status=failed"

    def test_format_loop_metadata_default_max_loops(self):
        """Test format_loop_metadata with default max_loops."""
        past_loops = [{"score": i, "status": "completed"} for i in range(10)]
        result = format_loop_metadata(past_loops)
        lines = result.split("\n")
        assert len(lines) == 5  # default max_loops is 5


class TestGetDebateEvolution:
    """Tests for get_debate_evolution function."""

    def test_get_debate_evolution_with_no_loops(self):
        """Test get_debate_evolution with no previous loops."""
        result = get_debate_evolution(None)
        assert result == "First round of debate"

    def test_get_debate_evolution_with_empty_list(self):
        """Test get_debate_evolution with empty list."""
        result = get_debate_evolution([])
        assert result == "First round of debate"

    def test_get_debate_evolution_with_one_loop(self):
        """Test get_debate_evolution with one previous loop."""
        past_loops = [{"score": 0.75}]
        result = get_debate_evolution(past_loops)
        assert result == "Second round - previous score: 0.75"

    def test_get_debate_evolution_with_improving_scores(self):
        """Test get_debate_evolution with improving scores."""
        past_loops = [
            {"score": 0.5},
            {"score": 0.7},
            {"score": 0.85}
        ]
        result = get_debate_evolution(past_loops)
        assert "Round 4" in result
        assert "improving" in result
        assert "0.5 → 0.7 → 0.85" in result

    def test_get_debate_evolution_with_declining_scores(self):
        """Test get_debate_evolution with declining scores."""
        past_loops = [
            {"score": 0.9},
            {"score": 0.7},
            {"score": 0.5}
        ]
        result = get_debate_evolution(past_loops)
        assert "Round 4" in result
        assert "declining" in result
        assert "0.9 → 0.7 → 0.5" in result

    def test_get_debate_evolution_with_equal_scores(self):
        """Test get_debate_evolution with equal first and last scores."""
        past_loops = [
            {"score": 0.7},
            {"score": 0.8},
            {"score": 0.7}
        ]
        result = get_debate_evolution(past_loops)
        assert "Round 4" in result
        # Since 0.7 == 0.7, it will be "declining" (not >)
        assert "declining" in result

    def test_get_debate_evolution_with_missing_scores(self):
        """Test get_debate_evolution with missing scores (defaults to 0)."""
        past_loops = [
            {},
            {"score": 0.5}
        ]
        result = get_debate_evolution(past_loops)
        assert "Round 3" in result
        # 0 to 0.5 is improving
        assert "improving" in result

    def test_get_debate_evolution_with_two_loops(self):
        """Test get_debate_evolution with exactly two loops."""
        past_loops = [
            {"score": 0.6},
            {"score": 0.8}
        ]
        result = get_debate_evolution(past_loops)
        assert "Round 3" in result
        assert "improving" in result
        assert "0.6 → 0.8" in result


class TestRegisterTemplateHelpers:
    """Tests for register_template_helpers function."""

    def test_register_template_helpers_filters(self):
        """Test that all filters are registered."""
        env = Environment()
        register_template_helpers(env)
        
        assert 'safe_get' in env.filters
        assert 'truncate' in env.filters
        assert 'format_loop_metadata' in env.filters

    def test_register_template_helpers_globals(self):
        """Test that all globals are registered."""
        env = Environment()
        register_template_helpers(env)
        
        assert 'safe_get' in env.globals
        assert 'safe_get_response' in env.globals
        assert 'get_agent_response' in env.globals
        assert 'get_loop_output' in env.globals
        assert 'truncate_text' in env.globals
        assert 'format_loop_metadata' in env.globals
        assert 'get_debate_evolution' in env.globals

    def test_register_template_helpers_filter_usage(self):
        """Test that registered filters work in templates."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ text | truncate(10) }}")
        result = template.render(text="This is a very long text")
        assert len(result) == 10
        assert result.endswith("...")

    def test_register_template_helpers_global_usage(self):
        """Test that registered globals work in templates."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ safe_get_response('agent1', 'default', previous_outputs) }}")
        result = template.render(previous_outputs={"agent1": {"response": "test"}})
        assert result == "test"

    def test_register_template_helpers_safe_get_as_filter(self):
        """Test safe_get works as a filter."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ obj | safe_get('key', 'default') }}")
        result = template.render(obj={"key": "value"})
        assert result == "value"

    def test_register_template_helpers_safe_get_as_global(self):
        """Test safe_get works as a global function."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ safe_get(obj, 'key', 'default') }}")
        result = template.render(obj={"key": "value"})
        assert result == "value"

    def test_register_template_helpers_get_loop_output_usage(self):
        """Test get_loop_output in template."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ get_loop_output('loop1', previous_outputs).loops_completed }}")
        previous_outputs = {
            "loop1": {
                "response": {
                    "loops_completed": 5
                }
            }
        }
        result = template.render(previous_outputs=previous_outputs)
        assert result == "5"

    def test_register_template_helpers_get_debate_evolution_usage(self):
        """Test get_debate_evolution in template."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ get_debate_evolution(past_loops) }}")
        result = template.render(past_loops=[])
        assert result == "First round of debate"

    def test_register_template_helpers_format_loop_metadata_as_filter(self):
        """Test format_loop_metadata as filter."""
        env = Environment()
        register_template_helpers(env)
        
        template = env.from_string("{{ past_loops | format_loop_metadata }}")
        result = template.render(past_loops=[{"score": 0.8, "status": "completed"}])
        assert "Loop 1: score=0.8, status=completed" in result


class TestEdgeCases:
    """Tests for edge cases and corner cases."""

    def test_safe_get_response_with_boolean_false(self):
        """Test safe_get_response with boolean False value."""
        previous_outputs = {"agent1": False}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "False"

    def test_safe_get_response_with_zero(self):
        """Test safe_get_response with zero value."""
        previous_outputs = {"agent1": 0}
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "0"

    def test_truncate_text_with_unicode(self):
        """Test truncate_text with unicode characters."""
        text = "Hello 世界 🌍" * 20
        result = truncate_text(text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_format_loop_metadata_with_float_scores(self):
        """Test format_loop_metadata with various float scores."""
        past_loops = [
            {"score": 0.123456, "status": "completed"},
            {"score": 0.999999, "status": "completed"}
        ]
        result = format_loop_metadata(past_loops)
        assert "0.123456" in result
        assert "0.999999" in result

    def test_get_debate_evolution_with_negative_scores(self):
        """Test get_debate_evolution with negative scores."""
        past_loops = [
            {"score": -0.5},
            {"score": 0.5}
        ]
        result = get_debate_evolution(past_loops)
        assert "improving" in result

    def test_safe_get_with_nested_object_access(self):
        """Test safe_get with nested object structures."""
        class Inner:
            value = "inner_value"
        
        class Outer:
            inner = Inner()
        
        obj = Outer()
        result = safe_get(obj, "inner", "default")
        assert isinstance(result, Inner)
        assert result.value == "inner_value"

    def test_safe_get_response_with_complex_nested_structure(self):
        """Test safe_get_response with complex nested structures."""
        previous_outputs = {
            "agent1": {
                "response": {
                    "response": {
                        "response": "deeply nested"
                    }
                }
            }
        }
        result = safe_get_response("agent1", "default", previous_outputs)
        # Should extract the first nested response
        assert "response" in result or "deeply nested" in result

    def test_get_loop_output_with_multiple_response_levels(self):
        """Test get_loop_output with multiple response nesting levels."""
        previous_outputs = {
            "loop1": {
                "response": {
                    "data": "value",
                    "nested": {"key": "nested_value"}
                }
            }
        }
        result = get_loop_output("loop1", previous_outputs)
        assert result["data"] == "value"
        assert result["nested"]["key"] == "nested_value"

    def test_truncate_text_length_equal_to_suffix(self):
        """Test truncate_text when length equals suffix length."""
        text = "Long text here"
        result = truncate_text(text, 3, "...")
        assert result == "..."

    def test_format_loop_metadata_with_zero_score(self):
        """Test format_loop_metadata with zero score."""
        past_loops = [{"score": 0, "status": "completed"}]
        result = format_loop_metadata(past_loops)
        assert "score=0" in result

    def test_get_agent_response_with_empty_string_value(self):
        """Test get_agent_response when agent returns empty string."""
        previous_outputs = {"agent1": {"response": ""}}
        result = get_agent_response("agent1", previous_outputs)
        assert result == ""

    def test_safe_get_with_list_object(self):
        """Test safe_get with list object (should use getattr)."""
        obj = [1, 2, 3]
        result = safe_get(obj, "append", "default")
        # Lists have append attribute
        assert callable(result)

    def test_safe_get_response_priority_response_over_result(self):
        """Test that 'response' field has priority over 'result'."""
        previous_outputs = {
            "agent1": {
                "response": "response_value",
                "result": "result_value",
                "output": "output_value"
            }
        }
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "response_value"

    def test_safe_get_response_priority_result_over_output(self):
        """Test that 'result' field has priority over 'output'."""
        previous_outputs = {
            "agent1": {
                "result": "result_value",
                "output": "output_value"
            }
        }
        result = safe_get_response("agent1", "default", previous_outputs)
        assert result == "result_value"
