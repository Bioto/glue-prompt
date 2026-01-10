"""Tests for template renderer."""

import pytest

from glueprompt.exceptions import TemplateRenderError
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition
from glueprompt.renderer import TemplateRenderer


def test_render_simple_template():
    """Test rendering a simple template."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    renderer = TemplateRenderer()
    result = renderer.render(prompt, name="World")

    assert result == "Hello World!"


def test_render_with_defaults():
    """Test rendering with default values."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}! You are {{ role }}.",
        variables={
            "name": VariableDefinition(type="string", required=True),
            "role": VariableDefinition(type="string", required=False, default="user"),
        },
    )

    renderer = TemplateRenderer()
    result = renderer.render(prompt, name="Alice")

    assert result == "Hello Alice! You are user."


def test_render_missing_required():
    """Test rendering with missing required variable."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    renderer = TemplateRenderer()

    with pytest.raises(TemplateRenderError) as exc_info:
        renderer.render(prompt)

    assert "Missing required variables" in str(exc_info.value)


def test_render_invalid_template():
    """Test rendering invalid template."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }",  # Missing closing braces
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    renderer = TemplateRenderer()

    with pytest.raises(TemplateRenderError):
        renderer.render(prompt, name="World")

