import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import get_settings
from .routers import exec as exec_router
from .routers import health as health_router
from .routers import git as git_router
from .routers import projects as projects_router
from .utils.logging import configure_audit_logging, configure_logging, get_audit_logger, set_request_id

settings = get_settings()

configure_logging(settings.logs_dir)
configure_audit_logging(settings.logs_dir)

app = FastAPI(
    title="Vibe Coding Central API",
    version="2.0.0",
    description="Multi-tenant development platform",
)

# Configure CORS with specific allowed origins for security
# If no allowed origins are specified, CORS is disabled
allowed_origins = []
if settings.allowed_origins:
    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
        max_age=3600,
    )

app.middleware("http")(set_request_id)


@app.middleware("http")
async def audit_requests(request: Request, call_next):  # pragma: no cover - integration behaviour
    audit_logger = get_audit_logger()
    status_code = 500
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        audit_logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            status_code,
            elapsed_ms,
        )

app.include_router(health_router.router)
app.include_router(projects_router.router)
app.include_router(exec_router.router)
app.include_router(git_router.router)

Instrumentator().instrument(app).expose(app, include_in_schema=False)


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
            "git": {
                "commit": "POST /git/commit",
                "log": "POST /git/log",
                "reset": "POST /git/reset",
            },
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
