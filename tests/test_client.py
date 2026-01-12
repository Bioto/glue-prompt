"""Tests for API client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from glueprompt.client import APIPromptRegistry
from glueprompt.exceptions import (
    GluePromptError,
    PromptNotFoundError,
    PromptValidationError,
    TemplateRenderError,
    VersionError,
)
from glueprompt.models.prompt import Prompt
from glueprompt.models.version import BranchInfo, VersionInfo
from glueprompt.server.models import (
    PromptMetadataResponse,
    PromptResponse,
    RenderResponse,
    RepoInfo,
    ReposResponse,
    VersionInfoResponse,
    VersionsResponse,
)


@pytest.fixture
def api_client():
    """Create an API client instance."""
    return APIPromptRegistry(base_url="http://localhost:8000", repo="test-repo")


@pytest.fixture
def sample_prompt_response():
    """Sample prompt response from API."""
    return PromptResponse(
        metadata=PromptMetadataResponse(
            name="test-prompt",
            version="1.0.0",
            description="A test prompt",
            author="test-author",
            tags=["test", "sample"],
        ),
        template="Hello {{ name }}!",
        variables={
            "name": {
                "type": "string",
                "required": True,
                "default": None,
                "description": "Name to greet",
            },
        },
    )


@pytest.fixture
def sample_versions_response():
    """Sample versions response from API."""
    return VersionsResponse(
        branches=[
            VersionInfoResponse(
                name="main",
                commit_hash="abc123",
                is_branch=True,
                is_current=True,
            ),
            VersionInfoResponse(
                name="feature-branch",
                commit_hash="def456",
                is_branch=True,
                is_current=False,
            ),
        ],
        tags=[
            VersionInfoResponse(
                name="v1.0.0",
                commit_hash="ghi789",
                is_branch=False,
            ),
        ],
        current="main",
    )


def test_client_init(api_client):
    """Test API client initialization."""
    assert api_client.base_url == "http://localhost:8000"
    assert api_client.repo == "test-repo"
    assert api_client.timeout == 30
    assert api_client.client is not None
    assert api_client.validator is not None


def test_client_init_custom_timeout():
    """Test API client with custom timeout."""
    client = APIPromptRegistry(base_url="http://localhost:8000", repo="test", timeout=60)
    assert client.timeout == 60


def test_client_base_url_trailing_slash():
    """Test that trailing slash is removed from base URL."""
    client = APIPromptRegistry(base_url="http://localhost:8000/", repo="test")
    assert client.base_url == "http://localhost:8000"


@pytest.mark.asyncio
async def test_client_context_manager():
    """Test API client as async context manager."""
    async with APIPromptRegistry(base_url="http://localhost:8000", repo="test-repo") as client:
        assert client.client is not None


@pytest.mark.asyncio
async def test_get_prompt_success(api_client, sample_prompt_response):
    """Test successfully getting a prompt."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_prompt_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    prompt = await api_client.get("test-prompt")

    assert isinstance(prompt, Prompt)
    assert prompt.metadata.name == "test-prompt"
    assert prompt.metadata.version == "1.0.0"
    assert prompt.template == "Hello {{ name }}!"
    assert "name" in prompt.variables

    api_client.client.get.assert_called_once_with(
        "http://localhost:8000/repos/test-repo/prompts/test-prompt",
        params={},
    )


@pytest.mark.asyncio
async def test_get_prompt_with_version(api_client, sample_prompt_response):
    """Test getting a prompt with specific version."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_prompt_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    await api_client.get("test-prompt", version="1.0.0")

    api_client.client.get.assert_called_once_with(
        "http://localhost:8000/repos/test-repo/prompts/test-prompt",
        params={"version": "1.0.0"},
    )


@pytest.mark.asyncio
async def test_get_prompt_without_validation(api_client, sample_prompt_response):
    """Test getting a prompt without validation."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_prompt_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    prompt = await api_client.get("test-prompt", validate=False)

    assert isinstance(prompt, Prompt)
    assert prompt.metadata.name == "test-prompt"


