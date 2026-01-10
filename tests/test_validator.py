"""Tests for prompt validator."""

import pytest

from glueprompt.exceptions import PromptValidationError
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition
from glueprompt.validator import PromptValidator


def test_validate_valid_prompt():
    """Test validating a valid prompt."""
    metadata = PromptMetadata(name="test-prompt")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="string", required=True),
        },
    )

    validator = PromptValidator()
    errors = validator.validate(prompt)

    assert errors == []


def test_validate_missing_name():
    """Test validating prompt without name."""
    metadata = PromptMetadata(name="")
    prompt = Prompt(
        metadata=metadata,
        template="Hello!",
        variables={},
    )

    validator = PromptValidator()
    errors = validator.validate(prompt)

    assert len(errors) > 0
    assert any("name" in error.lower() for error in errors)


def test_validate_undefined_variable():
    """Test validating prompt with undefined variable."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={},  # name is used but not defined
    )

    validator = PromptValidator()
    errors = validator.validate(prompt)

    assert len(errors) > 0
    assert any("undefined" in error.lower() for error in errors)


def test_validate_invalid_type():
    """Test validating prompt with invalid variable type."""
    metadata = PromptMetadata(name="test")
    prompt = Prompt(
        metadata=metadata,
        template="Hello {{ name }}!",
        variables={
            "name": VariableDefinition(type="invalid_type", required=True),
        },
    )

    validator = PromptValidator()
    errors = validator.validate(prompt)

    assert len(errors) > 0
    assert any("invalid type" in error.lower() for error in errors)


def test_validate_and_raise():
    """Test validate_and_raise method."""
    metadata = PromptMetadata(name="")
    prompt = Prompt(
        metadata=metadata,
        template="Hello!",
        variables={},
    )

    validator = PromptValidator()

    with pytest.raises(PromptValidationError):
        validator.validate_and_raise(prompt)

