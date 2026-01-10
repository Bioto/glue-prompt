"""Extended tests for template renderer - complex templates, custom env."""

import pytest
from jinja2 import Environment

from glueprompt.exceptions import TemplateRenderError
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition
from glueprompt.renderer import TemplateRenderer


def test_render_with_loop():
    """Test rendering template with Jinja2 loop."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Items:\n{% for item in items %}- {{ item }}\n{% endfor %}",
        variables={
            "items": VariableDefinition(type="list", required=True),
        },
    )

    renderer = TemplateRenderer()
    result = renderer.render(prompt, items=["apple", "banana", "cherry"])

    assert "apple" in result
    assert "banana" in result
    assert "cherry" in result


def test_render_with_conditional():
    """Test rendering template with Jinja2 conditional."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello{% if name %} {{ name }}{% endif %}!",
        variables={
            "name": VariableDefinition(type="string", required=False, default=""),
        },
    )

    renderer = TemplateRenderer()
    result1 = renderer.render(prompt, name="World")
    result2 = renderer.render(prompt)

    assert result1 == "Hello World!"
    assert result2 == "Hello!"  # Empty string makes conditional False, no space added


def test_render_undefined_variable():
    """Test rendering with undefined variable in template."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={},  # name not defined
    )

    renderer = TemplateRenderer()

    # Jinja2 will raise UndefinedError when rendering undefined variable
    with pytest.raises(TemplateRenderError, match="Undefined variable"):
        renderer.render(prompt)


def test_render_undefined_in_template():
    """Test rendering with undefined variable referenced in template."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }} and {{ missing }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    renderer = TemplateRenderer()

    with pytest.raises(TemplateRenderError, match="Undefined variable"):
        renderer.render(prompt, name="World")


def test_render_custom_jinja_env():
    """Test renderer with custom Jinja2 environment."""
    custom_env = Environment(trim_blocks=False, lstrip_blocks=False)
    renderer = TemplateRenderer(jinja_env=custom_env)

    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    result = renderer.render(prompt, name="World")
    assert "World" in result


def test_validate_template_syntax():
    """Test template syntax validation."""
    renderer = TemplateRenderer()

    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }",  # Invalid syntax
        variables={},
    )

    errors = renderer.validate_template(prompt)
    assert len(errors) > 0


def test_validate_template_valid():
    """Test template validation with valid template."""
    renderer = TemplateRenderer()

    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={},
    )

    # validate_template only checks syntax, not undefined variables
    errors = renderer.validate_template(prompt)
    assert len(errors) == 0


def test_render_variable_override_default():
    """Test that provided variables override defaults."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=False, default="Default"),
        },
    )

    renderer = TemplateRenderer()
    result = renderer.render(prompt, name="Override")

    assert result == "Hello Override!"
    assert "Default" not in result

