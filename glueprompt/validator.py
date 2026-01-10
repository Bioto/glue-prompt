"""Prompt validation utilities."""

import re
from typing import Any

from jinja2 import Environment, TemplateError

from glueprompt.exceptions import PromptValidationError
from glueprompt.models.prompt import Prompt


class PromptValidator:
    """Validates prompts for correctness and completeness.

    Attributes:
        jinja_env: Jinja2 environment for template parsing
    """

    def __init__(self, jinja_env: Environment | None = None):
        """Initialize the validator.

        Args:
            jinja_env: Custom Jinja2 environment, or None for default
        """
        self.jinja_env = jinja_env or Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def validate(self, prompt: Prompt) -> list[str]:
        """Validate a prompt for correctness.

        Checks:
        - Template syntax is valid
        - Required variables are defined
        - Variable definitions match template usage
        - Metadata is complete

        Args:
            prompt: Prompt to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        # Validate metadata
        if not prompt.metadata.name:
            errors.append("Prompt metadata must have a 'name' field")

        # Validate template syntax
        try:
            self.jinja_env.parse(prompt.template)
        except TemplateError as e:
            errors.append(f"Template syntax error: {e}")

        # Check for undefined variables in template
        template_vars = self._extract_template_variables(prompt.template)
        defined_vars = set(prompt.variables.keys())

        # Check for variables used in template but not defined
        undefined_vars = template_vars - defined_vars
        if undefined_vars:
            errors.append(
                f"Template uses undefined variables: {', '.join(sorted(undefined_vars))}"
            )

        # Check for variables defined but not used (warning, not error)
        unused_vars = defined_vars - template_vars
        if unused_vars:
            # This is just informational, not an error

            pass

        # Validate variable definitions
        for var_name, var_def in prompt.variables.items():
            if var_def.required and var_def.default is not None:
                errors.append(
                    f"Variable '{var_name}' is required but has a default value"
                )

            # Validate type (basic check)
            valid_types = {"string", "int", "float", "bool", "list", "dict", "any"}
            if var_def.type not in valid_types:
                errors.append(
                    f"Variable '{var_name}' has invalid type '{var_def.type}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )

        return errors

    def _extract_template_variables(self, template: str) -> set[str]:
        """Extract variable names from Jinja2 template.

        Args:
            template: Jinja2 template string

        Returns:
            Set of variable names used in template
        """
        variables: set[str] = set()

        # Pattern to match Jinja2 variable expressions: {{ var }} or {{ var.attr }}
        # Also handles {% set var = ... %} and {% for var in ... %}
        var_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\}\}"
        for_match = r"\{\%\s*for\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+in\s+"
        set_match = r"\{\%\s*set\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*="

        # Find all {{ var }} patterns
        for match in re.finditer(var_pattern, template):
            var_expr = match.group(1)
            # Extract base variable name (before first dot)
            base_var = var_expr.split(".")[0]
            variables.add(base_var)

        # Find {% for var in ... %} patterns
        for match in re.finditer(for_match, template):
            var_name = match.group(1)
            variables.add(var_name)

        # Find {% set var = ... %} patterns
        for match in re.finditer(set_match, template):
            var_name = match.group(1)
            variables.add(var_name)

        return variables

    def validate_and_raise(self, prompt: Prompt) -> None:
        """Validate prompt and raise exception if invalid.

        Args:
            prompt: Prompt to validate

        Raises:
            PromptValidationError: If validation fails
        """
        errors = self.validate(prompt)
        if errors:
            error_msg = "Prompt validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise PromptValidationError(error_msg)

