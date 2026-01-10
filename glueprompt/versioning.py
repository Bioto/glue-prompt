"""Git version management for prompts."""

from pathlib import Path
from typing import Any

from git import GitCommandError, InvalidGitRepositoryError, Repo
from git.exc import GitError

from glueprompt.exceptions import GitOperationError, VersionError
from glueprompt.models.version import BranchInfo, VersionInfo


class VersionManager:
    """Manages git branches and tags for prompt versioning.

    Attributes:
        repo: GitPython Repo instance
        prompts_dir: Path to prompts directory
    """

    def __init__(self, prompts_dir: Path | str):
        """Initialize the version manager.

        Args:
            prompts_dir: Path to prompts git repository/submodule

        Raises:
            GitOperationError: If prompts_dir is not a valid git repository
        """
        self.prompts_dir = Path(prompts_dir)

        try:
            self.repo = Repo(str(self.prompts_dir))
        except InvalidGitRepositoryError as e:
            raise GitOperationError(
                f"Not a valid git repository: {self.prompts_dir}"
            ) from e
        except Exception as e:
            raise GitOperationError(f"Failed to initialize git repo: {e}") from e

    def current_version(self) -> VersionInfo:
        """Get current version (branch or tag).

        Returns:
            VersionInfo for current branch/tag

        Raises:
            VersionError: If unable to determine current version
        """
        try:
            # Check if we're on a branch
            if self.repo.head.is_detached:
                # Check if HEAD points to a tag
                head_commit = self.repo.head.commit
                tags = [tag for tag in self.repo.tags if tag.commit == head_commit]
                if tags:
                    tag = tags[0]
                    return VersionInfo(
                        branch_or_tag=tag.name,
                        commit_hash=head_commit.hexsha[:8],
                        commit_message=head_commit.message.split("\n")[0],
                        commit_date=head_commit.committed_datetime,
                        is_branch=False,
                    )
                # Detached HEAD, not a tag
                return VersionInfo(
                    branch_or_tag="HEAD",
                    commit_hash=head_commit.hexsha[:8],
                    commit_message=head_commit.message.split("\n")[0],
                    commit_date=head_commit.committed_datetime,
                    is_branch=False,
                )
            else:
                # On a branch
                branch = self.repo.active_branch
                commit = branch.commit
                return VersionInfo(
                    branch_or_tag=branch.name,
                    commit_hash=commit.hexsha[:8],
                    commit_message=commit.message.split("\n")[0],
                    commit_date=commit.committed_datetime,
                    is_branch=True,
                )
        except Exception as e:
            raise VersionError(f"Failed to get current version: {e}") from e

    def list_branches(self) -> list[BranchInfo]:
        """List all branches (local and remote).

        Returns:
            List of BranchInfo for all branches
        """
        try:
            # Fetch latest from remote
            try:
                self.repo.git.fetch("--all", "--tags", "--prune")
            except Exception:
                pass

            current_branch = self.repo.active_branch.name if not self.repo.head.is_detached else None
            branches = []
            seen_branches = set()

            # List local branches
            for ref in self.repo.branches:
                if ref.name not in seen_branches:
                    branches.append(
                        BranchInfo(
                            name=ref.name,
                            commit_hash=ref.commit.hexsha[:8],
                            is_current=ref.name == current_branch,
                        )
                    )
                    seen_branches.add(ref.name)

            # List remote branches using git branch -r
            remote_output = self.repo.git.branch("-r", "--format=%(refname:short)")
            for line in remote_output.splitlines():
                line = line.strip()
                if line.startswith("origin/") and line != "origin/HEAD":
                    branch_name = line.replace("origin/", "")
                    if branch_name not in seen_branches:
                        commit_hash = self.repo.git.rev_parse(f"origin/{branch_name}", short=8)
                        branches.append(
                            BranchInfo(
                                name=branch_name,
                                commit_hash=commit_hash,
                                is_current=False,
                            )
                        )
                        seen_branches.add(branch_name)

            return branches
        except Exception as e:
            raise VersionError(f"Failed to list branches: {e}") from e

    def list_tags(self) -> list[VersionInfo]:
        """List all tags.

        Returns:
            List of VersionInfo for all tags
        """
        try:
            tags = []
            for tag in self.repo.tags:
                commit = tag.commit
                tags.append(
                    VersionInfo(
                        branch_or_tag=tag.name,
                        commit_hash=commit.hexsha[:8],
                        commit_message=commit.message.split("\n")[0],
                        commit_date=commit.committed_datetime,
                        is_branch=False,
                    )
                )
            return tags
        except Exception as e:
            raise VersionError(f"Failed to list tags: {e}") from e

    def checkout(self, branch_or_tag: str, create_branch: bool = False) -> None:
        """Checkout a branch or tag.

        Args:
            branch_or_tag: Branch or tag name to checkout
            create_branch: If True and branch doesn't exist, create it

        Raises:
            VersionError: If checkout fails
        """
        try:
            # Check if it's a tag
            tags = [tag.name for tag in self.repo.tags if tag.name == branch_or_tag]
            if tags:
                self.repo.git.checkout(branch_or_tag)
                return

            # Check if it's a branch
            branches = [ref.name for ref in self.repo.branches if ref.name == branch_or_tag]
            if branches:
                self.repo.git.checkout(branch_or_tag)
                return

            # Branch doesn't exist
            if create_branch:
                self.repo.git.checkout("-b", branch_or_tag)
                return

            raise VersionError(
                f"Branch or tag '{branch_or_tag}' not found. "
                f"Available branches: {[b.name for b in self.repo.branches]}, "
                f"Available tags: {[t.name for t in self.repo.tags]}"
            )
        except GitCommandError as e:
            raise VersionError(f"Git checkout failed: {e}") from e
        except Exception as e:
            raise VersionError(f"Failed to checkout {branch_or_tag}: {e}") from e

    def diff(
        self,
        prompt_path: str,
        version1: str | None = None,
        version2: str | None = None,
    ) -> str:
        """Get diff of a prompt file between two versions.

        Args:
            prompt_path: Relative path to prompt file
            version1: First version (branch/tag/commit), None for current
            version2: Second version (branch/tag/commit), None for current

        Returns:
            Git diff string

        Raises:
            VersionError: If diff operation fails
        """
        try:
            # Resolve prompt file path
            prompt_file = self.prompts_dir / f"{prompt_path}.yaml"
            if not prompt_file.exists():
                prompt_file = self.prompts_dir / f"{prompt_path}.yml"
            if not prompt_file.exists():
                raise VersionError(f"Prompt file not found: {prompt_path}")

            rel_path = prompt_file.relative_to(self.prompts_dir)

            # Build git diff command
            if version1 and version2:
                return self.repo.git.diff(version1, version2, "--", str(rel_path))
            elif version1:
                return self.repo.git.diff(version1, "--", str(rel_path))
            elif version2:
                return self.repo.git.diff(version2, "--", str(rel_path))
            else:
                # Diff against HEAD
                return self.repo.git.diff("HEAD", "--", str(rel_path))
        except GitCommandError as e:
            raise VersionError(f"Git diff failed: {e}") from e
        except Exception as e:
            raise VersionError(f"Failed to get diff: {e}") from e

    def rollback(self, version: str) -> None:
        """Rollback to a previous version (alias for checkout).

        Args:
            version: Branch or tag to rollback to

        Raises:
            VersionError: If rollback fails
        """
        self.checkout(version)

