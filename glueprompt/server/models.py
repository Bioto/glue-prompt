"""Pydantic models for FastAPI requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


class PromptMetadataResponse(BaseModel):
    """Prompt metadata response."""

    name: str
    version: str
    description: str
    author: str
    tags: list[str]


class PromptResponse(BaseModel):
    """Prompt response with metadata and template."""

    metadata: PromptMetadataResponse
    template: str
    variables: dict[str, dict[str, Any]]


class RenderRequest(BaseModel):
    """Request to render a prompt."""

    variables: dict[str, Any] = Field(default_factory=dict, description="Template variables")


class RenderResponse(BaseModel):
    """Rendered prompt response."""

    rendered: str
    version: str


class VersionInfoResponse(BaseModel):
    """Version information for API responses."""

    name: str
    commit_hash: str
    is_branch: bool
    is_current: bool = False


class VersionsResponse(BaseModel):
    """List of versions response."""

    branches: list[VersionInfoResponse]
    tags: list[VersionInfoResponse]
    current: str


class RepoInfo(BaseModel):
    """Repository information."""

    name: str
    url: str
    path: str
    current_branch: str | None = None


class ReposResponse(BaseModel):
    """List of repositories response."""

    repos: list[RepoInfo]

