"""Tests for prompt loader."""

import tempfile
from pathlib import Path

import pytest
import yaml

from glueprompt.exceptions import PromptNotFoundError, PromptValidationError
from glueprompt.loader import PromptLoader


def test_load_prompt_yaml():
    """Test loading a prompt from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test-prompt.yaml"

        prompt_data = {
            "name": "test-prompt",
            "version": "1.0.0",
            "description": "A test prompt",
            "template": "Hello {{ name }}!",
            "variables": {
                "name": {
                    "type": "string",
                    "required": True,
                    "description": "Name to greet",
                },
            },
        }

        with prompt_file.open("w") as f:
            yaml.dump(prompt_data, f)

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test-prompt")

        assert prompt.metadata.name == "test-prompt"
        assert prompt.metadata.version == "1.0.0"
        assert prompt.template == "Hello {{ name }}!"
        assert "name" in prompt.variables


def test_load_prompt_not_found():
    """Test loading a non-existent prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = PromptLoader(Path(tmpdir))

        with pytest.raises(PromptNotFoundError):
            loader.load("nonexistent-prompt")


def test_load_prompt_invalid_yaml():
    """Test loading invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "invalid.yaml"

        with prompt_file.open("w") as f:
            f.write("invalid: yaml: content: [unclosed")

        loader = PromptLoader(prompts_dir)

        with pytest.raises(PromptValidationError):
            loader.load("invalid")


def test_load_prompt_missing_template():
    """Test loading prompt without template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "no-template.yaml"

        prompt_data = {
            "name": "test",
            "version": "1.0.0",
        }

        with prompt_file.open("w") as f:
            yaml.dump(prompt_data, f)

        loader = PromptLoader(prompts_dir)

        with pytest.raises(PromptValidationError):
            loader.load("no-template")


def test_loader_caching():
    """Test prompt caching."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "cached.yaml"

        prompt_data = {
            "name": "cached",
            "version": "1.0.0",
            "template": "Hello!",
        }

        with prompt_file.open("w") as f:
            yaml.dump(prompt_data, f)

        loader = PromptLoader(prompts_dir, cache_enabled=True)

        # Load twice - should use cache second time
        prompt1 = loader.load("cached")
        prompt2 = loader.load("cached")

        assert prompt1 is prompt2  # Same object from cache

        # Clear cache
        loader.clear_cache()
        prompt3 = loader.load("cached")

        assert prompt3 is not prompt1  # New object after cache clear

