# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Template Validator
==================

Validates Jinja2 templates and extracts required variables to catch
template syntax errors at configuration load time rather than runtime.

This module provides strict validation for agent prompt templates to ensure
that all templates are syntactically correct before workflow execution begins.
"""

import logging
from typing import Set, Tuple

from jinja2 import Environment, TemplateSyntaxError, UndefinedError, meta

logger = logging.getLogger(__name__)


class TemplateValidator:
    """
    Validates Jinja2 templates and extracts required variables.

    This validator performs:
    - Syntax validation using Jinja2 parser
    - Variable extraction using jinja2.meta
    - Detailed error messages with line numbers and context

    Example:
        >>> validator = TemplateValidator()
        >>> is_valid, error, vars = validator.validate_template("Hello {{ name }}")
        >>> print(is_valid, vars)
        True {'name'}
    """

    def __init__(self):
        """Initialize the template validator with a Jinja2 environment."""
        self.env = Environment()
        # Note: UndefinedError is raised, not used as undefined class

    def validate_template(self, template_str: str) -> Tuple[bool, str, Set[str]]:
        """
        Validate template syntax and extract required variables.

        Args:
            template_str: The Jinja2 template string to validate

        Returns:
            Tuple containing:
            - is_valid (bool): True if template is syntactically correct
            - error_message (str): Detailed error message if invalid, empty string if valid
            - required_variables (Set[str]): Set of variable names used in template

        Example:
            >>> validator = TemplateValidator()
            >>> is_valid, error, vars = validator.validate_template("{{ user }}")
            >>> is_valid
            True
            >>> 'user' in vars
            True
        """
        if not template_str or not isinstance(template_str, str):
            return True, "", set()

        required_variables: Set[str] = set()

        try:
            # Parse the template to check for syntax errors
            ast = self.env.parse(template_str)

            # Extract all undeclared variables from the template
            required_variables = meta.find_undeclared_variables(ast)

            # Try to compile the template (catches additional errors)
            self.env.from_string(template_str)

            logger.debug(
                f"Template validated successfully. "
                f"Found {len(required_variables)} variables: {required_variables}"
            )

            return True, "", required_variables

        except TemplateSyntaxError as e:
            # Jinja2 template syntax error with line/column information
            error_msg = f"Template syntax error at line {e.lineno}: {e.message}"

            # Add context if available
            if hasattr(e, "source") and e.source:
                lines = e.source.split("\n")
                if 0 <= e.lineno - 1 < len(lines):
                    error_line = lines[e.lineno - 1]
                    error_msg += f"\n  Line {e.lineno}: {error_line.strip()}"

                    # Add pointer to error location if available
                    if hasattr(e, "column") and e.column:
                        error_msg += f"\n  {' ' * (len(str(e.lineno)) + 8 + e.column - 1)}^"

            logger.error(f"Template validation failed: {error_msg}")
            return False, error_msg, set()

        except Exception as e:
            # Catch any other template-related errors
            error_msg = f"Template validation error: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, set()

    def validate_templates(self, templates: dict[str, str]) -> Tuple[bool, dict[str, str]]:
        """
        Validate multiple templates at once.

        Args:
            templates: Dictionary mapping template names to template strings

        Returns:
            Tuple containing:
            - all_valid (bool): True if all templates are valid
            - errors (dict): Dictionary mapping template names to error messages
            (empty dict if all valid)
        """
        errors = {}

        for name, template_str in templates.items():
            is_valid, error_msg, _ = self.validate_template(template_str)
            if not is_valid:
                errors[name] = error_msg

        return len(errors) == 0, errors

    def extract_variables(self, template_str: str) -> Set[str]:
        """
        Extract all variable names from a template without validation.

        Args:
            template_str: The Jinja2 template string

        Returns:
            Set of variable names used in the template
        """
        try:
            ast = self.env.parse(template_str)
            return meta.find_undeclared_variables(ast)
        except Exception as e:
            logger.warning(f"Failed to extract variables from template: {e}")
            return set()
