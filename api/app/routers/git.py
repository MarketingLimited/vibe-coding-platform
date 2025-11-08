"""HTTP endpoints for git-related actions within a project workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings, get_settings
from ..dependencies import (
    get_project_manager_client,
    get_project_repository,
    get_rate_limiter,
    get_redis_client,
)
from ..models.git import (
    GitCommandResponse,
    GitCommitRequest,
    GitLogRequest,
    GitResetRequest,
)
from ..services.git import GitService
from ..services.projects import ProjectService
from ..services.rate_limiter import RateLimiter

router = APIRouter(prefix="/git", tags=["git"])


def get_project_service(
    redis_client=Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    repository=Depends(get_project_repository),
) -> ProjectService:
    return ProjectService(redis_client, settings, repository)


async def get_git_service(
    settings: Settings = Depends(get_settings),
    client=Depends(get_project_manager_client),
) -> GitService:
    return GitService(settings, client)


async def _verify_and_rate_limit(
    request_project_id: str,
    request_password: str,
    project_service: ProjectService,
    rate_limiter: RateLimiter,
) -> None:
    if not project_service.verify_credentials(request_project_id, request_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rate_limiter.check(
        f"git:{request_project_id}",
        project_service.settings.exec_rate_limit_per_minute,
    )


@router.post("/commit", response_model=GitCommandResponse)
async def git_commit(
    req: GitCommitRequest,
    project_service: ProjectService = Depends(get_project_service),
    git_service: GitService = Depends(get_git_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> GitCommandResponse:
    await _verify_and_rate_limit(req.project_id, req.password, project_service, rate_limiter)
    return await git_service.commit(req)


@router.post("/log", response_model=GitCommandResponse)
async def git_log(
    req: GitLogRequest,
    project_service: ProjectService = Depends(get_project_service),
    git_service: GitService = Depends(get_git_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> GitCommandResponse:
    await _verify_and_rate_limit(req.project_id, req.password, project_service, rate_limiter)
    return await git_service.log(req)


@router.post("/reset", response_model=GitCommandResponse)
async def git_reset(
    req: GitResetRequest,
    project_service: ProjectService = Depends(get_project_service),
    git_service: GitService = Depends(get_git_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> GitCommandResponse:
    await _verify_and_rate_limit(req.project_id, req.password, project_service, rate_limiter)
    return await git_service.reset(req)

