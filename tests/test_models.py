"""Tests for prompt models."""

import pytest

from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition


def test_prompt_metadata():
    """Test PromptMetadata model."""
    metadata = PromptMetadata(
        name="test-prompt",
        version="1.0.0",
        description="A test prompt",
        author="test-author",
        tags=["test", "example"],
    )

    assert metadata.name == "test-prompt"
    assert metadata.version == "1.0.0"
    assert metadata.description == "A test prompt"
    assert metadata.author == "test-author"
    assert metadata.tags == ["test", "example"]


def test_variable_definition():
    """Test VariableDefinition model."""
    var_def = VariableDefinition(
        type="string",
        required=True,
        description="A test variable",
    )

    assert var_def.type == "string"
    assert var_def.required is True
    assert var_def.description == "A test variable"


def test_prompt_model():
    """Test Prompt model."""
    metadata = PromptMetadata(name="test-prompt")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    assert prompt.metadata.name == "test-prompt"
    assert prompt.template == "Hello {{ name }}!"
    assert "name" in prompt.variables
    assert prompt.get_required_variables() == ["name"]


def test_prompt_get_defaults():
    """Test getting variable defaults."""
    metadata = PromptMetadata(name="test-prompt")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}! {{ optional }}",
        variables={
            "name": VariableDefinition(type="string", required=True),
            "optional": VariableDefinition(type="string", required=False, default="world"),
        },
    )

    defaults = prompt.get_variable_defaults()
    assert defaults == {"optional": "world"}
    assert prompt.get_required_variables() == ["name"]

