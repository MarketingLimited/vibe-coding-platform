from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..dependencies import get_docker_client, get_redis_client

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
