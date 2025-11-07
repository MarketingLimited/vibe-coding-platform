from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..dependencies import (
    get_docker_client,
    get_project_manager_client,
    get_project_repository,
    get_redis_client,
)

router = APIRouter()


@router.get("/health", tags=["system"])
async def health(
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
    docker_client=Depends(get_docker_client),
) -> Dict[str, Any]:
    redis_client.ping()
    docker_client.ping()

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis": "connected",
        "docker": "connected",
        "limits": {
            "projects_per_user": settings.max_projects_per_user,
            "exec_timeout": settings.exec_timeout,
            "max_output_size": settings.max_output_size,
        },
    }


@router.get("/health/services", tags=["system"])
async def health_services(
    settings: Settings = Depends(get_settings),
    redis_client=Depends(get_redis_client),
    docker_client=Depends(get_docker_client),
    repository=Depends(get_project_repository),
    project_manager=Depends(get_project_manager_client),
) -> Dict[str, Any]:
    status = "healthy"
    components: Dict[str, Dict[str, Any]] = {}

    try:
        redis_client.ping()
        components["redis"] = {"status": "ok"}
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        components["redis"] = {"status": "error", "detail": str(exc)}
        status = "degraded"

    try:
        repository.ping()
        components["database"] = {"status": "ok", "path": str(settings.db_path)}
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        components["database"] = {"status": "error", "detail": str(exc)}
        status = "degraded"

    try:
        docker_client.ping()
        components["docker"] = {"status": "ok"}
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        components["docker"] = {"status": "error", "detail": str(exc)}
        status = "degraded"

    try:
        manager_status = await project_manager.health()
        components["project_manager"] = {
            "status": manager_status.get("status", "ok"),
            "details": manager_status,
        }
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        components["project_manager"] = {"status": "error", "detail": str(exc)}
        status = "degraded"

    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "limits": {
            "rate_window_seconds": settings.rate_limit_window_seconds,
            "exec_limit_per_minute": settings.exec_rate_limit_per_minute,
            "project_create_limit": settings.project_create_rate_limit,
        },
    }
