"""Custom exceptions for glue-prompt."""


class GluePromptError(Exception):
    """Base exception for all glue-prompt errors."""

    pass


class PromptNotFoundError(GluePromptError):
    """Raised when a prompt cannot be found."""

    pass


class PromptValidationError(GluePromptError):
    """Raised when prompt validation fails."""

    pass


class VersionError(GluePromptError):
    """Raised when version operations fail."""

    pass


class GitOperationError(GluePromptError):
    """Raised when git operations fail."""

    pass


class TemplateRenderError(GluePromptError):
    """Raised when template rendering fails."""

    pass

