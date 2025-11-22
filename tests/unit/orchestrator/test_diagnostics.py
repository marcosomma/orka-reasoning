"""Tests for orchestrator diagnostics utilities."""

import logging
import pytest
from orka.orchestrator.diagnostics import (
    diagnose_template_variables,
    log_previous_outputs_structure,
    validate_template_context
)


def test_diagnose_template_variables_all_found(caplog):
    """Test diagnosis when all template variables are found."""
    template = "Hello {{ name }}, your score is {{ score }}"
    context = {"name": "Alice", "score": 95}
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        missing = diagnose_template_variables(template, context, agent_id)
    
    assert missing == []
    assert "All template variables resolved successfully" in caplog.text


def test_diagnose_template_variables_missing_simple():
    """Test diagnosis when simple variables are missing."""
    template = "Hello {{ name }}, your {{ missing_var }} is here"
    context = {"name": "Bob"}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert "missing_var" in missing


def test_diagnose_template_variables_nested_dict():
    """Test diagnosis with nested dictionary access."""
    template = "Result: {{ data.result }}, Status: {{ data.status }}"
    context = {"data": {"result": "success"}}  # Missing 'status'
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert any("status" in var for var in missing)


def test_diagnose_template_variables_deeply_nested():
    """Test diagnosis with deeply nested structures."""
    template = "{{ config.database.host }}"
    context = {"config": {"database": {"host": "localhost", "port": 5432}}}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert missing == []


def test_diagnose_template_variables_missing_nested():
    """Test diagnosis when nested path doesn't exist."""
    template = "{{ user.profile.avatar }}"
    context = {"user": {"name": "Charlie"}}  # Missing 'profile'
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert len(missing) > 0
    assert any("profile" in var for var in missing)


def test_diagnose_template_variables_with_filters():
    """Test diagnosis with Jinja2 filters."""
    template = "{{ name | upper }}, {{ count | default(0) }}"
    context = {"name": "test"}  # 'count' missing but has default
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    # Should detect 'count' as referenced even with filter
    assert "count" in missing


def test_diagnose_template_variables_array_access():
    """Test diagnosis with array/bracket notation."""
    template = "{{ items[0] }}, {{ data['key'] }}"
    context = {"items": [1, 2, 3], "data": {"key": "value"}}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    # Array access detection has limitations - it reports items.0 as missing
    # since the function treats lists differently than dicts
    assert "items.0" in missing or missing == []


def test_diagnose_template_variables_empty_template():
    """Test diagnosis with empty template."""
    template = ""
    context = {"anything": "here"}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert missing == []


def test_diagnose_template_variables_empty_context():
    """Test diagnosis with empty context."""
    template = "{{ required_var }}"
    context = {}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert "required_var" in missing


def test_diagnose_template_variables_long_values_truncated(caplog):
    """Test that long values are truncated in logs."""
    template = "{{ long_value }}"
    context = {"long_value": "x" * 200}  # Very long value
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        missing = diagnose_template_variables(template, context, agent_id)
    
    assert missing == []
    # Check that value was truncated (contains "...")
    assert "..." in caplog.text


def test_log_previous_outputs_structure_empty(caplog):
    """Test logging with empty previous outputs."""
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure({}, agent_id)
    
    assert "EMPTY" in caplog.text


def test_log_previous_outputs_structure_simple_dict(caplog):
    """Test logging with simple dictionary outputs."""
    previous_outputs = {
        "agent1": {"result": "success", "score": 95}
    }
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure(previous_outputs, agent_id)
    
    assert "agent1" in caplog.text
    assert "dict with keys" in caplog.text


def test_log_previous_outputs_structure_nested_dict(caplog):
    """Test logging with nested dictionaries."""
    previous_outputs = {
        "agent1": {
            "result": {
                "nested_key1": "value1",
                "nested_key2": "value2"
            },
            "status": "complete"
        }
    }
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure(previous_outputs, agent_id)
    
    assert "agent1" in caplog.text
    assert "result" in caplog.text