@pytest.mark.asyncio
async def test_get_prompt_not_found(api_client):
    """Test getting a non-existent prompt."""
    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 404
    mock_response.text = "Prompt not found"
    mock_response.json.return_value = {"detail": "Prompt not found"}

    api_client.client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(PromptNotFoundError, match="Prompt not found"):
        await api_client.get("nonexistent-prompt")


@pytest.mark.asyncio
async def test_get_prompt_validation_error(api_client):
    """Test getting a prompt with validation error."""
    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 400
    mock_response.text = "Validation failed"
    mock_response.json.return_value = {"detail": "Validation failed"}

    api_client.client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(PromptValidationError, match="Validation failed"):
        await api_client.get("invalid-prompt")


@pytest.mark.asyncio
async def test_get_prompt_server_error(api_client):
    """Test getting a prompt with server error."""
    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 500
    mock_response.text = "Internal server error"

    api_client.client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(GluePromptError, match="Server error"):
        await api_client.get("test-prompt")


@pytest.mark.asyncio
async def test_render_prompt_success(api_client, sample_prompt_response):
    """Test successfully rendering a prompt."""
    # Mock get for validation
    mock_get_response = MagicMock()
    mock_get_response.is_error = False
    mock_get_response.json.return_value = sample_prompt_response.model_dump()
    mock_get_response.text = ""

    # Mock render response
    render_response = RenderResponse(rendered="Hello Claude!", version="1.0.0")
    mock_render_response = MagicMock()
    mock_render_response.is_error = False
    mock_render_response.json.return_value = render_response.model_dump()
    mock_render_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_get_response)
    api_client.client.post = AsyncMock(return_value=mock_render_response)

    rendered = await api_client.render("test-prompt", name="Claude")

    assert rendered == "Hello Claude!"
    api_client.client.post.assert_called_once()


@pytest.mark.asyncio
async def test_render_prompt_without_validation(api_client):
    """Test rendering a prompt without validation."""
    render_response = RenderResponse(rendered="Hello Claude!", version="1.0.0")
    mock_render_response = MagicMock()
    mock_render_response.is_error = False
    mock_render_response.json.return_value = render_response.model_dump()
    mock_render_response.text = ""

    api_client.client.post = AsyncMock(return_value=mock_render_response)

    rendered = await api_client.render("test-prompt", validate=False, name="Claude")

    assert rendered == "Hello Claude!"


@pytest.mark.asyncio
async def test_render_prompt_with_version(api_client, sample_prompt_response):
    """Test rendering a prompt at specific version."""
    mock_get_response = MagicMock()
    mock_get_response.is_error = False
    mock_get_response.json.return_value = sample_prompt_response.model_dump()
    mock_get_response.text = ""

    render_response = RenderResponse(rendered="Hello!", version="1.0.0")
    mock_render_response = MagicMock()
    mock_render_response.is_error = False
    mock_render_response.json.return_value = render_response.model_dump()
    mock_render_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_get_response)
    api_client.client.post = AsyncMock(return_value=mock_render_response)

    await api_client.render("test-prompt", version="1.0.0", name="Test")

    # Check that version was passed in params
    call_args = api_client.client.post.call_args
    assert call_args[1]["params"] == {"version": "1.0.0"}


@pytest.mark.asyncio
async def test_render_prompt_template_error(api_client):
    """Test rendering a prompt with template error."""
    mock_response = MagicMock()
    mock_response.is_error = True
    mock_response.status_code = 400
    mock_response.text = "Template render error"
    mock_response.json.return_value = {"detail": "Template render error"}

    api_client.client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(TemplateRenderError, match="Template render error"):
        await api_client.render("test-prompt", validate=False, name="Claude")


@pytest.mark.asyncio
async def test_validate_prompt(api_client, sample_prompt_response):
    """Test validating a prompt."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_prompt_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    errors = await api_client.validate("test-prompt")

    assert isinstance(errors, list)
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_validate_prompt_with_version(api_client, sample_prompt_response):
    """Test validating a prompt at specific version."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_prompt_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    await api_client.validate("test-prompt", version="1.0.0")

    api_client.client.get.assert_called_once_with(
        "http://localhost:8000/repos/test-repo/prompts/test-prompt",
        params={"version": "1.0.0"},
    )


