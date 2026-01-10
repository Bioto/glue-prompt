"""Prompt models for YAML-based prompt definitions."""

from typing import Any

from pydantic import BaseModel, Field


class VariableDefinition(BaseModel):
    """Definition of a template variable.

    Attributes:
        type: The type of the variable (string, int, float, bool, etc.)
        required: Whether the variable is required
        default: Default value if not required
        description: Human-readable description of the variable
    """

    type: str = Field(default="string", description="Variable type")
    required: bool = Field(default=True, description="Whether variable is required")
    default: Any = Field(default=None, description="Default value if not required")
    description: str = Field(default="", description="Variable description")


class PromptMetadata(BaseModel):
    """Metadata for a prompt.

    Attributes:
        name: Prompt name/identifier
        version: Semantic version of the prompt
        description: Human-readable description
        author: Author name
        tags: List of tags for categorization
    """

    name: str = Field(description="Prompt name/identifier")
    version: str = Field(default="1.0.0", description="Semantic version")
    description: str = Field(default="", description="Prompt description")
    author: str = Field(default="", description="Author name")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class Prompt(BaseModel):
    """A prompt with template and metadata.

    Attributes:
        metadata: Prompt metadata
        template: Jinja2 template string
        variables: Variable definitions for template rendering
    """

    metadata: PromptMetadata = Field(description="Prompt metadata")
    template: str = Field(description="Jinja2 template string")
    variables: dict[str, VariableDefinition] = Field(
        default_factory=dict, description="Variable definitions"
    )

    def get_required_variables(self) -> list[str]:
        """Get list of required variable names.

        Returns:
            List of variable names that are required
        """
        return [
            name for name, var_def in self.variables.items() if var_def.required
        ]

    def get_variable_defaults(self) -> dict[str, Any]:
        """Get default values for optional variables.

        Returns:
            Dictionary mapping variable names to their default values
        """
        return {
            name: var_def.default
            for name, var_def in self.variables.items()
            if not var_def.required and var_def.default is not None
        }

