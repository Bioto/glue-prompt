"""Tests for FastAPI server application."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from glueprompt.server.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_repo_manager():
    """Mock RepoManager for testing."""
    with patch("glueprompt.server.app.RepoManager") as mock:
        manager = Mock()
        mock.return_value = manager
        yield manager


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_repos_empty(client, mock_repo_manager):
    """Test listing repos when none exist."""
    mock_repo_manager.list_repos.return_value = []

    response = client.get("/repos")
    assert response.status_code == 200
    data = response.json()
    assert "repos" in data
    assert data["repos"] == []


def test_list_repos(client, mock_repo_manager):
    """Test listing repos."""
    mock_repo_manager.list_repos.return_value = [
        {
            "name": "test-repo",
            "url": "https://github.com/user/test-repo.git",
            "path": "/tmp/test-repo",
            "exists": True,
            "branch": "main",
        }
    ]

    response = client.get("/repos")
    assert response.status_code == 200
    data = response.json()
    assert len(data["repos"]) == 1
    assert data["repos"][0]["name"] == "test-repo"
    assert data["repos"][0]["current_branch"] == "main"


def test_list_repos_missing(client, mock_repo_manager):
    """Test listing repos when repo directory is missing."""
    mock_repo_manager.list_repos.return_value = [
        {
            "name": "missing-repo",
            "url": "https://github.com/user/missing-repo.git",
            "path": "/tmp/missing-repo",
            "exists": False,
        }
    ]

    response = client.get("/repos")
    assert response.status_code == 200
    data = response.json()
    # Missing repos should be filtered out
    assert len(data["repos"]) == 0


def test_list_versions_not_found(client, mock_repo_manager):
    """Test listing versions for non-existent repo."""
    mock_repo_manager.get_path.side_effect = Exception("Repo not found")

    response = client.get("/repos/nonexistent/versions")
    assert response.status_code == 404


def test_list_versions(client, mock_repo_manager, tmp_path):
    """Test listing versions for a repo."""
    from glueprompt.models.version import BranchInfo, VersionInfo
    from glueprompt.versioning import VersionManager

    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    mock_repo_manager.get_path.return_value = repo_path

    with patch("glueprompt.server.app.VersionManager") as mock_version_mgr:
        version_manager = Mock(spec=VersionManager)
        mock_version_mgr.return_value = version_manager

        version_manager.list_branches.return_value = [
            BranchInfo(name="main", commit_hash="abc123", is_current=True)
        ]
        version_manager.list_tags.return_value = [
            VersionInfo(
                branch_or_tag="v1.0.0",
                commit_hash="def456",
                commit_message="Release 1.0.0",
                commit_date=datetime.now(UTC),
                is_branch=False,
            )
        ]
        version_manager.current_version.return_value = VersionInfo(
            branch_or_tag="main",
            commit_hash="abc123",
            commit_message="Current",
            commit_date=datetime.now(UTC),
            is_branch=True,
        )

        response = client.get("/repos/test-repo/versions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["branches"]) == 1
        assert len(data["tags"]) == 1
        assert data["current"] == "main"


def test_list_prompts(client, mock_repo_manager, tmp_path):
    """Test listing prompts."""
    from glueprompt.server.worktree_manager import WorktreeManager

    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    mock_repo_manager.get_path.return_value = repo_path

    with patch("glueprompt.server.app.WorktreeManager") as mock_worktree:
        worktree_mgr = Mock(spec=WorktreeManager)
        mock_worktree.return_value = worktree_mgr
        worktree_mgr.list_prompts.return_value = ["assistants/helper", "tools/summarizer"]

        response = client.get("/repos/test-repo/prompts")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert len(data["prompts"]) == 2
        assert "assistants/helper" in data["prompts"]


def test_get_prompt_not_found(client, mock_repo_manager):
    """Test getting a non-existent prompt."""
    mock_repo_manager.get_path.side_effect = Exception("Repo not found")

    response = client.get("/repos/test-repo/prompts/nonexistent")
    assert response.status_code == 404


def test_render_prompt_missing_variables(client, mock_repo_manager, tmp_path):
    """Test rendering prompt with missing required variables."""
    from git import Repo

    from glueprompt.exceptions import TemplateRenderError
    from glueprompt.loader import PromptLoader

    # Create a git repo for VersionManager with at least one commit
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    repo = Repo.init(str(repo_path))

    # Create initial commit so there's a branch to check out
    (repo_path / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    mock_repo_manager.get_path.return_value = repo_path

    with patch("glueprompt.server.app.WorktreeManager"), patch("glueprompt.server.app.PromptLoader") as mock_loader:
        loader = Mock(spec=PromptLoader)
        mock_loader.return_value = loader

        from glueprompt.models.prompt import Prompt, PromptMetadata
        prompt = Prompt(
            metadata=PromptMetadata(name="test"),
            template="Hello {{ name }}!",
            variables={},
        )
        loader.load.return_value = prompt

        with patch("glueprompt.server.app.TemplateRenderer") as mock_renderer:
            renderer = Mock()
            mock_renderer.return_value = renderer
            renderer.render.side_effect = TemplateRenderError("Missing required variables: name")

            response = client.post(
                "/repos/test-repo/prompts/test/render",
                json={"variables": {}},
            )
            assert response.status_code == 400
            assert "missing required" in response.json()["detail"].lower()

