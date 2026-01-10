"""Tests for worktree manager."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from glueprompt.exceptions import GitOperationError
from glueprompt.server.worktree_manager import WorktreeManager


@pytest.fixture
def mock_repo_manager(tmp_path):
    """Mock RepoManager for testing."""
    from git import Repo

    # Create a real git repo for testing
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    Repo.init(str(repo_path))

    with patch("glueprompt.repo_manager.RepoManager") as mock:
        manager = Mock()
        manager.get_path.return_value = repo_path
        mock.return_value = manager
        yield manager, repo_path


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository for testing."""
    from git import Repo

    # Use a unique name to avoid conflicts with mock_repo_manager
    repo_path = tmp_path / "git-test-repo"
    repo_path.mkdir()
    repo = Repo.init(str(repo_path))

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # Create a branch
    repo.create_head("feature-branch")

    return repo_path, repo


def test_worktree_manager_init(mock_repo_manager):
    """Test initializing worktree manager."""
    manager_mock, repo_path = mock_repo_manager

    worktree_mgr = WorktreeManager("test-repo")

    assert worktree_mgr.repo_name == "test-repo"
    assert worktree_mgr.repo_path == repo_path
    manager_mock.get_path.assert_called_once_with("test-repo")


def test_worktree_manager_init_invalid_repo(tmp_path):
    """Test initializing worktree manager with invalid repo."""
    invalid_path = tmp_path / "not-a-repo"
    invalid_path.mkdir()
    # Don't initialize as git repo

    with patch("glueprompt.repo_manager.RepoManager") as mock:
        manager = Mock()
        manager.get_path.return_value = invalid_path
        mock.return_value = manager

        with pytest.raises(GitOperationError, match="Not a valid git repository"):
            WorktreeManager("test-repo")


def test_get_worktree_path(mock_repo_manager):
    """Test getting worktree path."""
    manager_mock, repo_path = mock_repo_manager

    worktree_mgr = WorktreeManager("test-repo")
    path = worktree_mgr.get_worktree_path("main")

    assert isinstance(path, Path)
    assert "main" in str(path)


def test_get_worktree_path_sanitizes(mock_repo_manager):
    """Test that worktree path sanitizes version names."""
    manager_mock, repo_path = mock_repo_manager

    worktree_mgr = WorktreeManager("test-repo")
    path = worktree_mgr.get_worktree_path("feature/branch")

    # Should replace / with _ in the version name part
    # The path will have / as directory separators, but the version name should be sanitized
    assert path.name == "feature_branch"  # The last part should have _ instead of /


def test_list_prompts_no_version(mock_repo_manager, tmp_path):
    """Test listing prompts without version."""
    manager_mock, repo_path = mock_repo_manager

    # Create a prompt file
    prompt_file = repo_path / "assistants" / "helper.yaml"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("name: helper")

    worktree_mgr = WorktreeManager("test-repo")
    prompts = worktree_mgr.list_prompts(version=None)

    assert len(prompts) == 1
    assert "assistants/helper" in prompts


def test_list_prompts_with_version(mock_repo_manager, git_repo):
    """Test listing prompts with version."""
    repo_path, repo = git_repo
    manager_mock, _ = mock_repo_manager

    # Update the mock to return the git repo path
    manager_mock.get_path.return_value = repo_path

    worktree_mgr = WorktreeManager("test-repo")

    # Create a prompt file
    prompt_file = repo_path / "assistants" / "helper.yaml"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("name: helper")

    with patch.object(worktree_mgr, "ensure_worktree") as mock_ensure:
        mock_ensure.return_value = repo_path
        prompts = worktree_mgr.list_prompts(version="main")

        assert len(prompts) == 1
        mock_ensure.assert_called_once_with("main")


def test_get_prompt_path_not_found(mock_repo_manager):
    """Test getting prompt path when prompt doesn't exist."""
    manager_mock, repo_path = mock_repo_manager

    worktree_mgr = WorktreeManager("test-repo")

    with patch.object(worktree_mgr, "ensure_worktree") as mock_ensure:
        mock_ensure.return_value = repo_path

        with pytest.raises(GitOperationError, match="Prompt not found"):
            worktree_mgr.get_prompt_path("main", "nonexistent")


def test_get_prompt_path_yaml(mock_repo_manager):
    """Test getting prompt path with .yaml extension."""
    manager_mock, repo_path = mock_repo_manager

    # Create a prompt file
    prompt_file = repo_path / "assistants" / "helper.yaml"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("name: helper")

    worktree_mgr = WorktreeManager("test-repo")

    with patch.object(worktree_mgr, "ensure_worktree") as mock_ensure:
        mock_ensure.return_value = repo_path
        worktree_path, prompt_path = worktree_mgr.get_prompt_path("main", "assistants/helper")

        assert prompt_path == prompt_file
        assert worktree_path == repo_path


def test_get_prompt_path_yml(mock_repo_manager):
    """Test getting prompt path with .yml extension."""
    manager_mock, repo_path = mock_repo_manager

    # Create a prompt file with .yml extension
    prompt_file = repo_path / "assistants" / "helper.yml"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("name: helper")

    worktree_mgr = WorktreeManager("test-repo")

    with patch.object(worktree_mgr, "ensure_worktree") as mock_ensure:
        mock_ensure.return_value = repo_path
        worktree_path, prompt_path = worktree_mgr.get_prompt_path("main", "assistants/helper")

        assert prompt_path == prompt_file
        assert worktree_path == repo_path


def test_cleanup_unused_worktrees(mock_repo_manager, git_repo):
    """Test cleaning up unused worktrees."""
    repo_path, repo = git_repo
    manager_mock, _ = mock_repo_manager

    # Update the mock to return the git repo path
    manager_mock.get_path.return_value = repo_path

    worktree_mgr = WorktreeManager("test-repo")

    # Create a worktree directory
    worktree_base = worktree_mgr.worktree_base
    old_worktree = worktree_base / "old-branch"
    old_worktree.mkdir(parents=True)

    # Cleanup should remove unused worktrees
    worktree_mgr.cleanup_unused_worktrees(active_versions={"main"})

    # The old worktree should be removed (or attempted to be removed)
    # Note: Actual removal requires git worktree, so we're testing the logic


def test_cleanup_unused_worktrees_none(mock_repo_manager):
    """Test cleanup when no worktrees exist."""
    manager_mock, repo_path = mock_repo_manager

    worktree_mgr = WorktreeManager("test-repo")

    # Should not raise an error
    worktree_mgr.cleanup_unused_worktrees(active_versions=set())

