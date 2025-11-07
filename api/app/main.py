from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import exec as exec_router
from .routers import health as health_router
from .routers import projects as projects_router
from .utils.logging import configure_logging, set_request_id

configure_logging()

settings = get_settings()

app = FastAPI(
    title="Vibe Coding Central API",
    version="2.0.0",
    description="Multi-tenant development platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(set_request_id)

app.include_router(health_router.router)
app.include_router(projects_router.router)
app.include_router(exec_router.router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "Vibe Coding Central API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "projects": {
                "create": "POST /projects/create",
                "list": "GET /projects/{username}",
                "info": "POST /projects/info",
                "delete": "DELETE /projects/delete",
                "rotate_password": "POST /projects/rotate-password",
            },
            "exec": "POST /exec",
        },
    }


@app.on_event("startup")
async def startup_event() -> None:
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)


@app.get("/metadata")
async def metadata() -> dict:
    return {
        "domain": settings.domain,
        "limits": {
            "projects_per_user": settings.max_projects_per_user,
            "cpu": settings.project_cpu_limit,
            "memory": settings.project_memory_limit,
            "storage": settings.project_storage_limit,
            "exec_timeout": settings.exec_timeout,
            "max_output_size": settings.max_output_size,
        },
    }
