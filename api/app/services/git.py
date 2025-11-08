"""Service layer for proxying Git operations to the project manager."""

from __future__ import annotations

from typing import Any, Dict

from ..config import Settings
from ..models.git import (
    GitCommandResponse,
    GitCommitRequest,
    GitLogRequest,
    GitResetRequest,
)
from .project_manager import ProjectManagerClient


class GitService:
    """Forward Git operations to the project manager with platform defaults."""

    def __init__(self, settings: Settings, client: ProjectManagerClient):
        self.settings = settings
        self.client = client

    def _payload(self, request: Any, extras: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "cwd": request.cwd or "/workspace",
            "timeout": min(
                request.timeout or self.settings.exec_timeout,
                self.settings.exec_timeout,
            ),
            "max_output_size": request.max_output_size or self.settings.max_output_size,
        }
        if extras:
            payload.update(extras)
        return payload

    async def commit(self, request: GitCommitRequest) -> GitCommandResponse:
        payload = self._payload(
            request,
            {
                "message": request.message,
                "add_all": request.add_all,
                "amend": request.amend,
            },
        )
        result = await self.client.git_commit(request.project_id, payload)
        return GitCommandResponse(**result)

    async def log(self, request: GitLogRequest) -> GitCommandResponse:
        payload = self._payload(
            request,
            {
                "limit": request.limit,
                "format": request.format,
            },
        )
        result = await self.client.git_log(request.project_id, payload)
        return GitCommandResponse(**result)

    async def reset(self, request: GitResetRequest) -> GitCommandResponse:
        payload = self._payload(
            request,
            {
                "commit": request.commit,
                "hard": request.hard,
            },
        )
        result = await self.client.git_reset(request.project_id, payload)
        return GitCommandResponse(**result)

