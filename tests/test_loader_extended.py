"""Extended tests for prompt loader - file resolution, cache, variable parsing."""

import tempfile
import time
from pathlib import Path

import pytest
import yaml

from glueprompt.exceptions import PromptValidationError
from glueprompt.loader import PromptLoader


def test_resolve_yaml_extension():
    """Test resolving prompt with .yaml extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test")
        assert prompt.metadata.name == "test"


def test_resolve_yml_extension():
    """Test resolving prompt with .yml extension."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yml"
        prompt_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test")
        assert prompt.metadata.name == "test"


def test_resolve_index_yaml():
    """Test resolving prompt via index.yaml in directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_dir = prompts_dir / "test-prompt"
        prompt_dir.mkdir()
        index_file = prompt_dir / "index.yaml"
        index_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test-prompt")
        assert prompt.metadata.name == "test"


def test_cache_ttl_expiration():
    """Test cache expiration after TTL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir, cache_enabled=True, cache_ttl=1)
        prompt1 = loader.load("test")
        time.sleep(1.1)  # Wait for cache to expire
        prompt2 = loader.load("test")

        assert prompt1 is not prompt2  # Should be different objects after expiration


def test_cache_disabled():
    """Test loader with cache disabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir, cache_enabled=False)
        prompt1 = loader.load("test")
        prompt2 = loader.load("test")

        assert prompt1 is not prompt2  # No caching


def test_invalidate_specific_prompt():
    """Test invalidating cache for specific prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt1_file = prompts_dir / "test1.yaml"
        prompt2_file = prompts_dir / "test2.yaml"
        prompt1_file.write_text(yaml.dump({"name": "test1", "template": "Hello"}))
        prompt2_file.write_text(yaml.dump({"name": "test2", "template": "World"}))

        loader = PromptLoader(prompts_dir, cache_enabled=True)
        p1 = loader.load("test1")
        p2 = loader.load("test2")

        loader.invalidate_cache("test1")
        p1_new = loader.load("test1")
        p2_cached = loader.load("test2")

        assert p1 is not p1_new  # test1 was invalidated
        assert p2 is p2_cached  # test2 still cached


def test_simple_string_variable_format():
    """Test parsing simple string variable format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_data = {
            "name": "test",
            "template": "Hello {{ name }}!",
            "variables": {
                "name": "string",  # Simple string format
            },
        }
        prompt_file.write_text(yaml.dump(prompt_data))

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test")

        assert "name" in prompt.variables
        assert prompt.variables["name"].type == "string"


def test_empty_string_variable_format():
    """Test parsing empty string variable format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_data = {
            "name": "test",
            "template": "Hello!",
            "variables": {
                "name": "",  # Empty string defaults to "string"
            },
        }
        prompt_file.write_text(yaml.dump(prompt_data))

        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test")

        assert prompt.variables["name"].type == "string"


def test_non_dict_yaml():
    """Test loading non-dict YAML raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text(yaml.dump(["list", "not", "dict"]))

        loader = PromptLoader(prompts_dir)

        with pytest.raises(PromptValidationError, match="must be a dictionary"):
            loader.load("test")


def test_use_cache_parameter():
    """Test use_cache parameter bypasses cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        prompt_file = prompts_dir / "test.yaml"
        prompt_file.write_text(yaml.dump({"name": "test", "template": "Hello"}))

        loader = PromptLoader(prompts_dir, cache_enabled=True)
        prompt1 = loader.load("test", use_cache=True)
        prompt2 = loader.load("test", use_cache=True)

        assert prompt1 is prompt2  # Same object from cache

        # When use_cache=False, should reload from file
        prompt3 = loader.load("test", use_cache=False)
        # Even with same content, should be new object when bypassing cache
        assert prompt3 is not prompt1