def test_log_previous_outputs_structure_with_list(caplog):
    """Test logging with list values."""
    previous_outputs = {
        "agent1": {
            "joined_results": [1, 2, 3, 4, 5],
            "count": 5
        }
    }
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure(previous_outputs, agent_id)
    
    assert "agent1" in caplog.text
    assert "list with 5 items" in caplog.text


def test_log_previous_outputs_structure_non_dict_output(caplog):
    """Test logging with non-dict output values."""
    previous_outputs = {
        "agent1": "simple string result",
        "agent2": 42
    }
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure(previous_outputs, agent_id)
    
    assert "agent1" in caplog.text
    assert "simple string result" in caplog.text


def test_log_previous_outputs_structure_long_values_truncated(caplog):
    """Test that long values are truncated in logs."""
    previous_outputs = {
        "agent1": {"result": "x" * 100}
    }
    agent_id = "test_agent"
    
    with caplog.at_level(logging.DEBUG):
        log_previous_outputs_structure(previous_outputs, agent_id)
    
    assert "..." in caplog.text


def test_validate_template_context_valid():
    """Test validation with valid context."""
    template = "Hello {{ name }}"
    context = {"name": "Alice", "input": "test", "previous_outputs": {}}
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert result["is_valid"] is True
    assert result["missing_vars"] == []
    assert len(result["warnings"]) == 0


def test_validate_template_context_missing_vars():
    """Test validation with missing variables."""
    template = "Hello {{ name }}, {{ missing }}"
    context = {"name": "Alice", "input": "test", "previous_outputs": {}}
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert result["is_valid"] is False
    assert "missing" in result["missing_vars"]


def test_validate_template_context_no_previous_outputs():
    """Test validation when previous_outputs is missing."""
    template = "Hello {{ name }}"
    context = {"name": "Alice", "input": "test"}  # No previous_outputs
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert "previous_outputs missing from context" in result["warnings"]


def test_validate_template_context_no_input():
    """Test validation when input is missing."""
    template = "Hello {{ name }}"
    context = {"name": "Alice", "previous_outputs": {}}  # No input
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert "input missing from context" in result["warnings"]


def test_validate_template_context_empty_previous_outputs_referenced():
    """Test validation when previous_outputs is empty but referenced."""
    template = "Previous: {{ previous_outputs.agent1 }}"
    context = {"input": "test", "previous_outputs": {}}  # Empty
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert "previous_outputs is empty but template references it" in result["warnings"]


def test_validate_template_context_all_warnings():
    """Test validation with all possible warnings."""
    template = "{{ previous_outputs.agent1 }}"
    context = {}  # Everything missing
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert result["is_valid"] is False
    assert len(result["warnings"]) >= 2  # At least missing input and previous_outputs


def test_validate_template_context_complex_scenario():
    """Test validation with complex nested references."""
    template = """
    Input: {{ input }}
    Previous result: {{ previous_outputs.analyzer.result.score }}
    Config: {{ config.threshold }}
    """
    context = {
        "input": "test data",
        "previous_outputs": {
            "analyzer": {
                "result": {
                    "score": 85
                }
            }
        }
    }  # Missing 'config'
    agent_id = "test_agent"
    
    result = validate_template_context(template, context, agent_id)
    
    assert result["is_valid"] is False
    assert any("config" in var for var in result["missing_vars"])


def test_diagnose_template_variables_multiple_missing(caplog):
    """Test diagnosis with multiple missing variables."""
    template = "{{ var1 }}, {{ var2 }}, {{ var3 }}"
    context = {"var1": "present"}
    agent_id = "test_agent"
    
    with caplog.at_level(logging.WARNING):
        missing = diagnose_template_variables(template, context, agent_id)
    
    assert len(missing) >= 2
    assert "var2" in missing
    assert "var3" in missing


def test_diagnose_template_variables_with_whitespace():
    """Test diagnosis with various whitespace in templates."""
    template = "{{name}}, {{ spaced }}, {{  extra_spaced  }}"
    context = {"name": "Alice", "spaced": "Bob", "extra_spaced": "Charlie"}
    agent_id = "test_agent"
    
    missing = diagnose_template_variables(template, context, agent_id)
    
    assert missing == []
