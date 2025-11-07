import logging

from fastapi import Depends, FastAPI, HTTPException

from .config import Settings
from .models import ExecCommand, ProjectRequest
from .services import ProjectManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="Vibe Project Manager", version="2.0.0")


def get_settings() -> Settings:
    return Settings()


def get_manager(settings: Settings = Depends(get_settings)) -> ProjectManager:
    manager = ProjectManager(settings)
    try:
        yield manager
    finally:
        manager.close()


@app.get("/health")
async def health(manager: ProjectManager = Depends(get_manager)) -> dict:
    manager.docker_client.ping()
    return {"status": "healthy"}


@app.post("/internal/projects")
async def create_project(
    request: ProjectRequest,
    manager: ProjectManager = Depends(get_manager),
) -> dict:
    status = manager.create_project(request)
    return status.dict()


@app.get("/internal/projects/{project_id}")
async def project_status(
    project_id: str,
    manager: ProjectManager = Depends(get_manager),
) -> dict:
    status = manager.get_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    return status.dict()


@app.delete("/internal/projects/{project_id}")
async def delete_project(
    project_id: str,
    manager: ProjectManager = Depends(get_manager),
) -> dict:
    status = manager.delete_project(project_id)
    return status.dict()


@app.post("/internal/projects/{project_id}/exec")
async def exec_in_project(
    project_id: str,
    command: ExecCommand,
    manager: ProjectManager = Depends(get_manager),
) -> dict:
    try:
        return manager.exec(project_id, command)
    except Exception as exc:  # pragma: no cover - runtime errors are surfaced
        raise HTTPException(status_code=500, detail=str(exc)) from exc
