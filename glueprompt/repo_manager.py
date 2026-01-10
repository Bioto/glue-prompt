"""Repository management for cloning and caching prompt repos."""

import json
import shutil
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo

from glueprompt.exceptions import GitOperationError
from glueprompt.logging import get_logger

logger = get_logger(__name__)


def get_cache_dir() -> Path:
    """Get the cache directory for prompt repos.

    Returns:
        Path to cache directory (~/.cache/glueprompt/repos)
    """
    cache_dir = Path.home() / ".cache" / "glueprompt" / "repos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_config_dir() -> Path:
    """Get the config directory for glueprompt.

    Returns:
        Path to config directory (~/.config/glueprompt)
    """
    config_dir = Path.home() / ".config" / "glueprompt"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_repos_config_path() -> Path:
    """Get path to repos config file.

    Returns:
        Path to repos.json config file
    """
    return get_config_dir() / "repos.json"


def get_default_repo_path() -> Path:
    """Get path to default repo config file.

    Returns:
        Path to default_repo.txt file
    """
    return get_config_dir() / "default_repo.txt"


def get_default_repo() -> str | None:
    """Get the default repository name.

    Returns:
        Default repo name or None if not set
    """
    default_path = get_default_repo_path()
    if default_path.exists():
        return default_path.read_text().strip() or None
    return None


def set_default_repo(name: str | None) -> None:
    """Set the default repository name.

    Args:
        name: Repository name to set as default, or None to clear
    """
    default_path = get_default_repo_path()
    if name:
        default_path.write_text(name)
    elif default_path.exists():
        default_path.unlink()


def load_repos_config() -> dict[str, dict]:
    """Load the repos configuration.

    Returns:
        Dictionary mapping repo names to their config
    """
    config_path = get_repos_config_path()
    if config_path.exists():
        with config_path.open("r") as f:
            return json.load(f)
    return {}


def save_repos_config(config: dict[str, dict]) -> None:
    """Save the repos configuration.

    Args:
        config: Dictionary mapping repo names to their config
    """
    config_path = get_repos_config_path()
    logger.debug(f"Saving repos config to {config_path} ({len(config)} repos)")
    with config_path.open("w") as f:
        json.dump(config, f, indent=2)


def url_to_repo_name(url: str) -> str:
    """Extract repo name from URL.

    Args:
        url: Git repository URL

    Returns:
        Repository name (e.g., "my-prompts" from "https://github.com/user/my-prompts.git")
    """
    # Handle SSH and HTTPS URLs
    name = url.rstrip("/").rstrip(".git").split("/")[-1]
    return name


