"""Tests for prompt registry."""


import pytest
import yaml

from glueprompt.exceptions import PromptNotFoundError
from glueprompt.registry import PromptRegistry


@pytest.fixture
def sample_prompts_dir(tmp_path):
    """Create a temporary prompts directory with sample prompts."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create a sample prompt
    prompt_file = prompts_dir / "assistants" / "helpful-bot.yaml"
    prompt_file.parent.mkdir()

    prompt_data = {
        "name": "helpful-bot",
        "version": "1.0.0",
        "description": "A helpful assistant",
        "author": "test-author",
        "tags": ["assistant", "general"],
        "template": "You are a helpful assistant named {{ name }}.\n{{ extra_instructions }}",
        "variables": {
            "name": {
                "type": "string",
                "required": True,
                "description": "The assistant's name",
            },
            "extra_instructions": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Additional instructions",
            },
        },
    }

    with prompt_file.open("w") as f:
        yaml.dump(prompt_data, f)

    return prompts_dir


def test_registry_get(sample_prompts_dir):
    """Test getting a prompt from registry."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    prompt = registry.get("assistants/helpful-bot")

    assert prompt.metadata.name == "helpful-bot"
    assert prompt.metadata.version == "1.0.0"
    assert "name" in prompt.variables


def test_registry_render(sample_prompts_dir):
    """Test rendering a prompt through registry."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    rendered = registry.render("assistants/helpful-bot", name="Claude", extra_instructions="Be concise.")

    assert "Claude" in rendered
    assert "Be concise" in rendered


def test_registry_get_not_found(sample_prompts_dir):
    """Test getting a non-existent prompt."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    with pytest.raises(PromptNotFoundError):
        registry.get("nonexistent/prompt")


def test_registry_validate(sample_prompts_dir):
    """Test validating a prompt through registry."""
    registry = PromptRegistry(prompts_dir=sample_prompts_dir)

    errors = registry.validate("assistants/helpful-bot")

    assert errors == []  # Should be valid

