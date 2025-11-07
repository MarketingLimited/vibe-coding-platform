from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config import Settings, get_settings
from ..dependencies import get_http_client, get_project_manager_base_url, get_redis_client
from ..models.projects import ProjectAuth, ProjectCreate, ProjectInfo
from ..services.auth import generate_project_id, verify_master_key
from ..services.project_manager import ProjectManagerClient
from ..services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(
    redis_client=Depends(get_redis_client), settings: Settings = Depends(get_settings)
) -> ProjectService:
    return ProjectService(redis_client, settings)


async def get_project_manager(
    base_url: str = Depends(get_project_manager_base_url),
    http_client=Depends(get_http_client),
) -> ProjectManagerClient:
    return ProjectManagerClient(base_url, http_client)


@router.post("/create", dependencies=[Depends(verify_master_key)])
async def create_project(
    payload: ProjectCreate,
    project_service: ProjectService = Depends(get_project_service),
    project_manager: ProjectManagerClient = Depends(get_project_manager),
) -> Dict[str, Any]:
    project_id = generate_project_id(payload.username, payload.project_name)

    if project_service.project_exists(project_id):
        raise HTTPException(status_code=400, detail="Project already exists")

    if not project_service.can_create_project(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {project_service.settings.max_projects_per_user} projects per user",
        )

    manager_response = await project_manager.create_project(
        {
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
    )

    container_id = manager_response.get("container_id") or ""
    status = manager_response.get("status", "active")
    record = project_service.create_project_record(payload, container_id, status)

    return {
        "project_id": record["project_id"],
        "password": record["password"],
        "container_id": container_id,
        "status": manager_response.get("status", "active"),
        "message": "Save this password! It won't be shown again.",
    }


@router.get("/{username}")
async def list_projects(
    username: str,
    project_service: ProjectService = Depends(get_project_service),
    _: None = Depends(verify_master_key),
) -> Dict[str, Any]:
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
        }
        for project in projects
    ]
    return {"username": username, "projects": sanitized}


@router.post("/info")
async def project_info(
    auth: ProjectAuth,
    project_service: ProjectService = Depends(get_project_service),
    project_manager: ProjectManagerClient = Depends(get_project_manager),
) -> Dict[str, Any]:
    project = project_service.get_project(auth.project_id)
    if not project or not project_service.verify_credentials(auth.project_id, auth.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    status_payload = await project_manager.get_project_status(auth.project_id)
    container_status: Optional[str] = None
    if status_payload:
        container_status = status_payload.get("status")
        project_service.update_container_status(
            auth.project_id,
            status_payload.get("status", project.status),
            status_payload.get("container_id", project.container_id),
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
    }


@router.post("/rotate-password")
async def rotate_password(
    auth: ProjectAuth,
    project_service: ProjectService = Depends(get_project_service),
) -> Dict[str, str]:
    if not project_service.verify_credentials(auth.project_id, auth.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    new_password = project_service.rotate_password(auth.project_id)
    if not new_password:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return {"project_id": auth.project_id, "password": new_password}


@router.delete("/delete")
async def delete_project(
    auth: ProjectAuth,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    project_service: ProjectService = Depends(get_project_service),
    project_manager: ProjectManagerClient = Depends(get_project_manager),
    settings: Settings = Depends(get_settings),
) -> Dict[str, str]:
    master_key = settings.master_api_key or ""
    is_admin = bool(master_key) and x_api_key == master_key
    is_owner = project_service.verify_credentials(auth.project_id, auth.password)

    if not (is_admin or is_owner):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    project = project_service.remove_project(auth.project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await project_manager.delete_project(auth.project_id)

    return {"message": "Project deleted successfully", "project_id": auth.project_id}
