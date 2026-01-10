"""Tests for repository manager - clone, remove, default repo."""

from unittest.mock import patch

import pytest

from glueprompt.exceptions import GitOperationError
from glueprompt.repo_manager import (
    RepoManager,
    get_default_repo,
    set_default_repo,
    url_to_repo_name,
)


def test_url_to_repo_name_https():
    """Test extracting repo name from HTTPS URL."""
    assert url_to_repo_name("https://github.com/user/my-prompts.git") == "my-prompts"
    assert url_to_repo_name("https://github.com/user/my-prompts") == "my-prompts"


def test_url_to_repo_name_ssh():
    """Test extracting repo name from SSH URL."""
    assert url_to_repo_name("git@github.com:user/my-prompts.git") == "my-prompts"
    assert url_to_repo_name("git@github.com:user/my-prompts") == "my-prompts"


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.save_repos_config")
@patch("glueprompt.repo_manager.load_repos_config")
@patch("glueprompt.repo_manager.Repo.clone_from")
def test_clone_repository(mock_clone, mock_load, mock_save, mock_cache_dir, tmp_path):
    """Test cloning a repository."""
    from git import Repo

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir
    mock_load.return_value = {}

    repo_path = cache_dir / "test-repo"
    # Don't create repo_path - let clone create it

    # Mock clone_from to create the repo
    def create_repo(url, path, **kwargs):
        repo_path.mkdir()
        return Repo.init(repo_path)

    mock_clone.side_effect = create_repo

    manager = RepoManager()
    result = manager.clone("https://github.com/user/test-repo.git", name="test-repo")

    assert result == repo_path
    mock_clone.assert_called_once()


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.load_repos_config")
def test_clone_existing_repo_raises_error(mock_load, mock_cache_dir, tmp_path):
    """Test cloning existing repo raises error without force."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir

    repo_path = cache_dir / "existing-repo"
    repo_path.mkdir()

    mock_load.return_value = {"existing-repo": {"url": "test", "path": str(repo_path)}}

    manager = RepoManager()
    manager.config = {"existing-repo": {"url": "test", "path": str(repo_path)}}

    with pytest.raises(GitOperationError, match="already exists"):
        manager.clone("https://github.com/user/existing-repo.git", name="existing-repo")


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.save_repos_config")
@patch("glueprompt.repo_manager.load_repos_config")
def test_remove_repository(mock_load, mock_save, mock_cache_dir, tmp_path):
    """Test removing a repository."""

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir

    repo_path = cache_dir / "test-repo"
    repo_path.mkdir()

    mock_load.return_value = {"test-repo": {"url": "test", "path": str(repo_path)}}

    manager = RepoManager()
    manager.config = {"test-repo": {"url": "test", "path": str(repo_path)}}

    manager.remove("test-repo")

    assert "test-repo" not in manager.config
    mock_save.assert_called_once()


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.load_repos_config")
def test_get_path_existing(mock_load, mock_cache_dir, tmp_path):
    """Test getting path to existing repository."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir

    repo_path = cache_dir / "test-repo"
    repo_path.mkdir()

    mock_load.return_value = {"test-repo": {"url": "test", "path": str(repo_path)}}

    manager = RepoManager()
    manager.config = {"test-repo": {"url": "test", "path": str(repo_path)}}

    path = manager.get_path("test-repo")
    assert path == repo_path


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.load_repos_config")
def test_get_path_nonexistent(mock_load, mock_cache_dir, tmp_path):
    """Test getting path to non-existent repository raises error."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir
    mock_load.return_value = {}

    manager = RepoManager()

    with pytest.raises(GitOperationError, match="not found"):
        manager.get_path("nonexistent-repo")


@patch("glueprompt.repo_manager.get_cache_dir")
@patch("glueprompt.repo_manager.load_repos_config")
def test_list_repos(mock_load, mock_cache_dir, tmp_path):
    """Test listing repositories."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    mock_cache_dir.return_value = cache_dir

    repo_path = cache_dir / "test-repo"
    repo_path.mkdir()

    mock_load.return_value = {"test-repo": {"url": "test", "path": str(repo_path)}}

    manager = RepoManager()
    manager.config = {"test-repo": {"url": "test", "path": str(repo_path)}}

    repos = manager.list_repos()
    assert len(repos) == 1
    assert repos[0]["name"] == "test-repo"


@patch("glueprompt.repo_manager.get_default_repo_path")
def test_set_default_repo(mock_path, tmp_path):
    """Test setting default repository."""
    default_path = tmp_path / "default_repo.txt"
    mock_path.return_value = default_path

    set_default_repo("test-repo")
    assert default_path.read_text().strip() == "test-repo"

    set_default_repo(None)
    assert not default_path.exists()


@patch("glueprompt.repo_manager.get_default_repo_path")
def test_get_default_repo(mock_path, tmp_path):
    """Test getting default repository."""
    default_path = tmp_path / "default_repo.txt"
    mock_path.return_value = default_path

    default_path.write_text("test-repo")
    assert get_default_repo() == "test-repo"

    default_path.unlink()
    assert get_default_repo() is None

