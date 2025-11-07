from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings, get_settings
from ..dependencies import (
    get_project_manager_client,
    get_project_repository,
    get_rate_limiter,
    get_redis_client,
)
from ..models.exec import ExecRequest, ExecResponse
from ..services.execution import ExecutionService
from ..services.rate_limiter import RateLimiter
from ..services.projects import ProjectService

router = APIRouter(tags=["execution"])


def get_project_service(
    redis_client=Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    repository=Depends(get_project_repository),
) -> ProjectService:
    return ProjectService(redis_client, settings, repository)


async def get_execution_service(
    settings: Settings = Depends(get_settings),
    client=Depends(get_project_manager_client),
) -> ExecutionService:
    return ExecutionService(settings, client)


@router.post("/exec", response_model=ExecResponse)
async def execute_command(
    req: ExecRequest,
    project_service: ProjectService = Depends(get_project_service),
    executor: ExecutionService = Depends(get_execution_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> ExecResponse:
    if not project_service.verify_credentials(req.project_id, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rate_limiter.check(
        f"exec:{req.project_id}",
        project_service.settings.exec_rate_limit_per_minute,
    )

    return await executor.execute(req)
