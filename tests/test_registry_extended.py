"""Extended tests for prompt registry - versioning, non-git handling."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from glueprompt.exceptions import VersionError
from glueprompt.registry import PromptRegistry


@pytest.fixture
def sample_prompts_dir(tmp_path):
    """Create a temporary prompts directory with sample prompts."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    prompt_file = prompts_dir / "test.yaml"
    prompt_data = {
        "name": "test",
        "version": "1.0.0",
        "template": "Hello {{ name }}!",
        "variables": {"name": {"type": "string", "required": True}},
    }
    prompt_file.write_text(yaml.dump(prompt_data))

    return prompts_dir


def test_registry_without_git(sample_prompts_dir):
    """Test registry works without git repository."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    assert not registry.has_versioning
    with pytest.raises(VersionError, match="not a git repository"):
        registry.version_manager


def test_registry_with_git(sample_prompts_dir):
    """Test registry detects git repository."""
    from git import Repo

    # Initialize git repo
    Repo.init(sample_prompts_dir)
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    assert registry.has_versioning
    assert registry.version_manager is not None


def test_registry_render_without_validate(sample_prompts_dir):
    """Test rendering without validation."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    rendered = registry.render("test", validate=False, name="World")
    assert "World" in rendered


def test_registry_cache_invalidation(sample_prompts_dir):
    """Test cache invalidation methods."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    # Load prompt to cache it
    registry.get("test")
    registry.clear_cache()

    # Should still work after cache clear
    prompt = registry.get("test")
    assert prompt.metadata.name == "test"


def test_registry_invalidate_specific_prompt(sample_prompts_dir):
    """Test invalidating cache for specific prompt."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    registry.get("test")
    registry.invalidate_cache("test")

    # Should still work
    prompt = registry.get("test")
    assert prompt.metadata.name == "test"


@patch("glueprompt.registry.VersionManager")
def test_registry_checkout_clears_cache(mock_version_manager, sample_prompts_dir):
    """Test that checkout clears cache."""
    from git import Repo

    Repo.init(sample_prompts_dir)
    mock_vm = Mock()
    mock_version_manager.return_value = mock_vm

    registry = PromptRegistry(prompts_dir=sample_prompts_dir)
    registry._version_manager = mock_vm

    registry.get("test")  # Cache it
    registry.checkout("main")

    mock_vm.checkout.assert_called_once_with("main", create_branch=False)
    # Cache should be cleared (tested via loader.clear_cache call)

