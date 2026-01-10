"""Glue-Prompt - Git-based prompt versioning system.

Glue-Prompt provides a simple yet powerful way to version and manage prompts
using git branches. Prompts are stored as YAML files in a git submodule, and
you can switch between versions by checking out different branches.

Quick Start:
    >>> from glueprompt import PromptRegistry
    >>>
    >>> # Clone a prompts repo (one-time setup)
    >>> from glueprompt import RepoManager
    >>> manager = RepoManager()
    >>> manager.clone("https://github.com/org/my-prompts.git")
    >>>
    >>> # Use prompts
    >>> from glueprompt import PromptRegistry
    >>> registry = PromptRegistry(manager.get_path("my-prompts"))
    >>> rendered = registry.render("assistants/helpful-bot", name="Claude")
    >>>
    >>> # Switch versions
    >>> registry.checkout("v1.0")

Main Components:
    - PromptRegistry: Main entry point for prompt management
    - Prompt: Loaded prompt with rendering capabilities
    - VersionManager: Git branch/tag operations
    - PromptLoader: Load and parse YAML prompts
"""

from glueprompt.logging import get_logger
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition
from glueprompt.models.version import BranchInfo, VersionInfo
from glueprompt.registry import PromptRegistry
from glueprompt.repo_manager import RepoManager

__all__ = [
    "PromptRegistry",
    "RepoManager",
    "Prompt",
    "PromptMetadata",
    "VariableDefinition",
    "VersionInfo",
    "BranchInfo",
    "get_logger",
]

__version__ = "0.1.0"

