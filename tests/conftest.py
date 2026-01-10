"""Pytest configuration for glue-prompt tests."""

from pathlib import Path

import pytest
import yaml

from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary directory for prompts."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    return prompts_dir


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data dictionary."""
    return {
        "name": "test-prompt",
        "version": "1.0.0",
        "description": "A test prompt",
        "author": "test-author",
        "tags": ["test", "sample"],
        "template": "Hello {{ name }}!",
        "variables": {
            "name": {
                "type": "string",
                "required": True,
                "description": "Name to greet",
            },
        },
    }


@pytest.fixture
def sample_prompt_file(temp_prompts_dir, sample_prompt_data):
    """Create a sample prompt YAML file."""
    prompt_file = temp_prompts_dir / "test-prompt.yaml"
    with prompt_file.open("w") as f:
        yaml.dump(sample_prompt_data, f)
    return prompt_file


@pytest.fixture
def sample_prompt():
    """Create a sample Prompt object."""
    metadata = PromptMetadata(
        name="test-prompt",
        version="1.0.0",
        description="A test prompt",
        author="test-author",
        tags=["test", "sample"],
    )
    return Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(
                type="string",
                required=True,
                description="Name to greet",
            ),
        },
    )


@pytest.fixture
def complex_prompt():
    """Create a more complex Prompt object with multiple variables."""
    metadata = PromptMetadata(
        name="complex-prompt",
        version="1.0.0",
        description="A complex prompt with multiple variables",
    )
    return Prompt(
        metadata=metadata,
        template="Hello {{ name }}! You are {{ role }}. Status: {{ status }}.",
        variables={
            "name": VariableDefinition(type="string", required=True),
            "role": VariableDefinition(
                type="string",
                required=False,
                default="user",
                description="User role",
            ),
            "status": VariableDefinition(
                type="string",
                required=True,
                description="Current status",
            ),
        },
    )
