"""Main registry API for prompt management."""

from pathlib import Path
from typing import Any

from glueprompt.config import get_settings
from glueprompt.exceptions import GitOperationError, VersionError
from glueprompt.loader import PromptLoader
from glueprompt.models.prompt import Prompt
from glueprompt.models.version import BranchInfo, VersionInfo
from glueprompt.renderer import TemplateRenderer
from glueprompt.validator import PromptValidator
from glueprompt.versioning import VersionManager


class PromptRegistry:
    """Main entry point for prompt management.

    Provides a unified API for loading, rendering, and versioning prompts.
    Git versioning features are optional - if the prompts directory is not
    a git repository, basic prompt loading/rendering still works.

    Attributes:
        prompts_dir: Path to prompts directory
        loader: PromptLoader instance
        renderer: TemplateRenderer instance
        validator: PromptValidator instance
        version_manager: VersionManager instance (None if not a git repo)
    """

    def __init__(
        self,
        prompts_dir: Path | str | None = None,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
    ):
        """Initialize the prompt registry.

        Args:
            prompts_dir: Path to prompts directory (can be git repo or plain dir).
                        If None, uses default from settings.
            cache_enabled: Whether to enable prompt caching
            cache_ttl: Cache TTL in seconds
        """
        settings = get_settings()

        if prompts_dir is None:
            prompts_dir = settings.default_prompts_path

        self.prompts_dir = Path(prompts_dir)
        self.loader = PromptLoader(
            self.prompts_dir,
            cache_enabled=cache_enabled,
            cache_ttl=cache_ttl,
        )
        self.renderer = TemplateRenderer()
        self.validator = PromptValidator()

        # Version manager is optional - only works if prompts_dir is a git repo
        self._version_manager: VersionManager | None = None
        try:
            self._version_manager = VersionManager(self.prompts_dir)
        except GitOperationError:
            # Not a git repo, versioning features disabled
            pass

    @property
    def version_manager(self) -> VersionManager:
        """Get version manager, raising if not available."""
        if self._version_manager is None:
            raise VersionError(
                f"Versioning not available: '{self.prompts_dir}' is not a git repository. "
                f"Initialize it with 'git init' or use 'glueprompt repo add <url>' to clone a versioned repo."
            )
        return self._version_manager

    @property
    def has_versioning(self) -> bool:
        """Check if versioning is available."""
        return self._version_manager is not None

    def get(self, prompt_path: str, validate: bool = True) -> Prompt:
        """Get a prompt by path.

        Args:
            prompt_path: Relative path to prompt (e.g., "assistants/helpful-bot")
            validate: Whether to validate the prompt after loading

        Returns:
            Loaded Prompt instance

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptValidationError: If validation fails
        """
        prompt = self.loader.load(prompt_path)

        if validate:
            self.validator.validate_and_raise(prompt)

        return prompt

    def render(
        self,
        prompt_path: str,
        validate: bool = True,
        **variables: Any,
    ) -> str:
        """Load and render a prompt.

        Args:
            prompt_path: Relative path to prompt
            validate: Whether to validate before rendering
            **variables: Template variables

        Returns:
            Rendered prompt string

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptValidationError: If validation fails
            TemplateRenderError: If rendering fails
        """
        prompt = self.get(prompt_path, validate=validate)
        return self.renderer.render(prompt, **variables)

    def validate(self, prompt_path: str) -> list[str]:
        """Validate a prompt.

        Args:
            prompt_path: Relative path to prompt

        Returns:
            List of validation errors (empty if valid)

        Raises:
            PromptNotFoundError: If prompt doesn't exist
        """
        prompt = self.loader.load(prompt_path)
        return self.validator.validate(prompt)

    def checkout(self, branch_or_tag: str, create_branch: bool = False) -> None:
        """Checkout a version (branch or tag).

        Args:
            branch_or_tag: Branch or tag name
            create_branch: If True and branch doesn't exist, create it

        Raises:
            VersionError: If checkout fails
        """
        self.version_manager.checkout(branch_or_tag, create_branch=create_branch)
        # Invalidate cache after version change
        self.loader.clear_cache()

    def current_version(self) -> VersionInfo:
        """Get current version.

        Returns:
            VersionInfo for current branch/tag
        """
        return self.version_manager.current_version()

    def list_versions(self) -> dict[str, list[VersionInfo | BranchInfo]]:
        """List all available versions.

        Returns:
            Dictionary with 'branches' and 'tags' keys
        """
        return {
            "branches": self.version_manager.list_branches(),
            "tags": self.version_manager.list_tags(),
        }

    def diff(
        self,
        prompt_path: str,
        version1: str | None = None,
        version2: str | None = None,
    ) -> str:
        """Get diff of a prompt between two versions.

        Args:
            prompt_path: Relative path to prompt
            version1: First version (None for current)
            version2: Second version (None for current)

        Returns:
            Git diff string

        Raises:
            VersionError: If diff operation fails
        """
        return self.version_manager.diff(prompt_path, version1, version2)

    def rollback(self, version: str) -> None:
        """Rollback to a previous version.

        Args:
            version: Branch or tag to rollback to

        Raises:
            VersionError: If rollback fails
        """
        self.checkout(version)

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self.loader.clear_cache()

    def invalidate_cache(self, prompt_path: str | None = None) -> None:
        """Invalidate cache for a prompt or all prompts.

        Args:
            prompt_path: Specific prompt path, or None for all
        """
        self.loader.invalidate_cache(prompt_path)

