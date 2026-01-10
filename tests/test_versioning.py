"""Tests for version management - git operations, branches, tags."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from glueprompt.exceptions import GitOperationError, VersionError
from glueprompt.versioning import VersionManager


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    from git import Repo

    repo_path = tmp_path / "prompts"
    repo_path.mkdir()
    repo = Repo.init(repo_path)

    # Create initial commit
    (repo_path / "test.yaml").write_text("test: initial")
    repo.index.add(["test.yaml"])
    repo.index.commit("Initial commit")

    return repo_path


def test_version_manager_init_not_git(tmp_path):
    """Test VersionManager raises error for non-git directory."""
    with pytest.raises(GitOperationError, match="Not a valid git repository"):
        VersionManager(tmp_path)


def test_version_manager_init_valid(git_repo):
    """Test VersionManager initializes for valid git repo."""
    vm = VersionManager(git_repo)
    assert vm.prompts_dir == Path(git_repo)
    assert vm.repo is not None


def test_current_version_on_branch(git_repo):
    """Test getting current version on a branch."""
    from git import Repo

    repo = Repo(git_repo)
    repo.git.checkout("-b", "feature-branch")

    vm = VersionManager(git_repo)
    version = vm.current_version()

    assert version.branch_or_tag == "feature-branch"
    assert version.is_branch is True
    assert len(version.commit_hash) == 8


def test_current_version_detached_head(git_repo):
    """Test getting current version in detached HEAD state."""
    from git import Repo

    repo = Repo(git_repo)
    commit = repo.head.commit
    repo.git.checkout(commit.hexsha)

    vm = VersionManager(git_repo)
    version = vm.current_version()

    assert version.branch_or_tag == "HEAD"
    assert version.is_branch is False


def test_list_branches(git_repo):
    """Test listing branches."""
    from git import Repo

    repo = Repo(git_repo)
    repo.git.checkout("-b", "branch1")
    repo.git.checkout("-b", "branch2")

    vm = VersionManager(git_repo)
    branches = vm.list_branches()

    branch_names = [b.name for b in branches]
    assert "branch1" in branch_names
    assert "branch2" in branch_names


def test_list_tags(git_repo):
    """Test listing tags."""
    from git import Repo

    repo = Repo(git_repo)
    repo.create_tag("v1.0.0")
    repo.create_tag("v2.0.0")

    vm = VersionManager(git_repo)
    tags = vm.list_tags()

    tag_names = [t.branch_or_tag for t in tags]
    assert "v1.0.0" in tag_names
    assert "v2.0.0" in tag_names


def test_checkout_branch(git_repo):
    """Test checking out a branch."""
    from git import Repo

    repo = Repo(git_repo)
    repo.git.checkout("-b", "feature")

    vm = VersionManager(git_repo)
    vm.checkout("feature")

    assert repo.active_branch.name == "feature"


def test_checkout_tag(git_repo):
    """Test checking out a tag."""
    from git import Repo

    repo = Repo(git_repo)
    repo.create_tag("v1.0.0")

    vm = VersionManager(git_repo)
    vm.checkout("v1.0.0")

    assert repo.head.is_detached


def test_checkout_create_branch(git_repo):
    """Test creating and checking out new branch."""
    from git import Repo

    repo = Repo(git_repo)
    vm = VersionManager(git_repo)

    vm.checkout("new-branch", create_branch=True)

    assert repo.active_branch.name == "new-branch"


def test_checkout_nonexistent(git_repo):
    """Test checking out non-existent branch/tag raises error."""
    vm = VersionManager(git_repo)

    with pytest.raises(VersionError, match="not found"):
        vm.checkout("nonexistent-branch")


def test_diff_prompt_file(git_repo):
    """Test getting diff for prompt file."""
    from git import Repo

    repo = Repo(git_repo)
    prompt_file = git_repo / "test.yaml"
    prompt_file.write_text("test: modified")
    repo.index.add(["test.yaml"])
    repo.index.commit("Modify test")

    vm = VersionManager(git_repo)
    diff = vm.diff("test", version1="HEAD~1", version2="HEAD")

    assert len(diff) > 0
    assert "modified" in diff or "test" in diff


def test_diff_current_version(git_repo):
    """Test getting diff against current version."""
    from git import Repo

    repo = Repo(git_repo)
    prompt_file = git_repo / "test.yaml"
    original_content = prompt_file.read_text()
    prompt_file.write_text("test: changed")
    repo.index.add(["test.yaml"])

    vm = VersionManager(git_repo)
    diff = vm.diff("test")

    assert len(diff) > 0


def test_diff_prompt_not_found(git_repo):
    """Test diff raises error for non-existent prompt."""
    vm = VersionManager(git_repo)

    with pytest.raises(VersionError, match="not found"):
        vm.diff("nonexistent-prompt")


def test_rollback(git_repo):
    """Test rollback to previous version."""
    from git import Repo

    repo = Repo(git_repo)
    repo.git.checkout("-b", "v1.0")
    repo.create_tag("v1.0.0")

    vm = VersionManager(git_repo)
    vm.rollback("v1.0.0")

    assert repo.head.is_detached

