"""FastAPI application for serving prompts."""

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from glueprompt.loader import PromptLoader
from glueprompt.repo_manager import RepoManager
from glueprompt.renderer import TemplateRenderer
from glueprompt.server.models import (
    PromptMetadataResponse,
    PromptResponse,
    RenderRequest,
    RenderResponse,
    RepoInfo,
    ReposResponse,
    VersionInfo,
    VersionsResponse,
)
from glueprompt.server.worktree_manager import WorktreeManager
from glueprompt.versioning import VersionManager

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

    return ReposResponse(repos=repos)


@app.get("/repos/{repo}/versions", response_model=VersionsResponse)
def list_versions(repo: str) -> VersionsResponse:
    """List all available versions (branches and tags) for a repository."""
    manager = get_repo_manager()

    try:
        repo_path = manager.get_path(repo)
        version_mgr = VersionManager(repo_path)

        branches = version_mgr.list_branches()
        tags = version_mgr.list_tags()
        current = version_mgr.current_version()

        return VersionsResponse(
            branches=[
                VersionInfo(
                    name=branch.name,
                    commit_hash=branch.commit_hash,
                    is_branch=True,
                    is_current=branch.is_current,
                )
                for branch in branches
            ],
            tags=[
                VersionInfo(
                    name=tag.branch_or_tag,
                    commit_hash=tag.commit_hash,
                    is_branch=False,
                )
                for tag in tags
            ],
            current=current.branch_or_tag,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/repos/{repo}/prompts")
def list_prompts(
    repo: str,
    version: Annotated[str | None, Query(description="Version (branch or tag)")] = None,
) -> dict[str, list[str]]:
    """List all prompts in a repository, optionally filtered by version."""
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)
        prompts = worktree_mgr.list_prompts(version=version)

        return {"prompts": prompts}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/repos/{repo}/prompts/{prompt_path:path}", response_model=PromptResponse)
def get_prompt(
    repo: str,
    prompt_path: str,
    version: Annotated[str | None, Query(description="Prompt version (e.g., 1.0.5)")] = None,
) -> PromptResponse:
    """Get a prompt by path, optionally at a specific version.
    
    When version is specified, looks for tag '{prompt_path}/v{version}'.
    """
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)

        if version:
            # Convert version to prompt-specific tag format
            # e.g., version="1.0.5", prompt_path="default" -> tag="default/v1.0.5"
            prompt_name = prompt_path.replace("/", "-")
            tag_name = f"{prompt_name}/v{version}"
            
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
        # Provide more helpful error messages
        if "not found" in error_msg.lower() or "not exist" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


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
    manager = get_repo_manager()

    try:
        manager.get_path(repo)  # Verify repo exists
        worktree_mgr = WorktreeManager(repo)

        if version:
            # Convert version to prompt-specific tag format
            prompt_name = prompt_path.replace("/", "-")
            tag_name = f"{prompt_name}/v{version}"
            
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

        return RenderResponse(rendered=rendered, version=used_version)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "missing required" in error_msg.lower() or "template" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=f"Internal server error: {error_msg}")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

