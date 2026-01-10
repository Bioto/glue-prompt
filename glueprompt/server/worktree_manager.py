"""Git worktree management for concurrent version access."""

import shutil
from pathlib import Path

from git import GitCommandError, Repo
from git.exc import InvalidGitRepositoryError

from glueprompt.exceptions import GitOperationError
from glueprompt.logging import get_json_logger

logger = get_json_logger(__name__)


def get_worktree_dir() -> Path:
    """Get the worktree directory.

    Returns:
        Path to worktree directory (~/.cache/glueprompt/worktrees)
    """
    worktree_dir = Path.home() / ".cache" / "glueprompt" / "worktrees"
    worktree_dir.mkdir(parents=True, exist_ok=True)
    return worktree_dir


class WorktreeManager:
    """Manages git worktrees for concurrent version access.

    Creates separate worktrees for each version (branch/tag) so multiple
    versions can be accessed simultaneously without conflicts.
    """

    def __init__(self, repo_name: str):
        """Initialize worktree manager for a repository.

        Args:
            repo_name: Name of the cached repository

        Raises:
            GitOperationError: If repo doesn't exist
        """
        from glueprompt.repo_manager import RepoManager

        manager = RepoManager()
        self.repo_path = manager.get_path(repo_name)
        self.repo_name = repo_name
        self.worktree_base = get_worktree_dir() / repo_name
        self.worktree_base.mkdir(parents=True, exist_ok=True)

        # Open main repo
        try:
            self.main_repo = Repo(str(self.repo_path))
            logger.debug("Initialized worktree manager", extra={"repo": repo_name, "path": str(self.repo_path)})
        except InvalidGitRepositoryError as e:
            logger.error("Invalid git repository", extra={"repo": repo_name, "path": str(self.repo_path)}, exc_info=True)
            raise GitOperationError(f"Not a valid git repository: {self.repo_path}") from e

    def get_worktree_path(self, version: str) -> Path:
        """Get path to worktree for a version.

        Args:
            version: Branch or tag name

        Returns:
            Path to worktree directory
        """
        # Sanitize version name for filesystem
        safe_version = version.replace("/", "_").replace("\\", "_")
        return self.worktree_base / safe_version

    def ensure_worktree(self, version: str) -> Path:
        """Ensure worktree exists for a version, creating if needed.

        Args:
            version: Branch or tag name

        Returns:
            Path to worktree directory

        Raises:
            GitOperationError: If worktree creation fails
        """
        worktree_path = self.get_worktree_path(version)

        # Check if worktree already exists
        if worktree_path.exists():
            # Verify it's still valid
            try:
                Repo(str(worktree_path))
                # Check if it's pointing to the right commit
                logger.debug("Using existing worktree", extra={"repo": self.repo_name, "version": version, "path": str(worktree_path)})
                return worktree_path
            except Exception as e:
                # Worktree is broken, remove and recreate
                logger.warning("Broken worktree detected, removing", extra={"repo": self.repo_name, "version": version, "error": str(e)})
                shutil.rmtree(worktree_path)

        # Create new worktree
        logger.info("Creating worktree", extra={"repo": self.repo_name, "version": version, "path": str(worktree_path)})
        try:
            # Fetch latest from remote
            try:
                logger.debug("Fetching latest from remote", extra={"repo": self.repo_name})
                self.main_repo.git.fetch("--all", "--tags", "--prune")
            except Exception as e:
                logger.debug("Fetch failed (non-fatal)", extra={"repo": self.repo_name, "error": str(e)})

            # Check if version exists as tag, local branch, or remote branch
            tag_names = [tag.name for tag in self.main_repo.tags]
            branch_names = [ref.name for ref in self.main_repo.branches]

            # Get remote branches using git branch -r
            remote_branches = []
            try:
                output = self.main_repo.git.branch("-r", "--format=%(refname:short)")
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith("origin/") and line != "origin/HEAD":
                        remote_branches.append(line.replace("origin/", ""))
            except Exception as e:
                logger.debug(
                    "Failed to get remote branches (non-fatal)",
                    extra={"repo": self.repo_name, "error": str(e)},
                    exc_info=True,
                )

            if version in tag_names:
                # Create worktree from tag
                tag_ref = self.main_repo.tags[version]
                logger.debug("Creating worktree from tag", extra={"repo": self.repo_name, "version": version, "tag": version})
                self.main_repo.git.worktree("add", str(worktree_path), tag_ref.commit.hexsha)
            elif version in branch_names:
                # Create worktree from local branch
                logger.debug("Creating worktree from local branch", extra={"repo": self.repo_name, "version": version})
                self.main_repo.git.worktree("add", str(worktree_path), version)
            elif version in remote_branches:
                # Create worktree from remote branch (creates local tracking branch)
                logger.debug("Creating worktree from remote branch", extra={"repo": self.repo_name, "version": version})
                self.main_repo.git.worktree("add", "-b", version, str(worktree_path), f"origin/{version}")
            else:
                # Version not found - provide helpful error
                all_versions = branch_names + remote_branches + tag_names
                logger.error(
                    "Version not found",
                    extra={"repo": self.repo_name, "version": version, "available": all_versions},
                )
                raise GitOperationError(
                    f"Version '{version}' not found. "
                    f"Available versions: {all_versions if all_versions else ['(none)']}"
                )

            logger.info("Worktree created successfully", extra={"repo": self.repo_name, "version": version, "path": str(worktree_path)})
            return worktree_path
        except GitCommandError as e:
            logger.error("Failed to create worktree", extra={"repo": self.repo_name, "version": version, "error": str(e)}, exc_info=True)
            raise GitOperationError(f"Failed to create worktree for {version}: {e}") from e

    def get_prompt_path(self, version: str, prompt_path: str) -> tuple[Path, Path]:
        """Get path to a prompt file in a version worktree.

        Args:
            version: Branch or tag name
            prompt_path: Relative path to prompt (e.g., "assistants/helper")

        Returns:
            Tuple of (worktree_path, prompt_file_path)

        Raises:
            GitOperationError: If worktree or prompt doesn't exist
        """
        worktree_path = self.ensure_worktree(version)

        # Try .yaml first, then .yml
        yaml_path = worktree_path / f"{prompt_path}.yaml"
        if yaml_path.exists():
            return (worktree_path, yaml_path)

        yml_path = worktree_path / f"{prompt_path}.yml"
        if yml_path.exists():
            return (worktree_path, yml_path)

        raise GitOperationError(f"Prompt not found: {prompt_path} in version {version}")

    def list_prompts(self, version: str | None = None) -> list[str]:
        """List all prompts in a version.

        Args:
            version: Branch or tag name, or None for main branch

        Returns:
            List of prompt paths (relative, without extension)
        """
        base_path = self.repo_path if version is None else self.ensure_worktree(version)

        prompts: list[str] = []
        for yaml_file in base_path.rglob("*.yaml"):
            rel_path = yaml_file.relative_to(base_path)
            prompt_path = str(rel_path).rsplit(".", 1)[0]
            prompts.append(prompt_path)

        for yml_file in base_path.rglob("*.yml"):
            rel_path = yml_file.relative_to(base_path)
            prompt_path = str(rel_path).rsplit(".", 1)[0]
            if prompt_path not in prompts:
                prompts.append(prompt_path)

        return sorted(prompts)

    def cleanup_unused_worktrees(self, active_versions: set[str]) -> None:
        """Remove worktrees that are no longer needed.

        Args:
            active_versions: Set of version names that are currently in use
        """
        if not self.worktree_base.exists():
            return

        logger.info("Cleaning up unused worktrees", extra={"repo": self.repo_name, "active_versions": list(active_versions)})
        removed_count = 0

        for worktree_dir in self.worktree_base.iterdir():
            if not worktree_dir.is_dir():
                continue

            version = worktree_dir.name.replace("_", "/")
            if version not in active_versions:
                try:
                    # Remove worktree properly
                    logger.debug("Removing unused worktree", extra={"repo": self.repo_name, "version": version})
                    self.main_repo.git.worktree("remove", str(worktree_dir), force=True)
                    removed_count += 1
                except Exception as e:
                    # Fallback: just delete directory
                    logger.warning("Failed to remove worktree properly, using fallback", extra={"repo": self.repo_name, "version": version, "error": str(e)})
                    shutil.rmtree(worktree_dir, ignore_errors=True)
                    removed_count += 1

        if removed_count > 0:
            logger.info("Cleaned up worktrees", extra={"repo": self.repo_name, "removed_count": removed_count})

