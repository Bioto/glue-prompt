"""FastAPI application for serving prompts."""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from glueprompt.loader import PromptLoader
from glueprompt.logging import get_json_logger
from glueprompt.renderer import TemplateRenderer
from glueprompt.repo_manager import RepoManager
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
from glueprompt.server.worktree_manager import WorktreeManager
from glueprompt.versioning import VersionManager

logger = get_json_logger(__name__)

app = FastAPI(
    title="GluePrompt API",
    description="API for serving versioned prompts",
    version="0.1.0",
)


def get_repo_manager() -> RepoManager:
    """Get repository manager instance."""
    return RepoManager()


@app.get("/repos", response_model=ReposResponse)
def list_repos() -> ReposResponse:
    """List all available prompt repositories."""
    logger.info("Listing repositories", extra={"endpoint": "/repos"})
    manager = get_repo_manager()
    repos_data = manager.list_repos()

    repos = []
    for repo_info in repos_data:
        if repo_info["exists"]:
            repos.append(
                RepoInfo(
                    name=repo_info["name"],
                    url=repo_info["url"],
                    path=repo_info["path"],
                    current_branch=repo_info.get("branch"),
                )
            )

    logger.info("Listed repositories", extra={"count": len(repos)})
    return ReposResponse(repos=repos)


@app.get("/repos/{repo}/versions", response_model=VersionsResponse)
def list_versions(repo: str) -> VersionsResponse:
    """List all available versions (branches and tags) for a repository."""
    logger.info("Listing versions", extra={"repo": repo, "endpoint": f"/repos/{repo}/versions"})
    manager = get_repo_manager()

    try:
        repo_path = manager.get_path(repo)
        version_mgr = VersionManager(repo_path)

        branches = version_mgr.list_branches()
        tags = version_mgr.list_tags()
        current = version_mgr.current_version()

        logger.debug(
            "Retrieved versions",
            extra={
                "repo": repo,
                "branch_count": len(branches),
                "tag_count": len(tags),
                "current": current.branch_or_tag,
            },
        )

        return VersionsResponse(
            branches=[
                VersionInfoResponse(
                    name=branch.name,
                    commit_hash=branch.commit_hash,
                    is_branch=True,
                    is_current=branch.is_current,
                )
                for branch in branches
            ],
            tags=[
                VersionInfoResponse(
                    name=tag.branch_or_tag,
                    commit_hash=tag.commit_hash,
                    is_branch=False,
                )
                for tag in tags
            ],
            current=current.branch_or_tag,
        )
    except Exception as e:
        logger.error("Failed to list versions", extra={"repo": repo, "error": str(e)}, exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/repos/{repo}/prompts")
def list_prompts(
    repo: str,
    version: Annotated[str | None, Query(description="Version (branch or tag)")] = None,
) -> dict[str, list[str]]:
    """List all prompts in a repository, optionally filtered by version."""
    logger.info("Listing prompts", extra={"repo": repo, "version": version, "endpoint": f"/repos/{repo}/prompts"})
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)
        prompts = worktree_mgr.list_prompts(version=version)

        logger.info("Listed prompts", extra={"repo": repo, "version": version, "count": len(prompts)})
        return {"prompts": prompts}
    except Exception as e:
        logger.error("Failed to list prompts", extra={"repo": repo, "version": version, "error": str(e)}, exc_info=True)
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/repos/{repo}/prompts/{prompt_path:path}", response_model=PromptResponse)
def get_prompt(
    repo: str,
    prompt_path: str,
    version: Annotated[str | None, Query(description="Prompt version (e.g., 1.0.5)")] = None,
) -> PromptResponse:
    """Get a prompt by path, optionally at a specific version.

    When version is specified, looks for tag '{prompt_path}/v{version}'.
    """
    logger.info(
        "Getting prompt",
        extra={"repo": repo, "prompt": prompt_path, "version": version, "endpoint": f"/repos/{repo}/prompts/{prompt_path}"},
    )
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)

        if version:
            # Convert version to prompt-specific tag format
            # e.g., version="1.0.5", prompt_path="default" -> tag="default/v1.0.5"
            prompt_name = prompt_path.replace("/", "-")
            tag_name = f"{prompt_name}/v{version}"
            logger.debug("Using version-specific tag", extra={"repo": repo, "prompt": prompt_path, "tag": tag_name})

            # Use worktree for specific version
            worktree_path, prompt_file = worktree_mgr.get_prompt_path(tag_name, prompt_path)
            loader = PromptLoader(worktree_path, cache_enabled=False)
            # Extract relative path from worktree
            rel_path = prompt_file.relative_to(worktree_path)
            prompt_path_rel = str(rel_path).rsplit(".", 1)[0]
            prompt = loader.load(prompt_path_rel, use_cache=False)
        else:
            # Use main repo
            repo_path = manager.get_path(repo)
            loader = PromptLoader(repo_path, cache_enabled=False)
            prompt = loader.load(prompt_path, use_cache=False)

        logger.info(
            "Retrieved prompt",
            extra={
                "repo": repo,
                "prompt": prompt_path,
                "version": prompt.metadata.version,
                "name": prompt.metadata.name,
            },
        )
        return PromptResponse(
            metadata=PromptMetadataResponse(
                name=prompt.metadata.name,
                version=prompt.metadata.version,
                description=prompt.metadata.description,
                author=prompt.metadata.author,
                tags=prompt.metadata.tags,
            ),
            template=prompt.template,
            variables={
                name: {
                    "type": var_def.type,
                    "required": var_def.required,
                    "default": var_def.default,
                    "description": var_def.description,
                }
                for name, var_def in prompt.variables.items()
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Failed to get prompt",
            extra={"repo": repo, "prompt": prompt_path, "version": version, "error": error_msg},
            exc_info=True,
        )
        # Provide more helpful error messages
        if "not found" in error_msg.lower() or "not exist" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from e
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}") from e


