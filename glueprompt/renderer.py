"""Template rendering using Jinja2."""

from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateError, UndefinedError

from glueprompt.exceptions import TemplateRenderError
from glueprompt.logging import get_logger
from glueprompt.models.prompt import Prompt

logger = get_logger(__name__)


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
            undefined=StrictUndefined,  # Raise errors for undefined variables
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
        logger.debug(f"Rendering template for prompt: {prompt.metadata.name}")

        # Merge defaults with provided variables
        merged_vars = prompt.get_variable_defaults()
        merged_vars.update(variables)
        logger.debug(f"Merged variables: {list(merged_vars.keys())} (provided: {list(variables.keys())}, defaults: {list(prompt.get_variable_defaults().keys())})")

        # Check required variables
        required = prompt.get_required_variables()
        missing = [var for var in required if var not in merged_vars]
        if missing:
            logger.error(f"Missing required variables: {missing}")
            raise TemplateRenderError(
                f"Missing required variables: {', '.join(missing)}"
            )

        try:
            template = self.env.from_string(prompt.template)
            rendered = template.render(**merged_vars)
            logger.debug(f"Template rendered successfully (length={len(rendered)} chars)")
            return rendered
        except UndefinedError as e:
            logger.error(f"Undefined variable in template: {e}", exc_info=True)
            raise TemplateRenderError(
                f"Undefined variable in template: {e}"
            ) from e
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}", exc_info=True)
            raise TemplateRenderError(f"Template rendering error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected rendering error: {e}", exc_info=True)
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
            # Just parse the template to check syntax
            self.env.parse(prompt.template)
        except TemplateError as e:
            errors.append(f"Template syntax error: {e}")

        return errors

