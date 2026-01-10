"""Tests for prompt differ - diff and comparison utilities."""

from glueprompt.differ import PromptDiffer
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition


def test_diff_prompts():
    """Test generating diff between two prompts."""
    metadata1 = PromptMetadata(name="test", version="1.0.0")
    prompt1 = Prompt(
        metadata=metadata1,
        template="Hello {{ name }}!",
        variables={"name": VariableDefinition(type="string", required=True)},
    )

    metadata2 = PromptMetadata(name="test", version="2.0.0")
    prompt2 = Prompt(
        metadata=metadata2,
        template="Hello {{ name }}! How are you?",
        variables={"name": VariableDefinition(type="string", required=True)},
    )

    diff = PromptDiffer.diff_prompts(prompt1, prompt2, "test-prompt")

    assert "1.0.0" in diff
    assert "2.0.0" in diff
    assert "How are you" in diff


def test_compare_metadata():
    """Test comparing metadata between prompts."""
    metadata1 = PromptMetadata(name="test1", version="1.0.0", description="Old")
    prompt1 = Prompt(
        metadata=metadata1,
        template="Hello!",
        variables={"old_var": VariableDefinition(type="string")},
    )

    metadata2 = PromptMetadata(name="test2", version="2.0.0", description="New")
    prompt2 = Prompt(
        metadata=metadata2,
        template="Hello!",
        variables={
            "new_var": VariableDefinition(type="string"),
            "old_var": VariableDefinition(type="string", default="changed"),
        },
    )

    comparison = PromptDiffer.compare_metadata(prompt1, prompt2)

    assert comparison["name_changed"] is True
    assert comparison["version_changed"] is True
    assert comparison["description_changed"] is True
    assert "old_var" not in comparison["variables_removed"]  # old_var exists in both
    assert "new_var" in comparison["variables_added"]
    assert "old_var" in comparison["variables_changed"]  # old_var changed (default added)


def test_compare_metadata_no_changes():
    """Test comparing identical prompts."""
    metadata = PromptMetadata(name="test", version="1.0.0")
    prompt = Prompt(
        metadata=metadata,
        template="Hello!",
        variables={"var": VariableDefinition(type="string")},
    )

    comparison = PromptDiffer.compare_metadata(prompt, prompt)

    assert comparison["name_changed"] is False
    assert comparison["version_changed"] is False
    assert len(comparison["variables_added"]) == 0
    assert len(comparison["variables_removed"]) == 0
    assert len(comparison["variables_changed"]) == 0