class RepoManager:
    """Manages cloning and caching of prompt repositories."""

    def __init__(self):
        """Initialize the repo manager."""
        self.cache_dir = get_cache_dir()
        self.config = load_repos_config()

    def clone(
        self,
        url: str,
        name: str | None = None,
        branch: str | None = None,
        force: bool = False,
    ) -> Path:
        """Clone a prompt repository to the cache.

        Args:
            url: Git repository URL
            name: Optional name for the repo (defaults to repo name from URL)
            branch: Optional branch to checkout after cloning
            force: If True, remove existing repo and re-clone

        Returns:
            Path to cloned repository

        Raises:
            GitOperationError: If cloning fails
        """
        if name is None:
            name = url_to_repo_name(url)

        repo_path = self.cache_dir / name

        logger.info(f"Cloning repository: {name} from {url} (branch={branch}, force={force})")

        # Check if already exists
        if repo_path.exists():
            if force:
                logger.debug(f"Removing existing repository at {repo_path}")
                shutil.rmtree(repo_path)
            else:
                logger.warning(f"Repository '{name}' already exists at {repo_path}")
                raise GitOperationError(
                    f"Repository '{name}' already exists at {repo_path}. "
                    f"Use --force to re-clone or 'glueprompt repo remove {name}' first."
                )

        try:
            # Clone the repo
            clone_args = {}
            if branch:
                clone_args["branch"] = branch
                logger.debug(f"Cloning with branch: {branch}")

            logger.debug(f"Cloning to {repo_path}")
            Repo.clone_from(url, str(repo_path), **clone_args)

            # Fetch all branches and tags
            repo = Repo(str(repo_path))
            try:
                logger.debug("Fetching all branches and tags")
                repo.git.fetch("--all", "--tags", "--prune")
            except Exception as e:
                # If fetch fails, continue anyway
                logger.debug(f"Fetch failed (non-fatal): {e}")

            # Save to config
            self.config[name] = {
                "url": url,
                "path": str(repo_path),
                "default_branch": branch,
            }
            save_repos_config(self.config)

            logger.info(f"Successfully cloned repository: {name} to {repo_path}")
            return repo_path
        except GitCommandError as e:
            # Clean up partial clone
            if repo_path.exists():
                logger.debug(f"Cleaning up partial clone at {repo_path}")
                shutil.rmtree(repo_path)
            logger.error(f"Failed to clone repository: {e}", exc_info=True)
            raise GitOperationError(f"Failed to clone repository: {e}") from e

    def remove(self, name: str) -> None:
        """Remove a cached repository.

        Args:
            name: Repository name

        Raises:
            GitOperationError: If repo doesn't exist
        """
        logger.info(f"Removing repository: {name}")
        if name not in self.config:
            logger.error(f"Repository '{name}' not found in config")
            raise GitOperationError(f"Repository '{name}' not found in config")

        repo_path = Path(self.config[name]["path"])
        if repo_path.exists():
            logger.debug(f"Removing directory: {repo_path}")
            shutil.rmtree(repo_path)
        else:
            logger.debug(f"Repository directory does not exist: {repo_path}")

        del self.config[name]
        save_repos_config(self.config)
        logger.info(f"Successfully removed repository: {name}")

    def get_path(self, name: str) -> Path:
        """Get path to a cached repository.

        Args:
            name: Repository name

        Returns:
            Path to repository

        Raises:
            GitOperationError: If repo doesn't exist
        """
        if name not in self.config:
            raise GitOperationError(
                f"Repository '{name}' not found. "
                f"Use 'glueprompt repo add <url>' to add it."
            )

        path = Path(self.config[name]["path"])
        if not path.exists():
            raise GitOperationError(
                f"Repository '{name}' path no longer exists at {path}. "
                f"Use 'glueprompt repo add <url> --force' to re-clone."
            )

        return path

    def list_repos(self) -> list[dict]:
        """List all cached repositories.

        Returns:
            List of repo info dictionaries
        """
        repos = []
        for name, info in self.config.items():
            path = Path(info["path"])
            exists = path.exists()

            repo_info = {
                "name": name,
                "url": info["url"],
                "path": str(path),
                "exists": exists,
            }

            # Get current branch if exists
            if exists:
                try:
                    repo = Repo(str(path))
                    if not repo.head.is_detached:
                        repo_info["branch"] = repo.active_branch.name
                    else:
                        repo_info["branch"] = f"detached ({repo.head.commit.hexsha[:8]})"
                except Exception:
                    repo_info["branch"] = "unknown"

            repos.append(repo_info)

        return repos

    def update(self, name: str, branch: str | None = None) -> None:
        """Pull latest changes for a repository.

        Args:
            name: Repository name
            branch: Optional branch to checkout before pulling

        Raises:
            GitOperationError: If update fails
        """
        logger.info(f"Updating repository: {name} (branch={branch})")
        path = self.get_path(name)

        try:
            repo = Repo(str(path))

            if branch:
                logger.debug(f"Checking out branch: {branch}")
                repo.git.checkout(branch)

            # Pull latest
            logger.debug("Pulling latest changes")
            repo.git.pull()
            logger.info(f"Successfully updated repository: {name}")
        except GitCommandError as e:
            logger.error(f"Failed to update repository: {e}", exc_info=True)
            raise GitOperationError(f"Failed to update repository: {e}") from e

    def get_default_repo(self) -> str | None:
        """Get the default repository name.

        Returns:
            Default repo name or None if not set
        """
        return get_default_repo()

    def set_default_repo(self, name: str | None) -> None:
        """Set the default repository name.

        Args:
            name: Repository name to set as default, or None to clear

        Raises:
            GitOperationError: If repo doesn't exist
        """
        if name:
            logger.info(f"Setting default repository: {name}")
            if name not in self.config:
                logger.error(f"Repository '{name}' not found in config")
                raise GitOperationError(
                    f"Repository '{name}' not found. "
                    f"Use 'glueprompt repo add <url>' to add it first."
                )
        else:
            logger.info("Clearing default repository")
        set_default_repo(name)

