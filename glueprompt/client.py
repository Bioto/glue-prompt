"""API client for connecting to GluePrompt FastAPI server."""

from typing import Any

import httpx

from glueprompt.exceptions import (
    GluePromptError,
    PromptNotFoundError,
    PromptValidationError,
    TemplateRenderError,
    VersionError,
)
from glueprompt.logging import get_logger
from glueprompt.models.prompt import Prompt, PromptMetadata, VariableDefinition
from glueprompt.models.version import BranchInfo, VersionInfo
from glueprompt.server.models import (
    PromptMetadataResponse,
    PromptResponse,
    RenderRequest,
    RenderResponse,
    RepoInfo,
    ReposResponse,
    VersionInfoResponse,
    VersionsResponse,
)
from glueprompt.validator import PromptValidator

logger = get_logger(__name__)


class APIPromptRegistry:
    """API client for GluePrompt FastAPI server.

    Provides the same interface as PromptRegistry but connects to a remote
    FastAPI server via HTTP requests. All methods are async.

    Attributes:
        base_url: Base URL of the FastAPI server (e.g., "http://localhost:8000")
        repo: Repository name to use for API requests
        timeout: Request timeout in seconds
        client: httpx.AsyncClient instance
        validator: PromptValidator instance for local validation
    """

    def __init__(
        self,
        base_url: str,
        repo: str,
        timeout: int = 30,
    ):
        """Initialize the API client.

        Args:
            base_url: Base URL of the FastAPI server (e.g., "http://localhost:8000")
            repo: Repository name to use for API requests
            timeout: Request timeout in seconds

        Example:
            >>> client = APIPromptRegistry(
            ...     base_url="http://localhost:8000",
            ...     repo="my-prompts"
            ... )
        """
        self.base_url = base_url.rstrip("/")
        self.repo = repo
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.validator = PromptValidator()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.client.aclose()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Handle HTTP errors and convert to appropriate exceptions.

        Args:
            response: HTTP response with error status

        Raises:
            PromptNotFoundError: For 404 errors
            PromptValidationError: For 400 errors related to validation
            TemplateRenderError: For 400 errors related to rendering
            GluePromptError: For other errors
        """
        error_detail = response.text
        try:
            error_json = response.json()
            if "detail" in error_json:
                error_detail = error_json["detail"]
        except Exception:
            pass

        if response.status_code == 404:
            raise PromptNotFoundError(error_detail)
        elif response.status_code == 400:
            if "template" in error_detail.lower() or "render" in error_detail.lower():
                raise TemplateRenderError(error_detail)
            else:
                raise PromptValidationError(error_detail)
        elif response.status_code == 500:
            raise GluePromptError(f"Server error: {error_detail}")
        else:
            raise GluePromptError(f"HTTP {response.status_code}: {error_detail}")

    def _convert_prompt_response(self, response: PromptResponse) -> Prompt:
        """Convert API PromptResponse to local Prompt model.

        Args:
            response: API response model

        Returns:
            Local Prompt model
        """
        metadata = PromptMetadata(
            name=response.metadata.name,
            version=response.metadata.version,
            description=response.metadata.description,
            author=response.metadata.author,
            tags=response.metadata.tags,
        )

        variables: dict[str, VariableDefinition] = {}
        for var_name, var_data in response.variables.items():
            variables[var_name] = VariableDefinition(
                type=var_data.get("type", "string"),
                required=var_data.get("required", True),
                default=var_data.get("default"),
                description=var_data.get("description", ""),
            )

        return Prompt(
            metadata=metadata,
            template=response.template,
            variables=variables,
        )

    def _convert_version_info(self, version_info: VersionInfoResponse, is_branch: bool) -> VersionInfo | BranchInfo:
        """Convert API VersionInfoResponse to local VersionInfo or BranchInfo.

        Args:
            version_info: API response model
            is_branch: Whether this is a branch

        Returns:
            Local VersionInfo or BranchInfo model
        """
        if is_branch:
            return BranchInfo(
                name=version_info.name,
                commit_hash=version_info.commit_hash,
                is_current=version_info.is_current,
            )
        else:
            # For tags, we don't have commit_date or commit_message from API
            # Use a minimal VersionInfo
            from datetime import datetime

            return VersionInfo(
                branch_or_tag=version_info.name,
                commit_hash=version_info.commit_hash,
                commit_message="",
                commit_date=datetime.now(),  # API doesn't provide this
                is_branch=False,
            )

    async def get(
        self,
        prompt_path: str,
        validate: bool = True,
        version: str | None = None,
    ) -> Prompt:
        """Get a prompt by path, optionally at a specific version.

        Args:
            prompt_path: Relative path to prompt (e.g., "assistants/helpful-bot")
            validate: Whether to validate the prompt after loading
            version: Optional version (e.g., "1.0.5") to fetch specific version

        Returns:
            Loaded Prompt instance

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptValidationError: If validation fails
        """
        logger.info(f"Getting prompt via API: {prompt_path} (repo={self.repo}, version={version})")

        params = {}
        if version:
            params["version"] = version

        url = f"{self.base_url}/repos/{self.repo}/prompts/{prompt_path}"
        response = await self.client.get(url, params=params)

        if response.is_error:
            self._handle_http_error(response)

        prompt_response = PromptResponse(**response.json())
        prompt = self._convert_prompt_response(prompt_response)

        if validate:
            self.validator.validate_and_raise(prompt)
            logger.debug(f"Prompt validated successfully: {prompt_path}")

        logger.info(
            f"Retrieved prompt via API: {prompt_path} "
            f"(name={prompt.metadata.name}, version={prompt.metadata.version})"
        )
        return prompt

    async def render(
        self,
        prompt_path: str,
        validate: bool = True,
        version: str | None = None,
        **variables: Any,
    ) -> str:
        """Load and render a prompt.

        Args:
            prompt_path: Relative path to prompt
            validate: Whether to validate before rendering
            version: Optional version (e.g., "1.0.5") to render specific version
            **variables: Template variables

        Returns:
            Rendered prompt string

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptValidationError: If validation fails
            TemplateRenderError: If rendering fails
        """
        logger.info(
            f"Rendering prompt via API: {prompt_path} "
            f"(repo={self.repo}, version={version}, variables={list(variables.keys())})"
        )

        if validate:
            # Fetch and validate first
            await self.get(prompt_path, validate=True, version=version)

        params = {}
        if version:
            params["version"] = version

        url = f"{self.base_url}/repos/{self.repo}/prompts/{prompt_path}/render"
        request_data = RenderRequest(variables=variables)
        response = await self.client.post(url, json=request_data.model_dump(), params=params)

        if response.is_error:
            self._handle_http_error(response)

        render_response = RenderResponse(**response.json())

        logger.info(
            f"Rendered prompt via API: {prompt_path} "
            f"(version={render_response.version}, length={len(render_response.rendered)} chars)"
        )
        return render_response.rendered

    async def validate(self, prompt_path: str, version: str | None = None) -> list[str]:
        """Validate a prompt.

        Args:
            prompt_path: Relative path to prompt
            version: Optional version to validate

        Returns:
            List of validation errors (empty if valid)

        Raises:
            PromptNotFoundError: If prompt doesn't exist
        """
        prompt = await self.get(prompt_path, validate=False, version=version)
        return self.validator.validate(prompt)

    async def list_versions(self) -> dict[str, list[VersionInfo | BranchInfo]]:
        """List all available versions.

        Returns:
            Dictionary with 'branches' and 'tags' keys

        Raises:
            VersionError: If version listing fails
        """
        logger.info(f"Listing versions via API (repo={self.repo})")

        url = f"{self.base_url}/repos/{self.repo}/versions"
        response = await self.client.get(url)

        if response.is_error:
            self._handle_http_error(response)

        versions_response = VersionsResponse(**response.json())

        branches = [
            self._convert_version_info(branch, is_branch=True) for branch in versions_response.branches
        ]
        tags = [self._convert_version_info(tag, is_branch=False) for tag in versions_response.tags]

        logger.debug(f"Retrieved versions: {len(branches)} branches, {len(tags)} tags")
        return {"branches": branches, "tags": tags}

    async def current_version(self) -> VersionInfo:
        """Get current version.

        Returns:
            VersionInfo for current branch/tag

        Raises:
            VersionError: If version retrieval fails
        """
        # Fetch versions response to get current version name
        url = f"{self.base_url}/repos/{self.repo}/versions"
        response = await self.client.get(url)

        if response.is_error:
            self._handle_http_error(response)

        versions_response = VersionsResponse(**response.json())
        current_name = versions_response.current

        # Find the matching version info
        # Check branches first
        for branch_info in versions_response.branches:
            if branch_info.name == current_name:
                # Convert BranchInfo to VersionInfo
                from datetime import datetime

                return VersionInfo(
                    branch_or_tag=branch_info.name,
                    commit_hash=branch_info.commit_hash,
                    commit_message="",
                    commit_date=datetime.now(),
                    is_branch=True,
                )

        # Check tags
        for tag_info in versions_response.tags:
            if tag_info.name == current_name:
                from datetime import datetime

                return VersionInfo(
                    branch_or_tag=tag_info.name,
                    commit_hash=tag_info.commit_hash,
                    commit_message="",
                    commit_date=datetime.now(),
                    is_branch=False,
                )

        raise VersionError(f"Could not find current version: {current_name}")

    async def list_prompts(self, version: str | None = None) -> list[str]:
        """List all prompts in the repository.

        Args:
            version: Optional version to list prompts for

        Returns:
            List of prompt paths

        Raises:
            GluePromptError: If listing fails
        """
        logger.info(f"Listing prompts via API (repo={self.repo}, version={version})")

        params = {}
        if version:
            params["version"] = version

        url = f"{self.base_url}/repos/{self.repo}/prompts"
        response = await self.client.get(url, params=params)

        if response.is_error:
            self._handle_http_error(response)

        data = response.json()
        prompts = data.get("prompts", [])

        logger.info(f"Listed prompts: {len(prompts)} prompts")
        return prompts

    async def list_repos(self) -> list[RepoInfo]:
        """List all available repositories.

        Returns:
            List of RepoInfo objects

        Raises:
            GluePromptError: If listing fails
        """
        logger.info("Listing repositories via API")

        url = f"{self.base_url}/repos"
        response = await self.client.get(url)

        if response.is_error:
            self._handle_http_error(response)

        repos_response = ReposResponse(**response.json())

        logger.info(f"Listed repositories: {len(repos_response.repos)} repos")
        return repos_response.repos

    async def health_check(self) -> dict[str, str]:
        """Check server health.

        Returns:
            Dictionary with health status

        Raises:
            GluePromptError: If health check fails
        """
        url = f"{self.base_url}/health"
        response = await self.client.get(url)

        if response.is_error:
            self._handle_http_error(response)

        return response.json()

    # Methods not available via API - raise appropriate errors

    def checkout(self, branch_or_tag: str, create_branch: bool = False) -> None:
        """Checkout a version (branch or tag).

        Not available via API - raises VersionError.

        Args:
            branch_or_tag: Branch or tag name
            create_branch: If True and branch doesn't exist, create it

        Raises:
            VersionError: Always raised since this operation is not available via API
        """
        raise VersionError(
            "Checkout operation is not available via API. "
            "Use local PromptRegistry for git operations."
        )

    def diff(
        self,
        prompt_path: str,
        version1: str | None = None,
        version2: str | None = None,
    ) -> str:
        """Get diff of a prompt between two versions.

        Not available via API - raises VersionError.

        Args:
            prompt_path: Relative path to prompt
            version1: First version (None for current)
            version2: Second version (None for current)

        Returns:
            Git diff string

        Raises:
            VersionError: Always raised since this operation is not available via API
        """
        raise VersionError(
            "Diff operation is not available via API. "
            "Use local PromptRegistry for git operations."
        )

    def rollback(self, version: str) -> None:
        """Rollback to a previous version.

        Not available via API - raises VersionError.

        Args:
            version: Branch or tag to rollback to

        Raises:
            VersionError: Always raised since this operation is not available via API
        """
        raise VersionError(
            "Rollback operation is not available via API. "
            "Use local PromptRegistry for git operations."
        )

    def clear_cache(self) -> None:
        """Clear the prompt cache.

        Not available via API - cache is managed server-side.

        Raises:
            NotImplementedError: Always raised since cache is server-side
        """
        raise NotImplementedError(
            "Cache management is not available via API. "
            "Cache is managed server-side."
        )

    def invalidate_cache(self, prompt_path: str | None = None) -> None:
        """Invalidate cache for a prompt or all prompts.

        Not available via API - cache is managed server-side.

        Args:
            prompt_path: Specific prompt path, or None for all

        Raises:
            NotImplementedError: Always raised since cache is server-side
        """
        raise NotImplementedError(
            "Cache management is not available via API. "
            "Cache is managed server-side."
        )

    @property
    def has_versioning(self) -> bool:
        """Check if versioning is available.

        Always True for API client since server supports versioning.

        Returns:
            True (versioning is always available via API)
        """
        return True

