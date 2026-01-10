"""Configuration settings for glue-prompt."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class GluePromptSettings(BaseSettings):
    """Settings for glue-prompt.

    Attributes:
        default_prompts_path: Default path to prompts directory
        cache_enabled: Whether to cache loaded prompts
        cache_ttl_seconds: Cache TTL in seconds
    """

    default_prompts_path: Path = Path("./prompts")
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_prefix="glueprompt_",
        case_sensitive=False,
    )


# Global settings instance
_settings: GluePromptSettings | None = None


def get_settings() -> GluePromptSettings:
    """Get global settings instance.

    Returns:
        Global GluePromptSettings instance
    """
    global _settings
    if _settings is None:
        _settings = GluePromptSettings()
    return _settings


def reload_settings() -> GluePromptSettings:
    """Reload settings from environment.

    Returns:
        New GluePromptSettings instance
    """
    global _settings
    _settings = GluePromptSettings()
    return _settings


# Convenience accessor
settings = get_settings()

