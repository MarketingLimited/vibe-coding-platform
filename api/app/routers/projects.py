import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config import Settings, get_settings
from ..dependencies import (
    get_project_manager_client,
    get_project_repository,
    get_rate_limiter,
    get_redis_client,
    get_secret_storage,
)
from ..models.projects import ProjectAuth, ProjectCreate
from ..services.auth import generate_project_id, verify_master_key
from ..services.projects import ProjectService
from ..services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    redis_client=Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
    repository=Depends(get_project_repository),
    secret_storage=Depends(get_secret_storage),
) -> ProjectService:
    return ProjectService(redis_client, settings, repository, secret_storage)


@router.post("/create", dependencies=[Depends(verify_master_key)])
async def create_project(
    payload: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    project_manager=Depends(get_project_manager_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    project_id = generate_project_id(payload.username, payload.project_name)

    if project_service.project_exists(project_id):
        raise HTTPException(status_code=400, detail="Project already exists")

    rate_limiter.check(
        f"projects:create:{payload.username}",
        project_service.settings.project_create_rate_limit,
    )

    if not project_service.can_create_project(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {project_service.settings.max_projects_per_user} projects per user",
        )

    manager_payload = {
        "project_id": project_id,
        "project_type": payload.project_type,
        "database": payload.database,
        "redis": payload.redis,
        "username": payload.username,
        "limits": {
            "cpu": project_service.settings.project_cpu_limit,
            "memory": project_service.settings.project_memory_limit,
            "storage": project_service.settings.project_storage_limit,
        },
    }
    if payload.project_template:
        manager_payload["template"] = payload.project_template

    manager_response = await project_manager.create_project(manager_payload)

    container_id = manager_response.get("container_id") or ""
    status = manager_response.get("status", "active")
    info_block = manager_response.get("info") or {}
    preview_url = None
    if isinstance(info_block, dict):
        preview_url = info_block.get("preview_url")

    record = project_service.create_project_record(payload, container_id, status, preview_url)

    secret_payload = {
        "username": payload.username,
        "github_api_key": payload.github_api_key,
        "additional_secrets": payload.additional_secrets,
    }
    try:
        await project_manager.sync_project_secrets(project_id, secret_payload)
    except Exception as exc:
        logger.exception(
            "Failed to sync project secrets", extra={"project_id": project_id, "error": str(exc)}
        )
        project_service.remove_project(project_id)
        try:
            await project_manager.delete_project(project_id)
        except Exception:  # pragma: no cover - best effort rollback
            logger.warning(
                "Rollback delete failed after secret sync error", extra={"project_id": project_id}
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to synchronise project secrets. Please retry.",
        ) from exc

    return {
        "project_id": record["project_id"],
        "password": record["password"],
        "container_id": container_id,
        "status": manager_response.get("status", "active"),
        "preview_url": preview_url,
        "message": "Save this password! It won't be shown again.",
    }


@router.get("/{username}")
async def list_projects(
    username: str,
    project_service: ProjectService = Depends(get_project_service),
    _: None = Depends(verify_master_key),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    rate_limiter.check(
        f"projects:list:{username}",
        project_service.settings.rate_limit_per_minute,
    )
    projects = project_service.list_user_projects(username)
    sanitized = [
        {
            "project_id": project.project_id,
            "username": project.username,
            "project_name": project.project_name,
            "project_type": project.project_type,
            "created_at": project.created_at.isoformat(),
            "status": project.status,
            "container_id": project.container_id,
            "database": project.database,
            "redis": project.redis,
            "preview_url": project.preview_url,
        }
        for project in projects
    ]
    return {"username": username, "projects": sanitized}


@router.post("/info")
async def project_info(
    auth: ProjectAuth,
    project_service: ProjectService = Depends(get_project_service),
    project_manager=Depends(get_project_manager_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, Any]:
    project = project_service.get_project(auth.project_id)
    if not project or not project_service.verify_credentials(auth.project_id, auth.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    rate_limiter.check(
        f"projects:info:{auth.project_id}",
        project_service.settings.project_info_rate_limit,
    )

    status_payload = await project_manager.get_project_status(auth.project_id)
    container_status: Optional[str] = None
    preview_url = project.preview_url
    if status_payload:
        container_status = status_payload.get("status")
        info_block = status_payload.get("info") if isinstance(status_payload, dict) else None
        if isinstance(info_block, dict):
            preview_url = info_block.get("preview_url") or preview_url
        project_service.update_container_status(
            auth.project_id,
            status_payload.get("status", project.status),
            status_payload.get("container_id", project.container_id),
            preview_url,
        )

    return {
        "project_id": project.project_id,
        "username": project.username,
        "project_name": project.project_name,
        "project_type": project.project_type,
        "created_at": project.created_at.isoformat(),
        "status": container_status or project.status,
        "container_id": project.container_id,
        "database": project.database,
        "redis": project.redis,
        "preview_url": preview_url,
    }


@router.post("/rotate-password")
async def rotate_password(
    auth: ProjectAuth,
    project_service: ProjectService = Depends(get_project_service),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> Dict[str, str]:
    if not project_service.verify_credentials(auth.project_id, auth.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    rate_limiter.check(
        f"projects:rotate:{auth.project_id}",
        project_service.settings.password_rotate_rate_limit,
    )

    new_password = project_service.rotate_password(auth.project_id)
    if not new_password:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {"project_id": auth.project_id, "password": new_password}


@router.delete("/delete")
async def delete_project(
    auth: ProjectAuth,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    project_service: ProjectService = Depends(get_project_service),
    project_manager=Depends(get_project_manager_client),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> Dict[str, str]:
    master_key = settings.master_api_key or ""
    is_admin = bool(master_key) and x_api_key == master_key
    is_owner = project_service.verify_credentials(auth.project_id, auth.password)

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    rate_limiter.check(
        f"projects:delete:{auth.project_id}",
        project_service.settings.project_delete_rate_limit,
    )

    project = project_service.remove_project(auth.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await project_manager.delete_project(auth.project_id)

    return {"message": "Project deleted successfully", "project_id": auth.project_id}