@app.post("/repos/{repo}/prompts/{prompt_path:path}/render", response_model=RenderResponse)
def render_prompt(
    repo: str,
    prompt_path: str,
    request: RenderRequest,
    version: Annotated[str | None, Query(description="Prompt version (e.g., 1.0.5)")] = None,
) -> RenderResponse:
    """Render a prompt with variables, optionally at a specific version.

    When version is specified, looks for tag '{prompt_path}/v{version}'.
    """
    logger.info(
        "Rendering prompt",
        extra={
            "repo": repo,
            "prompt": prompt_path,
            "version": version,
            "variables": list(request.variables.keys()),
            "endpoint": f"/repos/{repo}/prompts/{prompt_path}/render",
        },
    )
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)

        if version:
            # Convert version to prompt-specific tag format
            prompt_name = prompt_path.replace("/", "-")
            tag_name = f"{prompt_name}/v{version}"
            logger.debug("Using version-specific tag", extra={"repo": repo, "prompt": prompt_path, "tag": tag_name})

            # Use worktree for specific version
            worktree_path, prompt_file = worktree_mgr.get_prompt_path(tag_name, prompt_path)
            loader = PromptLoader(worktree_path, cache_enabled=False)
            rel_path = prompt_file.relative_to(worktree_path)
            prompt_path_rel = str(rel_path).rsplit(".", 1)[0]
            prompt = loader.load(prompt_path_rel, use_cache=False)
            used_version = version
        else:
            # Use main repo
            repo_path = manager.get_path(repo)
            loader = PromptLoader(repo_path, cache_enabled=False)
            prompt = loader.load(prompt_path, use_cache=False)
            version_mgr = VersionManager(repo_path)
            used_version = version_mgr.current_version().branch_or_tag

        renderer = TemplateRenderer()
        rendered = renderer.render(prompt, **request.variables)

        logger.info(
            "Rendered prompt",
            extra={
                "repo": repo,
                "prompt": prompt_path,
                "version": used_version,
                "rendered_length": len(rendered),
            },
        )
        return RenderResponse(rendered=rendered, version=used_version)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(
            "Failed to render prompt",
            extra={
                "repo": repo,
                "prompt": prompt_path,
                "version": version,
                "error": error_msg,
            },
            exc_info=True,
        )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from e
        if "missing required" in error_msg.lower() or "template" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg) from e
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}") from e


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

