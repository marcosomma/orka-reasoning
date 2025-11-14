# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""
Tests for Template Validator
=============================

Tests the template validation functionality that catches Jinja2 syntax errors
at configuration load time.
"""

import pytest

from orka.utils.template_validator import TemplateValidator


class TestTemplateValidator:
    """Test suite for TemplateValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = TemplateValidator()

    def test_valid_simple_template(self):
        """Test validation of a simple valid template."""
        template = "Hello {{ name }}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert error == ""
        assert "name" in variables

    def test_valid_complex_template(self):
        """Test validation of a complex valid template."""
        template = """
        Query: {{ get_input() }}
        Memory: {{ get_agent_response('memory-reader') }}
        Context: {{ previous_outputs.classifier.result }}
        """
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert error == ""
        # Check that function calls and attribute access are recognized
        assert len(variables) > 0

    def test_invalid_syntax_missing_closing_brace(self):
        """Test detection of missing closing brace."""
        template = "Hello {{ name"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is False
        assert "syntax error" in error.lower() or "unexpected" in error.lower()
        assert variables == set()

    def test_invalid_syntax_bad_expression(self):
        """Test detection of invalid expression syntax."""
        template = "{{ , }}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is False
        assert len(error) > 0
        assert variables == set()

    def test_empty_template(self):
        """Test that empty templates are considered valid."""
        template = ""
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert error == ""
        assert variables == set()

    def test_none_template(self):
        """Test that None templates are handled gracefully."""
        template = None
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert error == ""
        assert variables == set()

    def test_template_with_no_variables(self):
        """Test template with no Jinja2 variables."""
        template = "This is just plain text"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert error == ""
        assert variables == set()

    def test_variable_extraction(self):
        """Test that variables are correctly extracted."""
        template = "{{ user }} likes {{ item }}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert "user" in variables
        assert "item" in variables
        assert len(variables) == 2

    def test_validate_multiple_templates(self):
        """Test batch validation of multiple templates."""
        templates = {
            "template1": "{{ valid }}",
            "template2": "{{ also_valid }}",
            "template3": "{{ missing_brace",
        }
        
        all_valid, errors = self.validator.validate_templates(templates)
        
        assert all_valid is False
        assert "template3" in errors
        assert len(errors) == 1

    def test_extract_variables_standalone(self):
        """Test standalone variable extraction."""
        template = "{{ foo }} and {{ bar }}"
        variables = self.validator.extract_variables(template)
        
        assert "foo" in variables
        assert "bar" in variables

    def test_extract_variables_from_invalid_template(self):
        """Test that extract_variables handles invalid templates gracefully."""
        template = "{{ invalid"
        variables = self.validator.extract_variables(template)
        
        # Should return empty set and log warning rather than crashing
        assert variables == set()

    def test_template_with_filters(self):
        """Test template with Jinja2 filters."""
        template = "{{ name|upper }}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert "name" in variables

    def test_template_with_conditionals(self):
        """Test template with conditional logic."""
        template = "{% if condition %}yes{% else %}no{% endif %}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert "condition" in variables

    def test_template_with_loops(self):
        """Test template with loops."""
        template = "{% for item in items %}{{ item }}{% endfor %}"
        is_valid, error, variables = self.validator.validate_template(template)
        
        assert is_valid is True
        assert "items" in variables

