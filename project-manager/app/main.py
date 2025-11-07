import asyncio
import logging
from contextlib import suppress

from fastapi import Depends, FastAPI, HTTPException, Request

from .config import Settings
from .models import ExecCommand, ProjectRequest
from .services import ProjectManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="Vibe Project Manager", version="2.0.0")


async def _monitor_loop(manager: ProjectManager, interval: int) -> None:
    interval = max(10, interval)
    while True:
        try:
            manager.sync_container_states()
        except Exception as exc:  # pragma: no cover - defensive logging only
            logging.getLogger(__name__).warning("Container sync failed", exc_info=exc)
        await asyncio.sleep(interval)


@app.on_event("startup")
async def startup_event() -> None:
    settings = Settings()
    manager = ProjectManager(settings)
    app.state.settings = settings
    app.state.manager = manager
    app.state.monitor_task = asyncio.create_task(
        _monitor_loop(manager, settings.health_poll_interval)
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    monitor_task: asyncio.Task | None = getattr(app.state, "monitor_task", None)
    if monitor_task:
        monitor_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitor_task
    manager: ProjectManager | None = getattr(app.state, "manager", None)
    if manager:
        manager.close()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_manager(request: Request) -> ProjectManager:
    return request.app.state.manager


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
