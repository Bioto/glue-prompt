"""Template rendering using Jinja2."""

from typing import Any

from jinja2 import Environment, Template, TemplateError, UndefinedError

from glueprompt.exceptions import TemplateRenderError
from glueprompt.models.prompt import Prompt


class TemplateRenderer:
    """Renders Jinja2 templates with variable substitution.

    Attributes:
        env: Jinja2 environment for template rendering
    """

    def __init__(self, jinja_env: Environment | None = None):
        """Initialize the template renderer.

        Args:
            jinja_env: Custom Jinja2 environment, or None for default
        """
        self.env = jinja_env or Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(
        self,
        prompt: Prompt,
        **variables: Any,
    ) -> str:
        """Render a prompt template with variables.

        Args:
            prompt: Prompt instance to render
            **variables: Template variables to substitute

        Returns:
            Rendered prompt string

        Raises:
            TemplateRenderError: If rendering fails or required variables missing
        """
        # Merge defaults with provided variables
        merged_vars = prompt.get_variable_defaults()
        merged_vars.update(variables)

        # Check required variables
        required = prompt.get_required_variables()
        missing = [var for var in required if var not in merged_vars]
        if missing:
            raise TemplateRenderError(
                f"Missing required variables: {', '.join(missing)}"
            )

        try:
            template = self.env.from_string(prompt.template)
            return template.render(**merged_vars)
        except UndefinedError as e:
            raise TemplateRenderError(
                f"Undefined variable in template: {e}"
            ) from e
        except TemplateError as e:
            raise TemplateRenderError(f"Template rendering error: {e}") from e
        except Exception as e:
            raise TemplateRenderError(f"Unexpected rendering error: {e}") from e

    def validate_template(self, prompt: Prompt) -> list[str]:
        """Validate that template syntax is correct.

        Args:
            prompt: Prompt to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        try:
            template = self.env.parse(prompt.template)
            # Check for undefined variables that aren't in the variables dict
            undefined_vars = self.env.get_template(
                prompt.template, globals={}
            ).get_corresponding_lineno(0)
            # This is a simplified check - Jinja2 doesn't easily expose undefined vars
            # For now, we'll just check syntax
        except TemplateError as e:
            errors.append(f"Template syntax error: {e}")

        return errors

