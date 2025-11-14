"""Unit tests for orka.utils.template_validator."""

import pytest

from orka.utils.template_validator import TemplateValidator

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestTemplateValidator:
    """Test suite for TemplateValidator class."""

    def test_init(self):
        """Test TemplateValidator initialization."""
        validator = TemplateValidator()
        assert validator.env is not None

    def test_validate_template_valid(self):
        """Test validate_template with valid template."""
        validator = TemplateValidator()
        
        template = "Hello {{ name }}"
        is_valid, error_msg, variables = validator.validate_template(template)
        
        assert is_valid is True
        assert error_msg == ""
        assert "name" in variables

    def test_validate_template_invalid_syntax(self):
        """Test validate_template with invalid syntax."""
        from orka.utils.logging_utils import setup_logging
        setup_logging()
        validator = TemplateValidator()
        
        template = "Hello {{ name } {% if condition %}"  # Malformed
        is_valid, error_msg, variables = validator.validate_template(template)
        
        assert is_valid is False
        assert len(error_msg) > 0
        assert "syntax error" in error_msg.lower()

    def test_validate_template_empty(self):
        """Test validate_template with empty string."""
        validator = TemplateValidator()
        
        is_valid, error_msg, variables = validator.validate_template("")
        
        assert is_valid is True
        assert variables == set()

    def test_validate_template_no_variables(self):
        """Test validate_template with no variables."""
        validator = TemplateValidator()
        
        template = "Hello World"
        is_valid, error_msg, variables = validator.validate_template(template)
        
        assert is_valid is True
        assert variables == set()

    def test_validate_template_multiple_variables(self):
        """Test validate_template with multiple variables."""
        validator = TemplateValidator()
        
        template = "Hello {{ name }}, you have {{ count }} messages"
        is_valid, error_msg, variables = validator.validate_template(template)
        
        assert is_valid is True
        assert "name" in variables
        assert "count" in variables

    def test_validate_template_with_conditionals(self):
        """Test validate_template with conditionals."""
        validator = TemplateValidator()
        
        template = "{% if condition %}Yes{% else %}No{% endif %}"
        is_valid, error_msg, variables = validator.validate_template(template)
        
        assert is_valid is True
        assert "condition" in variables

    def test_validate_templates_multiple(self):
        """Test validate_templates with multiple templates."""
        validator = TemplateValidator()
        
        templates = {
            "template1": "Hello {{ name }}",
            "template2": "Goodbye {{ name }}",
        }
        
        all_valid, errors = validator.validate_templates(templates)
        
        assert all_valid is True
        assert errors == {}

    def test_validate_templates_with_errors(self):
        """Test validate_templates with some invalid templates."""
        from orka.utils.logging_utils import setup_logging
        setup_logging()
        validator = TemplateValidator()
        
        templates = {
            "template1": "Hello {{ name }}",
            "template2": "Invalid {{ name } {% if",  # Malformed
        }
        
        all_valid, errors = validator.validate_templates(templates)
        
        assert all_valid is False
        assert "template2" in errors

    def test_extract_variables(self):
        """Test extract_variables method."""
        validator = TemplateValidator()
        
        template = "Hello {{ name }}, count: {{ count }}"
        variables = validator.extract_variables(template)
        
        assert "name" in variables
        assert "count" in variables

    def test_extract_variables_invalid_template(self):
        """Test extract_variables with invalid template."""
        validator = TemplateValidator()
        
        template = "Invalid {{ name } {% if"  # Malformed
        variables = validator.extract_variables(template)
        
        # Should return empty set on error
        assert variables == set()

