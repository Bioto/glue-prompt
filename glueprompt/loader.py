"""Load prompts from YAML files."""

import time
from pathlib import Path
from typing import Any

import yaml

from glueprompt.exceptions import PromptNotFoundError, PromptValidationError
from glueprompt.logging import get_logger
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition

logger = get_logger(__name__)


class PromptLoader:
    """Loads and caches prompts from YAML files.

    Attributes:
        prompts_dir: Directory containing prompt YAML files
        cache: In-memory cache of loaded prompts
        cache_ttl: Cache TTL in seconds
    """

    def __init__(
        self,
        prompts_dir: Path | str,
        cache_enabled: bool = True,
        cache_ttl: int = 300,
    ):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Path to directory containing prompts
            cache_enabled: Whether to enable caching
            cache_ttl: Cache TTL in seconds
        """
        self.prompts_dir = Path(prompts_dir)
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache: dict[str, tuple[Prompt, float]] = {}

    def _get_cache_key(self, prompt_path: str) -> str:
        """Generate cache key for a prompt path.

        Args:
            prompt_path: Relative path to prompt file

        Returns:
            Cache key string
        """
        return str(self.prompts_dir / prompt_path)

    def _is_cache_valid(self, cache_entry: tuple[Prompt, float]) -> bool:
        """Check if cache entry is still valid.

        Args:
            cache_entry: Tuple of (Prompt, timestamp)

        Returns:
            True if cache is valid
        """
        if not self.cache_enabled:
            return False
        _, timestamp = cache_entry
        return (time.time() - timestamp) < self.cache_ttl

    def _validate_prompt_path(self, resolved_path: Path) -> None:
        """Validate that resolved path doesn't escape prompts directory.

        Args:
            resolved_path: Resolved path to validate

        Raises:
            PromptValidationError: If path escapes prompts directory
        """
        try:
            resolved_prompts_dir = self.prompts_dir.resolve()
            resolved_file = resolved_path.resolve()
            if not resolved_file.is_relative_to(resolved_prompts_dir):
                logger.error(
                    f"Path traversal attempt detected: {resolved_path} "
                    f"escapes prompts directory {resolved_prompts_dir}"
                )
                raise PromptValidationError(
                    f"Invalid prompt path: path escapes prompts directory"
                )
        except (OSError, ValueError) as e:
            # Handle cases where path resolution fails (e.g., broken symlinks)
            logger.error(f"Failed to resolve path: {resolved_path}", exc_info=True)
            raise PromptValidationError(f"Invalid prompt path: {e}") from e

    def _resolve_prompt_file(self, prompt_path: str) -> Path:
        """Resolve prompt path to actual file.

        Args:
            prompt_path: Relative path (e.g., "assistants/helpful-bot")

        Returns:
            Path to prompt YAML file

        Raises:
            PromptNotFoundError: If prompt file doesn't exist
            PromptValidationError: If path escapes prompts directory
        """
        # Try with .yaml extension
        yaml_path = self.prompts_dir / f"{prompt_path}.yaml"
        if yaml_path.exists():
            self._validate_prompt_path(yaml_path)
            logger.debug(f"Resolved prompt file: {prompt_path} -> {yaml_path}")
            return yaml_path

        # Try with .yml extension
        yml_path = self.prompts_dir / f"{prompt_path}.yml"
        if yml_path.exists():
            self._validate_prompt_path(yml_path)
            logger.debug(f"Resolved prompt file: {prompt_path} -> {yml_path}")
            return yml_path

        # Try as directory with index.yaml
        index_path = self.prompts_dir / prompt_path / "index.yaml"
        if index_path.exists():
            self._validate_prompt_path(index_path)
            logger.debug(f"Resolved prompt file: {prompt_path} -> {index_path}")
            return index_path

        logger.error(f"Prompt file not found: {prompt_path} (tried: {yaml_path}, {yml_path}, {index_path})")
        raise PromptNotFoundError(
            f"Prompt not found: {prompt_path}. "
            f"Tried: {yaml_path}, {yml_path}, {index_path}"
        )

    def _parse_yaml(self, yaml_data: dict[str, Any]) -> Prompt:
        """Parse YAML data into Prompt model.

        Args:
            yaml_data: Parsed YAML dictionary

        Returns:
            Prompt instance

        Raises:
            PromptValidationError: If YAML structure is invalid
        """
        try:
            # Extract metadata
            metadata = PromptMetadata(
                name=yaml_data.get("name", ""),
                version=yaml_data.get("version", "1.0.0"),
                description=yaml_data.get("description", ""),
                author=yaml_data.get("author", ""),
                tags=yaml_data.get("tags", []),
            )

            # Extract template
            template = yaml_data.get("template", "")
            if not template:
                raise PromptValidationError("Prompt template is required")

            # Extract variables
            variables: dict[str, VariableDefinition] = {}
            var_defs = yaml_data.get("variables", {})
            for var_name, var_data in var_defs.items():
                if isinstance(var_data, dict):
                    variables[var_name] = VariableDefinition(**var_data)
                else:
                    # Simple string format: just the type
                    variables[var_name] = VariableDefinition(
                        type=str(var_data) if var_data else "string"
                    )

            return Prompt(
                metadata=metadata,
                template=template,
                variables=variables,
            )
        except Exception as e:
            logger.error(f"Failed to parse prompt YAML: {e}", exc_info=True)
            raise PromptValidationError(f"Failed to parse prompt YAML: {e}") from e

    def load(self, prompt_path: str, use_cache: bool = True) -> Prompt:
        """Load a prompt from file.

        Args:
            prompt_path: Relative path to prompt (e.g., "assistants/helpful-bot")
            use_cache: Whether to use cache if available

        Returns:
            Loaded Prompt instance

        Raises:
            PromptNotFoundError: If prompt file doesn't exist
            PromptValidationError: If prompt YAML is invalid
        """
        cache_key = self._get_cache_key(prompt_path)

        # Check cache
        if use_cache and self.cache_enabled and cache_key in self.cache:
            cached_prompt, timestamp = self.cache[cache_key]
            if self._is_cache_valid((cached_prompt, timestamp)):
                logger.debug(f"Cache hit for prompt: {prompt_path}")
                return cached_prompt
            else:
                logger.debug(f"Cache expired for prompt: {prompt_path}")

        logger.debug(f"Cache miss for prompt: {prompt_path}")

        # Load from file
        prompt_file = self._resolve_prompt_file(prompt_path)

        try:
            with prompt_file.open("r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            if not isinstance(yaml_data, dict):
                raise PromptValidationError(
                    f"Prompt YAML must be a dictionary, got {type(yaml_data)}"
                )

            prompt = self._parse_yaml(yaml_data)

            # Update cache
            if self.cache_enabled:
                self.cache[cache_key] = (prompt, time.time())

            logger.info(
                f"Loaded prompt: {prompt_path} (name={prompt.metadata.name}, "
                f"version={prompt.metadata.version}, cached=False)"
            )
            return prompt
        except FileNotFoundError as e:
            logger.error(f"Prompt file not found: {prompt_file}", exc_info=True)
            raise PromptNotFoundError(f"Prompt file not found: {prompt_file}") from e
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in prompt file {prompt_file}: {e}", exc_info=True)
            raise PromptValidationError(f"Invalid YAML in prompt file: {e}") from e

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.debug(f"Cleared prompt cache ({cache_size} entries)")

    def invalidate_cache(self, prompt_path: str | None = None) -> None:
        """Invalidate cache for a specific prompt or all prompts.

        Args:
            prompt_path: Specific prompt path to invalidate, or None for all
        """
        if prompt_path is None:
            self.clear_cache()
        else:
            cache_key = self._get_cache_key(prompt_path)
            if cache_key in self.cache:
                self.cache.pop(cache_key, None)
                logger.debug(f"Invalidated cache for prompt: {prompt_path}")
            else:
                logger.debug(f"Cache entry not found for prompt: {prompt_path}")

