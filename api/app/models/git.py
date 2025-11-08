"""Pydantic models representing Git operations forwarded to the project manager."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, validator


class _GitBaseRequest(BaseModel):
    project_id: str
    password: str
    cwd: Optional[str] = Field(None, description="Working directory inside the container")
    timeout: Optional[int] = Field(
        None,
        ge=1,
        description="Optional override for the execution timeout in seconds",
    )
    max_output_size: Optional[int] = Field(
        None,
        ge=1024,
        description="Maximum number of bytes to return for stdout/stderr",
    )

    @validator("cwd")
    def _normalise_cwd(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.startswith("/"):
            raise ValueError("cwd must be an absolute path")
        return value


class GitCommitRequest(_GitBaseRequest):
    message: str = Field(..., min_length=1, description="Commit message to use")
    add_all: bool = Field(
        True,
        description="Whether to stage all tracked and untracked files before committing",
    )
    amend: bool = Field(False, description="Amend the previous commit instead of creating a new one")


class GitLogRequest(_GitBaseRequest):
    limit: int = Field(10, ge=1, le=100, description="Maximum number of log entries to return")
    format: Optional[str] = Field(
        None,
        description="Optional pretty format passed to git log --pretty",
    )


class GitResetRequest(_GitBaseRequest):
    commit: str = Field(..., min_length=4, description="Commit hash or reference to reset to")
    hard: bool = Field(
        True,
        description="Perform a hard reset (discarding working tree changes) by default",
    )


class GitCommandResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    returncode: int
    backup_path: Optional[str] = Field(
        None,
        description="Path to the created workspace backup when a modifying command is executed",
    )

