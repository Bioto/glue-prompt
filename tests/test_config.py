"""Tests for configuration settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from glueprompt.config import GluePromptSettings, get_settings, reload_settings


def test_default_settings():
    """Test default settings values."""
    settings = GluePromptSettings()

    assert settings.default_prompts_path == Path("./prompts")
    assert settings.cache_enabled is True
    assert settings.cache_ttl_seconds == 300


@patch.dict(os.environ, {"GLUEPROMPT_DEFAULT_PROMPTS_PATH": "/custom/prompts"})
def test_settings_from_env():
    """Test loading settings from environment variables."""
    settings = GluePromptSettings()

    assert str(settings.default_prompts_path) == "/custom/prompts"


@patch.dict(os.environ, {"GLUEPROMPT_CACHE_ENABLED": "false"})
def test_settings_cache_disabled_from_env():
    """Test cache_enabled from environment."""
    settings = GluePromptSettings()

    assert settings.cache_enabled is False


@patch.dict(os.environ, {"GLUEPROMPT_CACHE_TTL_SECONDS": "600"})
def test_settings_cache_ttl_from_env():
    """Test cache_ttl_seconds from environment."""
    settings = GluePromptSettings()

    assert settings.cache_ttl_seconds == 600


def test_get_settings_singleton():
    """Test get_settings returns singleton instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_reload_settings():
    """Test reload_settings creates new instance."""
    settings1 = get_settings()
    settings2 = reload_settings()

    # Should be different instances
    assert settings1 is not settings2