@pytest.mark.asyncio
async def test_list_versions(api_client, sample_versions_response):
    """Test listing versions."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_versions_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    versions = await api_client.list_versions()

    assert "branches" in versions
    assert "tags" in versions
    assert len(versions["branches"]) == 2
    assert len(versions["tags"]) == 1
    assert isinstance(versions["branches"][0], BranchInfo)
    assert isinstance(versions["tags"][0], VersionInfo)


@pytest.mark.asyncio
async def test_current_version(api_client, sample_versions_response):
    """Test getting current version."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = sample_versions_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    current = await api_client.current_version()

    assert isinstance(current, VersionInfo)
    assert current.branch_or_tag == "main"


@pytest.mark.asyncio
async def test_current_version_tag(api_client):
    """Test getting current version when it's a tag."""
    versions_response = VersionsResponse(
        branches=[
            VersionInfoResponse(
                name="main",
                commit_hash="abc123",
                is_branch=True,
                is_current=False,
            ),
        ],
        tags=[
            VersionInfoResponse(
                name="v1.0.0",
                commit_hash="ghi789",
                is_branch=False,
            ),
        ],
        current="v1.0.0",
    )

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = versions_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    current = await api_client.current_version()

    assert isinstance(current, VersionInfo)
    assert current.branch_or_tag == "v1.0.0"
    assert current.is_branch is False


@pytest.mark.asyncio
async def test_list_prompts(api_client):
    """Test listing prompts."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"prompts": ["prompt1", "prompt2", "prompt3"]}
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    prompts = await api_client.list_prompts()

    assert len(prompts) == 3
    assert "prompt1" in prompts
    assert "prompt2" in prompts
    assert "prompt3" in prompts


@pytest.mark.asyncio
async def test_list_prompts_with_version(api_client):
    """Test listing prompts with version."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"prompts": ["prompt1"]}
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    prompts = await api_client.list_prompts(version="v1.0.0")

    assert len(prompts) == 1
    api_client.client.get.assert_called_once_with(
        "http://localhost:8000/repos/test-repo/prompts",
        params={"version": "v1.0.0"},
    )


@pytest.mark.asyncio
async def test_list_repos(api_client):
    """Test listing repositories."""
    repos_response = ReposResponse(
        repos=[
            RepoInfo(name="repo1", url="https://github.com/org/repo1", path="/path/to/repo1"),
            RepoInfo(name="repo2", url="https://github.com/org/repo2", path="/path/to/repo2"),
        ]
    )

    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = repos_response.model_dump()
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    repos = await api_client.list_repos()

    assert len(repos) == 2
    assert repos[0].name == "repo1"
    assert repos[1].name == "repo2"


@pytest.mark.asyncio
async def test_health_check(api_client):
    """Test health check."""
    mock_response = MagicMock()
    mock_response.is_error = False
    mock_response.json.return_value = {"status": "ok"}
    mock_response.text = ""

    api_client.client.get = AsyncMock(return_value=mock_response)

    health = await api_client.health_check()

    assert health == {"status": "ok"}


def test_checkout_not_available(api_client):
    """Test that checkout raises VersionError."""
    with pytest.raises(VersionError, match="Checkout operation is not available via API"):
        api_client.checkout("main")


def test_checkout_with_create_branch(api_client):
    """Test that checkout with create_branch raises VersionError."""
    with pytest.raises(VersionError, match="Checkout operation is not available via API"):
        api_client.checkout("new-branch", create_branch=True)


def test_diff_not_available(api_client):
    """Test that diff raises VersionError."""
    with pytest.raises(VersionError, match="Diff operation is not available via API"):
        api_client.diff("test-prompt", version1="v1.0", version2="v2.0")


def test_rollback_not_available(api_client):
    """Test that rollback raises VersionError."""
    with pytest.raises(VersionError, match="Rollback operation is not available via API"):
        api_client.rollback("v1.0")


