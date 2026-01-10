"""Version information models."""

from datetime import datetime

from pydantic import BaseModel, Field


class VersionInfo(BaseModel):
    """Information about a prompt version.

    Attributes:
        branch_or_tag: Branch or tag name
        commit_hash: Git commit hash
        commit_message: Commit message
        commit_date: Commit date
        is_branch: Whether this is a branch (True) or tag (False)
    """

    branch_or_tag: str = Field(description="Branch or tag name")
    commit_hash: str = Field(description="Git commit hash")
    commit_message: str = Field(default="", description="Commit message")
    commit_date: datetime = Field(description="Commit date")
    is_branch: bool = Field(description="True if branch, False if tag")


class BranchInfo(BaseModel):
    """Information about a git branch.

    Attributes:
        name: Branch name
        commit_hash: Latest commit hash
        is_current: Whether this is the currently checked out branch
    """

    name: str = Field(description="Branch name")
    commit_hash: str = Field(description="Latest commit hash")
    is_current: bool = Field(default=False, description="Whether currently checked out")

