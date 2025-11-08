"""Dependency helpers shared across FastAPI routers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator, Generator

import docker
import httpx
import redis
try:  # pragma: no cover - fallback for optional dependency in tests
    import requests_unixsocket
except ModuleNotFoundError:  # pragma: no cover - fallback for optional dependency in tests
    requests_unixsocket = None  # type: ignore[assignment]
from fastapi import Depends

from .config import Settings, get_settings
from .services.project_manager import ProjectManagerClient
from .services.rate_limiter import RateLimiter
from .services.repository import ProjectRepository
from .services.secrets import SecretStorage

logger = logging.getLogger(__name__)

_project_repository: ProjectRepository | None = None
_secret_storage: SecretStorage | None = None
_docker_requests_monkeypatched = False


def _ensure_docker_requests_adapter() -> None:
    """Register the http+docker transport so docker.from_env can connect."""

    global _docker_requests_monkeypatched
    if _docker_requests_monkeypatched:
        return

    if requests_unixsocket is None:  # pragma: no cover - only during partial installations
        logger.debug("requests-unixsocket is not installed; Docker socket support disabled")
        _docker_requests_monkeypatched = True
        return

    requests_unixsocket.monkeypatch()
    _docker_requests_monkeypatched = True


def get_project_repository(settings: Settings = Depends(get_settings)) -> ProjectRepository:
    """Return a singleton SQLite-backed repository for project metadata."""

    global _project_repository
    if _project_repository is None:
        db_path = Path(settings.db_path)
        logger.info("Initialising project repository", extra={"db_path": str(db_path)})
        _project_repository = ProjectRepository(db_path)
    return _project_repository


def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def get_docker_client() -> Generator[docker.DockerClient, None, None]:
    _ensure_docker_requests_adapter()
    client = docker.from_env()
    try:
        yield client
    finally:
        client.close()


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client


def get_project_manager_base_url(settings: Settings = Depends(get_settings)) -> str:
    return settings.project_manager_base_url


async def get_project_manager_client(
    base_url: str = Depends(get_project_manager_base_url),
    http_client=Depends(get_http_client),
) -> ProjectManagerClient:
    return ProjectManagerClient(base_url, http_client)


def get_rate_limiter(
    redis_client=Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> RateLimiter:
    return RateLimiter(
        redis_client,
        window_seconds=settings.rate_limit_window_seconds,
        enabled=settings.enable_rate_limit,
    )


def get_secret_storage(settings: Settings = Depends(get_settings)) -> SecretStorage:
    """Return the encrypted secrets storage singleton."""

    global _secret_storage
    if _secret_storage is None:
        if not settings.github_secrets_key:
            raise RuntimeError("GITHUB_SECRETS_KEY is not configured")

        logger.info(
            "Initialising encrypted secrets storage",
            extra={"path": str(settings.github_secrets_path)},
        )
        _secret_storage = SecretStorage(
            settings.github_secrets_path, settings.github_secrets_key
        )
    return _secret_storage