def test_clear_cache_not_available(api_client):
    """Test that clear_cache raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Cache management is not available via API"):
        api_client.clear_cache()


def test_invalidate_cache_not_available(api_client):
    """Test that invalidate_cache raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Cache management is not available via API"):
        api_client.invalidate_cache("test-prompt")


def test_invalidate_cache_all_not_available(api_client):
    """Test that invalidate_cache for all prompts raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Cache management is not available via API"):
        api_client.invalidate_cache()


def test_has_versioning(api_client):
    """Test that has_versioning always returns True."""
    assert api_client.has_versioning is True


@pytest.mark.asyncio
async def test_close_client(api_client):
    """Test closing the client."""
    api_client.client.aclose = AsyncMock()
    await api_client.close()
    api_client.client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_convert_prompt_response(api_client, sample_prompt_response):
    """Test converting API response to Prompt model."""
    prompt = api_client._convert_prompt_response(sample_prompt_response)

    assert isinstance(prompt, Prompt)
    assert prompt.metadata.name == "test-prompt"
    assert prompt.metadata.version == "1.0.0"
    assert prompt.template == "Hello {{ name }}!"
    assert "name" in prompt.variables
    assert prompt.variables["name"].type == "string"
    assert prompt.variables["name"].required is True


@pytest.mark.asyncio
async def test_convert_version_info_branch(api_client):
    """Test converting version info for branch."""
    version_info = VersionInfoResponse(
        name="main",
        commit_hash="abc123",
        is_branch=True,
        is_current=True,
    )

    result = api_client._convert_version_info(version_info, is_branch=True)

    assert isinstance(result, BranchInfo)
    assert result.name == "main"
    assert result.commit_hash == "abc123"
    assert result.is_current is True


@pytest.mark.asyncio
async def test_convert_version_info_tag(api_client):
    """Test converting version info for tag."""
    version_info = VersionInfoResponse(
        name="v1.0.0",
        commit_hash="abc123",
        is_branch=False,
    )

    result = api_client._convert_version_info(version_info, is_branch=False)

    assert isinstance(result, VersionInfo)
    assert result.branch_or_tag == "v1.0.0"
    assert result.commit_hash == "abc123"
    assert result.is_branch is False


@pytest.mark.asyncio
async def test_handle_http_error_404(api_client):
    """Test HTTP error handling for 404."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not found"
    mock_response.json.return_value = {"detail": "Resource not found"}

    with pytest.raises(PromptNotFoundError, match="Resource not found"):
        api_client._handle_http_error(mock_response)


@pytest.mark.asyncio
async def test_handle_http_error_400_validation(api_client):
    """Test HTTP error handling for 400 validation error."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Validation error"
    mock_response.json.return_value = {"detail": "Validation error"}

    with pytest.raises(PromptValidationError, match="Validation error"):
        api_client._handle_http_error(mock_response)


@pytest.mark.asyncio
async def test_handle_http_error_400_template(api_client):
    """Test HTTP error handling for 400 template error."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Template render failed"
    mock_response.json.return_value = {"detail": "Template render failed"}

    with pytest.raises(TemplateRenderError, match="Template render failed"):
        api_client._handle_http_error(mock_response)


@pytest.mark.asyncio
async def test_handle_http_error_500(api_client):
    """Test HTTP error handling for 500."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal error"
    mock_response.json.return_value = {"detail": "Internal server error"}

    with pytest.raises(GluePromptError, match="Server error"):
        api_client._handle_http_error(mock_response)


@pytest.mark.asyncio
async def test_handle_http_error_other(api_client):
    """Test HTTP error handling for other status codes."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = "Service unavailable"
    mock_response.json.side_effect = Exception("Invalid JSON")

    with pytest.raises(GluePromptError, match="HTTP 503"):
        api_client._handle_http_error(mock_response)


@pytest.mark.asyncio
async def test_handle_http_error_invalid_json(api_client):
    """Test HTTP error handling when JSON parsing fails."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Plain text error"
    mock_response.json.side_effect = Exception("Invalid JSON")

    with pytest.raises(PromptNotFoundError, match="Plain text error"):
        api_client._handle_http_error(mock_response)
