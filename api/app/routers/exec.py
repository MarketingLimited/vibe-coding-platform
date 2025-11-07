from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings, get_settings
from ..dependencies import get_http_client, get_project_manager_base_url, get_redis_client
from ..models.exec import ExecRequest, ExecResponse
from ..services.execution import ExecutionService
from ..services.project_manager import ProjectManagerClient
from ..services.projects import ProjectService

router = APIRouter(tags=["execution"])


def get_project_service(
    redis_client=Depends(get_redis_client), settings: Settings = Depends(get_settings)
) -> ProjectService:
    return ProjectService(redis_client, settings)


async def get_execution_service(
    settings: Settings = Depends(get_settings),
    base_url: str = Depends(get_project_manager_base_url),
    http_client=Depends(get_http_client),
) -> ExecutionService:
    client = ProjectManagerClient(base_url, http_client)
    return ExecutionService(settings, client)


@router.post("/exec", response_model=ExecResponse)
async def execute_command(
    req: ExecRequest,
    project_service: ProjectService = Depends(get_project_service),
    executor: ExecutionService = Depends(get_execution_service),
) -> ExecResponse:
    if not project_service.verify_credentials(req.project_id, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return await executor.execute(req)
